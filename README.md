# Yahtzee Coach v43B Phase 2K.13 — Pure Performance Pass

This is the full current app based on the known-good Phase 2K.12.5 build. Phase 2K.13 changes only internal performance behavior; gameplay, puzzle selection outputs, UI, scoring, coaching, persistence, avatars, medals, and Supabase behavior are preserved.

## What changed
- Cache the deterministic Daily 10 once per date for the shared Streamlit process, then deep-copy it for each player session.
- Reduce repeated pure-Python work inside the Daily selector without changing any scoring rule, RNG call, or candidate preference.
- Remove tracked Python bytecode/cache files and add `.gitignore` protection so they do not return.

## Measured effect
On the same benchmark environment:
- Five uncached Daily dates averaged about 494.5 ms each in Phase 2K.12.5 and about 348.7 ms in Phase 2K.13.
- Asking for the same Daily again fell from about 489.9 ms to about 0.15 ms because the deterministic template is reused.
- Repository payload drops by roughly 0.8 MB by removing `__pycache__` artifacts.

## No behavior drift
- Key historical/current/future Daily challenge-set IDs remain locked.
- A 31-date comparison produced identical Daily challenge IDs against Phase 2K.12.5.
- A seeded 50-puzzle Practice sequence was identical against Phase 2K.12.5.
- The exact strategy engine and protected `.npz` artifacts are byte-for-byte unchanged.

## Deployment
No Supabase migration. Replace/update the repository from `UPLOAD_TO_GITHUB`, commit, and push with GitHub Desktop.
