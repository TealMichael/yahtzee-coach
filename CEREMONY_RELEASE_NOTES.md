# v43B Phase 2K.14.9 — Welcome Back Celebration

Based literally on the delivered 2K.14.8 full-app ZIP.

## What changes
- Midnight-blue stage with warm spotlights, preserving Pixel Mike and the saved player avatar.
- Personal welcome and the existing result-specific gold, silver, bronze, and tie headlines.
- Yesterday’s podium reveals bronze, silver, then gold; final columns stay gold/silver/bronze with names beneath medals.
- Medal lift and shine for medal winners; a brief confetti burst for gold only.
- Non-podium finishers see their actual best-hold count when present in the existing results.
- New-day invitation at the end. Animation settles after four seconds; tap, Skip, or Escape finishes it immediately.
- Reduced-motion displays the finished content immediately. No sound, external fonts, images, video, or new data requests.
- The existing native Play Today’s 10 button moves above the ceremony, available without waiting or scrolling past the animation.

## Scope and behavior
Only two runtime files change: app.py and retro_podium.py. In app.py, only the release label and render_yesterday_final_standings_if_needed change. Existing empty-result and solo-group behavior is preserved: no empty podium or invented social medals. Ceremony frequency, group selection, standings, and seen-state persistence remain as before.

Strategy, rankings, Points Lost, Daily composition, comparison cards, Practice, authentication, database queries, avatar artwork, medal-award calculations, dependencies, and the 2K.14.8 performance improvements are unchanged.

## GitHub browser installation
Use the changed-files ZIP when your repository is already on 2K.14.8. Extract it locally, open UPLOAD_TO_GITHUB, and upload its contents into the existing repository root with Add file → Upload files. Do not upload the ZIP itself or create a nested UPLOAD_TO_GITHUB folder. Commit all changed files together.

The full ZIP is the complete backup/install package. No Supabase SQL, secrets, or account setup is required.

## Why the upload includes tests
Older regression suites assert the literal current version and ceremony artifact hash. Those assertions are advanced to this release; the former light-stage/no-confetti visual assertions are updated for the approved design. Other test behavior remains intact. A new ceremony regression covers personal outcomes, ties, escaping, skip/reduced-motion hooks, and the immediately available Play entry.

## Commit message
v43B Phase 2K.14.9 - add a personal welcome-back celebration
