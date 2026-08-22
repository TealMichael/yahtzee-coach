# Yahtzee Coach v43B Phase 2K.12 — Scorecard Realism

Phase 2K.12 makes generated puzzle scorecards feel more like believable Yahtzee games without changing the exact strategy engine or flattening the puzzle pool.

## What changed

- Added a conservative scorecard-plausibility filter for normal Simulated Game puzzles.
- A simulated scorecard is filtered only when a filled category mathematically proves an earlier Yahtzee while the Yahtzee box is still open.
- This catches distracting histories such as Sixes = 30 or Fives = 25 with Yahtzee still open, plus the small set of 3K/4K/Chance totals that can only come from five matching dice.
- Curated Edge Case scorecards remain exempt so deliberately unusual teaching positions stay available.
- Practice uses the realism filter immediately.
- Daily uses the filter forward-only beginning 2026-08-22. August 21 and all earlier Dailies remain unchanged.
- Added a safe selector fallback for rare dates where a hard Daily slot has only Joker candidates even though Joker was not in that week's soft family target. Hard composition rules remain locked.

## Variety impact

The audit found only 14 of 420 scorecard contexts with an indisputable passed-up-open-Yahtzee history. After filtering them, 193,551 of 200,140 Daily-eligible situations remain available (96.7%).

The locked Daily structure remains:
- 5 Roll 1 / 5 Roll 2
- 2 Opening / 3 Midgame / 3 Late Game / 2 True Endgame
- 2 Clear / 3 Medium / 2 Hard / 2 Punishing / 1 Knife-edge
- 9 Simulated Game / 1 Curated Edge Case
- Bank It or Break It remains occasional and balanced

## Strategy safety

Unchanged:
- `yahtzee_engine.py`
- `exact_runtime.py`
- `exact_mode.py`
- `exact_policy.npz`
- `puzzle_bank.npz`
- `challenge_catalog.npz`
- persistence stores, player/avatar system, medal system, and UI from 2K.11.3

Exact-policy SHA-256 remains:
`cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b`

## Supabase

No Supabase migration is required for Phase 2K.12.
