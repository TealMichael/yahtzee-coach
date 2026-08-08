from __future__ import annotations

from collections import Counter
from pathlib import Path
import random
import time

import numpy as np

import yahtzee_engine as yc
from exact_mode import (
    ExactPolicyTable,
    TIE_TOLERANCE,
    build_live_report_from_loader,
    build_live_report_with_fallback,
    canonical,
    decode_hold,
    encode_hold,
    scorecard_state_key,
)

ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "exact_policy.npz"


def legal_hold(dice, hold):
    dc = Counter(dice)
    hc = Counter(hold)
    return all(hc[face] <= dc[face] for face in hc)


def representative_scorecards():
    by_key = {}
    template_count = 0
    for scenario in yc.SPICY_PRACTICE_SCENARIOS:
        for filled in scenario["scorecards"]:
            template_count += 1
            scorecard = yc.make_scorecard(filled)
            by_key.setdefault(scorecard_state_key(scorecard), scorecard)
    return template_count, by_key


def test_policy_shape(policy):
    assert len(policy.state_keys) == 81
    assert len(policy.rolls) == 252
    assert policy.roll1_values.shape == (81, 252, 32)
    assert policy.roll2_values.shape == (81, 252, 32)
    print("PASS policy structure: 81 states × 252 rolls × 2 roll stages")


def test_deck_coverage(policy):
    template_count, reps = representative_scorecards()
    assert template_count == 100
    assert len(reps) == 81
    assert set(map(int, policy.state_keys)) == set(reps)
    print("PASS deck coverage: all 100 templates / 81 unique scorecard states are exact")
    return reps


def test_all_policy_records(policy, reps):
    started = time.perf_counter()
    record_count = 0
    hold_value_checks = 0
    tie_records = 0

    for state_index, state_key in enumerate(policy.state_keys):
        scorecard = reps[int(state_key)]
        for roll_id, dice_array in enumerate(policy.rolls):
            dice = tuple(int(x) for x in dice_array)
            valid_codes = [int(code) for code in policy.hold_codes[roll_id] if int(code) >= 0]
            assert valid_codes
            assert len(valid_codes) == len(set(valid_codes))

            for code in valid_codes:
                hold = decode_hold(code)
                assert legal_hold(dice, hold)
                assert encode_hold(hold) == code

            for roll_number, values, best_ids in (
                (1, policy.roll1_values, policy.roll1_best),
                (2, policy.roll2_values, policy.roll2_best),
            ):
                record_count += 1
                row = values[state_index, roll_id]
                valid_ids = [i for i, code in enumerate(policy.hold_codes[roll_id]) if int(code) >= 0]
                valid_values = np.asarray([row[i] for i in valid_ids], dtype=np.float64)
                assert np.all(np.isfinite(valid_values))
                expected_best_value = float(np.max(valid_values))
                stored_best_id = int(best_ids[state_index, roll_id])
                assert stored_best_id in valid_ids
                stored_best_value = float(row[stored_best_id])
                assert abs(stored_best_value - expected_best_value) <= TIE_TOLERANCE

                tied_ids = [i for i in valid_ids if expected_best_value - float(row[i]) <= TIE_TOLERANCE]
                if len(tied_ids) > 1:
                    tie_records += 1

                analyzed = policy.analyze(scorecard, dice, roll_number)
                assert abs(float(analyzed[0]["strategy_value"]) - expected_best_value) <= TIE_TOLERANCE
                assert legal_hold(dice, analyzed[0]["hold"])

                # Check every legal hold through the public lookup path.
                for hold_id in valid_ids:
                    hold = decode_hold(int(policy.hold_codes[roll_id, hold_id]))
                    looked_up = policy.hold_value(scorecard, dice, roll_number, hold)
                    assert looked_up is not None
                    assert abs(float(looked_up) - float(row[hold_id])) <= 1e-6
                    hold_value_checks += 1

    elapsed = time.perf_counter() - started
    assert record_count == 81 * 252 * 2 == 40_824
    print(
        f"PASS exhaustive policy audit: {record_count:,} state/roll records, "
        f"{hold_value_checks:,} legal-hold value lookups, {tie_records:,} tied-best records "
        f"in {elapsed:.2f}s"
    )
    return record_count, hold_value_checks, tie_records, elapsed


