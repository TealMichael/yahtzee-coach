from pathlib import Path

import yahtzee_engine as yc
from exact_mode import (
    EXPECTED_EXACT_POLICY_SHA256,
    _clear_takeaway_for_family,
    _simple_why_with_family,
    exact_policy_sha256,
)

ROOT = Path(__file__).resolve().parent


def screenshot_scorecard():
    # Mirrors the scorecard context that exposed the vague fallback language:
    # bonus dead, Twos/Fives and several lower boxes still open.
    return yc.make_scorecard({
        "ones": 0,
        "threes": 9,
        "fours": 4,
        "sixes": 12,
        "three_of_a_kind": 8,
        "four_of_a_kind": 6,
        "full_house": 25,
    })


def test_close_generic_fallback_validates_before_refining():
    family, text = _simple_why_with_family(
        screenshot_scorecard(),
        [5],
        [2, 5],
        roll_number=2,
        is_optimal=False,
        visible_reason="",
        points_lost=0.14,
    )
    assert family == "scorecard_fit_close"
    assert "already a strong idea" in text
    assert "open Fives and Twos boxes" in text
    assert "giving up 1 fresh reroll die" in text
    assert "only 0.14 Points Lost" in text
    assert "Chance" not in text
    assert "remaining routes are worth more than the pattern you chose" not in text
    print("PASS close-call fallback: tiny solver edges get concrete, proportional coaching")


def test_close_generic_takeaway_is_scorecard_specific():
    takeaway = _clear_takeaway_for_family("scorecard_fit_close", "fallback")
    assert takeaway == "When two holds are this close, use the open scorecard boxes to find the small edge."
    print("PASS close-call takeaway: Remember line teaches the scorecard edge")


def test_daily_review_surfaces_near_tie_without_opening_details():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    marker = "**🤏 Very close:** Your hold was only {loss:.2f} Points Lost from the exact best hold."
    assert marker in app
    assert "if 0.0 < loss <= 0.25:" in app
    assert "This was a fine distinction, not a bad strategy choice." in app
    print("PASS Daily review: <=0.25 Points Lost is visibly labeled as a near-tie")


def test_exact_policy_artifact_unchanged():
    assert exact_policy_sha256(ROOT / "exact_policy.npz") == EXPECTED_EXACT_POLICY_SHA256
    print("PASS exact policy: coaching change did not alter solver artifact")


def main():
    test_close_generic_fallback_validates_before_refining()
    test_close_generic_takeaway_is_scorecard_specific()
    test_daily_review_surfaces_near_tie_without_opening_details()
    test_exact_policy_artifact_unchanged()
    print("ALL PHASE 2K.9.1 CLOSE-CALL COACHING TESTS PASSED")


if __name__ == "__main__":
    main()
