from __future__ import annotations

"""Focused v43B Phase 2K.3.1 dark-mode + dead-bonus coaching protections."""

from pathlib import Path

from exact_mode import ExactPolicyTable, build_exact_report

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    policy = ExactPolicyTable(ROOT / "exact_policy.npz")
    scorecard = {
        "ones": 1,
        "twos": 2,
        "threes": 6,
        "fours": 4,
        "fives": 10,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": 25,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": 0,
        "chance": 21,
    }
    report, meta = build_exact_report(
        policy,
        dice=[1, 1, 3, 3, 6],
        scorecard=scorecard,
        user_hold=[3, 3],
        roll_number=1,
    )
    simple = meta.get("simple_why", "")

    checks = [
        ("Daily review boxes force dark text", ".review-box {" in app and "color:#111827 !important" in app),
        ("Daily review values force dark text", ".review-value { color:#111827 !important" in app),
        ("Daily review labels retain muted contrast", ".review-label { color:#6b7280 !important" in app),
        ("dead-bonus position exact best is keep 6", meta.get("optimal_hold") == "keep 6"),
        ("dead-bonus position keeps exact 1.94 loss", abs(float(meta.get("points_lost", 0.0)) - 1.93701171875) < 1e-8),
        ("dead-bonus explanation explicitly says not bonus chase", "not a bonus chase" in simple),
        ("dead-bonus explanation names impossible bonus", "35-point upper bonus" in simple and "out of reach" in simple),
        ("dead-bonus explanation names all live matching destinations", "Sixes" in simple and "Three of a Kind" in simple and "Four of a Kind" in simple),
        ("dead-bonus explanation contrasts pair of 3s", "pair of 3s" in simple),
        ("dead-bonus explanation explains two-reroll flexibility", "2 rerolls left" in simple and "4 fresh dice" in simple),
        ("text report still exposes dead bonus context", "upper bonus is mathematically out of reach" in report),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
