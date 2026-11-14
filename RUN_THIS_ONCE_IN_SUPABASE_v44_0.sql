-- Yahtzee Coach v44.0 — Weekly + Daily Six, existing v43B upgrade only.
-- Run in your existing YAHTZEE Supabase project's SQL Editor before uploading code.
-- This combines the two tested additive migrations. Do not run classroom SQL.
-- No player, group, result, or puzzle history is deleted or regenerated.


-- v43b_weekly_v1_migration.sql
-- Yahtzee Coach: Weekly v1. Additive; safe to rerun without resetting games.
-- Requires the existing v43B players, player_sessions and friend-group tables.
-- Run as the database owner in Supabase SQL Editor, not from a browser client.
begin;

create table if not exists public.yc_weekly_challenges (
    week_id date primary key check (extract(isodow from week_id) = 1),
    starts_at timestamptz not null,
    ends_at timestamptz not null check (ends_at > starts_at),
    rules_version text not null,
    dice_version text not null,
    commitment text not null check (commitment ~ '^[a-f0-9]{64}$'),
    private_schedule jsonb not null check (jsonb_typeof(private_schedule) = 'object'),
    created_at timestamptz not null default clock_timestamp()
);

create table if not exists public.yc_weekly_games (
    game_id uuid primary key default gen_random_uuid(),
    player_id uuid not null references public.players(player_id) on delete cascade,
    week_id date not null references public.yc_weekly_challenges(week_id) on delete restrict,
    mode text not null check (mode in ('official', 'practice')),
    state jsonb not null check (jsonb_typeof(state) = 'object'),
    revision bigint not null default 0 check (revision >= 0),
    total_score integer not null default 0 check (total_score between 0 and 1575),
    started_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    completed_at timestamptz,
    start_request_id uuid not null,
    last_request_id uuid,
    last_request jsonb,
    unique(player_id, week_id, mode),
    check ((last_request_id is null) = (last_request is null)),
    check ((state ->> 'revision')::bigint = revision),
    check (state ->> 'mode' = mode),
    check (state ->> 'week_id' = week_id::text),
    check ((completed_at is not null) = (jsonb_array_length(state -> 'rounds') = 13))
);

-- One working replay, plus one latest-completed snapshot and a best-score scalar.
-- No unbounded per-replay or per-hold history is accumulated.
create table if not exists public.yc_weekly_replay_summaries (
    player_id uuid not null references public.players(player_id) on delete cascade,
    week_id date not null references public.yc_weekly_challenges(week_id) on delete restrict,
    best_score integer not null check (best_score between 0 and 1575),
    latest_score integer not null check (latest_score between 0 and 1575),
    completed_count bigint not null check (completed_count > 0),
    latest_state jsonb not null,
    latest_completed_at timestamptz not null,
    primary key (player_id, week_id)
);

create index if not exists yc_weekly_completed_board_idx
    on public.yc_weekly_games(week_id, total_score desc)
    where mode = 'official' and completed_at is not null;
create index if not exists yc_weekly_player_history_idx
    on public.yc_weekly_games(player_id, week_id desc) where mode = 'official';

alter table public.yc_weekly_challenges enable row level security;
alter table public.yc_weekly_games enable row level security;
alter table public.yc_weekly_replay_summaries enable row level security;
-- Even the app's backend key uses the narrow RPC; it cannot edit these tables.
revoke all on public.yc_weekly_challenges, public.yc_weekly_games,
    public.yc_weekly_replay_summaries from public, anon, authenticated, service_role;

create or replace function public.yc_weekly_actor(
    p_session_id uuid, p_token_hash text, p_player_id uuid
) returns uuid language plpgsql security definer set search_path = pg_catalog, public, pg_temp
as $$
declare s public.player_sessions%rowtype;
begin
    if p_session_id is null or p_player_id is null or p_token_hash is null then
        raise exception 'WEEKLY_AUTH_REQUIRED';
    end if;
    -- Match the existing PIN-reset lock order: player first, then session.
    -- A reset/revoke either precedes this operation or waits for its commit.
    perform 1 from public.players where player_id = p_player_id for share;
    if not found then raise exception 'WEEKLY_AUTH_REQUIRED'; end if;
    select * into s from public.player_sessions where session_id = p_session_id for share;
    if not found or s.player_id <> p_player_id or s.token_hash <> p_token_hash
       or s.revoked_at is not null
       or (s.expires_at is not null and s.expires_at <= clock_timestamp()) then
        raise exception 'WEEKLY_AUTH_REQUIRED';
    end if;
    return s.player_id;
