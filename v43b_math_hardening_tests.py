"""Phase 2K.6 math-hardening regression suite.

Run:
    python v43b_math_hardening_tests.py

This suite protects the audited exact-policy artifact and proves that player-facing
Daily/Practice code fails closed rather than silently substituting heuristic advice.
"""
from __future__ import annotations

from math import factorial
from pathlib import Path

import numpy as np

from exact_mode import (
    CATEGORIES,
    EXPECTED_EXACT_POLICY_SHA256,
    ExactPolicyTable,
    build_exact_live_report_from_loader,
    verify_exact_policy_fingerprint,
)

ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "exact_policy.npz"
APP_PATH = ROOT / "app.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def empty_scorecard() -> dict[str, None]:
    return {category: None for category in CATEGORIES}


def canonical_roll_multiplicity(roll) -> int:
    counts = [list(roll).count(face) for face in range(1, 7)]
    ways = factorial(5)
    for count in counts:
        ways //= factorial(count)
    return ways


def starting_game_ev(policy: ExactPolicyTable) -> float:
    """Average the exact best Roll-1 value over all 7,776 equally likely first rolls."""
    state_index = policy.state_index(empty_scorecard())
    if state_index is None:
        raise AssertionError("all-open starting scorecard is missing from exact policy")
    weighted = 0.0
    total_ways = 0
    for roll_id, roll in enumerate(policy.rolls):
        values = policy.roll1_values[state_index, roll_id]
        best = float(np.nanmax(values))
        ways = canonical_roll_multiplicity(roll)
        weighted += best * ways
        total_ways += ways
    require(total_ways == 7776, "canonical-roll weights reconstruct all 7,776 first-roll outcomes")
    return weighted / total_ways


def check_published_exact_examples(policy: ExactPolicyTable) -> None:
    scorecard = empty_scorecard()
    examples = [
        ("Verhoeff opening 11666", [1, 1, 6, 6, 6], 1, [6, 6, 6], 265.11337),
        ("Verhoeff Roll-2 11346", [1, 1, 3, 4, 6], 2, [3, 4], 245.16327),
        ("Verhoeff opening 11236", [1, 1, 2, 3, 6], 1, [6], 249.82848),
    ]
    for name, dice, roll_number, expected_hold, expected_value in examples:
        best_hold, best_value = policy.best_hold(scorecard, dice, roll_number)
        require(list(best_hold) == expected_hold, f"{name}: exact best hold remains {expected_hold}")
        require(abs(best_value - expected_value) < 0.002, f"{name}: exact value remains ~{expected_value:.5f}")


def check_fail_closed_router() -> None:
    def broken_loader():
        raise FileNotFoundError("simulated missing policy")

    report, meta = build_exact_live_report_from_loader(
        broken_loader,
        dice=[1, 1, 3, 4, 6],
        scorecard=empty_scorecard(),
        user_hold=[3, 4],
        roll_number=2,
    )
    require(report == "", "exact-only router emits no coaching report when policy load fails")
    require(meta.get("source") == "exact_unavailable", "policy-load failure is marked exact_unavailable, not heuristic fallback")


def main() -> None:
    app = APP_PATH.read_text(encoding="utf-8")

    digest = verify_exact_policy_fingerprint(POLICY_PATH)
    require(digest == EXPECTED_EXACT_POLICY_SHA256, "exact_policy.npz matches the locked audited SHA-256 fingerprint")

    require('APP_RELEASE = "v43B Phase 2K.6.1"' in app, "release label advanced to Phase 2K.6.1")
    require("verify_exact_policy_fingerprint(EXACT_POLICY_PATH)" in app, "live exact-policy loader verifies the locked fingerprint")
    require("build_exact_live_report_from_loader" in app, "player-facing report path uses the exact-only router")
    require("build_live_report_from_loader" not in app, "player-facing app no longer imports the legacy fallback router")
    require("yc.generate_practice_challenge" not in app, "Practice no longer silently falls back to the heuristic-era generator")
    require("No heuristic coaching will be substituted" in app, "Practice tells the player when exact strategy is unavailable")
    require('solver_record.get("source") != "exact"' in app, "Practice refuses to grade a hold unless the exact solver produced it")

    policy = ExactPolicyTable(POLICY_PATH)
    ev = starting_game_ev(policy)
    require(abs(ev - 254.5877272445) < 0.002, f"locked policy reconstructs start-of-game EV 254.5877 (got {ev:.7f})")
    require(abs(ev - 254.59) < 0.02, "start-of-game EV agrees with the published ~254.59 optimal benchmark")

    check_published_exact_examples(policy)
    check_fail_closed_router()

    # Dead-upper-bonus regression from live beta feedback.
    dead_bonus_card = {
        "ones": 1, "twos": 2, "threes": 6, "fours": 4, "fives": 10, "sixes": None,
        "three_of_a_kind": None, "four_of_a_kind": None, "full_house": 25,
        "small_straight": 30, "large_straight": 40, "yahtzee": 0, "chance": 23,
    }
    best_hold, best_value = policy.best_hold(dead_bonus_card, [1, 1, 3, 3, 6], 1)
    pair_value = policy.hold_value(dead_bonus_card, [1, 1, 3, 3, 6], 1, [3, 3])
    require(list(best_hold) == [6], "dead-bonus regression still keeps the single 6")
    require(pair_value is not None and abs((best_value - pair_value) - 1.94) < 0.02, "dead-bonus pair of 3s remains about 1.94 points behind")

    print("ALL PHASE 2K.6 MATH-HARDENING TESTS PASSED")


if __name__ == "__main__":
    main()
