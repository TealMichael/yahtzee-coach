# Yahtzee Coach v43B Phase 2K.11.2 — Pre-Deployment Player Polish

Phase 2K.11.2 finishes the **My Player + Personal Medal Moments** retention feature before deployment. This is still presentation/social icing only; the Yahtzee game and exact strategy layer are frozen.

## What changed

- **Broader character creation.** Two unlabeled base character silhouettes (`Classic` and `Soft`) work with every hairstyle, outfit, skin tone, accessory, and shoe choice.
- **More hairstyle representation.** Ponytail, bob, long waves, high bun, and braids join the existing curly/spiky/short/sweep/buzz choices.
- **More outfit variety.** Teal Sport and Purple Skirt join the existing six looks.
- **No gender gate.** Players simply choose the sprite pieces that look right to them; the app never asks Male/Female.
- **Per-group medal cabinet.** My Player now has its own group selector when a player belongs to multiple friend groups. Medal totals stay separate by group, and browsing this selector cannot switch the active Daily competition group.
- **Medals sit directly under the player preview** in My Player, matching the personal medal moment hierarchy.
- **Avatar render safety regression.** Every creator option is rendered in idle, medal-receive, and celebration poses during automated testing.
- **Hard game-freeze hash guards.** The regression suite now fails if any protected game/strategy file changes during a presentation-only release.

## Supabase

There is **no new Phase 2K.11.2 migration**. The avatar JSON column added by Phase 2K.11 is flexible enough to accept the new `style` field and new option values.

If you have **not** already run Phase 2K.11, run `RUN_THIS_ONCE_IN_SUPABASE_Phase2K11.sql` once before deployment. If it is already applied, do nothing in Supabase.

## Game / strategy freeze

Byte-for-byte unchanged from Phase 2K.11.1:

- `yahtzee_engine.py`
- `exact_runtime.py`
- `exact_mode.py`
- `puzzle_bank.py`
- `daily_challenge.py`
- `daily_store.py`
- `supabase_daily_store.py`
- `session_learning.py`
- `practice_progress.py`
- `exact_policy.npz`
- `puzzle_bank.npz`
- `challenge_catalog.npz`

Protected exact-policy SHA-256:

`cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b`
