from __future__ import annotations

"""Focused v43B Phase 2K beta-readiness checks."""

from pathlib import Path

from daily_store import InMemoryDailyStore

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    schema = (ROOT / "v43b_schema.sql").read_text(encoding="utf-8")
    migration = (ROOT / "v43b_phase2k_beta_feedback_migration.sql").read_text(encoding="utf-8")
    store_source = (ROOT / "supabase_daily_store.py").read_text(encoding="utf-8")

    store = InMemoryDailyStore()
    player = store.create_player("Beta Friend", "2468")
    feedback = store.submit_feedback(
        player_id=player.player_id,
        feedback_type="Something confusing",
        message="I wasn't sure what EV Lost meant.",
        app_version="v43B Phase 2K",
        page_mode="Daily Challenge",
    )

    checks = [
        ("returning player remains first/default tab", 'st.tabs(["Returning Player", "Create Player"])' in app),
        ("forgot PIN help is visible but low-profile", 'with st.expander("Forgot your PIN?"' in app and "PIN recovery isn't available" in app),
        ("help and feedback lives in a collapsed footer", 'with st.expander("❓ Help & feedback", expanded=False)' in app),
        ("beta version label is only in help area", 'APP_PUBLIC_VERSION = "Yahtzee Coach Beta · v43B"' in app and 'st.caption(APP_PUBLIC_VERSION)' in app),
        ("feedback form has useful categories", 'Bug / something broke' in app and 'Idea / suggestion' in app and 'Account / PIN help' in app),
        ("feedback form warns against sharing PIN", "Please don't include your PIN" in app),
        ("feedback is stored with version and mode", feedback.app_version == "v43B Phase 2K" and feedback.page_mode == "Daily Challenge"),
        ("feedback keeps signed-in player reference", feedback.player_id == player.player_id),
        ("Supabase backend writes beta feedback", 'self.client.table("beta_feedback").insert(payload)' in store_source),
        ("fresh schema contains beta feedback inbox", 'create table if not exists public.beta_feedback' in schema),
        ("migration creates beta feedback inbox", 'create table if not exists public.beta_feedback' in migration),
        ("feedback table is server-only", 'alter table public.beta_feedback enable row level security' in schema and 'revoke all on table public.beta_feedback from anon, authenticated' in schema),
        ("Daily intro shows participation streak when active", '_daily_streak_copy(streak, completed_today=False)' in app),
        ("completed Daily shows participation streak", '_daily_streak_copy(participation_streak, completed_today=True)' in app),
        ("best-hold streak is clearly distinguished from Daily streak", "Best Streak" in app and "Daily streak" in app),
        ("first finisher state is intentional", "You're the first to finish today!" in app),
        ("partial leaderboard has waiting copy", 'finished · waiting for' in app),
        ("full leaderboard has final-standings copy", "Everyone's in — final standings for today." in app),
        ("single-member group has intentional empty state", "You're the only member so far." in app),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
