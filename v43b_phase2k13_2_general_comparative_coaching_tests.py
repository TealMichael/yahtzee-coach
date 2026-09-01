from pathlib import Path

import yahtzee_engine as yc
from exact_mode import (
    EXPECTED_EXACT_POLICY_SHA256,
    ExactPolicyTable,
    build_exact_report,
    exact_policy_sha256,
)
from puzzle_bank import scorecard_for_state_index


ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")


def screenshot_scorecard():
    return {
        "ones": None,
        "twos": None,
        "threes": None,
        "fours": 8,
        "fives": 10,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": None,
        "large_straight": None,
        "yahtzee": None,
        "chance": 26,
    }


def report_meta(dice, scorecard, user_hold, roll_number):
    return build_exact_report(
        POLICY,
        dice=dice,
        scorecard=scorecard,
        user_hold=user_hold,
        roll_number=roll_number,
    )[1]


def test_reported_singleton_tradeoff():
    meta = report_meta([1, 1, 2, 5, 6], screenshot_scorecard(), [6], 2)
    text = meta["simple_why"]
    assert meta["optimal_hold"] == "keep 2"
    assert round(meta["points_lost"], 2) == 0.03
    assert "upper-section route through Sixes" in text
    assert all(percent in text for percent in ("14.8%", "10.2%", "3.7%", "1.9%"))
    assert "Those advantages nearly cancel" in text
    assert "not a meaningful strategy mistake" in text
    assert "so Twos still matters" not in text
    print("PASS screenshot case compares the real upper-versus-straight tradeoff")


def test_two_pair_close_call():
    meta = report_meta(
        [2, 2, 5, 5, 6],
        yc.make_scorecard({"yahtzee": 0, "small_straight": 30, "chance": 21}),
        [5, 5],
        2,
    )
    text = meta["simple_why"]
    assert "open Fives box" in text
    assert "Full House 33.3% versus 9.3%" in text
    assert "slight 0.16-point edge" in text
    print("PASS close two-pair choice compares the player's box with the model's Full House gain")


def test_closed_pair_trap_keeps_scorecard_context():
    scorecard = {
        "ones": 0, "twos": 0, "threes": 9, "fours": 12, "fives": 20, "sixes": 24,
        "three_of_a_kind": 15, "four_of_a_kind": None, "full_house": 25,
        "small_straight": None, "large_straight": None, "yahtzee": None, "chance": 18,
    }
    meta = report_meta([1, 1, 3, 3, 5], scorecard, [3, 3], 2)
    text = meta["simple_why"]
    assert all(name in text for name in ("Threes", "Three of a Kind", "Full House", "Chance"))
    assert "Small Straight 25.0% versus 8.3%" in text
    assert "Large Straight 5.6% versus 0.0%" in text
    print("PASS closed-pair trap preserves the scorecard reason and adds exact straight evidence")


def test_large_error_does_not_lead_with_irrelevant_upside():
    meta = report_meta(
        [5, 5, 5, 5, 6],
        yc.make_scorecard({"four_of_a_kind": 0, "chance": 23}),
        [5],
        2,
    )
    text = meta["simple_why"]
    assert "open Fives box" in text
    assert "Three of a Kind 100.0% versus 21.3%" in text
    assert "Yahtzee 16.7% versus 0.1%" in text
    assert "Small Straight" not in text
    assert meta["points_lost"] > 20
    print("PASS major errors acknowledge the plan without promoting immaterial side benefits")


def test_honest_no_single_stat_fallback():
    scorecard = scorecard_for_state_index(250)
    meta = report_meta([1, 5, 5, 6, 6], scorecard, [6, 6], 1)
    text = meta["simple_why"]
    assert meta["optimal_hold"] == "keep 5, 5"
    assert "No single visible one-roll statistic separates the plans by much" in text
    assert "not a meaningful strategy mistake" in text
    print("PASS opaque solver hairlines are described honestly instead of receiving a fake lesson")


def test_broad_position_audit():
    family_count = set()
    max_length = 0
    reviewed = 0
    for state_index in range(420):
        scorecard = scorecard_for_state_index(state_index)
        dice = tuple(int(value) for value in POLICY.rolls[(state_index * 73 + 17) % 252])
        for roll_number in (1, 2):
            results = POLICY.analyze(scorecard, dice, roll_number)
            user_hold = results[min(3, len(results) - 1)]["hold"]
            meta = report_meta(dice, scorecard, user_hold, roll_number)
            text = meta["simple_why"]
            family_count.add(meta["coaching_family"])
            max_length = max(max_length, len(text))
            reviewed += 1
            assert text.strip()
            assert "interaction between the dice" not in text
            assert "prettiest pattern" not in text
            if 0.0 < meta["points_lost"] <= 0.10:
                assert "not a meaningful strategy mistake" in text

    assert reviewed == 840
    assert len(family_count) >= 15
    assert max_length < 500
    print(f"PASS broad audit: {reviewed} positions, {len(family_count)} families, max {max_length} characters")


def test_review_surfaces_use_margin_aware_copy():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "practical_tie = 0.0 < loss <= 0.10" in app
    assert "Why the model barely edges it" in app
    assert 'why_label = "Why the best hold wins"' in app
    assert "if lesson and not practical_tie" in app
    assert "if idea and not practical_tie" in app
    assert "Why this wins" not in app
    print("PASS Daily and Practice use comparative, proportional review language")


def test_exact_policy_unchanged():
    assert exact_policy_sha256(ROOT / "exact_policy.npz") == EXPECTED_EXACT_POLICY_SHA256
    print("PASS exact policy remains the audited artifact")


def main():
    test_reported_singleton_tradeoff()
    test_two_pair_close_call()
    test_closed_pair_trap_keeps_scorecard_context()
    test_large_error_does_not_lead_with_irrelevant_upside()
    test_honest_no_single_stat_fallback()
    test_broad_position_audit()
    test_review_surfaces_use_margin_aware_copy()
    test_exact_policy_unchanged()
    print("ALL PHASE 2K.13.2 GENERAL COMPARATIVE COACHING TESTS PASSED")


if __name__ == "__main__":
    main()
