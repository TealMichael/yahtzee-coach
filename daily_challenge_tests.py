from datetime import datetime, timezone

from daily_challenge import (
    DAILY_CHALLENGE_VERSION,
    LEGACY_DAILY_CHALLENGE_VERSION,
    best_exact_streak,
    build_leaderboard,
    challenge_set_id,
    current_daily_date_key,
    daily_challenges,
    group_story,
    summarize_attempt,
    user_rank,
)


def fake_record(loss):
    return {"points_lost": float(loss)}


def run():
    checks = []

    c1 = daily_challenges("2026-08-08")
    c2 = daily_challenges("2026-08-08")
    checks.append(("daily has exactly ten", len(c1) == 10))
    checks.append(("same date is deterministic", [c["challenge_id"] for c in c1] == [c["challenge_id"] for c in c2]))
    checks.append(("five Roll 1 and five Roll 2", [c["roll_number"] for c in c1].count(1) == 5 and [c["roll_number"] for c in c1].count(2) == 5))
    checks.append(("legacy daily version preserved", all(c["daily_version"] == LEGACY_DAILY_CHALLENGE_VERSION for c in c1)))
    new_daily = daily_challenges("2026-08-19")
    checks.append(("2K.9 daily version begins forward-only", all(c["daily_version"] == DAILY_CHALLENGE_VERSION for c in new_daily)))
    checks.append(("set id stable", challenge_set_id("2026-08-08", c1) == challenge_set_id("2026-08-08", c2)))

    records = [fake_record(x) for x in [0, 0, .2, 0, 0, 0, 1.2, 0, .5, 0]]
    summary = summarize_attempt(records)
    checks.append(("attempt summary", summary["questions"] == 10 and summary["exact_count"] == 7 and abs(summary["total_ev_loss"] - 1.9) < 1e-9))
    checks.append(("best streak", best_exact_streak(records) == 3))

    board1 = build_leaderboard("2026-08-08", c1, records)
    board2 = build_leaderboard("2026-08-08", c1, records)
    checks.append(("mock leaderboard deterministic", [(r["display_name"], round(r["total_ev_loss"], 8)) for r in board1] == [(r["display_name"], round(r["total_ev_loss"], 8)) for r in board2]))
    checks.append(("user ranks", user_rank(board1) is not None and len(board1) == 8))
    story = group_story(board1, c1)
    checks.append(("group story available", story["toughest"] is not None and story["easiest"] is not None))

    aware = datetime(2026, 8, 9, 3, 30, tzinfo=timezone.utc)  # 11:30pm ET on Aug 8
    checks.append(("daily boundary uses ET", current_daily_date_key(aware) == "2026-08-08"))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
