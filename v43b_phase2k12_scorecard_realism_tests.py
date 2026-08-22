from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
import random

from daily_challenge import (
    DAILY_CHALLENGE_VERSION,
    PHASE2K9_DAILY_CHALLENGE_VERSION,
    daily_challenges,
)
from puzzle_bank import (
    _data,
    _eligible_indices,
    _scorecard_proves_passed_up_open_yahtzee,
    generate_daily_challenge_set,
    generate_practice_challenge,
)

AUG19_IDS = [
    "752e3eec1520f139", "fd5e335a12b4ae35", "0e8f1721f3e56130", "685bcfb39c75a4a3",
    "55aa33280d737165", "b9022212d2d17868", "aba1be7ebf216b47", "822f970040928b9f",
    "187f487fb9852986", "acac701293e4d418",
]
AUG20_IDS = [
    "0f42d70c16b45f72", "990680d8b2260231", "d92ff0a66fdeb5e7", "eefbf16d17965f9e",
    "d858adc1ec6d2dbc", "707bc82b2475861a", "f3f50e98d1d9f0f4", "a19bd40f5d58f523",
    "2229c5c982833570", "4c70bdae1942d6e2",
]
AUG21_IDS = [
    "d7cea74ebb342a4e", "37e6be784121f680", "ca79abe04ce60f98", "295f39bfbba77707",
    "f94cd33e32d40729", "eabc796ed75b248a", "6dc5b79de35f2f03", "989bf7e3803fd696",
    "f948ead52484c585", "235fc6046d776c61",
]


def _assert_locked_composition(challenges):
    assert len(challenges) == 10
    assert Counter(item["roll_number"] for item in challenges) == Counter({1: 5, 2: 5})
    assert Counter(item["stage"] for item in challenges) == Counter({
        "Opening": 2, "Midgame": 3, "Late Game": 3, "True Endgame": 2,
    })
    assert Counter(item["difficulty"] for item in challenges) == Counter({
        "Clear": 2, "Medium": 3, "Hard": 2, "Punishing": 2, "Knife-edge": 1,
    })
    assert Counter(item["scorecard_origin"] for item in challenges) == Counter({
        "Simulated Game": 9, "Curated Edge Case": 1,
    })


def test_audit_rule_is_narrow_and_preserves_curated_edges():
    data = _data()
    flagged = [
        index for index in range(len(data["state_keys"]))
        if _scorecard_proves_passed_up_open_yahtzee(index)
    ]
    assert len(flagged) == 14
    assert all(str(data["origin"][index]) == "Simulated Game" for index in flagged)
    assert all(str(data["yahtzee_status"][index]) == "Open" for index in flagged)
    assert not any(
        _scorecard_proves_passed_up_open_yahtzee(index)
        for index in range(len(data["state_keys"]))
        if str(data["origin"][index]) == "Curated Edge Case"
    )
    total_daily = len(_eligible_indices(daily=True))
    realistic_daily = len(_eligible_indices(daily=True, realistic=True))
    assert total_daily == 200140
    assert realistic_daily == 193551
    assert realistic_daily / total_daily > 0.96
    print(f"PASS narrow realism rule: 14/420 contexts flagged; {realistic_daily}/{total_daily} Daily situations retained")


def test_forward_only_boundary_preserves_played_dailies():
    for key, expected in [
        ("2026-08-19", AUG19_IDS),
        ("2026-08-20", AUG20_IDS),
        ("2026-08-21", AUG21_IDS),
    ]:
        challenges = daily_challenges(key)
        assert [item["challenge_id"] for item in challenges] == expected
        assert all(item["daily_version"] == PHASE2K9_DAILY_CHALLENGE_VERSION for item in challenges)
    new_daily = daily_challenges("2026-08-22")
    assert all(item["daily_version"] == DAILY_CHALLENGE_VERSION for item in new_daily)
    print("PASS forward-only realism boundary: Aug 19-21 remain byte-for-byte challenge-ID compatible")


def test_future_dailies_remove_only_implausible_history_and_keep_mix():
    start = date(2026, 8, 22)
    days = 60
    unique_ids = set()
    bank_break_days = 0
    joker_days = 0
    curated_count = 0
    for offset in range(days):
        key = (start + timedelta(days=offset)).isoformat()
        challenges = generate_daily_challenge_set(key)
        _assert_locked_composition(challenges)
        assert not any(
            _scorecard_proves_passed_up_open_yahtzee(item["bank_state_index"])
            for item in challenges
        ), key
        assert len({item["bank_state_index"] for item in challenges}) == 10
        specials = [item for item in challenges if item.get("puzzle_theme") == "Bank It or Break It"]
        assert len(specials) <= 1
        bank_break_days += bool(specials)
        joker_days += any(item["skill_tag"] == "Joker / Extra Yahtzee" for item in challenges)
        curated_count += sum(item["scorecard_origin"] == "Curated Edge Case" for item in challenges)
        unique_ids.update(item["challenge_id"] for item in challenges)
    assert 15 <= bank_break_days <= 28  # still roughly the planned 30-40% neighborhood
    assert curated_count == days
    assert len(unique_ids) == days * 10
    print(
        f"PASS {days}-day realism audit: 0 implausible scorecards, {bank_break_days} Bank/Break days, "
        f"{joker_days} Joker days, {len(unique_ids)}/{days*10} date-safe challenge IDs"
    )


def test_november_5_soft_family_fallback_keeps_hard_mix():
    challenges = generate_daily_challenge_set("2026-11-05")
    _assert_locked_composition(challenges)
    assert any(item["skill_tag"] == "Joker / Extra Yahtzee" for item in challenges)
    assert not any(
        _scorecard_proves_passed_up_open_yahtzee(item["bank_state_index"])
        for item in challenges
    )
    print("PASS Nov 5 safety fallback: Daily generates and preserves all hard composition rules")


def test_practice_never_draws_flagged_simulated_history():
    random.seed(4212)
    seen_curated = 0
    for _ in range(400):
        challenge = generate_practice_challenge()
        if challenge["scorecard_origin"] == "Curated Edge Case":
            seen_curated += 1
        assert not _scorecard_proves_passed_up_open_yahtzee(challenge["bank_state_index"])
    assert seen_curated > 0
    print(f"PASS Practice realism sampling: 400 draws, 0 flagged histories, curated edges still surface ({seen_curated})")


def main():
    test_audit_rule_is_narrow_and_preserves_curated_edges()
    test_forward_only_boundary_preserves_played_dailies()
    test_future_dailies_remove_only_implausible_history_and_keep_mix()
    test_november_5_soft_family_fallback_keeps_hard_mix()
    test_practice_never_draws_flagged_simulated_history()
    print("ALL PHASE 2K.12 SCORECARD-REALISM TESTS PASSED")


if __name__ == "__main__":
    main()
