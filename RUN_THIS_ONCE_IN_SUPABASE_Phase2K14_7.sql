-- v43B Phase 2K.14.7: run before installing the app update.
begin;
alter table public.player_sessions alter column expires_at drop not null;
-- Preserve remembered logins still valid at installation. Never revive expired/revoked tokens.
update public.player_sessions set expires_at = null
where revoked_at is null and expires_at > now();

create or replace function public.yahtzee_admin_reset_pin(
    actor_id uuid, actor_pin_hash text, target_id uuid, new_pin_hash text
) returns boolean
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
begin
    -- Only the trusted app server can execute this function; it checks the
    -- configured admin ID and verifies the admin's current PIN before calling.
    perform player_id from public.players
    where player_id in (actor_id, target_id) order by player_id for update;
    if not exists (select 1 from public.players where player_id = actor_id and pin_hash = actor_pin_hash) then
        raise exception 'Admin credentials changed; sign in again';
    end if;
    if not exists (select 1 from public.players where player_id = target_id) then
        raise exception 'Player not found';
    end if;
    if new_pin_hash is null or new_pin_hash not like 'scrypt$16384$8$1$32$%' then
        raise exception 'Invalid PIN hash';
    end if;
    update public.players set pin_hash = new_pin_hash where player_id = target_id;
    update public.player_sessions set revoked_at = now()
    where player_id = target_id and revoked_at is null;
    return true;
end;
$$;
revoke all on function public.yahtzee_admin_reset_pin(uuid,text,uuid,text) from public, anon, authenticated;
grant execute on function public.yahtzee_admin_reset_pin(uuid,text,uuid,text) to service_role;
commit;

-- Find Mike's existing account ID for YAHTZEE_ADMIN_PLAYER_ID in Streamlit Secrets.
-- Match your exact display name before copying the ID. No PIN hashes are displayed.
select player_id, display_name from public.players order by display_name;
