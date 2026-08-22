# Yahtzee Coach v43B Phase 2K.12.5 — Exact Old Dice Restoration Hotfix

This is the full current app. It preserves Phase 2K.12 scorecard realism, Phase 2K.12.1 creator/hair work, and the duplicate-dice correctness fix while restoring the exact pre-fix dice renderer.

## What changed
- Daily and Practice once again use the same large `st.pills` dice renderer that was live before the duplicate-dice fix.
- The old pill CSS block is byte-for-byte identical to the Phase 2K.12.1 working version.
- Duplicate dice remain independent because the five pill options are now unique underlying strings; the old `format_func` path is no longer used.
- Back/Edit clears and restores the new pill widget state correctly.

## Regression example
For dice `2,3,3,4,4`, tapping the 2, one 3, and one 4 saves exactly `2,3,4`. Visually, the dice are the same large square dice from the pre-fix build.

## Scope
Production/runtime change from Phase 2K.12.4: `app.py` only.
No strategy math, puzzle generation, scorecard realism, persistence, avatar/medal logic, or Supabase schema changed.

## Deployment
No Supabase migration. Copy the contents of `UPLOAD_TO_GITHUB` into the repo, commit, and push with GitHub Desktop.
