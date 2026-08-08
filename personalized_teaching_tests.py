from pathlib import Path

import yahtzee_engine as yc
from exact_mode import ExactPolicyTable, build_exact_report

ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")


def card(filled):
    return yc.make_scorecard(filled)


def section(report, header):
    lines = report.splitlines()
    start = lines.index(header) + 1
    out = []
    for line in lines[start:]:
        if not line.strip():
            break
        out.append(line)
    return "\n".join(out)


def test_near_tie_preserves_player_logic():
    report, meta = build_exact_report(
        POLICY,
        dice=[2, 2, 5, 5, 6],
        scorecard=card({"yahtzee": 0, "small_straight": 30, "chance": 21}),
        user_hold=[5, 5],
        roll_number=2,
    )
    block = section(report, "Your idea vs. best idea:")
    assert "Your idea:" in block
    assert "pair of 5s" in block
    assert "Best idea:" in block
    assert "keep 2, 2, 5, 5" in block
    assert "Tiny refinement:" in block
    assert "also protect 2, 2" in block
    assert 0.15 < meta["points_lost"] < 0.17
    print("PASS personalized near tie: validates the player's plan before refining it")


def test_major_error_gets_specific_correction():
    report, meta = build_exact_report(
        POLICY,
        dice=[5, 5, 5, 5, 6],
        scorecard=card({"four_of_a_kind": 0, "chance": 23}),
        user_hold=[5],
        roll_number=2,
    )
    block = section(report, "Your idea vs. best idea:")
    assert "open Fives box" in block
    assert "keep 5, 5, 5, 5" in block
    assert "Major correction:" in block
    assert "also protect 5, 5, 5" in block
    assert meta["points_lost"] > 20
    print("PASS personalized major correction: names the player's target and the missing structure")


def test_optimal_move_affirms_player_plan():
    report, meta = build_exact_report(
        POLICY,
        dice=[3, 3, 3, 4, 6],
        scorecard=card({}),
        user_hold=[3, 3, 3],
        roll_number=2,
    )
    block = section(report, "Your idea vs. best idea:")
    assert "builds around three 3s" in block
    assert "exact solver agrees with that plan" in block
    assert "No adjustment needed" in block
    assert meta["points_lost"] == 0
    print("PASS personalized optimal: explains what the player did right instead of only saying A+")


def test_straight_chase_can_be_overruled_by_scorecard():
    report, meta = build_exact_report(
        POLICY,
        dice=[1, 2, 3, 5, 6],
        scorecard=card({}),
        user_hold=[1, 2, 3],
        roll_number=1,
    )
    block = section(report, "Your idea vs. best idea:")
    assert "Large Straight chase" in block
    assert "exact plan is keep 5" in block
    assert "Fives is still open" in block
    assert "protect 5 and release 1, 2, 3" in block
    assert meta["points_lost"] > 1
    print("PASS personalized contrast: recognizes a sensible visible pattern when the scorecard prefers another plan")


def test_metadata_exposes_teaching_comparison():
    _, meta = build_exact_report(
        POLICY,
        dice=[2, 2, 3, 4, 5],
        scorecard=card({"small_straight": 30}),
        user_hold=[3],
        roll_number=1,
    )
    for key in ("user_idea", "best_idea", "adjustment"):
        assert meta.get(key), f"missing {key}"
    print("PASS personalized metadata: app/session tooling can inspect the three teaching messages")


def main():
    test_near_tie_preserves_player_logic()
    test_major_error_gets_specific_correction()
    test_optimal_move_affirms_player_plan()
    test_straight_chase_can_be_overruled_by_scorecard()
    test_metadata_exposes_teaching_comparison()
    print("ALL PERSONALIZED TEACHING TESTS PASSED")


if __name__ == "__main__":
    main()
