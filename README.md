# Yahtzee Coach v43B Phase 2K.13.1 — Auto-Login Fast Path

This is a narrow performance patch on top of Phase 2K.13. It changes only the remembered-login startup path. Gameplay, UI, puzzles, scoring, exact strategy, persistence behavior, avatars, medals, and Supabase schema are unchanged.

## What changed
- The Components-v2 localStorage bridge now mirrors a valid remembered-device token into the existing secure SameSite first-party cookie.
- On future fresh browser/Streamlit connections where that cookie is present, the app authenticates the cookie before mounting the localStorage bridge.
- A successful cookie restore skips the localStorage component entirely, avoiding its browser-to-Python state update and extra script rerun.
- A stale/invalid cookie does not block localStorage recovery; the app falls back to the durable localStorage token exactly as before.
- Sign-out still revokes the server-side device session and clears both browser credentials.

## First-launch behavior after deployment
Existing remembered users may still take the old localStorage path once after this patch if their browser does not already have the cookie. That successful localStorage read now heals the cookie. The next fresh launch is the meaningful speed test.

## Safety
No Supabase migration. All gameplay/data engines and protected NPZ files are byte-for-byte unchanged from Phase 2K.13.

## Tests
58/58 automated suites pass, including the exhaustive 3,669,120 legal-hold exact-policy audit.
