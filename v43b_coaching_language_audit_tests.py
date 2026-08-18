from __future__ import annotations

"""Phase 2K.3.2 coaching-language family audit.

The exact policy still determines every ranking.  These checks protect the
player-facing translation layer so surprising holds explain the visible dice +
scorecard tradeoff in short, concrete language.
"""

from pathlib import Path
from collections import Counter

import yahtzee_engine as yc
from exact_mode import (
    ExactPolicyTable,
    _clear_takeaway_for_family,
    _simple_why_with_family,
    _visible_strategy_reason,
)
from puzzle_bank import scorecard_for_state_index

ROOT = Path(__file__).parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")


def card(filled=None):
    return yc.make_scorecard(filled or {})


def why(scorecard, user, best, roll=1):
    _, visible, fallback = _visible_strategy_reason(scorecard, best, roll)
    family, text = _simple_why_with_family(
        scorecard,
        user,
        best,
        roll_number=roll,
        is_optimal=False,
        visible_reason=visible,
    )
    remember = _clear_takeaway_for_family(family, fallback)
    return family, text, remember


def require(name, condition):
    if not condition:
        raise AssertionError(name)
    print("PASS", name)


def direct_family_checks():
    # Pair vs straight: the exact live-test case that triggered the language pass.
    c = {
        "ones": 0, "twos": 0, "threes": 9, "fours": 12, "fives": 20, "sixes": 24,
        "three_of_a_kind": 15, "four_of_a_kind": None, "full_house": 25,
        "small_straight": None, "large_straight": None, "yahtzee": None, "chance": 18,
    }
    fam, text, remember = why(c, [3, 3], [3, 5], 2)
    require("pair-vs-straight family", fam == "pair_vs_straight")
    require("pair-vs-straight names closed matching support", all(x in text for x in ("Threes", "Three of a Kind", "Full House", "Chance")))
    require("pair-vs-straight names live straight paths", "Small Straight" in text and "Large Straight" in text)
    require("pair-vs-straight reusable lesson is plain", "distinct connected numbers" in remember)

    # Dead bonus: the [1,1,3,3,6] case stays explicit that 63 is impossible.
    c = {
        "ones": 1, "twos": 2, "threes": 6, "fours": 4, "fives": 10, "sixes": None,
        "three_of_a_kind": None, "four_of_a_kind": None, "full_house": 25,
        "small_straight": 30, "large_straight": 40, "yahtzee": 0, "chance": 21,
    }
    fam, text, remember = why(c, [3, 3], [6], 1)
    require("dead-bonus high-die family", fam == "bonus_dead_high_die")
    require("dead-bonus explicitly rejects bonus chase", "not a bonus chase" in text and "out of reach" in text)
    require("dead-bonus names remaining boxes", all(x in text for x in ("Sixes", "Three of a Kind", "Four of a Kind")))
    require("dead-bonus remember removes 63 pressure", "stop paying for 63" in remember)

    # Bonus alive / secured / dead pair states.
    fam, text, remember = why(card({}), [1, 6], [6, 6], 1)
    require("bonus-alive pair family", fam == "bonus_alive_pair")
    require("bonus-alive pair explains 63 is still in play", "still in play" in text and "remaining upper boxes" in text)

    earned = card({"ones": 5, "twos": 10, "threes": 15, "fours": 20, "fives": 25})
    fam, text, remember = why(earned, [1, 6], [6, 6], 2)
    require("bonus-secured pair family", fam == "bonus_secured_pair")
    require("bonus-secured language says 63 is safe", "already secured" in text and "not about protecting 63" in text)

    dead = card({"ones": 1, "twos": 2, "threes": 3, "fours": 4, "fives": 5})
    fam, text, remember = why(dead, [3, 6], [6, 6], 2)
    require("bonus-dead pair family", fam == "bonus_dead_pair")
    require("bonus-dead pair removes bonus help", "out of reach" in text and "without any bonus help" in text)

    # Matching structures.
    c = card({"chance": 20})
    fam, text, remember = why(c, [5], [5, 5, 5], 1)
    require("triple family", fam == "triple_matching" and "Three 5s" in text and "fresh dice" in text)
    fam, text, remember = why(c, [5, 5], [5, 5, 5, 5], 2)
    require("four-matching family", fam == "four_matching" and "one matching die from Yahtzee" in text)

    # Full House / straight structures.
    c = card({"small_straight": 30, "chance": 20})
    fam, text, remember = why(c, [5, 5], [2, 2, 5, 5], 2)
    require("two-pair Full House family", fam == "two_pair_full_house" and "Full House" in text and "last die" in text)
    c = card({"small_straight": 30})
    fam, text, remember = why(c, [3], [2, 3, 4, 5], 1)
    require("straight-core family", fam == "straight_structure" and "4 distinct numbers" in text and "1 fresh die" in text)
    require("straight remember calls core premium", "premium structure" in remember)

    # Made-hand decisions in both directions.
    c = card({})
    fam, text, remember = why(c, [6, 6], [3, 3, 3, 6, 6], 2)
    require("protect-made-hand family", fam == "protect_made_hand" and "25-point Full House" in text and "banks that guaranteed score" in text)
    fam, text, remember = why(c, [3, 3, 3, 6, 6], [3, 3, 3], 1)
    require("break-made-hand family", fam == "break_made_hand" and "reasonable safety play" in text and "does not automatically mean keep" in text)

    # Extra-Yahtzee/Joker rules.
    c = card({"yahtzee": 50})
    fam, text, remember = why(c, [6], [6, 6, 6], 1)
    require("extra-Yahtzee/Joker family", fam == "extra_yahtzee_joker" and "100-point bonus" in text and "Joker" in text)

    # True endgame, Chance timing, open-board flexibility, and generic scorecard fit.
    c = card({
        "ones": 1, "twos": 2, "threes": 3, "fours": 4, "fives": 5,
        "three_of_a_kind": 12, "four_of_a_kind": 0, "full_house": 25,
        "small_straight": 30, "large_straight": 40, "yahtzee": 0,
    })  # Sixes + Chance open
    fam, text, remember = why(c, [5, 6], [6], 2)
    require("true-endgame family", fam == "true_endgame" and "Only Sixes and Chance remain open" in text)
    require("true-endgame remember rejects generic opening rules", "boxes that are actually left" in remember)

    c = card({
        "ones": 1, "twos": 2, "threes": 3, "fours": 4, "fives": 5, "sixes": 6,
        "full_house": 25, "small_straight": 30, "large_straight": 40, "yahtzee": 0,
    })  # 3K, 4K, Chance open
    fam, text, remember = why(c, [3, 4], [5, 6], 2)
    require("Chance-timing family", fam == "chance_timing" and "raw die total" in text and "11 points" in text)

    c = card({})
    fam, text, remember = why(c, [2, 3], [], 1)
    require("open-board flexibility family", fam == "open_board_flexibility" and "board is still wide open" in text)

    c = card({"small_straight": 30, "large_straight": 40})
    fam, text, remember = why(c, [5], [4, 5], 2)
    require("generic scorecard-fit family", fam == "scorecard_fit" and "Your hold is mainly aiming" in text and "exact hold" in text)