def test_exact_first_router_on_every_record(policy, reps):
    started = time.perf_counter()
    routed = 0

    def forbidden_legacy(*args, **kwargs):
        raise AssertionError("legacy fallback was called for a covered exact state")

    for state_key in policy.state_keys:
        scorecard = reps[int(state_key)]
        for dice_array in policy.rolls:
            dice = tuple(int(x) for x in dice_array)
            for roll_number in (1, 2):
                optimal_hold, _ = policy.best_hold(scorecard, dice, roll_number)
                report, meta = build_live_report_with_fallback(
                    policy,
                    dice=dice,
                    scorecard=scorecard,
                    user_hold=optimal_hold,
                    roll_number=roll_number,
                    legacy_report_factory=forbidden_legacy,
                )
                assert meta["source"] == "exact"
                assert "Grade: A+" in report
                assert "Hold rank: #1" in report
                assert "Optimal choice:" in report
                routed += 1

    elapsed = time.perf_counter() - started
    assert routed == 40_824
    print(f"PASS exact-first integration: {routed:,}/{routed:,} records used exact mode in {elapsed:.2f}s")
    return elapsed


def test_generator_coverage(policy, rounds=20_000):
    keys = set(map(int, policy.state_keys))
    random.seed(20260808)
    missing = []
    for _ in range(rounds):
        challenge = yc.generate_practice_challenge()
        key = scorecard_state_key(challenge["scorecard"])
        if key not in keys:
            missing.append(key)
    assert not missing, f"generator produced {len(missing)} unsupported scorecard states"
    print(f"PASS generator coverage: {rounds:,}/{rounds:,} generated rounds had an exact state")


def test_fallback(policy):
    # Construct a valid but deliberately non-deck state.  Exact policy should
    # decline it cleanly and the legacy callback should receive control.
    scorecard = yc.blank_scorecard()
    scorecard["ones"] = 1
    scorecard["twos"] = 2
    sentinel = "LEGACY FALLBACK REPORT"
    called = {"count": 0}

    def legacy(dice, sc, hold, roll_number):
        called["count"] += 1
        return sentinel

    report, meta = build_live_report_with_fallback(
        policy,
        dice=[1, 2, 3, 4, 6],
        scorecard=scorecard,
        user_hold=[1, 2, 3, 4],
        roll_number=2,
        legacy_report_factory=legacy,
    )
    assert report == sentinel
    assert meta["source"] == "legacy_fallback"
    assert called["count"] == 1
    print("PASS safe fallback: unsupported state routes to legacy coach without crashing")



def test_policy_load_fallback():
    sentinel = "POLICY LOAD FALLBACK REPORT"
    called = {"count": 0}

    def broken_loader():
        raise FileNotFoundError("missing exact policy")

    def legacy(dice, sc, hold, roll_number):
        called["count"] += 1
        return sentinel

    report, meta = build_live_report_from_loader(
        broken_loader,
        dice=[1, 2, 3, 4, 6],
        scorecard=yc.blank_scorecard(),
        user_hold=[1, 2, 3, 4],
        roll_number=2,
        legacy_report_factory=legacy,
    )
    assert report == sentinel
    assert meta["source"] == "legacy_fallback"
    assert "policy_load_error" in meta["error"]
    assert called["count"] == 1
    print("PASS policy-load fallback: missing/corrupt policy can still use legacy coach")

def test_lookup_speed(policy, reps, n=10_000):
    scorecard = next(iter(reps.values()))
    dice = tuple(int(x) for x in policy.rolls[137])
    started = time.perf_counter()
    for i in range(n):
        policy.best_hold(scorecard, dice, 1 if i % 2 == 0 else 2)
    elapsed = time.perf_counter() - started
    per_lookup_ms = elapsed * 1000 / n
    print(f"PASS lookup speed: {n:,} ranked exact lookups in {elapsed:.4f}s ({per_lookup_ms:.4f} ms each)")
    return elapsed, per_lookup_ms


def main():
    policy = ExactPolicyTable(POLICY_PATH)
    test_policy_shape(policy)
    reps = test_deck_coverage(policy)
    test_all_policy_records(policy, reps)
    test_exact_first_router_on_every_record(policy, reps)
    test_generator_coverage(policy)
    test_fallback(policy)
    test_policy_load_fallback()
    test_lookup_speed(policy, reps)
    print("ALL EXACT INTEGRATION TESTS PASSED")


if __name__ == "__main__":
    main()
