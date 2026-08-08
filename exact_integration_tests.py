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
    decode_hold,
    encode_hold,
    scorecard_state_key,
)
from puzzle_bank import generate_practice_challenge, scorecard_for_state_index

ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "exact_policy.npz"
BANK_PATH = ROOT / "puzzle_bank.npz"


def legal_hold(dice, hold):
    dc = Counter(dice)
    hc = Counter(hold)
    return all(hc[face] <= dc[face] for face in hc)


def test_policy_shape(policy):
    assert len(policy.state_keys) == 420
    assert len(policy.rolls) == 252
    assert policy.roll1_values.shape == (420, 252, 32)
    assert policy.roll2_values.shape == (420, 252, 32)
    print("PASS policy structure: 420 states × 252 rolls × 2 roll stages")


def test_previous_deck_preserved(policy):
    old_keys = set()
    templates = 0
    for scenario in yc.SPICY_PRACTICE_SCENARIOS:
        for filled in scenario["scorecards"]:
            templates += 1
            old_keys.add(scorecard_state_key(yc.make_scorecard(filled)))
    assert templates == 100
    assert len(old_keys) == 81
    assert old_keys.issubset(set(map(int, policy.state_keys)))
    print("PASS backward coverage: all 100 old templates / 81 old exact states remain supported")


def test_bank_state_coverage(policy):
    bank = np.load(BANK_PATH, allow_pickle=False)
    assert np.array_equal(bank["state_keys"], policy.state_keys)
    for index in range(len(policy.state_keys)):
        card = scorecard_for_state_index(index)
        assert policy.state_index(card) == index
    print("PASS expanded coverage: all 420 scorecard contexts map to exact policy states")


def test_all_policy_values_structurally(policy):
    started = time.perf_counter()
    legal_by_roll = []
    for roll_id, dice_array in enumerate(policy.rolls):
        dice = tuple(int(x) for x in dice_array)
        valid_ids = []
        for hold_id, code in enumerate(policy.hold_codes[roll_id]):
            code = int(code)
            if code < 0:
                continue
            hold = decode_hold(code)
            assert legal_hold(dice, hold)
            assert encode_hold(hold) == code
            valid_ids.append(hold_id)
        assert valid_ids
        legal_by_roll.append(valid_ids)

    total_hold_values = 0
    tied_best = 0
    for values, best_ids in ((policy.roll1_values, policy.roll1_best), (policy.roll2_values, policy.roll2_best)):
        assert np.all(np.any(np.isfinite(values), axis=2))
        computed_best = np.nanmax(values, axis=2)
        stored_best = np.take_along_axis(values, best_ids[..., None], axis=2)[..., 0]
        assert np.all(np.isfinite(stored_best))
        assert np.max(np.abs(computed_best.astype(np.float64) - stored_best.astype(np.float64))) <= TIE_TOLERANCE
        total_hold_values += int(np.isfinite(values).sum())
        ties = np.sum(np.abs(values - computed_best[..., None]) <= TIE_TOLERANCE, axis=2)
        tied_best += int(np.sum(ties > 1))

    elapsed = time.perf_counter() - started
    assert total_hold_values == 3_669_120
    print(f"PASS exhaustive value-table audit: {total_hold_values:,} legal hold values; {tied_best:,} tied-best records in {elapsed:.2f}s")


def test_public_lookup_sample(policy, samples=20_000):
    rng = random.Random(4252026)
    started = time.perf_counter()
    for _ in range(samples):
        si = rng.randrange(420)
        rid = rng.randrange(252)
        roll_number = rng.choice((1, 2))
        scorecard = scorecard_for_state_index(si)
        dice = tuple(int(x) for x in policy.rolls[rid])
        analyzed = policy.analyze(scorecard, dice, roll_number)
        assert analyzed
        best_value = float(analyzed[0]["strategy_value"])
        hold = analyzed[rng.randrange(len(analyzed))]["hold"]
        looked_up = policy.hold_value(scorecard, dice, roll_number, hold)
        assert looked_up is not None and np.isfinite(looked_up)
        assert best_value + 1e-6 >= float(looked_up)
    elapsed = time.perf_counter() - started
    print(f"PASS public lookup sample: {samples:,} exact analyses/value lookups in {elapsed:.2f}s")


