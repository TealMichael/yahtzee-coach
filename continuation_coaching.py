"""Verified now-versus-later explanations; never used to rank or grade holds.

The small offline evidence file is validated against the locked policy. It covers
67 scorecards with Full House, both straights and Chance closed. Unsupported
positions and comparisons keep their existing explanation.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np


@lru_cache(maxsize=1)
def _evidence():
    with np.load(Path(__file__).with_name("continuation_evidence.npz"), allow_pickle=False) as data:
        return (
            {int(key): i for i, key in enumerate(data["state_keys"])},
            {int(code): i for i, code in enumerate(data["hold_codes"])},
            data["stats"].copy(),
        )


def _code(hold):
    return sum(tuple(hold).count(face) << (3 * (face - 1)) for face in range(1, 7))


def explain_continuation(state_key, left, right, roll_number, winner_side, edge):
    """Return prose only when verified later value outweighs immediate points."""
    if roll_number not in (1, 2) or not np.isfinite(edge):
        return None
    try:
        states, holds, stats = _evidence()
        pair = stats[states[state_key], roll_number - 1, [holds[_code(left)], holds[_code(right)]]]
    except (OSError, ValueError, KeyError):
        return None
    winner_index = 0 if winner_side == "left" else 1
    winner, other = pair[winner_index], pair[1 - winner_index]
    # A changed model or an unrelated comparison must not inherit this lesson.
    if abs(float(winner[0] - other[0]) - edge) > 0.0001:
        return None
    now_cost = float(other[1] - winner[1])
    later_gain = float((winner[0] - winner[1]) - (other[0] - other[1]))
    if now_cost < 0.10 or later_gain < 0.10:
        return None

    winning_hold = tuple(left if winner_index == 0 else right)
    other_hold = tuple(right if winner_index == 0 else left)
    def name(hold):
        return "Rerolling everything" if not hold else "Keeping " + ", ".join(map(str, hold))

    if (state_key & 63) == 63 and winning_hold == (1,) and winner[3] > other[3] + 0.05 and other[2] > winner[2] + 0.05:
        reason = "The 1 gives a weak finish a useful home in Ones, leaving the higher upper boxes for better turns. "
    else:
        reason = "A bigger score now can use up a box that is worth saving for a better turn. "
    summary = (
        reason
        + f"{name(other_hold)} earns about {now_cost:.2f} more points this turn, but "
        + f"{name(winning_hold).lower()} leaves about {later_gain:.2f} more expected points for later. "
        + f"That leaves a {edge:.2f}-point edge."
    )
    if edge <= 0.10:
        summary += " These choices are effectively tied."
    takeaway = "" if edge <= 0.10 else "Consider both the points you score and the boxes you leave for later."
    detail = (
        "These averages choose the best scoring box after seeing the final dice; they do not commit to one box in advance. "
        + " ".join(
            f"{name(hold)}: {values[1]:.3f} points this turn + {values[0] - values[1]:.3f} expected points later = {values[0]:.3f} remaining points."
            for hold, values in zip((left, right), pair)
        )
        + " Upper bonuses earned on this turn count in this turn's points; bonuses earned later count in later points. "
        + ("After Roll 2, the hold can change before the final reroll. " if roll_number == 1 else "")
        + "Figures are rounded. These combined totals are separate from the individual category paths in the table."
    )
    return summary, takeaway, detail
