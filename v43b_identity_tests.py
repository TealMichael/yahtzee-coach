from __future__ import annotations

"""Focused v43B Phase 2B player-identity regression checks.

Run:
    python v43b_identity_tests.py

These tests do not contact Supabase. They verify the permanent-player contract
with the in-memory backend and confirm the Streamlit app is wired to that
contract without changing the Daily scoring engine.
"""

from pathlib import Path

from daily_store import InMemoryDailyStore, InvalidPin, PlayerNameTaken


def run():
    checks = []
    store = InMemoryDailyStore()

    player = store.create_player("TealDuck", "2468")
    checks.append(("create player returns permanent public identity", player.display_name == "TealDuck" and bool(player.player_id)))
    checks.append(("returning player lookup is case-insensitive", store.authenticate_player("tealduck", "2468") == player))
    checks.append(("wrong PIN cannot authenticate", store.authenticate_player("TealDuck", "9999") is None))
    checks.append(("plaintext PIN is never stored", store.players[player.player_id].pin_hash != "2468" and store.players[player.player_id].pin_hash.startswith("scrypt$")))

    try:
        store.create_player("TEALDUCK", "1111")
        duplicate_blocked = False
    except PlayerNameTaken:
        duplicate_blocked = True
    checks.append(("duplicate display names are blocked case-insensitively", duplicate_blocked))

    try:
        store.create_player("BadPin", "12ab")
        bad_pin_blocked = False
    except InvalidPin:
        bad_pin_blocked = True
    checks.append(("new-player PIN must be 4-12 digits", bad_pin_blocked))

    source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    checks.append(("Daily mode gates on persistent player identity", 'if not st.session_state.get("active_player_id")' in source and "render_player_identity_gate()" in source))
    checks.append(("Returning Player is first/default and Create Player remains available", 'st.tabs(["Returning Player", "Create Player"])' in source and 'load_daily_store().create_player' in source))
    checks.append(("Returning Player UI authenticates against the store", 'load_daily_store().authenticate_player' in source and '"Display name or PIN did not match."' in source))
    checks.append(("Practice remains available without an account", 'Open Practice without signing in' in source))
    checks.append(("Daily leaderboard name comes from authenticated identity", 'st.session_state.daily_display_name = player.display_name' in source))
    checks.append(("PIN entry uses masked password widgets", source.count('type="password"') >= 3))
    checks.append(("PIN forms clear submitted private values", 'st.form("create_player_form", clear_on_submit=True)' in source and 'st.form("returning_player_form", clear_on_submit=True)' in source))
    checks.append(("Phase 2B leaves exact competitive guard intact", 'if solver_record.get("source") != "exact"' in source))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