end;
$$;

create or replace function public.yc_weekly_public_game(g public.yc_weekly_games)
returns jsonb language sql stable security definer set search_path = pg_catalog, public, pg_temp
as $$
    select jsonb_build_object('game_id', g.game_id, 'week_id', g.week_id,
        'mode', g.mode, 'state', g.state, 'revision', g.revision,
        'total_score', g.total_score, 'started_at', g.started_at,
        'updated_at', g.updated_at, 'completed_at', g.completed_at);
$$;

create or replace function public.yc_weekly_initial(c public.yc_weekly_challenges, p_mode text)
returns jsonb language sql stable security definer set search_path = pg_catalog, public, pg_temp
as $$
    select jsonb_build_object('state_version', 1, 'week_id', c.week_id::text,
        'rules_version', c.rules_version, 'dice_version', c.dice_version,
        'schedule_commitment', c.commitment, 'mode', p_mode,
        'scores', '[null,null,null,null,null,null,null,null,null,null,null,null,null]'::jsonb,
        'held', '[]'::jsonb, 'revision', 0, 'rounds', '[]'::jsonb,
        'rolls', jsonb_build_array(jsonb_build_object('held_before', '[]'::jsonb,
            'dice', (select jsonb_agg(value order by value)
                from jsonb_array_elements(c.private_schedule #> '{pools,0,0}')))));
$$;

create or replace function public.yc_weekly_state_total(p_state jsonb)
returns integer language plpgsql immutable security definer set search_path = pg_catalog, public, pg_temp
as $$
declare v jsonb; r jsonb; n integer; i integer := 0; upper_sum integer := 0;
        subtotal integer := 0; extra integer := 0;
begin
    if jsonb_typeof(p_state -> 'scores') is distinct from 'array'
       or jsonb_array_length(p_state -> 'scores') <> 13
       or jsonb_typeof(p_state -> 'rounds') is distinct from 'array'
       or jsonb_array_length(p_state -> 'rounds') > 13 then
        raise exception 'WEEKLY_INVALID_STATE';
    end if;
    for v in select value from jsonb_array_elements(p_state -> 'scores') loop
        if v = 'null'::jsonb then n := 0;
        else
            if jsonb_typeof(v) <> 'number' or v::text !~ '^[0-9]+$' then
                raise exception 'WEEKLY_INVALID_STATE';
            end if;
            n := v::text::integer;
            if n > 50 then raise exception 'WEEKLY_INVALID_STATE'; end if;
        end if;
        subtotal := subtotal + n;
        if i < 6 then upper_sum := upper_sum + n; end if;
        i := i + 1;
    end loop;
    for r in select value from jsonb_array_elements(p_state -> 'rounds') loop
        if (r -> 'yahtzee_bonus') is null or r -> 'yahtzee_bonus' not in ('0'::jsonb, '100'::jsonb) then
            raise exception 'WEEKLY_INVALID_STATE';
        end if;
        extra := extra + (r ->> 'yahtzee_bonus')::integer;
    end loop;
    if extra > 1200 or (extra > 0 and p_state #>> '{scores,11}' is distinct from '50') then
        raise exception 'WEEKLY_INVALID_STATE';
    end if;
    return subtotal + extra + case when upper_sum >= 63 then 35 else 0 end;
end;
$$;

create or replace function public.yc_weekly_guard_game_update()
returns trigger language plpgsql security definer set search_path = pg_catalog, public, pg_temp
as $$
declare c public.yc_weekly_challenges%rowtype;
begin
    if tg_op = 'INSERT' then
        if new.mode = 'official' then
            select * into c from public.yc_weekly_challenges where week_id = new.week_id;
            if clock_timestamp() < c.starts_at or clock_timestamp() >= c.ends_at then
                raise exception 'WEEKLY_EXPIRED';
            end if;
        end if;
        return new;
    end if;
    if old.completed_at is not null then raise exception 'WEEKLY_GAME_LOCKED'; end if;
    if (new.game_id, new.player_id, new.week_id, new.mode, new.started_at, new.start_request_id)
        is distinct from (old.game_id, old.player_id, old.week_id, old.mode, old.started_at, old.start_request_id)
       or new.revision <> old.revision + 1 then raise exception 'WEEKLY_INVALID_STATE'; end if;
    if old.mode = 'official' then
        select * into c from public.yc_weekly_challenges where week_id = old.week_id;
        if clock_timestamp() < c.starts_at or clock_timestamp() >= c.ends_at then
            raise exception 'WEEKLY_EXPIRED';
        end if;
    end if;
    return new;
end;
$$;
drop trigger if exists yc_weekly_game_update_guard on public.yc_weekly_games;
create trigger yc_weekly_game_update_guard before update on public.yc_weekly_games
    for each row execute function public.yc_weekly_guard_game_update();
-- AFTER INSERT catches a cutoff crossed while waiting for uniqueness/row locks.
drop trigger if exists yc_weekly_game_insert_guard on public.yc_weekly_games;
create trigger yc_weekly_game_insert_guard after insert on public.yc_weekly_games
    for each row execute function public.yc_weekly_guard_game_update();

create or replace function public.yc_weekly_board(p_actor uuid, p_week date, p_group uuid)
returns jsonb language plpgsql security definer set search_path = pg_catalog, public, pg_temp
as $$
declare group_name text; finished bigint; unlocked boolean; board jsonb := '[]'::jsonb;
begin
    select fg.group_name into group_name from public.friend_groups fg
        join public.group_members gm on gm.group_id = fg.group_id
        where fg.group_id = p_group and gm.player_id = p_actor for share of gm;
    if not found then raise exception 'WEEKLY_ACCESS_DENIED'; end if;
    select exists(select 1 from public.yc_weekly_games where player_id = p_actor
        and week_id = p_week and mode = 'official' and completed_at is not null) into unlocked;
    select count(*) into finished from public.yc_weekly_games g
        join public.group_members gm on gm.player_id = g.player_id and gm.group_id = p_group
        where g.week_id = p_week and g.mode = 'official' and g.completed_at is not null
        and g.player_id <> p_actor;
    if unlocked then
        -- Rank only by score. Names sort ties for display without breaking the tie.
        select coalesce(jsonb_agg(to_jsonb(b) order by b.rank, lower(b.display_name), b.player_id), '[]'::jsonb)
        into board from (
            select rank() over(order by g.total_score desc) as rank,
                p.player_id, p.display_name, g.total_score as score
            from public.yc_weekly_games g
            join public.group_members gm on gm.player_id = g.player_id and gm.group_id = p_group
            join public.players p on p.player_id = g.player_id
            where g.week_id = p_week and g.mode = 'official' and g.completed_at is not null
        ) b;
    end if;
    return jsonb_build_object('group_id', p_group, 'group_name', group_name,
        'completed_friends', finished, 'unlocked', unlocked, 'standings', board);
end;
$$;

create or replace function public.yc_weekly_rpc(
    p_session_id uuid, p_token_hash text, p_player_id uuid,
    p_operation text, p_payload jsonb default '{}'::jsonb
) returns jsonb language plpgsql security definer set search_path = pg_catalog, public, pg_temp
as $$
declare actor uuid; wk date; c public.yc_weekly_challenges%rowtype;
    g public.yc_weekly_games%rowtype; official public.yc_weekly_games%rowtype;
    replay public.yc_weekly_games%rowtype; snapshot jsonb; pools jsonb; round_pool jsonb; pool jsonb; face jsonb;
    next_state jsonb; receipt jsonb; req_id uuid; expected bigint; kind text;
    old_rounds integer; new_rounds integer; old_rolls integer; new_rolls integer;
    total integer; done boolean; response jsonb; boards jsonb; history jsonb;
    opened timestamptz; closes timestamptz; new_mode text; page_size integer;
begin
    actor := public.yc_weekly_actor(p_session_id, p_token_hash, p_player_id);
    if jsonb_typeof(p_payload) is distinct from 'object' then raise exception 'WEEKLY_INVALID_REQUEST'; end if;
    if p_operation = 'history' then
        page_size := least(100, greatest(1, coalesce((p_payload ->> 'limit')::integer, 52)));
        select coalesce(jsonb_agg(to_jsonb(h) order by h.week_id desc), '[]'::jsonb) into history
        from (select week_id, completed_at, total_score from public.yc_weekly_games
            where player_id = actor and mode = 'official'
            and (p_payload ->> 'before_week' is null or week_id < (p_payload ->> 'before_week')::date)
            order by week_id desc limit page_size) h;
        return jsonb_build_object('weeks', history);
    end if;

    if p_operation in ('context', 'commit') then
        select * into g from public.yc_weekly_games
            where game_id = (p_payload ->> 'game_id')::uuid and player_id = actor for update;
        if not found then raise exception 'WEEKLY_GAME_NOT_FOUND'; end if;
        wk := g.week_id;
    else
        wk := (p_payload ->> 'week_id')::date;
        if wk is null or extract(isodow from wk) <> 1 then raise exception 'WEEKLY_INVALID_WEEK'; end if;
    end if;
    opened := wk::timestamp at time zone 'America/New_York';
    closes := (wk + 7)::timestamp at time zone 'America/New_York';
    select * into c from public.yc_weekly_challenges where week_id = wk;

    if p_operation = 'standings' then
        return public.yc_weekly_board(actor, wk, (p_payload ->> 'group_id')::uuid);
    elsif p_operation = 'dashboard' then
        select * into official from public.yc_weekly_games where player_id = actor and week_id = wk and mode = 'official';
        if official.completed_at is not null then
            select * into replay from public.yc_weekly_games where player_id = actor and week_id = wk and mode = 'practice';
            select jsonb_build_object('best_score', best_score, 'latest_score', latest_score,
                'completed_count', completed_count, 'latest_completed_at', latest_completed_at,
                'latest_state', latest_state) into snapshot from public.yc_weekly_replay_summaries
                where player_id = actor and week_id = wk;
        end if;
        select coalesce(jsonb_agg(public.yc_weekly_board(actor, wk, gm.group_id) order by gm.group_id), '[]'::jsonb)
            into boards from public.group_members gm where gm.player_id = actor;
        return jsonb_build_object('week_id', wk, 'starts_at', coalesce(c.starts_at, opened), 'ends_at', coalesce(c.ends_at, closes),
            'server_now', clock_timestamp(), 'official', case when official.game_id is not null then public.yc_weekly_public_game(official) end,
            'replay', case when replay.game_id is not null then public.yc_weekly_public_game(replay) end,
            'replay_summary', snapshot, 'groups', boards);
    elsif p_operation in ('start', 'replay') then
        req_id := (p_payload ->> 'request_id')::uuid;
        if req_id is null then raise exception 'WEEKLY_INVALID_REQUEST'; end if;
        -- Serializes concurrent starts/replay resets across app processes.
        perform pg_advisory_xact_lock(hashtextextended('yc-weekly|' || actor::text || '|' || wk::text, 0));
        new_mode := case when p_operation = 'start' then 'official' else 'practice' end;
        select * into g from public.yc_weekly_games where player_id = actor and week_id = wk and mode = new_mode for update;
        if p_operation = 'start' and g.game_id is not null then return public.yc_weekly_public_game(g); end if;
        if p_operation = 'replay' then
            if not exists(select 1 from public.yc_weekly_games where player_id = actor and week_id = wk
                and mode = 'official' and completed_at is not null) then raise exception 'WEEKLY_REPLAY_LOCKED'; end if;
            if g.game_id is not null and g.start_request_id = req_id then
                return public.yc_weekly_public_game(g);
            end if;
            -- A delayed old restart must not create a new replay after a newer
            -- replay has finished. One comparison token bounds receipt storage.
            if not (p_payload ? 'expected_replay_id') or g.game_id is distinct from
                (p_payload ->> 'expected_replay_id')::uuid then raise exception 'WEEKLY_STALE_STATE'; end if;
            if g.game_id is not null and g.completed_at is null then
                return public.yc_weekly_public_game(g);
            end if;
            if c.week_id is null then raise exception 'WEEKLY_GAME_NOT_FOUND'; end if;
        else
            if clock_timestamp() < opened or clock_timestamp() >= closes then raise exception 'WEEKLY_EXPIRED'; end if;
            if c.week_id is null then
                snapshot := p_payload -> 'schedule';
                if snapshot ->> 'week_id' is distinct from wk::text
                   or snapshot ->> 'rules_version' is distinct from 'classic-yahtzee-v1'
                   or snapshot ->> 'dice_version' is distinct from 'hmac-sha256-pools-v1'
                   or coalesce(p_payload ->> 'commitment', '') !~ '^[a-f0-9]{64}$'
                   or jsonb_typeof(snapshot -> 'pools') is distinct from 'array'
                   or jsonb_array_length(snapshot -> 'pools') <> 13 then raise exception 'WEEKLY_INVALID_SCHEDULE'; end if;
                for round_pool in select value from jsonb_array_elements(snapshot -> 'pools') loop
                    if jsonb_typeof(round_pool) <> 'array' or jsonb_array_length(round_pool) <> 3 then
                        raise exception 'WEEKLY_INVALID_SCHEDULE'; end if;
                    for pool in select value from jsonb_array_elements(round_pool) loop
                        if jsonb_typeof(pool) <> 'array' or jsonb_array_length(pool) <> 5 then
                            raise exception 'WEEKLY_INVALID_SCHEDULE'; end if;
                        for face in select value from jsonb_array_elements(pool) loop
                            if jsonb_typeof(face) <> 'number' or face::text !~ '^[1-6]$' then
                                raise exception 'WEEKLY_INVALID_SCHEDULE'; end if;
                        end loop;
                    end loop;
                end loop;
                insert into public.yc_weekly_challenges(week_id, starts_at, ends_at, rules_version, dice_version, commitment, private_schedule)
                    values(wk, opened, closes, snapshot ->> 'rules_version', snapshot ->> 'dice_version', p_payload ->> 'commitment', snapshot)
                    on conflict(week_id) do nothing;
                select * into c from public.yc_weekly_challenges where week_id = wk;
            end if;
        end if;
        if c.rules_version <> 'classic-yahtzee-v1' or c.dice_version <> 'hmac-sha256-pools-v1' then
            raise exception 'WEEKLY_UNSUPPORTED_VERSION'; end if;
        if p_operation = 'replay' then
            delete from public.yc_weekly_games where player_id = actor and week_id = wk and mode = 'practice';
        end if;
        insert into public.yc_weekly_games(player_id, week_id, mode, state, start_request_id)
            values(actor, wk, new_mode, public.yc_weekly_initial(c, new_mode), req_id) returning * into g;
        return public.yc_weekly_public_game(g);
    elsif p_operation = 'context' then
        -- Trusted server only: never forward this response to a browser/component.
        return jsonb_build_object('game', public.yc_weekly_public_game(g), 'schedule', c.private_schedule,
            'server_now', clock_timestamp(), 'last_request_id', g.last_request_id, 'last_request', g.last_request);
    elsif p_operation = 'commit' then
        req_id := (p_payload ->> 'request_id')::uuid;
        expected := (p_payload ->> 'expected_revision')::bigint;
        receipt := jsonb_build_object('action', p_payload -> 'action', 'revision', expected);
        if req_id is null or expected is null or expected < 0 then raise exception 'WEEKLY_INVALID_REQUEST'; end if;
        if g.last_request_id = req_id then
            if g.last_request is distinct from receipt then raise exception 'WEEKLY_REQUEST_REUSED'; end if;
            return public.yc_weekly_public_game(g);
        end if;
        if g.revision <> expected then raise exception 'WEEKLY_STALE_STATE'; end if;
        if g.completed_at is not null then raise exception 'WEEKLY_GAME_LOCKED'; end if;
        -- Use wall clock AFTER acquiring the row lock, including lock-wait time.
        if g.mode = 'official' and (clock_timestamp() < c.starts_at or clock_timestamp() >= c.ends_at) then
            raise exception 'WEEKLY_EXPIRED'; end if;
        if g.mode = 'practice' and not exists(select 1 from public.yc_weekly_games where player_id = actor
            and week_id = wk and mode = 'official' and completed_at is not null) then raise exception 'WEEKLY_REPLAY_LOCKED'; end if;
        next_state := p_payload -> 'next_state';
        kind := p_payload #>> '{action,kind}';
        if jsonb_typeof(next_state) is distinct from 'object'
            or next_state - array['state_version','week_id','rules_version','dice_version','schedule_commitment','mode','scores','held','revision','rolls','rounds'] <> '{}'::jsonb
            or next_state -> 'state_version' is distinct from g.state -> 'state_version'
            or next_state -> 'week_id' is distinct from g.state -> 'week_id'
            or next_state -> 'mode' is distinct from g.state -> 'mode'
            or next_state -> 'rules_version' is distinct from g.state -> 'rules_version'
            or next_state -> 'dice_version' is distinct from g.state -> 'dice_version'
            or next_state -> 'schedule_commitment' is distinct from g.state -> 'schedule_commitment'
            or next_state -> 'revision' is distinct from to_jsonb(expected + 1)
            or jsonb_typeof(next_state -> 'rolls') is distinct from 'array'
            or jsonb_typeof(next_state -> 'held') is distinct from 'array'
            or jsonb_typeof(next_state -> 'rounds') is distinct from 'array' then raise exception 'WEEKLY_INVALID_STATE'; end if;
        total := public.yc_weekly_state_total(next_state);
        old_rounds := jsonb_array_length(g.state -> 'rounds');
        new_rounds := jsonb_array_length(next_state -> 'rounds');
        old_rolls := jsonb_array_length(g.state -> 'rolls');
        new_rolls := jsonb_array_length(next_state -> 'rolls');
        if new_rolls not between 1 and 3 or jsonb_array_length(next_state -> 'held') > 5 then
            raise exception 'WEEKLY_INVALID_STATE'; end if;
        if kind = 'hold' then
            if (p_payload -> 'action') - array['kind','held'] <> '{}'::jsonb
                or next_state -> 'held' is distinct from p_payload #> '{action,held}' or old_rolls >= 3
                or next_state - array['held','revision'] is distinct from g.state - array['held','revision'] then
                raise exception 'WEEKLY_INVALID_STATE'; end if;
        elsif kind = 'reroll' then
            if p_payload -> 'action' is distinct from '{"kind":"reroll"}'::jsonb
                or new_rolls <> old_rolls + 1 or next_state -> 'rounds' is distinct from g.state -> 'rounds'
                or next_state -> 'scores' is distinct from g.state -> 'scores'
                or (next_state -> 'rolls') - (new_rolls - 1) is distinct from g.state -> 'rolls' then
                raise exception 'WEEKLY_INVALID_STATE'; end if;
        elsif kind = 'score' then
            if (p_payload -> 'action') - array['kind','category'] <> '{}'::jsonb
                or new_rounds <> old_rounds + 1
                or (next_state -> 'rounds') - (new_rounds - 1) is distinct from g.state -> 'rounds'
                or next_state #> array['rounds',old_rounds::text,'rolls'] is distinct from g.state -> 'rolls'
                or next_state #> array['rounds',old_rounds::text,'category'] is distinct from p_payload #> '{action,category}'
                or next_state -> 'held' <> '[]'::jsonb
                or (new_rounds < 13 and new_rolls <> 1)
                or (new_rounds = 13 and next_state -> 'rolls' is distinct from g.state -> 'rolls') then
                raise exception 'WEEKLY_INVALID_STATE'; end if;
        else raise exception 'WEEKLY_INVALID_REQUEST'; end if;
        done := new_rounds = 13;
        if done and exists(select 1 from jsonb_array_elements(next_state -> 'scores') v where v = 'null'::jsonb) then
            raise exception 'WEEKLY_INVALID_STATE'; end if;
        update public.yc_weekly_games set state = next_state, revision = expected + 1,
            total_score = total, updated_at = clock_timestamp(),
            completed_at = case when done then clock_timestamp() else null end,
            last_request_id = req_id, last_request = receipt where game_id = g.game_id returning * into g;
        if done and g.mode = 'practice' then
            insert into public.yc_weekly_replay_summaries as rs(player_id, week_id, best_score, latest_score,
                completed_count, latest_state, latest_completed_at)
                values(actor, wk, total, total, 1, g.state, g.completed_at)
            on conflict(player_id, week_id) do update set best_score = greatest(rs.best_score, excluded.best_score),
                latest_score = excluded.latest_score, completed_count = rs.completed_count + 1,
                latest_state = excluded.latest_state, latest_completed_at = excluded.latest_completed_at;
        end if;
        return public.yc_weekly_public_game(g);
    else raise exception 'WEEKLY_INVALID_REQUEST'; end if;
end;
$$;

-- Functions are private by default in this release, including helper functions.
revoke all on function public.yc_weekly_actor(uuid,text,uuid),
    public.yc_weekly_public_game(public.yc_weekly_games),
    public.yc_weekly_initial(public.yc_weekly_challenges,text),
    public.yc_weekly_state_total(jsonb), public.yc_weekly_guard_game_update(),
    public.yc_weekly_board(uuid,date,uuid), public.yc_weekly_rpc(uuid,text,uuid,text,jsonb)
    from public, anon, authenticated, service_role;
grant execute on function public.yc_weekly_rpc(uuid,text,uuid,text,jsonb) to service_role;
commit;


-- v43b_daily_six_v1_migration.sql
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


notify pgrst, 'reload schema';
