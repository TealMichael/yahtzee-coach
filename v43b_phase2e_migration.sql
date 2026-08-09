-- Yahtzee Coach v43B Phase 2E — one-time migration
-- Purpose: allow a player to revise a saved Daily answer BEFORE final submission,
-- while keeping completed Daily attempts immutable. Safe to run more than once.

create or replace function public.guard_daily_answer_update()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    parent_attempt public.daily_attempts%rowtype;
    expected_puzzle text;
begin
    select * into parent_attempt
    from public.daily_attempts
    where attempt_id = old.attempt_id
    for update;

    if not found then
        raise exception 'Unknown Daily attempt';
    end if;

    if parent_attempt.completed_at is not null then
        raise exception 'Completed Daily answers cannot be changed';
    end if;

    if new.attempt_id is distinct from old.attempt_id
       or new.question_number is distinct from old.question_number
       or new.puzzle_id is distinct from old.puzzle_id then
        raise exception 'Daily answer identity cannot be changed';
    end if;

    select (puzzle_ids ->> (new.question_number - 1))
    into expected_puzzle
    from public.daily_challenges
    where challenge_id = parent_attempt.challenge_id;

    if expected_puzzle is distinct from new.puzzle_id then
        raise exception 'Puzzle ID does not match registered Daily challenge slot';
    end if;

    if new.solver_source <> 'exact' then
        raise exception 'Official Daily answers must use exact scoring';
    end if;

    if new.exact is distinct from (new.points_lost <= 0.000000001) then
        raise exception 'Exact flag does not match points_lost';
    end if;

    new.submitted_at := now();
    return new;
end;
$$;

create or replace function public.prevent_daily_answer_delete()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    raise exception 'Daily answers cannot be deleted';
end;
$$;

-- Remove the old Phase 2C/2D mutation lock, then replace it with:
-- updates allowed only before completion; deletes never allowed.
drop trigger if exists daily_answers_no_update on public.daily_answers;
drop trigger if exists daily_answers_update_guard on public.daily_answers;
create trigger daily_answers_update_guard
before update on public.daily_answers
for each row execute function public.guard_daily_answer_update();

drop trigger if exists daily_answers_no_delete on public.daily_answers;
create trigger daily_answers_no_delete
before delete on public.daily_answers
for each row execute function public.prevent_daily_answer_delete();
