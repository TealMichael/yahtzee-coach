-- Yahtzee Coach v43B — Supabase/Postgres persistence schema
-- Phase 1 contract: identity, friend groups, deterministic challenge IDs,
-- one attempt per player/challenge, editable exact-only draft answers until final submit, resume state,
-- leaderboard metrics, and participation-streak source data.
--
-- Run this in the Supabase SQL Editor for a NEW v43B project/database.
-- The Streamlit app will access these tables only from the trusted server using
-- a Supabase secret key stored in Streamlit secrets.  No secret belongs in GitHub.

create extension if not exists pgcrypto;

create table if not exists public.players (
    player_id uuid primary key default gen_random_uuid(),
    display_name text not null check (char_length(display_name) between 2 and 24),
    display_name_key text not null unique,
    pin_hash text not null check (pin_hash like 'scrypt$%'),
    created_at timestamptz not null default now()
);


create table if not exists public.player_sessions (
    session_id uuid primary key default gen_random_uuid(),
    player_id uuid not null references public.players(player_id) on delete cascade,
    token_hash text not null check (char_length(token_hash) = 64),
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    last_used_at timestamptz not null default now(),
    revoked_at timestamptz,
    check (expires_at > created_at)
);

create table if not exists public.friend_groups (
    group_id uuid primary key default gen_random_uuid(),
    group_name text not null check (char_length(group_name) between 2 and 40),
    join_code text not null unique check (char_length(join_code) between 4 and 12),
    created_by_player_id uuid not null references public.players(player_id) on delete cascade,
    created_at timestamptz not null default now()
);

create table if not exists public.group_members (
    group_id uuid not null references public.friend_groups(group_id) on delete cascade,
    player_id uuid not null references public.players(player_id) on delete cascade,
    joined_at timestamptz not null default now(),
    primary key (group_id, player_id)
);

create table if not exists public.daily_challenges (
    challenge_id text primary key,
    challenge_date date not null,
    challenge_version text not null,
    puzzle_ids jsonb not null,
    created_at timestamptz not null default now(),
    unique (challenge_date, challenge_version),
    check (jsonb_typeof(puzzle_ids) = 'array' and jsonb_array_length(puzzle_ids) = 10)
);

create table if not exists public.daily_attempts (
    attempt_id uuid primary key default gen_random_uuid(),
    player_id uuid not null references public.players(player_id) on delete cascade,
    challenge_id text not null references public.daily_challenges(challenge_id) on delete restrict,
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    total_ev_loss double precision check (total_ev_loss is null or total_ev_loss >= 0),
    exact_count integer check (exact_count is null or exact_count between 0 and 10),
    worst_miss double precision check (worst_miss is null or worst_miss >= 0),
    best_exact_streak integer check (best_exact_streak is null or best_exact_streak between 0 and 10),
    unique (player_id, challenge_id),
    check (
        (completed_at is null and total_ev_loss is null and exact_count is null and worst_miss is null and best_exact_streak is null)
        or
        (completed_at is not null and total_ev_loss is not null and exact_count is not null and worst_miss is not null and best_exact_streak is not null)
    )
);

create table if not exists public.daily_answers (
    attempt_id uuid not null references public.daily_attempts(attempt_id) on delete cascade,
    question_number integer not null check (question_number between 1 and 10),
    puzzle_id text not null,
    chosen_hold jsonb not null,
    optimal_hold jsonb not null,
    points_lost double precision not null check (points_lost >= 0),
    exact boolean not null,
    solver_source text not null default 'exact' check (solver_source = 'exact'),
    submitted_at timestamptz not null default now(),
    primary key (attempt_id, question_number),
    check (jsonb_typeof(chosen_hold) = 'array'),
    check (jsonb_typeof(optimal_hold) = 'array')
);

create table if not exists public.beta_feedback (
    feedback_id uuid primary key default gen_random_uuid(),
    player_id uuid references public.players(player_id) on delete set null,
    feedback_type text not null check (char_length(feedback_type) between 1 and 40),
    message text not null check (char_length(message) between 3 and 1200),
    app_version text not null default '' check (char_length(app_version) <= 80),
    page_mode text not null default '' check (char_length(page_mode) <= 80),
    created_at timestamptz not null default now()
);

create index if not exists beta_feedback_created_idx on public.beta_feedback(created_at desc);
create index if not exists beta_feedback_player_idx on public.beta_feedback(player_id);

create index if not exists player_sessions_player_idx on public.player_sessions(player_id, expires_at desc);
create index if not exists player_sessions_expiry_idx on public.player_sessions(expires_at) where revoked_at is null;
create index if not exists group_members_player_idx on public.group_members(player_id);
create index if not exists daily_attempts_challenge_idx on public.daily_attempts(challenge_id);
create index if not exists daily_attempts_completed_idx on public.daily_attempts(player_id, completed_at);
create index if not exists daily_answers_attempt_idx on public.daily_answers(attempt_id);

-- Save each answer at the database layer and ensure first-pass answers arrive sequentially.
create or replace function public.guard_daily_answer_insert()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    parent_attempt public.daily_attempts%rowtype;
    expected_question integer;
    expected_puzzle text;
begin
    select * into parent_attempt
    from public.daily_attempts
    where attempt_id = new.attempt_id
    for update;

    if not found then
        raise exception 'Unknown Daily attempt';
    end if;

    if parent_attempt.completed_at is not null then
        raise exception 'Daily attempt is already complete';
    end if;

    select coalesce(max(question_number), 0) + 1
    into expected_question
    from public.daily_answers
    where attempt_id = new.attempt_id;

    if new.question_number <> expected_question then
        raise exception 'Expected Daily question %, got %', expected_question, new.question_number;
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

    return new;
end;
$$;

drop trigger if exists daily_answers_insert_guard on public.daily_answers;
create trigger daily_answers_insert_guard
before insert on public.daily_answers
for each row execute function public.guard_daily_answer_insert();

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

drop trigger if exists daily_answers_no_update on public.daily_answers;
drop trigger if exists daily_answers_update_guard on public.daily_answers;
create trigger daily_answers_update_guard
before update on public.daily_answers
for each row execute function public.guard_daily_answer_update();

drop trigger if exists daily_answers_no_delete on public.daily_answers;
create trigger daily_answers_no_delete
before delete on public.daily_answers
for each row execute function public.prevent_daily_answer_delete();

-- Public browser/API access is intentionally closed for the custom-PIN v43B
-- architecture.  The Streamlit server will perform authorization and use a
-- secret backend key stored only in Streamlit Community Cloud secrets.
alter table public.players enable row level security;
alter table public.player_sessions enable row level security;
alter table public.friend_groups enable row level security;
alter table public.group_members enable row level security;
alter table public.daily_challenges enable row level security;
alter table public.daily_attempts enable row level security;
alter table public.daily_answers enable row level security;
alter table public.beta_feedback enable row level security;

revoke all on table public.players from anon, authenticated;
revoke all on table public.player_sessions from anon, authenticated;
revoke all on table public.friend_groups from anon, authenticated;
revoke all on table public.group_members from anon, authenticated;
revoke all on table public.daily_challenges from anon, authenticated;
revoke all on table public.daily_attempts from anon, authenticated;
revoke all on table public.daily_answers from anon, authenticated;
revoke all on table public.beta_feedback from anon, authenticated;
