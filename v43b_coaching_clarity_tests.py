from __future__ import annotations

"""Focused v43B Phase 2K.3 coaching clarity checks."""

from pathlib import Path

from exact_mode import ExactPolicyTable, build_exact_report

ROOT = Path(__file__).parent


def run():
    policy = ExactPolicyTable(ROOT / "exact_policy.npz")
    scorecard = {
        "ones": 0,
        "twos": 0,
        "threes": 9,
        "fours": 12,
        "fives": 20,
        "sixes": 24,
        "three_of_a_kind": 15,
        "four_of_a_kind": None,
        "full_house": 25,
        "small_straight": None,
        "large_straight": None,
        "yahtzee": None,
        "chance": 18,
    }
    report, meta = build_exact_report(
        policy,
        dice=[1, 1, 3, 3, 5],
        scorecard=scorecard,
        user_hold=[3, 3],
        roll_number=2,
    )
    app = (ROOT / "app.py").read_text(encoding="utf-8")

    simple = meta.get("simple_why", "")
    checks = [
        ("simple why is included in exact metadata", bool(simple)),
        ("simple why is included in text report", "Simple why:" in report),
        ("pair trap explanation names filled 3s support", "Threes" in simple and "Three of a Kind" in simple and "Full House" in simple),
        ("pair trap explanation names Chance as filled", "Chance" in simple),
        ("pair trap explanation names remaining matching upside", "Four of a Kind" in simple and "Yahtzee" in simple),
        ("pair trap explanation names both straight boxes", "Small Straight" in simple and "Large Straight" in simple),
        ("pair trap explanation names exact keep", "Keeping 3, 5" in simple),
        ("pair trap explanation stays concise", len(simple) < 430),
        ("Practice coach uses simple why for why-it-matters", 'simple_why_items[0] if simple_why_items' in app),
        ("Daily review shows Why this wins", "💡 Why this wins" in app),
        ("Daily review uses Remember instead of abstract Key lesson label", "🧠 Remember" in app),
        ("Daily review uses Try this instead label", "Try this instead" in app),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
