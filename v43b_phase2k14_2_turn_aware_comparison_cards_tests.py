"""Phase 2K.14.2 turn-aware comparison-card regressions."""
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
    return {
        "ones": None, "twos": None, "threes": None,
        "fours": None, "fives": None, "sixes": None,
        "three_of_a_kind": None, "four_of_a_kind": None,
        "full_house": None, "small_straight": None,
        "large_straight": None, "yahtzee": None, "chance": 13,
    }


def report_meta(dice, scorecard, user_hold, roll_number):
    return build_exact_report(
        POLICY,
        dice=dice,
        scorecard=scorecard,
        user_hold=user_hold,
        roll_number=roll_number,
    )[1]


def row_by_label(card, label):
    return next(row for row in card["rows"] if row["label"] == label)


def test_reported_bonus_vs_straight_tradeoff_is_turn_aware():
    meta = report_meta([1, 1, 4, 5, 6], reported_scorecard(), [1, 1], 1)
    card = meta["comparison_card"]

    assert card["title"] == "Keep 5 wins"
    assert card["summary_label"] == "Why the 5 wins"
    assert card["winner_side"] == "right"
    assert card["rank_text"] == "Your hold: #8 of 24"
    assert card["status"] == "Crowded decision"
    assert card["edge"] == "0.77"
    assert len(card["rows"]) == 5

    upper = row_by_label(card, "Expected upper box")
    assert (upper["left_value"], upper["left_note"]) == ("2.92", "Ones · target 3")
    assert (upper["right_value"], upper["right_note"]) == ("11.11", "Fives · target 15")
    assert upper["advantage"] == "split"

    bonus = row_by_label(card, "Three-of-a-face chance")
    assert bonus["left_value"] == "66.5%" and bonus["right_value"] == "35.8%"
    assert bonus["advantage"] == "split"  # Different faces are not overall bonus odds.

    straight = row_by_label(card, "Straight chances")
    assert straight["left_value"] == "SS 26.9% · LS 6.0%"
    assert straight["right_value"] == "SS 39.4% · LS 14.6%"
    assert straight["advantage"] == "right"

    payoff = row_by_label(card, "Straight payoff")
    assert payoff["left_value"] == "8.60 pts" and payoff["right_value"] == "13.10 pts"
    assert "4.50 more expected straight points" in card["summary"]
    assert "11/36" in card["math_detail"]
    assert "locked exact policy" in card["math_detail"]
    print("PASS reported pair-of-Ones card credits bonus pace and proves why straight flexibility wins")


def test_every_audited_review_gets_a_compact_real_comparison():
    reviewed = 0
    row_counts = set()
    for state_index in range(420):
        scorecard = scorecard_for_state_index(state_index)
        dice = tuple(int(value) for value in POLICY.rolls[(state_index * 73 + 17) % 252])
        for roll_number in (1, 2):
            results = POLICY.analyze(scorecard, dice, roll_number)
            user_hold = results[min(3, len(results) - 1)]["hold"]
            card = report_meta(dice, scorecard, user_hold, roll_number)["comparison_card"]
            assert card["title"] and card["summary"] and card["math_detail"]
            assert 1 <= len(card["rows"]) <= 5
            assert all(row["left_value"] and row["right_value"] for row in card["rows"])
            assert all(row["advantage"] in {"left", "right", "split", "neutral"} for row in card["rows"])
            assert card["roll_number"] == roll_number
            row_counts.add(len(card["rows"]))
            reviewed += 1
    assert reviewed == 840
    assert row_counts == {1, 2, 3, 4, 5}
    print("PASS 840 varied nonoptimal decisions receive one-to-five selected evidence rows")


def test_correct_answers_compare_against_an_instructive_alternative():
    reviewed = 0
    for state_index in range(420):
        scorecard = scorecard_for_state_index(state_index)
        dice = tuple(int(value) for value in POLICY.rolls[(state_index * 37 + 11) % 252])
        for roll_number in (1, 2):
            best_hold = POLICY.analyze(scorecard, dice, roll_number)[0]["hold"]
            meta = report_meta(dice, scorecard, best_hold, roll_number)
            card = meta["comparison_card"]
            assert card["winner_side"] == "left"
            assert card["left_role"] == "You · Best"
            assert card["right_role"] == "Compare"
            assert card["left_hold"] != card["right_hold"]
            assert card["rows"] and card["summary"]
            reviewed += 1
    assert reviewed == 840
    print("PASS 840 correct decisions teach by comparing the winning hold with a real alternative")


def test_existing_daily_click_opens_the_complete_card():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    daily_start = app.index("def _render_daily_review_body")
    daily_end = app.index("def _daily_review_item", daily_start)
    daily_body = app[daily_start:daily_end]
    item_start = daily_end
    item_end = app.index("def _rebuild_friend_daily_answers", item_start)
    item_body = app[item_start:item_end]

    assert "render_comparison_card(" in daily_body
    assert "top_holds=extract_section(report, \"Top exact holds:\")" in daily_body
    assert "with st.expander(label, expanded=False):" in item_body
    assert "_render_daily_review_body(answer)" in item_body
    assert "render_comparison_card(feedback[\"comparison_card\"])" in app
    assert "comparison_card = record.get(\"comparison_card\")" in app
    assert "evidence-grid" in app and "evidence-summary" in app
    assert 'APP_RELEASE = "v43B Phase 2K.14.4"' in app
    print("PASS the existing one-click Daily review reveals the complete shared comparison card")


def test_strategy_artifact_is_unchanged():
    assert exact_policy_sha256(ROOT / "exact_policy.npz") == EXPECTED_EXACT_POLICY_SHA256
    print("PASS turn-aware teaching evidence does not alter the exact policy")


def main():
    test_reported_bonus_vs_straight_tradeoff_is_turn_aware()
    test_every_audited_review_gets_a_compact_real_comparison()
    test_correct_answers_compare_against_an_instructive_alternative()
    test_existing_daily_click_opens_the_complete_card()
    test_strategy_artifact_is_unchanged()
    print("ALL PHASE 2K.14.2 TURN-AWARE COMPARISON CARD TESTS PASSED")


if __name__ == "__main__":
    main()
