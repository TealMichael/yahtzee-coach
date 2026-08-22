# Yahtzee Coach v43B Phase 2K.12.2 — Duplicate Dice Selection Hotfix

This is the full current app. It preserves Phase 2K.12 scorecard realism, the Phase 2K.12.1 creator/hair expansion, and all earlier game/social/avatar work.

## What changed
- Daily and Practice no longer use `st.pills` to select dice.
- Each physical die is now its own independently keyed Streamlit button.
- Matching dice remain visually identical, but tapping one duplicate cannot select another duplicate.
- Saved holds, Back/Edit, exact grading, and persistence continue to use the same hold-value multiset as before.

## Regression example
For dice `2,3,3,4,4`, tapping the 2, one 3, and one 4 saves exactly `2,3,4`.

## Scope
Runtime change from the live Phase 2K.12.1 Hair Expansion build: `app.py` only.
No strategy math, puzzle generation, scorecard realism, persistence, avatar/medal logic, or Supabase schema changed.

## Deployment
No Supabase migration. Copy the contents of `UPLOAD_TO_GITHUB` into the repo, commit, and push with GitHub Desktop.
