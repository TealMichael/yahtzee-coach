"""Phase 2K.14.1 winner-first and rank-context coaching regressions."""
from pathlib import Path

from exact_mode import (
    EXPECTED_EXACT_POLICY_SHA256,
    ExactPolicyTable,
    build_exact_report,
    exact_policy_sha256,
)
from puzzle_bank import scorecard_for_state_index


ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")


def reported_scorecard():
    card = {
        "ones": None, "twos": None, "threes": None,
        "fours": None, "fives": None, "sixes": None,
        "three_of_a_kind": None, "four_of_a_kind": None,
        "full_house": None, "small_straight": None,
        "large_straight": None, "yahtzee": None, "chance": 13,
    }
    return card


def report_meta(dice, scorecard, user_hold, roll_number):
    return build_exact_report(
        POLICY,
        dice=dice,
        scorecard=scorecard,
        user_hold=user_hold,
        roll_number=roll_number,
    )[1]


def test_reported_low_pair_is_explained_by_value_not_raw_frequency():
    meta = report_meta([1, 1, 4, 5, 6], reported_scorecard(), [1, 1], 1)
    text = meta["simple_why"]

    assert meta["optimal_hold"] == "keep 5"
    assert meta["hold_rank"] == 8
    assert round(meta["points_lost"], 2) == 0.77
    assert meta["coaching_family"] == "low_pair_open_board_value"
    assert text.startswith("Keeping 5 wins")
    assert "4 fresh dice" in text
    assert "8.3 expected Fives" in text and "2.5 Ones" in text
    assert "Small Straight 14.8% versus 2.8%" in text
    assert "Large Straight 3.7% versus 0.0%" in text
    assert "raw Three-of-a-Kind chance to 44.4% versus 21.3%" in text
    assert "nearly even: 4.72 versus 4.32" in text
    assert text.index("Keeping 5 wins") < text.index("Your pair raises")
    assert len(text) < 500
    print("PASS reported pair-of-Ones decision leads with why keep 5 wins and qualifies the flashy match rates")


def test_rank_eight_is_reconciled_with_the_small_point_spread():
    meta = report_meta([1, 1, 4, 5, 6], reported_scorecard(), [1, 1], 1)
    context = meta["rank_context"]
    assert "Crowded field" in context
    assert "#8" in context and "seven legal holds" in context
    assert "0.77 expected points from first" in context
    assert "Rank is order; Points Lost is distance" in context
    print("PASS ordinal hold rank is explicitly separated from expected-point distance")


def test_broad_nonoptimal_coaching_never_leads_with_the_loser_advantage():
    reviewed = 0
    crowded = 0
    max_length = 0
    for state_index in range(420):
        scorecard = scorecard_for_state_index(state_index)
        dice = tuple(int(value) for value in POLICY.rolls[(state_index * 73 + 17) % 252])
        for roll_number in (1, 2):
            results = POLICY.analyze(scorecard, dice, roll_number)
            user_hold = results[min(3, len(results) - 1)]["hold"]
            meta = report_meta(dice, scorecard, user_hold, roll_number)
            text = meta["simple_why"]
            lower = text.lower()
            reviewed += 1
            max_length = max(max_length, len(text))

            assert text.strip() and meta["rank_context"].strip()
            assert not lower.startswith("on the next roll, your hold has the stronger")
            assert not lower.startswith("on the final roll, your hold has the stronger")
            assert not lower.startswith("your hold has the stronger")
            if "your hold has the stronger" in lower:
                winner_phrase = (
                    "rerolling everything"
                    if meta["optimal_hold"] == "reroll everything"
                    else meta["optimal_hold"].replace("keep ", "keeping ")
                )
                winner_position = lower.find(winner_phrase)
                assert 0 <= winner_position < lower.find("your hold has the stronger")
            if meta["hold_rank"] >= 4 and 0 < meta["points_lost"] <= 1.50:
                crowded += 1
                assert meta["rank_context"].startswith("Crowded field:")

    assert reviewed == 840
    assert crowded > 50
    assert max_length < 500
    print(f"PASS broad winner-first audit: {reviewed} decisions, {crowded} crowded fields, max {max_length} characters")


def test_every_review_surface_uses_the_shared_order_and_context():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    spotlight = (ROOT / "daily_spotlight.py").read_text(encoding="utf-8")
    assert 'APP_RELEASE = "v43B Phase 2K.14.7"' in app
    assert 'why_label = "Why the best hold wins"' in app
    assert 'rank_context_items = extract_section(report, "Rank context:")' in app
    assert "📊 Rank context" in app
    assert app.index("{lead_title}</div><div>{why_it_matters}") < app.index("✓ {player_title}")
    assert "top_holds[:4]" in app
    assert '"rank_context": meta.get("rank_context", "")' in spotlight
    assert "feedback.get(\"rank_context\")" in app
    print("PASS Practice, Daily, friend review, Spotlight, and What If share winner-first context")


def test_exact_policy_is_unchanged():
    assert exact_policy_sha256(ROOT / "exact_policy.npz") == EXPECTED_EXACT_POLICY_SHA256
    print("PASS exact policy remains the audited artifact")


def main():
    test_reported_low_pair_is_explained_by_value_not_raw_frequency()
    test_rank_eight_is_reconciled_with_the_small_point_spread()
    test_broad_nonoptimal_coaching_never_leads_with_the_loser_advantage()
    test_every_review_surface_uses_the_shared_order_and_context()
    test_exact_policy_is_unchanged()
    print("ALL PHASE 2K.14.1 WINNER-FIRST CLARITY TESTS PASSED")


if __name__ == "__main__":
    main()
