from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from pathlib import Path
import random

from daily_challenge import (
    DAILY_CHALLENGE_VERSION,
    LEGACY_DAILY_CHALLENGE_VERSION,
    challenge_set_id,
    daily_challenges,
)
from exact_mode import ExactPolicyTable, build_exact_report
from puzzle_bank import (
    BANK_BREAK_THEME,
    _bank_break_day_plan,
    challenge_signature,
    generate_daily_challenge_set,
    generate_practice_challenge,
)

ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")
LEGACY_AUG18_IDS = [
    "099ab08517f79ad9", "0f07a1ff3159d342", "fd28a4d3aa2d1e41", "243522e34fbb954f",
    "b13907e002af8ad3", "d7ae5dc07e1119dc", "d3f9d0bd8a593cd4", "b8db766f9976b0c0",
    "3fc911f33dbec52a", "9d1ea169e39d8eaa",
]


def _pattern(dice):
    counts = sorted(Counter(int(value) for value in dice).values(), reverse=True)
    if counts == [3, 2]:
        return "Full House"
    if counts == [1, 1, 1, 1, 1]:
        return "All different"
    return "Other"


def test_forward_only_version_boundary():
    legacy = daily_challenges("2026-08-18")
    current = daily_challenges("2026-08-19")
    assert [item["challenge_id"] for item in legacy] == LEGACY_AUG18_IDS
    assert all(item["daily_version"] == LEGACY_DAILY_CHALLENGE_VERSION for item in legacy)
    assert all(item["daily_version"] == DAILY_CHALLENGE_VERSION for item in current)
    assert challenge_set_id("2026-08-18", legacy).startswith("2026-08-18-")
    assert challenge_set_id("2026-08-19", current).startswith("2026-08-19-")
    print("PASS 2K.9 forward-only boundary preserves the exact Aug 18 Daily and historical version")


def test_bank_break_schedule_is_occasional_and_balanced():
    start = date(2026, 8, 19)
    plans = [_bank_break_day_plan((start + timedelta(days=i)).isoformat()) for i in range(90)]
    active = [value for value in plans if value]
    rate = len(active) / len(plans)
    counts = Counter(active)
    adjacent = sum(plans[i] is not None and plans[i - 1] is not None for i in range(1, len(plans)))
    assert 0.30 <= rate <= 0.40
    assert abs(counts["BANK"] - counts["BREAK"]) <= 2
    assert adjacent <= 6
    print(f"PASS Bank/Break schedule: {len(active)}/90 days ({rate:.1%}), {dict(counts)}, only {adjacent} adjacent-day transitions")


def test_phase2k9_daily_composition_and_exact_bank_break():
    start = date(2026, 8, 19)
    outcomes = Counter()
    joker_days = 0
    messy = 0
    total = 0
    family_counts = []

    for offset in range(21):
        key = (start + timedelta(days=offset)).isoformat()
        challenges = generate_daily_challenge_set(key)
        assert len(challenges) == 10
        assert Counter(item["roll_number"] for item in challenges) == Counter({1: 5, 2: 5})
        assert Counter(item["stage"] for item in challenges) == Counter({"Midgame": 3, "Late Game": 3, "Opening": 2, "True Endgame": 2})
        assert Counter(item["scorecard_origin"] for item in challenges) == Counter({"Simulated Game": 9, "Curated Edge Case": 1})
        assert Counter(item["difficulty"] for item in challenges) == Counter({"Medium": 3, "Punishing": 2, "Hard": 2, "Clear": 2, "Knife-edge": 1})

        families = set(item["skill_tag"] for item in challenges)
        family_counts.append(len(families))
        assert 5 <= len(families) <= 7
        joker_days += "Joker / Extra Yahtzee" in families

        specials = [item for item in challenges if item.get("puzzle_theme") == "Bank It or Break It"]
        assert len(specials) <= 1
        assert bool(specials) == bool(_bank_break_day_plan(key))
        if specials:
            item = specials[0]
            assert item["scenario_name"] == BANK_BREAK_THEME
            assert item["roll_number"] == 2
            assert item["scorecard"]["full_house"] is None
            assert _pattern(item["dice"]) == "Full House"
            best, _ = POLICY.best_hold(item["scorecard"], item["dice"], item["roll_number"])
            exact_outcome = "BANK" if len(best) == 5 else "BREAK"
            assert exact_outcome == item["bank_break_outcome"]
            outcomes[exact_outcome] += 1
            wrong_hold = list(item["dice"]) if exact_outcome == "BREAK" else list(best[:-1])
            _, meta = build_exact_report(
                POLICY, dice=item["dice"], scorecard=item["scorecard"],
                user_hold=wrong_hold, roll_number=item["roll_number"],
            )
            assert "25" in meta["simple_why"]
            if exact_outcome == "BREAK":
                assert "reopens" in meta["simple_why"]
                assert meta["coaching_family"] == "break_made_hand"
            else:
                assert "banks" in meta["simple_why"]
                assert meta["coaching_family"] == "protect_made_hand"

        messy += sum(_pattern(item["dice"]) == "All different" for item in challenges)
        total += len(challenges)

    assert outcomes["BANK"] > 0 and outcomes["BREAK"] > 0
    assert 2 <= joker_days <= 7
    assert 0.03 <= messy / total <= 0.12
    print(
        f"PASS 21-day 2K.9 Daily audit: Bank/Break {dict(outcomes)}, Joker on {joker_days}/21 days, "
        f"messy rolls {messy}/{total}, families/day {min(family_counts)}-{max(family_counts)}"
    )


def test_practice_surfaces_bank_break_regularly_without_drilling_it():
    random.seed(4269)
    recent_titles = []
    recent_signatures = []
    outcomes = Counter()
    rounds = 600
    for _ in range(rounds):
        challenge = generate_practice_challenge(recent_titles, recent_signatures)
        if challenge.get("puzzle_theme") == "Bank It or Break It":
            outcomes[challenge["bank_break_outcome"]] += 1
        recent_titles = (recent_titles + [challenge.get("scenario_name")])[-5:]
        recent_signatures = (recent_signatures + [challenge_signature(challenge)])[-12:]
    rate = sum(outcomes.values()) / rounds
    assert 0.08 <= rate <= 0.18
    assert outcomes["BANK"] > 0 and outcomes["BREAK"] > 0
    print(f"PASS Practice Bank/Break exposure: {sum(outcomes.values())}/{rounds} ({rate:.1%}), {dict(outcomes)}")


def main():
    test_forward_only_version_boundary()
    test_bank_break_schedule_is_occasional_and_balanced()
    test_phase2k9_daily_composition_and_exact_bank_break()
    test_practice_surfaces_bank_break_regularly_without_drilling_it()
    print("ALL PHASE 2K.9 PUZZLE-BALANCE TESTS PASSED")


if __name__ == "__main__":
    main()
