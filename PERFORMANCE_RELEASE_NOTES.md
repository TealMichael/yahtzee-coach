# v43B Phase 2K.14.8 — Performance + Complete History

Baseline: the literal working v43B Phase 2K.14.7 full-app ZIP.

## What changed

- Remembered login fetches the session and related public player fields together: one database request instead of two. Token hashing, expiry compatibility, indefinite sessions and revocation checks remain intact. No PIN hash is needed for this path.
- Daily resume fetches an attempt and its saved answers together: one request instead of two. Answers retain question-number ordering, saved-score verification, completion state and next-question behavior. Starting a Daily benefits from this same combined read; existing creation and uniqueness safeguards remain.
- Completed results reuse their loaded group-member snapshot for the friend-management section. If its group selector changes to another group, the normal lookup still runs for that group.
- Completing a Daily invalidates only its affected group standings/statistics and the player's current streak entry. Unrelated avatar profiles, medal histories and other groups/dates stay cached. Group creation/joining retains the existing broader refresh. A cache-refresh lookup failure does not report a successfully committed Daily as a failed submission.
- A bounded 4,096-entry cache reuses exact final-dice/category scoring facts. The original arithmetic and rules are unchanged. The comparison table, wording and math stay identical.
- Medal and participation-streak history reads retrieve all pages instead of relying on one API response. Pages advance by unique ID; challenge-date lookups use batches of at most 100 IDs to keep request URLs bounded. The reader handles response limits smaller than its requested page size.

## Why the history change matters

Supabase commonly caps a response at 1,000 rows. Ten daily players can accumulate that many group attempts in roughly 100 days. The prior medal-history query could then use incomplete history. This patch preserves the existing ranking, competition ties, joining dates, cutoff dates and official-challenge-selection rules while reading the complete input. It does not recalculate or overwrite stored results. Medal totals may correctly increase if older rows were previously omitted by the response cap.

## What did not change

Only three runtime files changed: app.py, supabase_daily_store.py and exact_mode.py. Test changes include the current release label, approved auth-query fixtures, updated fingerprints for changed files, and the new performance regression.

No changes to the strategy policy, hold rankings, Points Lost, grades, puzzle bank, Daily selection/balance/date boundaries, scorecard realism, Daily Ten flow, Practice flow, comparison layout, coaching wording, dice controls, avatars, ceremony presentation, login persistence, admin identity, PIN-reset behavior or database schema. All existing stored account/game data remains in place.

The final-dice scoring calculation body is AST-identical to 2K.14.7. Only its invocation is cached. No heuristic replacement and no weakened exact-policy integrity checks.

## Verification

- New regression verifies one-read remembered login and one-read Daily resume, including tampered/expired/revoked tokens, answer ordering and completion state.
- 1,200 group attempts tested under API caps of 17, 1,000 and 10,000 rows. Gold/silver/bronze totals and 1,1,3 competition ties remain correct.
- 1,201-day participation streak preserved; an intervening unfinished day breaks it correctly.
- Scoped cache invalidation tested across multiple groups and an unavailable group lookup.
- All 3,528 legal final-roll/category scoring facts compare exactly; cached size remains bounded.
- 280 complete coaching reports over 14 Daily sets compared with caching enabled/disabled. Report text and all non-timing metadata match.
- Full legacy suite includes Daily/Practice UI, auth/reset, coaching, puzzle balance, realism and the exhaustive 3,669,120-hold audit. The release handoff reports the observed final ZIP pass count.

Tests use controlled backend responses and Streamlit AppTest. Live Supabase round-trip latency and physical iPhone timing were not measured. No particular tap-to-ready speedup is promised. The cache mainly helps cold calculations; already-warm calculations were already fast.

Exact-policy SHA-256 remains:
`cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b`

## Install from GitHub's browser

1. Use the browser-upload changed-files ZIP over the installed 2K.14.7 version.
2. Extract it. Open the existing repository folder containing app.py.
3. Choose Add file → Upload files, then upload the files INSIDE UPLOAD_TO_GITHUB. Do not upload the ZIP or create an extra enclosing folder. Keep every other repository file.
4. Commit using the message below and allow Streamlit to restart.

**No new Supabase migration, secrets edit or admin setup is required.** Keep YAHTZEE_ADMIN_PLAYER_ID and existing Supabase settings exactly as they are. Historical SQL files in the full package do not need to be rerun for this update. No Daily puzzle schedule change or activation date.

The full current app is also included as a complete release copy.

## GitHub commit

```text
v43B Phase 2K.14.8 - reduce repeated reads and preserve complete history
```