def test_exact_first_router_across_bank(policy):
    def forbidden_legacy(*args, **kwargs):
        raise AssertionError("legacy fallback was called for a covered exact state")

    routed = 0
    # One Roll-1 and one Roll-2 case for every scorecard state is enough to
    # exercise routing without generating 211,680 long teaching reports.
    for si in range(420):
        scorecard = scorecard_for_state_index(si)
        rid = (si * 97) % 252
        dice = tuple(int(x) for x in policy.rolls[rid])
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
            routed += 1
    assert routed == 840
    print("PASS exact-first router: 840/840 representative expanded-bank reports used exact mode")


def test_generator_coverage(policy, rounds=20_000):
    keys = set(map(int, policy.state_keys))
    random.seed(20260808)
    stages = Counter(); rolls = Counter(); skills = Counter()
    for _ in range(rounds):
        challenge = generate_practice_challenge()
        key = scorecard_state_key(challenge["scorecard"])
        assert key in keys
        assert challenge.get("bank_version") == "42.5"
        stages[challenge["stage"]] += 1
        rolls[challenge["roll_number"]] += 1
        skills[challenge["skill_tag"]] += 1
    # Generator intentionally broadens practice. These are loose sanity bounds,
    # not statistical claims about natural Yahtzee roll frequencies.
    assert len(stages) == 4
    assert set(rolls) == {1, 2}
    assert len(skills) >= 8
    assert 0.45 <= rolls[1] / rounds <= 0.55
    print(f"PASS expanded generator: {rounds:,}/{rounds:,} rounds exact; 4 stages; {len(skills)} skill families; Roll 1 share {rolls[1]/rounds:.3f}")


def _unsupported_scorecard(policy):
    # Find a plausible state not selected into the 420-state live bank.
    for ones in (0, 1, 2, 3, 4, 5):
        for twos in (0, 2, 4, 6, 8, 10):
            card = yc.blank_scorecard()
            card["ones"] = ones
            card["twos"] = twos
            if policy.state_index(card) is None:
                return card
    raise AssertionError("could not construct unsupported fallback state")


def test_fallback(policy):
    scorecard = _unsupported_scorecard(policy)
    sentinel = "LEGACY FALLBACK REPORT"
    called = {"count": 0}
    def legacy(dice, sc, hold, roll_number):
        called["count"] += 1
        return sentinel
    report, meta = build_live_report_with_fallback(
        policy,
        dice=[1, 2, 3, 4, 6], scorecard=scorecard,
        user_hold=[1, 2, 3, 4], roll_number=2,
        legacy_report_factory=legacy,
    )
    assert report == sentinel and meta["source"] == "legacy_fallback" and called["count"] == 1
    print("PASS safe fallback: unsupported state still routes to legacy coach")


def test_policy_load_fallback():
    sentinel = "POLICY LOAD FALLBACK REPORT"
    called = {"count": 0}
    def broken_loader(): raise FileNotFoundError("missing exact policy")
    def legacy(dice, sc, hold, roll_number): called["count"] += 1; return sentinel
    report, meta = build_live_report_from_loader(
        broken_loader, dice=[1,2,3,4,6], scorecard=yc.blank_scorecard(),
        user_hold=[1,2,3,4], roll_number=2, legacy_report_factory=legacy,
    )
    assert report == sentinel and meta["source"] == "legacy_fallback" and "policy_load_error" in meta["error"]
    print("PASS policy-load fallback")


def test_lookup_speed(policy, n=10_000):
    scorecard = scorecard_for_state_index(211)
    dice = tuple(int(x) for x in policy.rolls[137])
    started = time.perf_counter()
    for i in range(n):
        policy.best_hold(scorecard, dice, 1 if i % 2 == 0 else 2)
    elapsed = time.perf_counter() - started
    per_lookup_ms = elapsed * 1000 / n
    assert per_lookup_ms < 1.0
    print(f"PASS lookup speed: {n:,} ranked exact lookups in {elapsed:.4f}s ({per_lookup_ms:.4f} ms each)")


def main():
    policy = ExactPolicyTable(POLICY_PATH)
    test_policy_shape(policy)
    test_previous_deck_preserved(policy)
    test_bank_state_coverage(policy)
    test_all_policy_values_structurally(policy)
    test_public_lookup_sample(policy)
    test_exact_first_router_across_bank(policy)
    test_generator_coverage(policy)
    test_fallback(policy)
    test_policy_load_fallback()
    test_lookup_speed(policy)
    print("ALL EXPANDED EXACT INTEGRATION TESTS PASSED")

if __name__ == "__main__":
    main()
