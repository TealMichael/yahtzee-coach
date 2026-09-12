from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from exact_mode import (
    EXPECTED_EXACT_POLICY_SHA256,
    ExactPolicyTable,
    build_exact_report,
    exact_policy_sha256,
)
from puzzle_bank import generate_daily_challenge_set, scorecard_for_state_index


ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")


def report_meta(dice, scorecard, user_hold, roll_number):
    return build_exact_report(
        POLICY,
        dice=dice,
        scorecard=scorecard,
        user_hold=user_hold,
        roll_number=roll_number,
    )[1]


def test_wife_reported_two_pair_choice():
    scorecard = {
        "ones": None, "twos": None, "threes": None, "fours": None,
        "fives": None, "sixes": None, "three_of_a_kind": None,
        "four_of_a_kind": 7, "full_house": None, "small_straight": None,
        "large_straight": None, "yahtzee": None, "chance": None,
    }
    meta = report_meta([1, 1, 2, 2, 5], scorecard, [2, 2], 1)
    text = meta["simple_why"]
    assert meta["points_lost"] == 0.0
    assert meta["hold_rank"] == 1
    assert meta["instructive_alternative"] == "keep 1, 1, 2, 2"
    assert meta["instructive_alternative_kind"] == "two_pair_full_house"
    assert round(meta["instructive_alternative_gap"], 2) == 1.30
    assert "Keeping both pairs (1s and 2s)" in text
    assert "33.3%" in text and "9.3%" in text
    assert "1 fresh die" in text and "3 fresh dice" in text
    assert all(path in text for path in ("Twos", "Three of a Kind", "Yahtzee"))
    assert "1.30 expected points ahead" in text
    assert "You found the exact best hold" not in text
    print("PASS wife-reported Full House choice explains why the correct pair beats keeping both pairs")


def test_made_full_house_bank_and_break():
    examples = {}
    start = date(2026, 8, 19)
    for offset in range(90):
        key = (start + timedelta(days=offset)).isoformat()
        for challenge in generate_daily_challenge_set(key):
            if challenge.get("puzzle_theme") != "Bank It or Break It":
                continue
            best, _ = POLICY.best_hold(
                challenge["scorecard"], challenge["dice"], challenge["roll_number"]
            )
            outcome = "BANK" if len(best) == 5 else "BREAK"
            examples.setdefault(outcome, (challenge, best))
        if len(examples) == 2:
            break

    assert set(examples) == {"BANK", "BREAK"}
    for outcome, (challenge, best) in examples.items():
        meta = report_meta(
            challenge["dice"], challenge["scorecard"], best, challenge["roll_number"]
        )
        text = meta["simple_why"]
        assert meta["points_lost"] == 0.0
        assert meta["instructive_alternative_kind"] == "made_full_house"
        assert meta["instructive_alternative"]
        assert meta["instructive_alternative_gap"] > 0
        assert "guaranteed 25-point Full House" in text
        assert "Full-game lookahead" in text
        if outcome == "BANK":
            assert "banks" in text and "does not repay that risk" in text
        else:
            assert "would bank" in text and "upside is worth the risk" in text
    print("PASS correct Bank It or Break It answers explain the meaningful opposite choice")


def test_roll_one_endgame_straight_flexibility():
    scorecard = {
        "ones": 3, "twos": None, "threes": 9, "fours": 4,
        "fives": 15, "sixes": 12, "three_of_a_kind": 20,
        "four_of_a_kind": 16, "full_house": 25, "small_straight": 30,
        "large_straight": None, "yahtzee": 0, "chance": 20,
    }
    meta = report_meta([1, 1, 3, 5, 6], scorecard, [3, 5, 6], 1)
    text = meta["simple_why"]
    assert meta["optimal_hold"] == "keep 3, 5"
    assert round(meta["points_lost"], 2) == 0.87
    assert meta["coaching_family"] == "true_endgame_straight_flexibility"
    assert "both Large Straight routes open" in text
    assert "1–2–3–4–5 or 2–3–4–5–6" in text
    assert "Both holds are 5.6%" in text
    assert "18.4%" in text and "16.4%" in text
    assert "required by either straight" in text
    assert "score Twos" in text
    assert "keeping the 6 was reasonable" in text
    print("PASS reported endgame straight explains the replaceable 6 across both remaining rerolls")


def test_broad_optimal_answer_audit():
    kinds = Counter()
    max_length = 0
    reviewed = 0
    for state_index in range(420):
        scorecard = scorecard_for_state_index(state_index)
        dice = tuple(int(value) for value in POLICY.rolls[(state_index * 73 + 17) % 252])
        for roll_number in (1, 2):
            results = POLICY.analyze(scorecard, dice, roll_number)
            best_hold = results[0]["hold"]
            meta = report_meta(dice, scorecard, best_hold, roll_number)
            text = meta["simple_why"]
            reviewed += 1
            max_length = max(max_length, len(text))
            kinds[meta["instructive_alternative_kind"]] += 1
            assert meta["points_lost"] == 0.0
            assert meta["hold_rank"] == 1
            assert text.strip()
            if meta["instructive_alternative"]:
                assert meta["instructive_alternative_gap"] > 0
                assert "expected points" in text
                assert "You found the exact best hold" not in text
            assert "prettiest pattern" not in text
            assert "interaction between the dice" not in text

    assert reviewed == 840
    assert kinds["runner_up"] > 700
    assert max_length < 650
    print(f"PASS broad optimal audit: {reviewed} positions, {dict(kinds)}, max {max_length} characters")


def test_release_and_policy_guards():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'APP_RELEASE = "v43B Phase 2K.14.8"' in app
    assert exact_policy_sha256(ROOT / "exact_policy.npz") == EXPECTED_EXACT_POLICY_SHA256
    print("PASS release label advances while the exact policy remains unchanged")


def main():
    test_wife_reported_two_pair_choice()
    test_made_full_house_bank_and_break()
    test_roll_one_endgame_straight_flexibility()
    test_broad_optimal_answer_audit()
    test_release_and_policy_guards()
    print("ALL PHASE 2K.13.3 OPTIMAL-CHOICE COACHING TESTS PASSED")


if __name__ == "__main__":
    main()
