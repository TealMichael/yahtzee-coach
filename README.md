# Yahtzee Coach v43B Phase 2K.12.1 — Mobile Creator Readability Hotfix

This is the full current app. It preserves Phase 2K.12 scorecard realism and all earlier game/social/avatar work.

## What changed
- Character creator no longer uses horizontally squeezed Streamlit pills for categories or choices.
- Creator now uses two full-width, mobile-safe select boxes: one for the category and one for the option.
- Full labels such as `Long Waves`, `White Headband`, and `Purple Skirt` remain readable on narrow phones.
- Live avatar preview, Randomize, Save Player, medal history, and all avatar choices are unchanged.

## Scope
Runtime change from Phase 2K.12: `app.py` only.
No Yahtzee strategy, puzzle generation, scorecard-realism logic, persistence, avatar artwork, medal logic, or Supabase schema changed.

## Deployment
No Supabase migration. Upload the contents of `UPLOAD_TO_GITHUB` to the repo root, or when updating directly from 2K.12, replacing `app.py` is sufficient.
