from __future__ import annotations

"""Phase 2K.8.3 coaching semantic audit.

The exact policy determines every ranking. These tests only verify that the
player-facing language describes the selected hold and scorecard truthfully.
"""

from pathlib import Path

import yahtzee_engine as yc
from exact_mode import (
    ExactPolicyTable,
    _clear_takeaway_for_family,
    _hold_intent,
    _live_paths_for_hold,
    _pattern_lines,
    _simple_why_with_family,
    _upper_bonus_context,
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


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print("PASS", name)


def direct_checks():
    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    check(
        "Daily Remember uses the full teaching takeaway instead of only the lesson title",
        'takeaway_items = extract_section(report, "Teaching takeaway:")' in app_text
        and 'takeaway.split(": ", 1)[1]' in app_text,
    )

    # Exact live case reported by a tester: two pairs were incorrectly described
    # as a 3K/4K/Yahtzee plan even though Full House was the obvious immediate idea.
    c = {
        "ones": None, "twos": None, "threes": None, "fours": None,
        "fives": 10, "sixes": 18,
        "three_of_a_kind": None, "four_of_a_kind": None, "full_house": None,
        "small_straight": None, "large_straight": 40, "yahtzee": None, "chance": None,
    }
    report, meta = __import__("exact_mode").build_exact_report(
        POLICY,
        dice=[2, 5, 5, 6, 6],
        scorecard=c,
        user_hold=[5, 5, 6, 6],
        roll_number=1,
    )
    check("reported two-pair case remains exact keep 6,6", meta["optimal_hold"] == "keep 6, 6")
    check("reported two-pair case remains about 1.70 points behind", 1.69 < meta["points_lost"] < 1.71)
    check("reported two-pair case names Full House intent", "natural Full House chase" in meta["simple_why"])
    check("reported two-pair case no longer mislabels user plan as generic matching chase", "Your hold is mainly aiming at Three of a Kind" not in meta["simple_why"])
    check("reported two-pair case explains extra fresh dice", "3 fresh dice" in meta["simple_why"])

    # Two pairs only create a direct Full House try when exactly four dice are held.
    c = card({})
    check("four-die two-pair intent is direct Full House", "direct Full House path" in _hold_intent([2, 2, 5, 5], c))
    locked = _hold_intent([2, 2, 5, 5, 6], c)
    check("five-die two-pair intent does not claim active Full House chase", "stops the reroll" in locked and "actively chasing" in locked)
    check("two-pair direct paths prioritize Full House", _live_paths_for_hold([2, 2, 5, 5], c, limit=1) == ["Full House"])

    c_fh_closed = card({"full_house": 25})
    closed_intent = _hold_intent([2, 2, 5, 5], c_fh_closed)
    check("two pairs with Full House closed say it is filled", "Full House is already filled" in closed_intent)
    check("pattern praise does not claim Full House when box is closed", all("Full House" not in line for line in _pattern_lines([2,2,5,5,6], [2,2,5,5], c_fh_closed)))

    # Four matching dice should not tell players they are one die from a Yahtzee
    # when the Yahtzee box is already gone.
    c_y_closed = card({"yahtzee": 0})
    fam, text, remember = why(c_y_closed, [6, 6], [6, 6, 6, 6], 2)
    check("four-matching family still selected", fam == "four_matching")
    check("four-matching explanation respects closed Yahtzee", "one matching die from Yahtzee" not in text)
    check("four-matching Remember line respects closed Yahtzee", "one die from Yahtzee" not in remember)

    # A triple should surface Full House before remote Yahtzee routes when FH is open.
    triple_paths = _live_paths_for_hold([5, 5, 5], card({}), limit=4)
    check("triple direct paths include Full House", "Full House" in triple_paths)

    # Extra-Yahtzee language should acknowledge forced-upper/Joker rules rather
    # than implying Joker scoring always applies immediately.
    fam, text, remember = why(card({"yahtzee": 50}), [6], [6, 6, 6], 1)
    check("extra-Yahtzee language names forced-upper/Joker rules", "forced-upper/Joker" in text and "forced-upper/Joker" in remember)

    # Mixed pair holds should admit the extra kept die instead of claiming every
    # loose die is being rerolled.
    mixed = _hold_intent([3, 3, 5], card({"threes": 9}))
    check("mixed pair intent names extra held singleton", "plus 5" in mixed and "instead of rerolling all the loose values" in mixed)

    # A triple should never be called merely a pair in the pair-vs-straight or
    # dead-bonus language families.
    c = card({"threes": 9, "three_of_a_kind": 15, "full_house": 25, "chance": 20})
    fam, text, _ = why(c, [3, 3, 3], [3, 4, 5], 2)
    check("triple-vs-straight language does not downgrade triple to pair", "Your pair of 3s" not in text)


def broad_semantic_audit():
    checked = 0
    family_counts = {}
    # 4 deterministic rolls per state x both roll numbers. For every position,
    # inspect a spread of legal non-best holds so rare structures are represented.
    for state_index in range(420):
        scorecard = scorecard_for_state_index(state_index)
        bonus = _upper_bonus_context(scorecard)
        for offset in (7, 61, 137, 211):
            dice = tuple(int(x) for x in POLICY.rolls[(state_index * 37 + offset) % 252])
            for roll in (1, 2):
                results = POLICY.analyze(scorecard, dice, roll)
                best = tuple(results[0]["hold"])
                sample_indices = sorted(set([1, min(3, len(results)-1), min(7, len(results)-1), len(results)-1]))
                _, visible, fallback = _visible_strategy_reason(scorecard, best, roll)
                for idx in sample_indices:
                    if idx <= 0 or idx >= len(results):
                        continue
                    user = tuple(results[idx]["hold"])
                    family, text = _simple_why_with_family(
                        scorecard, user, best,
                        roll_number=roll, is_optimal=False, visible_reason=visible,
                    )
                    remember = _clear_takeaway_for_family(family, fallback)
                    family_counts[family] = family_counts.get(family, 0) + 1
                    checked += 1

                    lower = text.lower()
                    if "upper bonus is out of reach" in lower or "bonus is already out of reach" in lower:
                        assert not bonus["alive"] and not bonus["earned"], (family, text)
                    if "upper bonus is already secured" in lower:
                        assert bonus["earned"], (family, text)
                    if "upper bonus is still in play" in lower:
                        assert bonus["alive"] and not bonus["earned"], (family, text)
                    if "yahtzee is already scored for 50" in lower:
                        assert scorecard.get("yahtzee") == 50, (family, text)
                    if family == "two_pair_full_house_tradeoff":
                        assert scorecard.get("full_house") is None and len(user) == 4, (user, text)
                        assert "Full House" in text
                    if family == "two_pair_locked_fifth":
                        assert scorecard.get("full_house") is None and len(user) == 5, (user, text)
                    if family == "two_pair_no_full_house":
                        assert scorecard.get("full_house") is not None, (user, text)
                    if family == "two_pair_full_house":
                        assert scorecard.get("full_house") is None and len(best) == 4, (best, text)
                    if family == "four_matching" and scorecard.get("yahtzee") not in (None, 50):
                        assert "one matching die from Yahtzee" not in text, text
                    assert "1 fresh dice" not in text
                    assert remember.strip()

    check("broad semantic audit inspects thousands of exact coaching contrasts", checked >= 12000)
    check("broad semantic audit covers many coaching families", len(family_counts) >= 15)
    print("SEMANTIC AUDIT POSITIONS", checked)
    print("SEMANTIC AUDIT FAMILY COUNTS", dict(sorted(family_counts.items())))


def run():
    direct_checks()
    broad_semantic_audit()
    print("ALL COACHING SEMANTIC AUDIT TESTS PASSED")


if __name__ == "__main__":
    run()
