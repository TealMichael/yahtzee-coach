# Yahtzee Coach v43B Phase 2K.12.4 — Restored Large Dice Hotfix

This is the full current app. It preserves Phase 2K.12 scorecard realism, the Phase 2K.12.1 creator/hair expansion, and the Phase 2K.12.2 duplicate-dice selection fix.

## What changed
- Daily and Practice still use five independently keyed physical-die buttons.
- The button visuals now restore the exact large-dice sizing from the pre-bug picker instead of the tiny native-button glyphs seen in Phase 2K.12.3.
- Held dice still turn red and duplicate values remain independent.

## Regression example
For dice `2,3,3,4,4`, tapping the 2, one 3, and one 4 still saves exactly `2,3,4`, but the dice look like the large approved picker again.

## Scope
Runtime change from Phase 2K.12.3: `app.py` only.
No strategy math, puzzle generation, scorecard realism, persistence, avatar/medal logic, or Supabase schema changed.

## Deployment
No Supabase migration. Copy the contents of `UPLOAD_TO_GITHUB` into the repo, commit, and push with GitHub Desktop.
