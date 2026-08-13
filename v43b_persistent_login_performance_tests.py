from datetime import datetime, timedelta, timezone
from pathlib import Path

from daily_store import InMemoryDailyStore

ROOT = Path(__file__).resolve().parent


def run():
    checks = []

    now = [datetime(2026, 8, 12, 23, 0, tzinfo=timezone.utc)]
    store = InMemoryDailyStore(now_factory=lambda: now[0])
    player = store.create_player("Mike", "2468")

    token = store.create_device_session(player.player_id, 30)
    checks.append(("remember token is opaque and does not contain PIN", "2468" not in token and "." in token))
    restored = store.authenticate_device_session(token)
    checks.append(("remember token restores the same player", restored is not None and restored.player_id == player.player_id))

    session_id, secret = token.split(".", 1)
    tampered = f"{session_id}.{secret[:-1]}X"
    checks.append(("tampered remembered-device secret is rejected", store.authenticate_device_session(tampered) is None))

    store.revoke_device_session(token)
    checks.append(("sign out revokes remembered-device token", store.authenticate_device_session(token) is None))

    token2 = store.create_device_session(player.player_id, 30)
    now[0] += timedelta(days=31)
    checks.append(("remembered-device token expires after its TTL", store.authenticate_device_session(token2) is None))

    app = (ROOT / "app.py").read_text()
    sql = (ROOT / "v43b_phase2k4_persistent_login_migration.sql").read_text()
    supa = (ROOT / "supabase_daily_store.py").read_text()

    checks.append(("returning players get a 30-day remember checkbox", 'Keep me signed in on this device for 30 days' in app and 'returning_player_remember' in app))
    checks.append(("new players can also remember the device", 'create_player_remember' in app))
    checks.append(("new Streamlit sessions retain the first-party cookie fallback", 'st.context.cookies.get(REMEMBER_COOKIE_NAME' in app and '_restore_remembered_player(' in app))
    checks.append(("browser cookie is secure and same-site", 'SameSite=Lax; Secure' in app and 'Max-Age={REMEMBER_COOKIE_MAX_AGE}' in app))
    checks.append(("sign out revokes server token and clears browser cookie", 'revoke_device_session(token)' in app and '_queue_remember_cookie_delete()' in app))
    checks.append(("PIN is not written to browser cookie", 'return_pin' not in app[app.index('def render_pending_remember_cookie_command'):app.index('def _restore_remembered_player')]))

    checks.append(("migration creates revocable player sessions", 'create table if not exists public.player_sessions' in sql and 'revoked_at' in sql and 'expires_at' in sql))
    checks.append(("remembered sessions are closed to browser API roles", 'revoke all on table public.player_sessions from anon, authenticated' in sql))
    checks.append(("remember secret is hashed before Supabase storage", 'hash_device_token_secret(secret)' in supa and '"token_hash"' in supa))

    checks.append(("group lookup batches friend-group rows", '.in_("group_id", group_ids)' in supa))
    checks.append(("group member lookup batches player rows", '.in_("player_id", player_ids)' in supa))
    checks.append(("leaderboard batches group attempts", '.in_("player_id", player_ids)' in supa and 'completed = [_attempt_from_row' in supa))
    checks.append(("question stats batch all completed answers", '.in_("attempt_id", attempt_ids)' in supa and 'by_question' in supa))
    checks.append(("streak lookup batches challenge dates", '.in_("challenge_id", challenge_ids)' in supa))

    checks.append(("short-lived Streamlit caches reduce repeated social reads", '@st.cache_data(ttl=12' in app and '@st.cache_data(ttl=20' in app and '@st.cache_data(ttl=60' in app))
    checks.append(("writes clear social caches", app.count('_clear_social_caches()') >= 4))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL") + ": " + name)
    print(f"\n{len(checks)-len(failed)}/{len(checks)} checks passed")
    if failed:
        raise SystemExit("Failed: " + "; ".join(failed))


if __name__ == "__main__":
    run()
