# v44.0 final validation

Verified through November 13, 2026. **122 focused tests pass** across the retained
focused runs and the final five-test full-app recheck. Combined regression
evidence is **95 of 112 suites passing**, with exactly the same **17 pre-existing
failures** recorded before this project began. There are no new unresolved test
failures. This is not a claim that the inherited suite is entirely green.

## Focused coverage

| Area | Passing tests | What was exercised |
|---|---:|---|
| Weekly engine | 48 | All categories, ordinary hands against the independent scorer, bonuses/Joker rules, 13 rounds, identical holds, deterministic pools, expiry and restoration |
| Weekly PostgreSQL | 34 | One official game, concurrent actions, idempotent retries, revoked sessions, locked results, cutoff after lock waits, bounded replays and database permissions |
| Weekly Streamlit UI | 14 | Complete game, hold/reroll/score, explicit zero, resume, failed-response retry, stale clicks, membership changes and replay isolation |
| Weekly login helpers | 3 | Existing remembered login and transient sessions without remembering |
| Daily Six | 8 | Eight weeks of selection, independent caches, old identities, both lengths in memory, reviews, medals, streaks, share text and separate awards |
| Daily PostgreSQL | 10 | Exact combined install SQL, reruns, persistent activation, legacy records, both lengths through the production store, invalid answer/completion refusal, simultaneous registration and role permissions |
| Full production app UI | 5 | Real sign-in, six- and ten-puzzle journeys, review/edit/submit, Daily/Weekly/Practice/My Player navigation, sign-out/revocation another player's clean session, and interrupted-start recovery from both Daily and yesterday's recap |

The database tests use isolated PostgreSQL and synthetic players. The full-app
tests execute the actual `app.py` through Streamlit AppTest with the production
Daily and Weekly stores. A test adapter replaces the Supabase HTTP transport;
the production SQL and game logic run unchanged.

The regression total combines the final all-suite run with targeted reruns after
updating old source-text assertions for the approved navigation, format, and
release-label changes. All original failure logs, recheck logs, source hashes,
and the original baseline manifest are retained in the working checkpoint.
Historical challenge-output fingerprints and exact-policy checks remain enforced.

## Browser and final-change verification

Local Chromium, with its sandbox enabled, exercised the real app and production
stores against synthetic local PostgreSQL fixtures. Portrait widths 320, 390,
and 430 pixels and a 1280-pixel desktop width passed horizontal-overflow checks.
Rendered screens were visually inspected. Weekly dice fit one row with measured
tap targets at least 44 by 44 pixels.

Weekly: start, hold, reroll, all 13 scoring rounds, expanded scorecard, locked
result, friend standings, saved-round review, replay completion and unchanged
official score. Daily: sign-in, six questions, navigation through Weekly and
Practice, review, edit, final submission, six grades, share preview, Weekly
resume, sign-out and a second player's clean session.

Browser testing found and fixed the following issues: the six-question introduction still
said five decisions per roll stage; and a background rerun could interrupt a
Daily start after creating the attempt. The start button now records pending
intent in a callback, then completes the idempotent create/resume before clearing
it. Both the normal intro and yesterday's recap use this path. A regression test
reproduced the lost start before the fix. All five full-app UI tests now pass,
including legacy ten-question completion and interrupted-start recovery from
both entry points. Four affected historical UI/ceremony/login suites also pass.
Sign-in also now captures its submitted intent in a form callback so a component
rerun cannot consume the submission. Credentials are cleared on authentication
success or handled failure. A fifth full-app test forces an intervening rerun
and verifies successful sign-in as well as rejection of an incorrect PIN.
Five affected historical login suites were rechecked after this correction.
No broad all-suite rerun was needed for these localized changes.

Browser-checker corrections included waiting for Streamlit to settle, avoiding
stale controls during mode changes, and using keyboard selection for the editable
review selector. These are test changes, not changes to the app's selector.

## Installation checks and limits

- **Physical device:** Chromium phone-size emulation is not a physical iPhone or
  Safari test. Check the installed app on your phone using INSTALL_v44_0.md.
- **Live hosting:** no production SQL, GitHub push, live deployment, real-player
  official attempt, Supabase HTTP gateway test or real network-latency test occurred.
