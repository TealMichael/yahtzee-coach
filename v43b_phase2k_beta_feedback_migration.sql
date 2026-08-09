-- Yahtzee Coach v43B Phase 2K — Beta feedback inbox
-- Safe to run more than once in the Supabase SQL Editor.

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

alter table public.beta_feedback enable row level security;
revoke all on table public.beta_feedback from anon, authenticated;
