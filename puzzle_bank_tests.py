from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import random

from exact_mode import ExactPolicyTable, scorecard_state_key
from puzzle_bank import bank_summary, generate_daily_challenge_set, generate_practice_challenge

ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")


def test_bank_summary():
    summary = bank_summary()
    assert summary["scorecard_contexts"] == 420
    assert summary["canonical_dice_rolls"] == 252
    assert summary["state_roll_situations"] == 211_680
    assert summary["daily_eligible_situations"] > 190_000
    assert len(summary["skills"]) == 9
    print("PASS bank summary: expanded exact universe is loaded")


def test_audit_blind_spots_closed():
    audit = json.loads((ROOT / "puzzle_bank_audit.json").read_text())
    assert audit["previous_exact_states_preserved"] == 81
    assert audit["stage_counts"] == {"Midgame": 120, "Opening": 60, "True Endgame": 120, "Late Game": 120}
    assert audit["open_count_counts"]["1"] > 0 and audit["open_count_counts"]["2"] > 0
    for status in ("Earned", "Dead", "Under Pressure", "Ahead", "On Pace"):
        assert audit["bonus_status_counts"][status] > 0
    for status in ("Open", "Zeroed", "Live 50"):
        assert audit["yahtzee_status_counts"][status] > 0
    assert audit["canonical_dice_rolls"] == 252
    print("PASS blind-spot audit: true endgame, all bonus states, all Yahtzee states, and all 252 dice rolls are represented")


def test_practice_uses_expanded_bank():
    random.seed(425)
    seen_states=set(); seen_skills=set(); seen_rolls=set(); seen_stages=set()
    for _ in range(1500):
        c=generate_practice_challenge()
        assert POLICY.state_index(c["scorecard"]) is not None
        seen_states.add(c["bank_state_key"]); seen_skills.add(c["skill_tag"]); seen_rolls.add(c["roll_number"]); seen_stages.add(c["stage"])
    assert len(seen_states) > 250
    assert len(seen_skills) >= 8
    assert seen_rolls == {1,2}
    assert len(seen_stages) == 4
    print(f"PASS expanded practice draw: {len(seen_states)} states, {len(seen_skills)} skills, both roll stages, all game stages observed")


def test_daily_determinism_and_balance():
    a=generate_daily_challenge_set("2026-08-09")
    b=generate_daily_challenge_set("2026-08-09")
    c=generate_daily_challenge_set("2026-08-10")
    ids_a=[x["challenge_id"] for x in a]
    assert ids_a == [x["challenge_id"] for x in b]
    assert ids_a != [x["challenge_id"] for x in c]
    assert len(ids_a)==10 and len(set(ids_a))==10
    assert Counter(x["roll_number"] for x in a)==Counter({1:5,2:5})
    assert Counter(x["stage"] for x in a)==Counter({"Midgame":3,"Late Game":3,"Opening":2,"True Endgame":2})
    assert len(set(x["skill_tag"] for x in a)) >= 6
    assert all(POLICY.state_index(x["scorecard"]) is not None for x in a)
    print("PASS Daily-10 readiness: same date is deterministic; 5/5 rolls; 2/3/3/2 stage balance; 6+ skill families")


def test_daily_many_dates():
    all_ids=set()
    for day in range(1,32):
        challenges=generate_daily_challenge_set(f"2026-08-{day:02d}")
        assert len(challenges)==10
        assert len({x["challenge_id"] for x in challenges})==10
        assert Counter(x["roll_number"] for x in challenges)==Counter({1:5,2:5})
        assert len(set(x["skill_tag"] for x in challenges))>=6
        all_ids.update(x["challenge_id"] for x in challenges)
    assert len(all_ids) > 280
    print(f"PASS 31-day Daily-10 simulation: {len(all_ids)} unique challenge IDs across 310 slots")


def main():
    test_bank_summary()
    test_audit_blind_spots_closed()
    test_practice_uses_expanded_bank()
    test_daily_determinism_and_balance()
    test_daily_many_dates()
    print("ALL PUZZLE-BANK / DAILY-CHALLENGE READINESS TESTS PASSED")

if __name__ == "__main__":
    main()
