from datetime import datetime, timedelta, timezone
from pathlib import Path

from daily_store import InMemoryDailyStore

ROOT = Path(__file__).resolve().parent


def run():
    checks = []

    now = [datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)]
    store = InMemoryDailyStore(now_factory=lambda: now[0])
    player = store.create_player("Mike", "2468")
    token = store.create_device_session(player.player_id, 30)

    checks.append(("device token restores player", store.authenticate_device_session(token).player_id == player.player_id))
    checks.append(("device token still expires server-side", True))
    now[0] += timedelta(days=31)
    checks[-1] = (checks[-1][0], store.authenticate_device_session(token) is None)

    app = (ROOT / "app.py").read_text()
    req = (ROOT / "requirements.txt").read_text()

    checks.append(("release bumped to 2K.4.2", 'APP_RELEASE = "v43B Phase 2K.4.2"' in app))
    checks.append(("browser localStorage has a dedicated key", 'REMEMBER_STORAGE_KEY = "yc_remember_device_v2"' in app))
    checks.append(("uses Streamlit Components v2 bridge", 'st.components.v2.component(' in app and 'yahtzee_remember_storage' in app))
    checks.append(("bridge reads browser localStorage", 'window.localStorage.getItem(key)' in app))
    checks.append(("bridge writes browser localStorage", 'window.localStorage.setItem(key, token)' in app))
    checks.append(("bridge deletes browser localStorage on sign out", 'window.localStorage.removeItem(key)' in app))
    checks.append(("browser sends storage token back to Python", 'setStateValue("payload"' in app and 'getattr(result, "payload"' in app))
    checks.append(("restore prefers storage token with cookie fallback", 'token = storage_token or cookie_token' in app))
    checks.append(("restore waits for async browser read", 'if not cookie_token and not storage_ready:' in app))
    checks.append(("remember action queues localStorage set", '_queue_remember_storage_set(token)' in app))
    checks.append(("sign out queues localStorage delete", '_queue_remember_storage_delete()' in app))
    checks.append(("legacy secure same-site cookie remains fallback", 'SameSite=Lax; Secure' in app and 'st.context.cookies.get(REMEMBER_COOKIE_NAME' in app))
    checks.append(("PIN is never sent to localStorage bridge", 'return_pin' not in app[app.index('def render_remember_storage_bridge'):app.index('def render_pending_remember_cookie_command')]))
    checks.append(("Components-v2-capable Streamlit is required", 'streamlit>=1.52' in req))
    checks.append(("bridge runs before restore", app.index('_remember_storage_state = render_remember_storage_bridge()') < app.index('_restore_remembered_player(_remember_storage_state)')))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL") + ": " + name)
    print(f"\n{len(checks)-len(failed)}/{len(checks)} checks passed")
    if failed:
        raise SystemExit("Failed: " + "; ".join(failed))


if __name__ == "__main__":
    run()
