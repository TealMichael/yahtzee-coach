from pathlib import Path

import yahtzee_engine as yc
from exact_mode import ExactPolicyTable, build_exact_report

ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")


def card(filled):
    return yc.make_scorecard(filled)


def assert_contains(report, *phrases):
    for phrase in phrases:
        assert phrase in report, f"missing teaching phrase: {phrase!r}\n\n{report}"


def test_near_tie_two_pairs():
    report, meta = build_exact_report(
        POLICY,
        dice=[2, 2, 5, 5, 6],
        scorecard=card({"yahtzee": 0, "small_straight": 30, "chance": 21}),
        user_hold=[5, 5],
        roll_number=2,
    )
    assert meta["optimal_hold"] == "keep 2, 2, 5, 5"
    assert 0.15 < meta["points_lost"] < 0.17
    assert_contains(
        report,
        "Near tie:",
        "Keep both pairs alive:",
        "Full House",
        "focus on the small structural advantage",
    )
    print("PASS near-tie teaching: close alternatives are not over-punished")


def test_four_kind_correction():
    report, meta = build_exact_report(
        POLICY,
        dice=[5, 5, 5, 5, 6],
        scorecard=card({"four_of_a_kind": 0, "chance": 23}),
        user_hold=[5],
        roll_number=2,
    )
    assert meta["optimal_hold"] == "keep 5, 5, 5, 5"
    assert meta["points_lost"] > 20
    assert_contains(
        report,
        "Large edge:",
        "Protect four matching dice:",
        "Keeping all four 5s",
        "Yahtzee",
    )
    print("PASS four-kind teaching: large structural mistakes get a clear rule")


def test_scorecard_over_visible_pattern():
    report, meta = build_exact_report(
        POLICY,
        dice=[1, 1, 4, 5, 6],
        scorecard=card({"ones": 3, "fours": 8, "sixes": 18,
                        "three_of_a_kind": 20, "four_of_a_kind": 0,
                        "full_house": 25, "chance": 22}),
        user_hold=[1, 1],
        roll_number=1,
    )
    # This specific template is intentionally cramped.  The exact answer should
    # explain the scorecard interaction rather than pretending a visible pair wins.
    assert meta["source"] == "exact"
    assert_contains(report, "Teaching takeaway:", "scorecard", "expected game points")
    print("PASS scorecard teaching: constrained positions explain board context")


def test_single_six_endgame_case():
    report, meta = build_exact_report(
        POLICY,
        dice=[1, 4, 4, 5, 6],
        scorecard=card({"threes": 9, "fours": 12, "fives": 15,
                        "three_of_a_kind": 22, "full_house": 25,
                        "small_straight": 30, "large_straight": 40,
                        "chance": 23}),
        user_hold=[4, 4],
        roll_number=1,
    )
    assert meta["optimal_hold"] == "keep 6"
    assert_contains(
        report,
        "Let the scorecard choose the die:",
        "Sixes is still open",
        "Read the open boxes, not just the dice.",
    )
    print("PASS endgame teaching: surprising lone-die answers explain why")


def test_straight_core_case():
    report, meta = build_exact_report(
        POLICY,
        dice=[2, 2, 3, 4, 5],
        scorecard=card({"small_straight": 30}),
        user_hold=[3],
        roll_number=1,
    )
    assert meta["optimal_hold"] == "keep 2, 3, 4, 5"
    assert_contains(
        report,
        "Protect the straight core:",
        "four-number core for Large Straight",
        "premium structure",
    )
    print("PASS straight teaching: four-die straight cores are made explicit")


def test_report_structure():
    report, _ = build_exact_report(
        POLICY,
        dice=[3, 3, 3, 4, 6],
        scorecard=card({}),
        user_hold=[3, 3, 3],
        roll_number=2,
    )
    for header in (
        "Your idea vs. best idea:",
        "How close was it?",
        "What was good about your move?",
        "Why was the optimal move better?",
        "Teaching takeaway:",
        "Top exact holds:",
        "Coach recommendation:",
    ):
        assert header in report
    assert "Expected game points lost:" in report
    print("PASS teaching report structure: every key learning layer is present")


def main():
    test_near_tie_two_pairs()
    test_four_kind_correction()
    test_scorecard_over_visible_pattern()
    test_single_six_endgame_case()
    test_straight_core_case()
    test_report_structure()
    print("ALL TEACHING EXPERIENCE TESTS PASSED")


if __name__ == "__main__":
    main()
