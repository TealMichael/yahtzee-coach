-- Yahtzee Coach v44.0: additive six-puzzle Daily migration.
-- Run BEFORE uploading the app. No old rows are regenerated or deleted.
-- The first updated-app Daily load schedules the switch for next midnight ET.
-- Re-running this file does not change that date. Do not rerun the baseline schema.
begin;

create table if not exists public.yc_daily_format_config (
    singleton boolean primary key default true check (singleton),
    six_effective_date date,
    activated_at timestamptz
);
insert into public.yc_daily_format_config(singleton) values(true) on conflict do nothing;
alter table public.yc_daily_format_config enable row level security;
revoke all on public.yc_daily_format_config from public, anon, authenticated, service_role;

-- Only replace the old length check; retain every other historical constraint.
do $$ declare c record; begin
    for c in select conname from pg_constraint
        where conrelid='public.daily_challenges'::regclass and contype='c'
          and pg_get_constraintdef(oid) like '%jsonb_array_length(puzzle_ids)%'
    loop execute format('alter table public.daily_challenges drop constraint %I',c.conname); end loop;
end $$;
alter table public.daily_challenges add constraint daily_challenges_puzzle_ids_check
    check (jsonb_typeof(puzzle_ids)='array' and jsonb_array_length(puzzle_ids) in (6,10));

create or replace function public.yc_daily_format(p_day date)
returns jsonb language plpgsql security definer set search_path=pg_catalog,public as $$
declare effective date; registered public.daily_challenges%rowtype;
begin
    if p_day is null then raise exception 'Daily date is required'; end if;
    select six_effective_date into effective from public.yc_daily_format_config
        where singleton for update;
    if effective is null then
        effective := (clock_timestamp() at time zone 'America/New_York')::date + 1;
        update public.yc_daily_format_config set six_effective_date=effective,
            activated_at=clock_timestamp() where singleton;
    end if;
    select * into registered from public.daily_challenges where challenge_date=p_day
        order by created_at desc, challenge_id desc limit 1;
    if found then
        return jsonb_build_object('question_count',jsonb_array_length(registered.puzzle_ids),
            'challenge_id',registered.challenge_id,'challenge_version',registered.challenge_version,
            'puzzle_ids',registered.puzzle_ids,'six_effective_date',effective);
    end if;
    return jsonb_build_object('question_count',case when p_day>=effective then 6 else 10 end,
        'six_effective_date',effective);
end $$;
revoke all on function public.yc_daily_format(date) from public,anon,authenticated;
grant execute on function public.yc_daily_format(date) to service_role;

create or replace function public.yc_guard_daily_format()
returns trigger language plpgsql security definer set search_path=pg_catalog,public as $$
declare effective date; expected integer;
begin
    if tg_op='UPDATE' then
        if new is distinct from old then raise exception 'Registered Daily challenges are immutable'; end if;
        return new;
    end if;
    select six_effective_date into effective from public.yc_daily_format_config where singleton for update;
    if exists(select 1 from public.daily_challenges where challenge_date=new.challenge_date) then
        raise exception 'Daily date unique constraint: already registered' using errcode='23505';
    end if;
    expected := case when effective is not null and new.challenge_date>=effective then 6 else 10 end;
    if jsonb_array_length(new.puzzle_ids)<>expected
        or (expected=6 and new.challenge_version<>'43B-bank42.6-six-v1')
        or (expected=10 and new.challenge_version='43B-bank42.6-six-v1') then
        raise exception 'Daily format changed; reload the updated app';
    end if;
    if (select count(distinct value) from jsonb_array_elements_text(new.puzzle_ids))<>expected then
        raise exception 'Daily puzzle IDs must be unique';
    end if;
    return new;
end $$;
revoke all on function public.yc_guard_daily_format() from public,anon,authenticated,service_role;
drop trigger if exists yc_daily_format_guard on public.daily_challenges;
create trigger yc_daily_format_guard before insert or update on public.daily_challenges
    for each row execute function public.yc_guard_daily_format();

-- Existing answer triggers already compare the slot to the registered puzzle
-- array, so slot seven is rejected on a six-day. The 1..10 outer checks remain
-- necessary for historical ten-day answers; do not replace them with 1..6.
create or replace function public.yc_guard_daily_completion()
returns trigger language plpgsql security definer set search_path=pg_catalog,public as $$
declare expected integer; saved integer; actual_exact integer; loss double precision;
    worst double precision; streak integer:=0; best integer:=0; a record; q integer:=0;
begin
    if new.attempt_id<>old.attempt_id or new.player_id<>old.player_id
       or new.challenge_id<>old.challenge_id or new.started_at<>old.started_at then
        raise exception 'Daily attempt identity cannot be changed';
    end if;
    if old.completed_at is not null then
        if new is distinct from old then raise exception 'Completed Daily attempts are immutable'; end if;
        return new;
    end if;
    if new.completed_at is null then return new; end if;
    select jsonb_array_length(puzzle_ids) into expected from public.daily_challenges
        where challenge_id=new.challenge_id;
    select count(*),count(*) filter(where exact),sum(points_lost),max(points_lost)
        into saved,actual_exact,loss,worst from public.daily_answers where attempt_id=new.attempt_id;
    if saved<>expected then raise exception 'Save all Daily answers before completing'; end if;
    for a in select question_number,exact from public.daily_answers
        where attempt_id=new.attempt_id order by question_number loop
        q:=q+1;
        if a.question_number<>q then raise exception 'Daily answer sequence is incomplete'; end if;
        if a.exact then streak:=streak+1; else streak:=0; end if;
        best:=greatest(best,streak);
    end loop;
    if new.exact_count is distinct from actual_exact or new.best_exact_streak is distinct from best
       or new.total_ev_loss is null or abs(new.total_ev_loss-loss)>0.000001
       or new.worst_miss is null or abs(new.worst_miss-worst)>0.000001 then
        raise exception 'Daily summary does not match saved answers';
    end if;
    return new;
end $$;
revoke all on function public.yc_guard_daily_completion() from public,anon,authenticated,service_role;
drop trigger if exists yc_daily_completion_guard on public.daily_attempts;
create trigger yc_daily_completion_guard before update on public.daily_attempts
    for each row execute function public.yc_guard_daily_completion();
commit;
