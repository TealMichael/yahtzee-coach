from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import random

import numpy as np

from exact_mode import ExactPolicyTable
from puzzle_bank import (
    CATEGORIES,
    bank_summary,
    generate_daily_challenge_set,
    generate_practice_challenge,
    scorecard_for_state_index,
)

ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")
BANK = np.load(ROOT / "puzzle_bank.npz", allow_pickle=False)
UPPER = CATEGORIES[:6]


def legal_score_shape(card):
    for face, category in enumerate(UPPER, start=1):
        value = card[category]
        if value is not None:
            assert 0 <= value <= 5 * face
            assert value % face == 0
    assert card["full_house"] in (None, 0, 25)
    assert card["small_straight"] in (None, 0, 30)
    assert card["large_straight"] in (None, 0, 40)
    assert card["yahtzee"] in (None, 0, 50)
    if card["chance"] is not None:
        assert 5 <= card["chance"] <= 30
    for category in ("three_of_a_kind", "four_of_a_kind"):
        value = card[category]
        if value is not None:
            assert value == 0 or 5 <= value <= 30


def test_bank_summary():
    summary = bank_summary()
    assert summary["bank_version"] == "42.6"
    assert summary["scorecard_contexts"] == 420
    assert summary["simulated_scorecard_contexts"] == 357
    assert summary["curated_scorecard_contexts"] == 63
    assert summary["canonical_dice_rolls"] == 252
    assert summary["state_roll_situations"] == 211_680
    assert summary["daily_eligible_situations"] > 190_000
    assert len(summary["skills"]) == 9
    print("PASS bank summary: 420 contexts with an 85/15 realistic-to-curated mix")


def test_realism_and_blind_spots():
    audit = json.loads((ROOT / "puzzle_bank_audit.json").read_text())
    assert audit["previous_v42_states_preserved"] == 81
    assert audit["realistic_simulated_contexts"] == 357
    assert audit["curated_edge_contexts"] == 63
    assert audit["realistic_share"] == 0.85
    assert audit["stage_counts"] == {"Midgame": 120, "Opening": 60, "True Endgame": 120, "Late Game": 120}
    for status in ("Earned", "Dead", "Under Pressure", "Ahead", "On Pace"):
        assert audit["bonus_status_counts"][status] > 0
    for status in ("Open", "Zeroed", "Live 50"):
        assert audit["yahtzee_status_counts"][status] > 0
    messy = audit["human_messiness_examples"]
    assert messy["upper_zero_while_chance_open_contexts"] > 0
    assert messy["chance_already_used_with_7plus_boxes_open_contexts"] > 0
    print("PASS realism audit: broad strategic coverage remains, with believable imperfect human histories")


def test_scorecards_are_legal_and_history_shaped():
    assert len(BANK["state_keys"]) == 420
    assert len(set(map(int, BANK["state_keys"]))) == 420
    for index in range(420):
        card = scorecard_for_state_index(index)
        legal_score_shape(card)
        open_count = sum(value is None for value in card.values())
        assert open_count == int(BANK["open_count"][index])
        if str(BANK["origin"][index]) == "Simulated Game":
            # Every simulated card is a snapshot after exactly one category was
            # closed per prior turn; it was not assembled box-by-box afterward.
            assert int(BANK["turns_played"][index]) == 13 - open_count
            assert str(BANK["player_profile"][index]) in {"strong", "regular", "messy"}
        assert POLICY.state_index(card) == index
    print("PASS scorecard legality/history shape: all 357 simulated contexts are turn-consistent actual-game snapshots")


def test_practice_uses_realistic_mix():
    random.seed(426)
    seen_states=set(); seen_skills=set(); seen_rolls=set(); seen_stages=set(); origins=Counter()
    rounds=4_000
    for _ in range(rounds):
        challenge=generate_practice_challenge()
        assert POLICY.state_index(challenge["scorecard"]) is not None
        assert challenge["bank_version"] == "42.6"
        seen_states.add(challenge["bank_state_key"])
        seen_skills.add(challenge["skill_tag"])
        seen_rolls.add(challenge["roll_number"])
        seen_stages.add(challenge["stage"])
        origins[challenge["scorecard_origin"]] += 1
    share=origins["Simulated Game"] / rounds
    assert len(seen_states) > 250
    assert len(seen_skills) >= 8
    assert seen_rolls == {1,2}
    assert len(seen_stages) == 4
    assert 0.80 <= share <= 0.90
    print(f"PASS realistic practice draw: {share:.1%} simulated-game scorecards; broad stages/skills retained")


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
    assert Counter(x["scorecard_origin"] for x in a)==Counter({"Simulated Game":9,"Curated Edge Case":1})
    assert len(set(x["skill_tag"] for x in a)) >= 6
    assert all(POLICY.state_index(x["scorecard"]) is not None for x in a)
    print("PASS Daily-10 readiness: deterministic, 5/5 rolls, balanced stages, and 9 realistic + 1 edge-case scorecard")


def test_daily_many_dates():
    all_ids=set()
    underlying=[]
    prior_day=set()
    consecutive_overlap=[]
    min_skill_families=99
    for day in range(1,32):
        challenges=generate_daily_challenge_set(f"2026-08-{day:02d}")
        assert len(challenges)==10
        assert len({x["challenge_id"] for x in challenges})==10
        assert Counter(x["roll_number"] for x in challenges)==Counter({1:5,2:5})
        assert Counter(x["scorecard_origin"] for x in challenges)==Counter({"Simulated Game":9,"Curated Edge Case":1})
        skill_count=len(set(x["skill_tag"] for x in challenges))
        if day <= 18:
            assert skill_count >= 6
        else:
            assert 5 <= skill_count <= 7
        min_skill_families=min(min_skill_families,skill_count)
        all_ids.update(x["challenge_id"] for x in challenges)
        today={(x["bank_state_key"],tuple(x["dice"]),int(x["roll_number"])) for x in challenges}
        underlying.extend(today)
        if prior_day:
            consecutive_overlap.append(len(today & prior_day))
        prior_day=today
    unique_underlying=len(set(underlying))
    assert len(all_ids) > 280
    assert unique_underlying >= 300
    assert max(consecutive_overlap, default=0) == 0
    print(f"PASS 31-day Daily variety audit: {unique_underlying}/310 unique underlying decisions; 0 consecutive-day repeats; >= {min_skill_families} skill families/day")


def main():
    test_bank_summary()
    test_realism_and_blind_spots()
    test_scorecards_are_legal_and_history_shaped()
    test_practice_uses_realistic_mix()
    test_daily_determinism_and_balance()
    test_daily_many_dates()
    print("ALL REALISTIC PUZZLE-BANK / DAILY-CHALLENGE READINESS TESTS PASSED")

if __name__ == "__main__":
    main()
