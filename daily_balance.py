"""Selection-only decision evidence. Never changes policy values or Practice.

Bonus sensitivity compares existing supported states with identical open boxes
and Yahtzee eligibility. It is a selection signal, not an EV decomposition.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np


@lru_cache(maxsize=1)
def decision_evidence():
    root = Path(__file__).resolve().parent
    with np.load(root / 'challenge_catalog.npz', allow_pickle=False) as catalog:
        rows = catalog['rows']
        skills = tuple(str(x) for x in catalog['skill_names'])
    with np.load(root / 'puzzle_bank.npz', allow_pickle=False) as bank:
        cards = bank['scorecards']
        keys = bank['state_keys']
    codes = rows['best_hold_code'].astype(np.int64)
    counts = np.array([(codes >> (3 * i)) & 7 for i in range(6)]).T
    sizes = counts.sum(axis=1)
    distinct = (counts > 0).sum(axis=1)
    states = rows['state_index']
    upper = cards[:, :6]
    totals = np.maximum(upper, 0).sum(axis=1)
    maximum = totals + ((upper < 0) * np.arange(1, 7) * 5).sum(axis=1)
    alive = (totals < 63) & (maximum >= 63)
    face = counts.argmax(axis=1)
    builds_upper = alive[states] & (distinct == 1) & (upper[states, face] < 0)
    # A singleton is often an open-board flexibility move, not a bonus lesson.
    bonus = builds_upper & (sizes >= 2) & (sizes <= 4)
    straight = rows['skill_code'] == skills.index('Straight Structure')
    for width, column, starts in ((4, 9, range(3)), (5, 10, range(2))):
        for start in starts:
            fits = counts[:, start:start + width].sum(axis=1) == sizes
            straight |= (distinct == sizes) & (sizes >= 3) & fits & (cards[states, column] < 0)

    sensitive = np.zeros(len(rows), dtype=bool)
    groups = {}
    for i, key in enumerate(keys):
        groups.setdefault(int(key) & (8191 | (1 << 19)), []).append(i)
    # Fixed, small offline-sized table; vectorized per state/roll, cached once.
    with np.load(root / 'exact_policy.npz', allow_pickle=False) as policy:
        policy_keys = policy['state_keys']
        policy_indices = np.searchsorted(policy_keys, keys)
        for roll in (1, 2):
            values = policy[f'roll{roll}_hold_values']
            best_ids = policy[f'roll{roll}_best_hold_ids']
            for siblings in groups.values():
                if len(siblings) < 2:
                    continue
                for state in siblings:
                    selected = np.flatnonzero(bonus & (states == state) & (rows['roll_number'] == roll))
                    if not len(selected):
                        continue
                    rid = rows['roll_id'][selected]
                    sid = int(policy_indices[state])
                    original = values[sid, rid]
                    held = best_ids[sid, rid]
                    for other in siblings:
                        if totals[other] == totals[state]:
                            continue
                        oid = int(policy_indices[other])
                        changed = values[oid, rid]
                        # Compare the same two legal holds within both states.
                        margin_change = (original - original[np.arange(len(rid)), held, None]) - (changed - changed[np.arange(len(rid)), held, None])
                        finite = np.isfinite(margin_change)
                        relevant = original >= original[np.arange(len(rid)), held, None] - 4.0
                        sensitive[selected] |= np.any(finite & relevant & (np.abs(margin_change) >= 0.50), axis=1)
    return straight.tolist(), bonus.tolist(), sensitive.tolist(), codes.tolist()