- **Optional exact Weekly coaching:** saved-round review is included, but full-game
  exact strategy grading is not. The frozen policy lacks some full-game states.
  No coaching or future dice are revealed during official play.

## Historical regression failures

Thirteen suites refer to old classroom-app screens rather than this Yahtzee app:
`ui_contract_tests.py`, `v2_ui_contract_tests.py`, `v2_1_research_pin_tests.py`,
`v2_2_weekly_mystery_tests.py`, `v2_2_1_roster_management_tests.py`,
`v2_2_2_roster_ui_tests.py`, `v2_2_3_fast_bulk_delete_tests.py`,
`v2_2_4_student_leaderboard_privacy_tests.py`,
`v2_2_5_classroom_load_reliability_tests.py`, `v2_2_6_focus_speed_tests.py`,
`v2_3_classroom_clarity_tests.py`, `v2_4_persistent_login_tests.py`, and
`v2_5_student_experience_tests.py`.

The other four retain their original failures:

- `v43b_coaching_semantic_audit_tests.py`: an older Daily takeaway source contract.
- `v43b_phase2k14_streamlit_interaction_tests.py`: its existing fixture's
  `session_state.filtered_state` access is incompatible with this Streamlit runtime.
- `v43b_share_placement_hotfix_tests.py`: an outdated source substring lookup.
- `v43b_social_results_cleanup_tests.py`: an outdated source substring lookup.

No suite was removed to improve the reported pass count.

## Daily composition and historical safety

New six-puzzle days contain one Opening, two Midgame, two Late Game, and one
True Endgame situation; three first-roll and three second-roll decisions; one
Clear, two Medium, two Hard, and one Punishing or Knife-edge decision. The
56-day sample contained five or six skill families per day (mean 5.77), at most
two repetitions of a family, unique scorecard states, and deterministic IDs.
The selector does not truncate the first six from a legacy ten-puzzle set.

Fewer decisions provide fewer opportunities to separate players, so more ties
are possible. This is a design expectation, not an observed player-study result.
Existing two-decimal Points Lost ranking and shared ties remain. Daily medals
are awarded within each date; old and new total losses are not mixed into a new
cross-format leaderboard. Perfect Ten remains exclusive to ten exact answers;
six exact answers receive Perfect Six.

The first updated Daily load schedules the next Eastern midnight. Registered
challenge IDs, puzzle order and versions are authoritative, including an unusual
already-registered future ten-puzzle day. Reruns do not move the boundary. Old
app code cannot create a conflicting ten-puzzle day after cutover. Historical
ten-question answer bounds remain valid; six-question bounds and completion
are checked against the registered puzzle array.

## Preserved math and Weekly fairness

`exact_mode.py`, `exact_policy.npz`, the legacy engine, and binary banks are
unchanged. Exact-policy SHA-256:
`cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b`.

Weekly uses private, versioned HMAC-SHA256 pools for each round and roll stage.
Rejection sampling maps accepted bytes 0–251 evenly to 1–6. The first k values
are used for k rerolled dice, and equal held multisets yield equal results.
Different strategies can produce different realized hands from the common
opportunities. Only observed dice leave the trusted server. Sharing spoilers
after replay is socially possible; this is not a spoiler-proof tournament.

## Local reproduction for developers

Use Python 3.12 and install `requirements-dev.txt`. Verification used Streamlit
1.67.0, supabase 2.34.1, NumPy 2.3.5, pandas 2.2.3, pgserver 0.1.4, and
psycopg 3.3.8. No new production dependency was added.

```sh
python weekly_game_tests.py
python weekly_postgres_tests.py
python weekly_ui_tests.py
python weekly_auth_tests.py
python daily_six_tests.py
python daily_six_postgres_tests.py
python daily_six_ui_tests.py
python run_release_tests.py --logs /tmp/yahtzee-release-tests --workers 3
```

The last command retains the documented 17 inherited failures. Local PostgreSQL
binaries omit pgcrypto; the fixture omits the baseline extension creation only,
using PostgreSQL 16's built-in UUID function. The new installation SQL itself
runs unchanged, including its service-role permissions and triggers.
