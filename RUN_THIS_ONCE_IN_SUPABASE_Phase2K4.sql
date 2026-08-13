-- Yahtzee Coach v43B Phase 2K.4
-- One-time migration: remembered-device sessions for 30-day persistent login.
-- Safe to run more than once.
-- The browser stores only a high-entropy random token. The database stores only
-- a SHA-256 hash of the secret portion; player PINs are never stored in cookies.

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

create index if not exists player_sessions_player_idx
    on public.player_sessions(player_id, expires_at desc);
create index if not exists player_sessions_expiry_idx
    on public.player_sessions(expires_at)
    where revoked_at is null;

alter table public.player_sessions enable row level security;
revoke all on table public.player_sessions from anon, authenticated;
