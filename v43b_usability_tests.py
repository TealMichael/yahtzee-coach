from __future__ import annotations

"""Focused v43B Phase 2E usability/persistence wiring checks."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    store = (ROOT / "daily_store.py").read_text(encoding="utf-8")
    supabase_store = (ROOT / "supabase_daily_store.py").read_text(encoding="utf-8")
    schema = (ROOT / "v43b_schema.sql").read_text(encoding="utf-8")
    migration = (ROOT / "v43b_phase2e_migration.sql").read_text(encoding="utf-8")

    checks = [
        ("public invite URL uses group code query param", 'PUBLIC_APP_URL = "https://teals-yahtzee-coach.streamlit.app/"' in app and '?invite={code}' in app),
        ("invite link is detected before identity gate", "_pending_invite_code" in app and "Friend-group invite detected" in app),
        ("new/returning player auto-joins pending invite", "process_pending_group_invite" in app and ".join_group(st.session_state.active_player_id, code)" in app),
        ("invite query is cleared after successful join", "_clear_pending_invite()" in app and "Joined {group.group_name} from the invite link." in app),
        ("friend group has native share control", "📤 Share invite" in app and "nav.share" in app),
        ("friend group has copy-link control", "🔗 Copy invite link" in app and "clipboard.writeText" in app),
        ("Daily Back button is present", '"← Back"' in app and "daily_question_index = index - 1" in app),
        ("Daily revisions use exact backend method", "load_daily_store().revise_answer(" in app and 'solver_source="exact"' in app),
        ("ten answers reach a no-feedback final review", "Check your 10 choices" in app and "No grades, EV loss, or exact answers are shown yet." in app),
        ("final submission is explicit and permanent", "🏁 Submit final Daily Challenge" in app and "complete_attempt(attempt_id)" in app),
        ("reference store exposes revise_answer", "def revise_answer(" in store and "Completed Daily attempts are immutable." in store),
        ("Supabase store exposes revise_answer", "def revise_answer(" in supabase_store and '.update(payload)' in supabase_store),
        ("fresh schema allows guarded pre-submit updates", "guard_daily_answer_update" in schema and "Completed Daily answers cannot be changed" in schema),
        ("fresh schema still blocks deletes", "prevent_daily_answer_delete" in schema and "Daily answers cannot be deleted" in schema),
        ("migration replaces old no-update trigger", "drop trigger if exists daily_answers_no_update" in migration and "daily_answers_update_guard" in migration),
        ("home-screen button is visible outside active run", "📲 Add Yahtzee Coach to your Home Screen" in app and "Add to Home Screen" in app),
        ("iOS and Android install instructions exist", "🍎 iPhone / iPad" in app and "🤖 Android" in app and "Add to Home screen" in app),
        ("home-screen help does not falsely promise forced install", "cannot press Add to Home Screen automatically" in app),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
