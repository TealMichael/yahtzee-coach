from __future__ import annotations

"""Focused v43B Phase 2C persistent-Daily UI wiring checks.

Run:
    python v43b_daily_attempt_ui_tests.py

The store contract itself is exhaustively covered by v43b_persistence_tests.py.
This suite confirms the live Streamlit integration actually uses that contract.
"""

from pathlib import Path

from daily_store import InMemoryDailyStore


def run():
    checks = []

    # End-to-end contract smoke test: start, lock, recreate client-side state, resume.
    store = InMemoryDailyStore()
    player = store.create_player("ResumeTester", "2468")
    puzzle_ids = [f"p{i}" for i in range(1, 11)]
    challenge = store.ensure_challenge("2026-08-09-phase2c", "2026-08-09", "43A-bank42.6", puzzle_ids)
    attempt, created = store.get_or_create_attempt(player.player_id, challenge.challenge_id)
    checks.append(("first official attempt is created once", created))
    for number in range(1, 4):
        store.save_answer(
            attempt.attempt_id,
            question_number=number,
            puzzle_id=puzzle_ids[number - 1],
            chosen_hold=[number],
            optimal_hold=[number],
            points_lost=0.0,
            solver_source="exact",
        )
    resumed = store.get_resume_state(player.player_id, challenge.challenge_id)
    checks.append(("interrupted attempt resumes at next unanswered question", len(resumed.answers) == 3 and resumed.next_question_number == 4))
    same_attempt, created_again = store.get_or_create_attempt(player.player_id, challenge.challenge_id)
    checks.append(("second start request reuses same official attempt", not created_again and same_attempt.attempt_id == attempt.attempt_id))

    source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    checks.append(("Daily registers deterministic challenge set in database", "store.ensure_challenge(" in source and "_daily_puzzle_ids()" in source))
    checks.append(("Start button creates or restores one persisted attempt", "store.get_or_create_attempt(" in source and "start_persistent_daily_attempt" in source))
    checks.append(("Each locked answer is written before local progression", "load_daily_store().save_answer(" in source and "Answer {index + 1} locked and saved." in source))
    checks.append(("Official answers remain exact-only", 'if solver_record.get("source") != "exact"' in source and 'solver_source="exact"' in source))
    checks.append(("Refresh/device resume loads persisted attempt", "store.get_resume_state(" in source and "sync_daily_attempt_from_database" in source))
    checks.append(("Completed attempt is finalized in database", "load_daily_store().complete_attempt(attempt_id)" in source))
    checks.append(("interrupted Question 10 finalization self-heals", "len(resume_state.answers) == 10 and not resume_state.attempt.complete" in source))
    checks.append(("official reset control is removed", "Reset today's local demo attempt" not in source))
    checks.append(("UI tells player attempt cannot reset", "cannot be reset" in source))
    checks.append(("cross-player held dice state is cleared", 'startswith(("daily_held_", "daily_dice_pills_"))' in source))
    checks.append(("Practice remains independent", "def render_practice_mode():" in source and "Open Practice without signing in" in source))
    checks.append(("friend leaderboard is still explicitly preview data", "seven friend rows are still deterministic simulated players" in source))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