def broad_language_audit():
    counts = Counter()
    max_length = 0
    vague_phrases = ("interaction between the dice", "useful flexibility", "prettiest pattern")

    # One deterministic roll per state at both Roll 1 and Roll 2 = 840 real exact
    # positions. Use a clearly non-best legal hold so the explanation has to teach
    # a contrast rather than simply congratulate the optimal play.
    for state_index in range(420):
        scorecard = scorecard_for_state_index(state_index)
        dice = tuple(int(x) for x in POLICY.rolls[(state_index * 73 + 17) % 252])
        for roll in (1, 2):
            results = POLICY.analyze(scorecard, dice, roll)
            best = tuple(results[0]["hold"])
            user = tuple(results[min(3, len(results) - 1)]["hold"])
            _, visible, fallback = _visible_strategy_reason(scorecard, best, roll)
            family, text = _simple_why_with_family(
                scorecard,
                user,
                best,
                roll_number=roll,
                is_optimal=False,
                visible_reason=visible,
            )
            remember = _clear_takeaway_for_family(family, fallback)
            counts[family] += 1
            max_length = max(max_length, len(text))
            require_text = text.lower()
            if any(phrase in require_text for phrase in vague_phrases):
                raise AssertionError(f"vague phrase leaked into {family}: {text}")
            if "1 fresh dice" in text:
                raise AssertionError(f"bad singular grammar in {family}: {text}")
            if not remember.strip():
                raise AssertionError(f"missing Remember line for {family}")

    require("840-position audit covers many coaching families", len(counts) >= 15)
    require("840-position explanations stay concise", max_length < 360)
    require("840-position audit avoids old vague language", True)
    print("AUDIT FAMILY COUNTS", dict(sorted(counts.items())))
    print("MAX EXPLANATION LENGTH", max_length)


def run():
    direct_family_checks()
    broad_language_audit()
    print("ALL COACHING-LANGUAGE FAMILY AUDIT TESTS PASSED")


if __name__ == "__main__":
    run()
