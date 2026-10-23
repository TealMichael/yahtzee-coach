"""Zero-point Yahtzee Joker explanation, with frozen-strategy safeguards.

These are coaching-only regressions. Hasbro's Joker rule still applies after
Yahtzee is scored as zero; the 100-point extra-Yahtzee bonus does not.
"""

from pathlib import Path

from exact_mode import (
    EXPECTED_EXACT_POLICY_SHA256,
    ExactPolicyTable,
    _build_comparison_card,
    build_exact_report,
    exact_policy_sha256,
)


ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")


def reported_scorecard():
    return {
        "ones": None, "twos": 2, "threes": 9, "fours": 8,
        "fives": 20, "sixes": 12, "three_of_a_kind": 16,
        "four_of_a_kind": 23, "full_house": 25,
        "small_straight": None, "large_straight": None,
        "yahtzee": 0, "chance": None,
    }


def card_for(hold, roll_number):
    report, meta = build_exact_report(
        POLICY,
        dice=[1, 5, 5, 5, 5],
        scorecard=reported_scorecard(),
        user_hold=hold,
        roll_number=roll_number,
    )
    return report, meta, meta["comparison_card"]


def test_question_seven_keeps_its_exact_result():
    report, meta, card = card_for([5], 1)
    assert meta["optimal_hold"] == "keep 5, 5, 5, 5"
    assert abs(meta["points_lost"] - 3.5107345581054688) < 1e-8
    assert meta["grade"] == "B-" and meta["hold_rank"] == 3
    assert card["edge"] == "3.51" and card["winner_side"] == "right"
    assert "A zero in Yahtzee removes the 100-point bonus, but NOT the Joker rule" in card["summary"]
    assert "five 5s can score 40 in Large Straight" in card["summary"]
    assert "30.6%" in card["summary"]
    assert "3.51 expected points" in card["summary"]
    assert "Even a zero in Yahtzee leaves the Joker rule active" in card["takeaway"]
    assert "ordinary-straight row" in card["math_detail"]
    assert "Your exact expected game value: 75.20" in report

    rows = {row["label"]: row for row in card["rows"]}
    assert len(card["rows"]) <= 5
    assert rows["Joker five-of-a-kind"]["left_value"] == "0.9%"
    assert rows["Joker five-of-a-kind"]["right_value"] == "30.6%"
    assert rows["Joker five-of-a-kind"]["advantage"] == "right"
    assert rows["Straight chances"]["left_value"] == "SS 39.4% · LS 14.6%"
    assert rows["Straight chances"]["right_value"] == "SS 18.6% · LS 4.6%"
    assert "excludes Joker" in rows["Straight chances"]["right_note"]
    assert rows["Chance total"]["left_value"] == "22.00"
    assert rows["Chance total"]["right_value"] == "24.25"


def test_roll_two_and_correct_answer_are_also_explained():
    _, meta, card = card_for([5], 2)
    assert meta["optimal_hold"] == "keep 5, 5, 5, 5"
    assert "16.7%" in card["summary"] and "final roll" in card["summary"]
    assert any(row["label"] == "Joker five-of-a-kind" for row in card["rows"])

    _, meta, card = card_for([5, 5, 5, 5], 1)
    assert meta["points_lost"] == 0 and card["winner_side"] == "left"
    assert "30.6%" in card["summary"] and "Joker" in card["takeaway"]


def test_no_false_joker_claim_if_yahtzee_unfilled_or_upper_open():
    for change in ({"yahtzee": None}, {"fives": None}):
        scorecard = {**reported_scorecard(), **change}
        card = _build_comparison_card(
            scorecard, [5], [5, 5, 5, 5],
            roll_number=1, points_lost=3.51, hold_rank=3,
            legal_hold_count=10, is_optimal=False,
            comparison_gap=None, coaching_family="four_matching",
            takeaway="Protect a strong matching core.", existing_math_detail="",
        )
        assert "Joker five-of-a-kind" not in {row["label"] for row in card["rows"]}
        assert "A zero in Yahtzee removes" not in card["summary"]


def test_strategy_artifact_was_not_touched():
    assert exact_policy_sha256(ROOT / "exact_policy.npz") == EXPECTED_EXACT_POLICY_SHA256


def main():
    test_question_seven_keeps_its_exact_result()
    test_roll_two_and_correct_answer_are_also_explained()
    test_no_false_joker_claim_if_yahtzee_unfilled_or_upper_open()
    test_strategy_artifact_was_not_touched()
    print("PASS Joker-zero teaching, both rerolls, truthful odds, unchanged exact policy")


if __name__ == "__main__":
    main()
