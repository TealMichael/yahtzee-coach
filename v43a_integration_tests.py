from pathlib import Path

from daily_challenge import build_leaderboard, daily_challenges, group_story, summarize_attempt, user_rank
from exact_mode import ExactPolicyTable, build_exact_report

ROOT = Path(__file__).resolve().parent


def run():
    checks = []
    policy = ExactPolicyTable(ROOT / "exact_policy.npz")
    challenges = daily_challenges("2026-08-08")

    checks.append(("ten unique daily challenge ids", len(challenges) == 10 and len({c['challenge_id'] for c in challenges}) == 10))
    checks.append(("daily composition 9 realistic + 1 curated", sum(c['scorecard_origin'] == 'Simulated Game' for c in challenges) == 9 and sum(c['scorecard_origin'] == 'Curated Edge Case' for c in challenges) == 1))
    checks.append(("daily stage mix", {stage: sum(c['stage'] == stage for c in challenges) for stage in ['Opening','Midgame','Late Game','True Endgame']} == {'Opening':2,'Midgame':3,'Late Game':3,'True Endgame':2}))

    records = []
    for challenge in challenges:
        analysis = policy.analyze(challenge['scorecard'], challenge['dice'], challenge['roll_number'])
        best_hold = analysis[0]['hold']
        report, record = build_exact_report(
            policy,
            dice=challenge['dice'],
            scorecard=challenge['scorecard'],
            user_hold=best_hold,
            roll_number=challenge['roll_number'],
        )
        record['daily_number'] = challenge['daily_number']
        records.append(record)
        if record['points_lost'] > 1e-9 or record['source'] != 'exact':
            checks.append((f"Q{challenge['daily_number']} optimal scoring", False))
            break
    else:
        checks.append(("all ten exact-best choices score 0.00", True))

    summary = summarize_attempt(records)
    checks.append(("perfect daily summary", summary['questions'] == 10 and summary['exact_count'] == 10 and summary['total_ev_loss'] <= 1e-9 and summary['best_exact_streak'] == 10))
    board = build_leaderboard("2026-08-08", challenges, records, user_name="Tester")
    checks.append(("perfect user leads demo leaderboard", user_rank(board) == 1))
    story = group_story(board, challenges)
    checks.append(("group comparison produces killer/most-solved cards", story['toughest'] is not None and story['easiest'] is not None))

    app_text = (ROOT / "app.py").read_text()
    checks.append(("Daily Challenge is first/default mode", 'options=["Daily Challenge", "Practice"]' in app_text and 'st.session_state.app_mode = "Daily Challenge"' in app_text))
    checks.append(("daily answers hide strategy hints", 'No strategy label or difficulty hint is shown during the official run.' in app_text))
    checks.append(("visible segmented Daily progress bar", "daily-progress-percent" in app_text and "Question {index + 1} of 10" in app_text))
    checks.append(("intro summary boxes removed", "<div class='review-label'>Format</div>" not in app_text and "<div class='review-label'>Reset</div>" not in app_text))
    checks.append(("Daily results link back to Practice", "Go to open Practice" in app_text and 'st.session_state.app_mode = "Practice"' in app_text))
    checks.append(("Practice can return to completed leaderboard", "View today's Daily leaderboard" in app_text and 'st.session_state.app_mode = "Daily Challenge"' in app_text))
    checks.append(("competitive mode rejects heuristic fallback", 'this answer was NOT locked' in app_text and 'solver_record.get("source") != "exact"' in app_text))
    checks.append(("coaching waits until completion", 'Now that the competitive run is over, every exact answer and teaching explanation is unlocked.' in app_text))
    checks.append(("prototype reset control exists", "Reset today's local demo attempt" in app_text))
    checks.append(("mobile daily result grid protected", '@media (max-width:640px)' in app_text and '.daily-result-grid { grid-template-columns:repeat(2' in app_text))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
