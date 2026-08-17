# Yahtzee Coach v43B Phase 2K.8.3 — Coaching Semantic Audit

This release is a coaching-language correctness pass on top of Phase 2K.8.2. The exact policy and every strategy ranking remain unchanged; this patch only improves how the app translates exact decisions into human explanations.

## v43B Phase 2K.8.3 changes

- **Two-pair holds now read as two-pair holds.** When Full House is open, keeping two pairs is described first as the natural one-die Full House chase instead of being mislabeled as a generic Three/Four of a Kind or Yahtzee plan.
- **Two pairs with the fifth die also held are handled separately.** The coach now recognizes that holding all five leaves no fresh die for a direct Full House attempt.
- **Two pairs stop receiving Full House language after Full House is filled.**
- **Triples are no longer able to fall into a template that calls them a pair.**
- **Four matching dice no longer say “one die from Yahtzee” when the Yahtzee box is already gone.** The explanation instead names the live matching routes on the actual scorecard.
- **Triple path language now prioritizes direct live routes such as Full House before more remote matching outcomes.**
- **Dead-upper-bonus explanations are shorter and more precise.** They still make clear that a high upper die can be optimal even when 63 is impossible, without implying the dead bonus is influencing the ranking.
- **Extra-Yahtzee language now says forced-upper/Joker rules can come into play** rather than implying Joker scoring always applies immediately.
- **Mixed holds acknowledge extra dice the player kept.** A pair-plus-singleton hold is no longer described as if every loose die were being rerolled.
- **Daily “Remember” now displays the full reusable teaching takeaway**, not just a short internal lesson title. Practice already used the richer takeaway; Daily review now matches it.

## Coaching audit

The new semantic regression suite directly protects the live tester case `2,5,5,6,6` on Roll 1: keeping `5,5,6,6` is correctly recognized as a Full House chase while the exact best remains `6,6` at about 1.70 Points Lost.

In addition to the permanent regression suite, the final audit generated and checked **635,040 player-vs-exact coaching contrasts** across all 420 exact scorecard states, all 252 canonical dice rolls, both coached roll stages, and multiple non-best legal holds per position. The audit checks scorecard truth (bonus alive/dead/secured, Yahtzee status, Full House status), hold structure, grammar, and family-specific claims.

## Math / strategy

**No recommended hold changed.** `exact_policy.npz`, the puzzle bank, challenge catalog, Yahtzee engine, Daily generator, and Practice generator are unchanged. The locked exact-policy start-of-game expectation remains **254.5877272**, and the published optimal benchmark positions remain protected.

## Supabase

**No new Supabase migration is required.** Phase 2K.4 remains the latest required database migration.

## Phase 2K.8.3 live-test goal

1. Review a few Daily and Practice misses, especially pairs, two pairs, triples, and four matching dice.
2. Confirm **Why this wins** describes what the player actually held before explaining the exact alternative.
3. Confirm **Remember** is now a useful strategy sentence rather than only a short title.
4. Confirm all Phase 2K.8.2 social results, sharing, podium, login, and performance behavior is unchanged.

---

# Yahtzee Coach v43B Phase 2K.8.2 — Share Placement Hotfix

This is a surgical UI hotfix on top of Phase 2K.8.1. The spoiler-free share feature is unchanged; it is simply moved to a more natural and visible location directly beneath the player's personal Daily result summary.

## v43B Phase 2K.8.2 changes

- **Share today’s result now appears immediately below the personal result hero** and before Daily Standings.
- The intended flow is now: **Your Result → Share → Daily Standings → Group Insights → Your 10 Grades → Peek at a Friend’s Picks → Invite/manage friends.**
- **The share card itself is unchanged:** same spoiler-free grid, same native Share / Copy result behavior, same text payload, and same group-rank information.
- **Nothing else in the completed-Daily UI was changed.** The cleaned-up leaderboard, Group Insights, compact personal grades, lightweight friend peek, and yesterday podium all remain exactly as in Phase 2K.8.1.
- **No strategy, persistence, login, leaderboard-ranking, puzzle, or database behavior changed.**

## Supabase

**No new Supabase migration is required.** Phase 2K.4 remains the latest required database migration.

## Phase 2K.8.2 live-test goal

1. Finish a Daily and confirm **📤 Share today's result** is easy to find immediately beneath your result summary.
2. Confirm Daily Standings still follows directly after Share.
3. Confirm the existing share text/grid behaves exactly as before.
4. Confirm Group Insights, Your 10 Grades, friend peek, and invite/manage remain in their Phase 2K.8.1 positions.

---

# Yahtzee Coach v43B Phase 2K.8.1 — Daily Results Social UI Cleanup

This hotfix keeps the new Phase 2K.8 yesterday-podium feature but completely cleans up the completed-Daily social/results screen before the next Daily. The goal is simple: **standings first, group story second, your own grades third, optional friend curiosity last.**

## v43B Phase 2K.8.1 changes

- **Daily Standings are a leaderboard again.** Player names are no longer Streamlit buttons and the board no longer uses three squeezed columns per player. Each finisher is one consistent full-width row with rank, name, Points Lost, and best-hold count.
- **The results hierarchy is now fixed:** Daily Standings → Group Insights → Your 10 Grades → Share → Peek at a Friend’s Picks → Invite/manage friends.
- **Group Insights stay visible and fun** directly below the standings: Today’s Killer plus Everyone Nailed It / Most Solved.
- **Your 10 Grades return to compact expanders.** Each row is short (`Q4 · B · 1.94 lost`) and opens only when the player wants the full dice/scorecard/coaching review.
- **The side-by-side friend comparison dashboard is removed.** No You-vs-Friend cards, different-choice count, biggest-miss comparison sentence, or tiny five-column question grid.
- **Friend review becomes a lightweight bottom-of-page peek.** Choose a finished friend and press one button to reveal their 10 saved holds with a simple Best / Points Lost result for each question.
- **Friend picks remain spoiler-safe.** The persistence layer still refuses to return another player’s detailed choices until the viewer has completed their own Daily, and unfinished friends remain private.
- **Yesterday’s Final Standings / Podium Ceremony stays intact** and automatically benefits from the cleaner shared leaderboard rows.
- **The Phase 2K.7 scorecard readability work stays intact.** The live decision screen still uses the short labels and slightly larger score values/boxes while keeping Roll + scorecard + dice together.

## What is intentionally unchanged

- Exact solver, exact policy, and every recommended hold / Points Lost value.
- `exact_policy.npz`, `puzzle_bank.npz`, and `challenge_catalog.npz`.
- Daily puzzle generator/composition and Practice puzzle generation.
- Group ranking and tie-break rules.
- Yesterday’s podium logic.
- 30-day remembered login, performance caching, sharing, invite links, persistence, and spoiler protections.

## Supabase

**No new Supabase migration is required for Phase 2K.8.1.** Phase 2K.4 remains the latest required database migration. The included `RUN_THIS_ONCE_IN_SUPABASE_Phase2K4.sql` is only for a fresh/clean setup.

## Phase 2K.8.1 live-test goals

1. Finish the Daily on a phone and confirm **Daily Standings** is immediately easy to scan.
2. Confirm the order is **Daily Standings → Group Insights → Your 10 Grades**.
3. Open several of **Your 10 Grades** and confirm the compact row expands into the full exact coaching.
4. Open **Peek at a Friend’s Picks**, choose a completed friend, and press the peek button.
5. Confirm their 10 rows show what they kept and where they lost points without a comparison dashboard.
6. Confirm unfinished friends cannot be peeked at.
7. On the next day, confirm Yesterday’s Final Standings / podium still renders correctly with the cleaner leaderboard rows.
8. Confirm Daily play, Practice, remembered login, sharing, and exact strategy behave normally.

---

# Yahtzee Coach v43B Phase 2K.7 — Scorecard Readability + Friend Daily Reviews

This release responds directly to live tester feedback. The decision screen keeps the compact one-screen hierarchy that is working, but restores the original short Yahtzee scorecard labels and makes the score boxes/numbers slightly larger. It also adds a new social review feature: after you finish your own Daily, you can tap a completed friend's name and inspect exactly how they played all 10 questions.

## v43B Phase 2K.7 changes

- **The live scorecard returns to the original short labels:** `1s`–`6s`, `3K`, `4K`, `FH`, `SS`, `LS`, `YTZ`, and `CH`.
- **Score boxes and score values are slightly larger than Phase 2K.6.1.** The shorter labels create the room; the full scorecard remains visible without an extra click.
- **The one-screen decision hierarchy is preserved:** compact Roll stage → complete scorecard → dice. The duplicate open-category chip row remains removed.
- **Upper subtotal remains visible as `Upper: X / 63`.** It is factual score information only and does not pre-coach whether the player should chase the bonus.
- **Completed friend names are now reviewable from the Daily leaderboard.** After finishing your own Daily, tap a finished friend's name to open their result.
- **Friend review begins with a You-vs-Friend comparison** showing Points Lost, best holds, how many of the 10 choices were different, and the friend's biggest miss.
- **All 10 friend decisions are summarized at a glance.** Each question shows whether the friend found a best hold or how many Points Lost they gave up.
- **Choose any friend question for the full review:** dice, scorecard at the decision, what the friend kept, exact best hold, hold rank, Points Lost, Why this wins, Remember, and the exact top-holds detail.
- **Spoiler protection is enforced in the persistence layer.** A player cannot retrieve another member's detailed choices until the viewer has completed their own Daily, and unfinished friends remain private.
- **Friend reviews use the same audited exact-policy coaching as your own Review Your 10.** Saved friend Points Lost are rechecked against the locked exact policy before the review is shown.

## Supabase

**No new Supabase migration is required.** The existing `daily_attempts`, `daily_answers`, `players`, and `group_members` data already contains everything needed for friend review. Phase 2K.4 remains the latest required database migration.

## What is intentionally unchanged

- `exact_policy.npz`, `puzzle_bank.npz`, and `challenge_catalog.npz`.
- Exact-policy SHA-256 and Phase 2K.6 fail-closed math hardening.
- Every recommended Yahtzee hold and every Points Lost value.
- Daily puzzle generator/composition and Practice puzzle generation.
- 30-day remembered login, login-autofill fix, and performance caching.
- Group ranking rules and pre-completion spoiler protections.

## Phase 2K.7 live-test goals

1. On a phone, confirm the scorecard is easier to read while Roll + full scorecard + all five dice still fit together as well as the current layout.
2. Finish today's Daily and tap a completed friend's name in the group leaderboard.
3. Confirm the comparison correctly shows both totals and how many decisions were different.
4. Open several friend questions and confirm their chosen hold, exact best hold, Points Lost, and coaching match the shared Daily position.
5. Confirm a friend who has not finished cannot be reviewed.
6. Confirm the exact solver, Daily saving/resume, Practice, remembered login, and sharing behave normally.

---

# Yahtzee Coach v43B Phase 2K.6.1.1 — Deployment-Safety Hotfix

This hotfix repairs a mixed-version startup failure seen immediately after the Phase 2K.6.1 upload. The compact scorecard layout itself was not the cause. Streamlit received the new `app.py` while an older cached/deployed `exact_mode.py` was still being served, so importing the newly added exact-policy helper by name raised an `ImportError` before the app could render.

## v43B Phase 2K.6.1.1 changes

- **The app no longer imports newly added exact-mode helper names directly at startup.** A small `exact_runtime.py` bridge imports only the long-lived exact module and safely adapts to either the current exact-mode file or a temporarily stale one during deployment propagation.
- **Exact-policy fingerprint verification remains mandatory.** The bridge independently verifies the audited SHA-256 before the policy loads.
- **Player-facing coaching remains exact-only.** If the newer exact-only report helper is missing, the bridge calls the established exact report builder directly; it never invokes the legacy heuristic fallback.
- **Policy/load failures still fail closed** with `exact_unavailable` rather than approximate coaching.
- **The Phase 2K.6.1 compact decision layout is unchanged.** Full scorecard, upper subtotal, compact Roll line, and compact labels remain exactly as designed.

## Supabase

**No new Supabase migration is required.** Upload the full current release to GitHub and let Streamlit redeploy.

## Live-test goal

1. Confirm the app opens normally instead of showing the red ImportError screen.
2. Open a Daily or Practice decision and inspect the new compact layout.
3. Confirm Roll stage, full scorecard, and dice remain visible/compact as intended.
4. Play one decision normally to confirm exact coaching and persistence still work.

---

# Yahtzee Coach v43B Phase 2K.6.1 — Compact Decision Layout

This release keeps the complete strategy-relevant scorecard visible at all times while restoring the compact phone layout. The goal is simple: on a normal phone screen, a player should be able to see the roll stage, every current score/open box, and the decision dice together without opening another panel.

## v43B Phase 2K.6.1 changes

- **The full scorecard is always visible.** No extra tap or collapsed scorecard is introduced; filled scores remain part of every decision.
- **Removed the duplicate green open-category chip row.** The scorecard itself already shows which boxes are open and, more importantly, the actual scores in filled boxes.
- **Restored compact scorecard labels.** Upper cards use `1s`–`6s`; Lower uses readable short labels such as `3 Kind`, `4 Kind`, `Full H.`, `Sm Str.`, and `Lg Str.` while full category names remain in coaching/explanations.
- **Mobile Lower scorecard is back to four columns.** Seven lower boxes fit in two compact rows instead of four tall rows.
- **Scorecard cards use tighter padding and height** so the full board takes substantially less vertical space.
- **Upper subtotal is surfaced as `Upper: X / 63`.** This is only arithmetic already visible in the scorecard; it does not tell the player whether to chase or abandon the bonus.
- **Roll stage is one compact high-visibility line**, e.g. `ROLL 1 · First roll · 2 rerolls left`, preserving the blue/green Roll 1/Roll 2 distinction.
- **Dice instructions are one short line:** `Which dice would you keep? Tap to select.`
- Daily now presents the roll stage immediately before the scorecard; Practice uses the same compact decision hierarchy.

## Supabase

**No new Supabase migration is required for Phase 2K.6.1.** If Phase 2K.4 is already deployed, simply upload this full release.

## What is intentionally unchanged

- Exact solver, exact policy, and every recommended hold.
- Exact-policy fingerprint and Phase 2K.6 fail-closed math hardening.
- Daily puzzle bank, challenge catalog, Daily generator/composition, and scoring rules.
- Supabase persistence/social code and the Phase 2K.4 performance improvements.
- 30-day remembered login and iPhone Returning Player autofill fix.
- Coaching-language families and Points Lost math.

## Phase 2K.6.1 live-test goals

1. Open a Daily or Practice decision on a phone.
2. Confirm the roll stage, complete scorecard, and all five decision dice are visible together or with only minimal natural scrolling.
3. Confirm every filled score is visible without opening a panel.
4. Check that the abbreviated scorecard labels remain immediately understandable.
5. Confirm Roll 1 / Roll 2 is still impossible to miss.
6. Play/save normally and confirm no strategy or persistence behavior changed.

---

# Yahtzee Coach v43B Phase 2K.6 — Exact Strategy Math Hardening

This release does **not** change any recommended Yahtzee hold or regenerate the exact policy. It hardens the app around the already-audited exact strategy so player-facing Daily and Practice coaching can never silently substitute the older heuristic coach.

## v43B Phase 2K.6 changes

- **Daily and Practice are now exact-only.** If the exact policy cannot load or a puzzle is not covered, the app refuses to grade/coach the decision instead of silently substituting heuristic advice.
- **Practice no longer falls back to the old heuristic-era puzzle generator** if the expanded exact Practice bank fails to load. It shows a retry message instead.
- **The exact policy is fingerprint-locked.** `exact_policy.npz` must match the audited SHA-256 `cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b`; otherwise exact coaching fails closed.
- **A start-of-game gold-standard regression was added.** The packaged policy reconstructs an expected optimal starting score of **254.587727**, matching the published ~254.59 optimal benchmark.
- **Published exact-position benchmarks are now checked directly against `exact_policy.npz`**, including the well-known 11666, 11346, and 11236 decisions.
- The live beta dead-upper-bonus regression remains protected: `1,1,3,3,6` on Roll 1 with the bonus mathematically dead still prefers **keep 6**, with **keep 3,3 about 1.94 points behind**.
- The existing float32 policy remains unchanged. The audit still identifies 3,135 tied-best state/roll records within the app's `1e-5` tie tolerance; tied alternatives remain treated as 0 Points Lost.

## Supabase

**No new Supabase migration is required for Phase 2K.6.** If Phase 2K.4 is already deployed, simply upload this full release.

## What is intentionally unchanged

- Every exact-policy value and recommended hold.
- `exact_policy.npz`, `puzzle_bank.npz`, and `challenge_catalog.npz`.
- Daily puzzle generation/composition.
- The Yahtzee engine's historical heuristic code (it remains available only for legacy regression tooling, not player-facing Daily/Practice routing).
- Friend groups, persistence, remembered login, scoring/ranking rules, UI, and coaching-language families.

## Phase 2K.6 live-test goals

1. Play a few Daily and Practice decisions normally; recommendations/results should look unchanged.
2. Confirm Practice still opens quickly and gives normal instant coaching.
3. Confirm Daily still saves/resumes normally.
4. No player should ever see heuristic advice if the exact policy is unavailable; the app should instead show an exact-strategy-unavailable message.

---

# Yahtzee Coach v43B Phase 2K.5 — Performance + Fifth-Grade Clarity

This release is a focused performance and player-clarity pass. It does not add a new game mode or change the exact Yahtzee strategy. Instead, it makes the existing Daily and Practice experience faster to interact with, easier to scan on a phone, and easier for younger players to understand.

## v43B Phase 2K.5 changes

- **Dice taps are now fragment-scoped.** Selecting or unselecting a die reruns only the interactive dice area instead of rebuilding the whole Streamlit app. Full reruns still happen for meaningful navigation actions such as Save & Next, Back, and submitting a Practice hold.
- **Daily Save & Next uses one Supabase write instead of several read-before-write checks.** The existing PostgreSQL guard trigger remains the authoritative protection for puzzle order, attempt state, puzzle identity, exact-source requirements, and duplicate answers.
- **Completed Daily social data is batched.** Group members, completed attempts, answers, leaderboard rows, and question statistics are assembled through one snapshot path instead of several overlapping request chains.
- **Scorecard category names are spelled out.** Player-facing cards now use names such as Three of a Kind, Four of a Kind, Full House, Small Straight, and Large Straight instead of 3K / 4K / FH / SS / LS abbreviations.
- **Main scoring language is simpler.** Player-facing screens use **Points Lost**, **Best Holds**, and **Best Streak**. Exact expected-value details remain available in Strategy Details for players who want the deeper math.
- **Daily instructions and progress are quieter.** The repeated percentage/saved-status wording and developer-style “no hint” message are gone. The puzzle screen focuses on the question number, saved count, roll stage, scorecard, and dice.
- **Practice scenario introductions use simpler language.** Older phrases such as “option value,” “escape valve,” “reroll flexibility,” and “damage-control Yahtzee” were replaced with direct descriptions of what the player should notice.
- **Final review and leaderboards are phone-friendly cards.** The main player flow no longer relies on wide data tables for these screens.
- **Review Your 10 now loads one detailed question at a time.** Players choose Q1–Q10 and see only that question's dice, hold comparison, coaching, and optional top-holds detail.
- The Phase 2K.4 remembered-login/performance work, Phase 2K.4.1 localStorage reliability fix, and Phase 2K.4.2 iPhone autofill fix are all preserved.

## Supabase

**No new Supabase migration is required for Phase 2K.5.** If Phase 2K.4 is already deployed, simply upload this full release. The Phase 2K.4 `player_sessions` SQL remains in the package for clean/fresh installs.

## What is intentionally unchanged

- Exact solver and exact-policy values.
- Daily puzzle bank, challenge composition, and Daily generator.
- Practice puzzle generation and exact scoring.
- One-official-attempt-per-day persistence rules.
- Friend-group ranking rules and spoiler protections.
- PIN security and the 30-day remembered-device design.

## Phase 2K.5 live-test goals

1. Tap several dice in Daily and Practice and confirm the page feels steadier/faster while selecting a hold.
2. Save several Daily answers and notice whether Save & Next feels quicker.
3. Confirm scorecard categories are easy to understand without abbreviations.
4. Finish a Daily and check the card-style Final Review and friend leaderboard.
5. Open **Review Your 10**, switch among several question numbers, and confirm only the selected question's detailed coaching is shown.
6. Check a few Practice scenarios for simpler pre-puzzle wording.
7. Confirm remembered login and Returning Player autofill still behave correctly.

---

# Yahtzee Coach v43B Phase 2K.4.2 — Returning Player Autofill Hotfix

This small hotfix corrects the browser autofill semantics on the Returning Player form. Streamlit defaults password-type text inputs to `autocomplete="new-password"` when no value is specified, which can make iPhone/Safari offer to create a new strong password even though the player is signing in to an existing account.

## v43B Phase 2K.4.2 changes

- Returning Player **Display name** now explicitly uses `autocomplete="username"`.
- Returning Player **PIN** now explicitly uses `autocomplete="current-password"`, so browsers recognize it as an existing-login credential instead of a new-account password.
- Create Player keeps explicit `autocomplete="new-password"` on both PIN fields, where new-password behavior is appropriate.
- The 30-day remembered-login system, localStorage bridge, server-side device sessions, and Phase 2K.4 performance improvements are unchanged.
- Exact solver, exact policy, puzzle bank, Daily generation, Practice generation, EV rankings, coaching, persistence, and social behavior are unchanged.

## Supabase

**No Supabase step is required.** This is a player-facing browser/autofill metadata fix only.

## Phase 2K.4.2 live-test goal

1. Upload the full current app.
2. If you are already remembered, use **Sign out** once so the Returning Player form appears.
3. Tap the PIN field on iPhone/Safari. It should no longer treat the field as a new-password creation field or offer to generate a new strong password.
4. Sign in normally with **Keep me signed in on this device for 30 days** checked.
5. Fully close/reopen the app and confirm remembered login still works.
6. Confirm the faster Phase 2K.4 loading behavior remains.

---

# Yahtzee Coach v43B Phase 2K.4.1 — Remembered Login Reliability Hotfix

This hotfix keeps the Phase 2K.4 performance improvements and replaces the fragile cookie-only remembered-login handoff with a first-party browser `localStorage` bridge using Streamlit Components v2. The secure server-side device-session design is unchanged: the browser stores only the high-entropy device token, never the player's PIN, and Supabase stores only the hashed token secret.

## v43B Phase 2K.4.1 changes

- Fixes the live bug where **Keep me signed in on this device for 30 days** worked during the current Streamlit session but did not reliably restore after fully closing/reopening the app.
- Adds a hidden **Streamlit Components v2** bridge that can read/write the remembered device token from browser `localStorage` and send it back to Python on a brand-new Streamlit session.
- Keeps the Phase 2K.4 first-party cookie as a compatibility fallback rather than relying on it as the only restore path.
- A new session waits for the browser-storage read to finish before deciding that no remembered login exists.
- **Sign out** now revokes the Supabase device session and clears both browser persistence mechanisms.
- PINs are still never stored in the browser. Remembered sessions still expire server-side after 30 days.
- All Phase 2K.4 batched Supabase queries and short-lived performance caches are unchanged.
- Exact solver, exact policy, puzzle bank, Daily generation, Practice generation, EV rankings, and coaching strategy are unchanged.

## Supabase

**No new migration is required for this hotfix.** If Phase 2K.4 is already live and its `player_sessions` migration was run, simply upload this release. The Phase 2K.4 SQL files remain in the full package for clean installs.

## Phase 2K.4.1 live-test goal

1. Upload the full current app.
2. Sign in with **Keep me signed in on this device for 30 days** checked.
3. Fully close the browser tab or Home Screen app.
4. Reopen Yahtzee Coach and confirm the player is restored automatically.
5. Press **Sign out**, fully close/reopen again, and confirm the player stays signed out.
6. Confirm the faster Phase 2K.4 loading behavior remains.

---

# Yahtzee Coach v43B Phase 2K.4 — Remember This Device + Performance Patch

This release keeps every Phase 2K.3.2 coaching and dark-mode improvement, then removes the need to type a display name/PIN every time the app is reopened and cuts the biggest repeated Supabase round trips in the social/Daily loading path.

## v43B Phase 2K.4 changes

- Adds **Keep me signed in on this device for 30 days** to Returning Player and Create Player. It is checked by default.
- After a successful PIN sign-in, the browser receives a high-entropy remembered-device token. **The PIN itself is never written to the browser.**
- Supabase stores only a SHA-256 hash of the token secret, plus the player ID and expiration.
- On a later browser/app session, Yahtzee Coach reads the first-party cookie and restores that player automatically.
- **Sign out** revokes the server-side device session and deletes the browser cookie, so the next open remains signed out.
- Remembered-device sessions expire after 30 days and can be revoked without changing the player's PIN.
- Group member lookup, friend-group lookup, leaderboard loading, group question stats, and Daily streak loading now batch database reads instead of fetching one player/attempt/question at a time.
- Adds short-lived Streamlit caches for read-only group/streak data so normal reruns do not repeatedly hit Supabase for the same information. Cache entries are cleared after group changes or Daily completion.
- The exact solver, exact-policy files, Daily puzzle bank, challenge generator, Practice generator, scoring, and coaching values are unchanged.

## One-time Supabase migration required

For the existing live project, run **`RUN_THIS_ONCE_IN_SUPABASE_Phase2K4.sql`** in a **new SQL Editor query** before uploading this release. It creates only the `player_sessions` table and its indexes/security settings. It does not modify existing players, PIN hashes, Daily attempts, answers, friend groups, scores, or feedback.

The migration is safe to run more than once. A brand-new database can use the updated `v43b_schema.sql`.

## Why the performance patch matters

The old social code used several N+1 query patterns. For an 8-player group, one leaderboard or question-stat view could require many sequential Supabase requests because players, attempts, and answers were fetched one at a time. Phase 2K.4 batches those rows with `IN (...)` queries and reuses recent read-only results for a few seconds. This does not eliminate Streamlit Community Cloud cold starts, but it removes a large amount of avoidable app-side database waiting.

## Phase 2K.4 live-test goal

1. Run the one-time Phase 2K.4 Supabase migration.
2. Upload the full current app.
3. Sign in with **Keep me signed in on this device for 30 days** checked.
4. Fully close the tab/Home Screen app, reopen it, and confirm you land signed in without entering your PIN.
5. Press **Sign out**, close/reopen, and confirm you stay signed out.
6. Notice whether the Daily home/leaderboard feels faster; the biggest improvement should be on an already-awake app.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2K.3.2 — Coaching Language Audit + Dark-Mode Hotfix

This release replaces the not-yet-deployed Phase 2K.3.1 package. It keeps the dark-mode review fix and dead-bonus protection, then audits the rest of the exact-coaching language so surprising holds are explained with the same kind of concrete scorecard logic.

## v43B Phase 2K.3.2 changes

- Keeps the completed Daily dark-mode fix so **You Kept / Exact Best / Hold Rank / EV Lost** remain readable on phone dark mode.
- Keeps the exact dead-bonus regression for `1,1,3,3,6` on Roll 1: **keep 6** remains best and **keep 3,3** remains about **1.94 EV** behind.
- Adds a structured coaching-language audit across the main explanation families instead of relying on one-off wording.
- **Why this wins** now explicitly connects the player's visible idea to the scorecard destinations the exact hold actually supports.
- **Remember** lines are now family-specific and shorter, so they teach a reusable rule without falling back to vague phrases like “useful flexibility.”
- Clear explanation families now cover: upper bonus alive, secured, and dead; pair-vs-straight; straight cores; triples; four matching dice; two-pair Full House; made-hand keep/break decisions; Chance timing; true endgame; open-board flexibility; extra Yahtzee/Joker situations; and generic scorecard-fit decisions.
- Adds a diagnostic `coaching_family` tag to exact report metadata for testing only; it does not affect ranking or player scoring.
- Adds a new **840-position real exact-policy language audit**. Across that sample, explanations covered 18 naturally occurring coaching families, avoided the old vague phrases, avoided singular/plural errors like “1 fresh dice,” and stayed under 280 characters.
- Adds direct regression cases for Chance timing and open-board flexibility, which are less common in the deterministic 840-position sample.
- No Supabase migration is required.

## What is intentionally unchanged

- Exact strategy rankings and policy values.
- Daily puzzle composition/version.
- Practice generator and scoring.
- Player identity, saved Daily attempts, friend groups, leaderboards, streaks, sharing, and feedback.
- Roll 1 / Roll 2 clarity and Practice UI cleanup.

## Phase 2K.3.2 live-test goal

1. Upload this full current-app package instead of the earlier Phase 2K.3.1 ZIP.
2. Open a completed Daily review in dark mode and confirm the four summary values are readable.
3. In Practice, intentionally choose several reasonable-looking non-optimal holds from different strategy types.
4. Confirm **Why it matters / Why this wins** answers the practical question: *Why is the exact hold better on this particular scorecard?*
5. Confirm **Remember** gives one short reusable lesson rather than repeating solver jargon.
6. Confirm exact holds, EV losses, grades, Daily results, and social features remain unchanged.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2K.3.1 — Dark-Mode Review Hotfix + Dead-Bonus Explanation Guard

This is a very small display/teaching hotfix on top of Phase 2K.3. Strategy values, Daily puzzles, persistence, friend groups, Practice flow, and scoring are unchanged.

## v43B Phase 2K.3.1 changes

- Fixes the completed Daily review cards in phone dark mode so **You Kept / Exact Best / Hold Rank / EV Lost** always render with readable dark value text on the light cards.
- Adds an explicit regression for the late-game dead-bonus position `1,1,3,3,6` on Roll 1 with only Sixes / 3K / 4K open.
- Protects the exact ranking for that state: **keep 6** remains best; **keep 3,3** remains about **1.94 EV** behind.
- Improves the coaching for that situation so it explicitly says the **35-point upper bonus is already out of reach** and that keeping the 6 is **not a bonus chase**.
- The explanation now connects the 6 to every remaining live matching destination and explains why four fresh dice with two rerolls beat committing early to the lower pair.
- No Supabase migration is required.

## Phase 2K.3.1 live-test goal

1. Upload the full current app to GitHub.
2. Open a completed Daily review in iPhone dark mode.
3. Confirm **You Kept / Exact Best / Hold Rank / EV Lost** are readable.
4. If the `1,1,3,3,6` dead-bonus example appears again, confirm the coaching explicitly says the 6 is not being kept to chase an impossible bonus.
5. Confirm all existing Roll clarity, Practice cleanup, sharing, friend-group, and Daily behavior remains unchanged.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2K.3 — Clearer Coaching Explanations

This is a focused teaching-language refinement on top of the successful Phase 2K.2 Practice cleanup. Strategy rankings, exact values, puzzle generation, Daily rules, and social/persistence behavior are unchanged.

## v43B Phase 2K.3 changes

- Adds a new **Simple why** coaching layer to exact-mode reports.
- Coaching now directly connects the player's tempting hold to the **boxes that are still open or already filled** instead of relying on abstract phrases such as “preserve flexibility.”
- Common pair-vs-straight traps now explain why the pair has lost value on that specific scorecard and why distinct straight anchors create more useful paths.
- The exact playtest example `1,1,3,3,5` with the 3s / 3K / Full House / Chance already filled now explains that **keep 3,3 mostly chases Four of a Kind / Yahtzee, while keep 3,5 keeps both straight boxes alive with three fresh dice**.
- Practice's **Why it matters** coaching box uses the new concrete explanation automatically.
- Completed Daily review now shows **💡 Why this wins** before the broader takeaway.
- Daily review labels are simplified to **🧠 Remember** and **Try this instead**.
- Existing full exact math, Top exact holds, EV loss, and detailed report remain available.
- No Supabase migration is required.

## Phase 2K.3 live-test goal

1. Upload the full current app to GitHub.
2. In Practice, intentionally choose a reasonable-looking but non-optimal hold.
3. Confirm **Why it matters** explains the scorecard tradeoff in plain language.
4. Open a completed Daily question and confirm **💡 Why this wins** gives the same kind of concrete explanation.
5. Confirm the exact hold, EV loss, grades, and Top exact holds are unchanged.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2K.2 — Practice UI Cleanup + Roll Clarity Bundle

This release combines the already-approved **Roll 1 / Roll 2 clarity fix** and **Practice navigation hotfix** with a focused Practice-mode UI cleanup, so only one upload is needed.

## v43B Phase 2K.2 changes

- Keeps the Daily puzzle roll-stage card: **ROLL 1 · First roll / 2 rerolls remaining** and **ROLL 2 · Second roll / 1 reroll remaining**.
- Keeps the Streamlit callback hotfix that prevents **Open Practice without signing in** from crashing.
- Practice now opens with a clean **Practice** header and the simple promise: **Unlimited practice · instant coaching after every decision**.
- If today's Daily is complete, the crossover is reduced to one compact **Daily complete · View leaderboard** button instead of a large banner.
- The session dashboard no longer appears above the current puzzle.
- Practice now prioritizes the learning loop: **scenario → roll stage → scorecard → choose dice → submit → coaching → next puzzle**.
- The scenario name and short description remain visible because Practice is the teaching mode.
- Practice uses the same prominent blue/green Roll 1 / Roll 2 indicator as Daily.
- Dice instructions are shortened to one line: tap dice to keep them; leave all unselected to reroll everything.
- After coaching, **Next Practice Puzzle →** is the primary action.
- Session grade, exact-rate progress, badges, Session Coach, and strategy mastery move into a collapsed **See my practice progress** section below the primary next-puzzle action.
- Session history remains collapsed at the bottom.
- Exact solver behavior, Practice puzzle generation, grading, coaching content, Daily behavior, persistence, friend groups, streaks, feedback, and sharing are unchanged.
- No Supabase migration is required.

## Phase 2K.2 live-test goal

1. Upload this one full package instead of installing Phase 2K.1.1 separately.
2. While signed out, press **Open Practice without signing in** and confirm Practice opens normally.
3. Confirm Practice feels cleaner and the current puzzle is the first thing that matters.
4. Submit a hold and confirm coaching appears immediately.
5. Confirm **Next Practice Puzzle →** appears before the optional Practice progress dashboard.
6. Open **See my practice progress** and confirm the existing session stats, badges, Session Coach, and mastery tools are still available.
7. On tomorrow's Daily, confirm Roll 1 / Roll 2 remains impossible to miss.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2K.1.1 — Practice Navigation Hotfix

This is a small production hotfix on top of the Roll Clarity release. A live beta test exposed a Streamlit navigation-state crash when an unsigned player pressed **Open Practice without signing in**.

## v43B Phase 2K.1.1 changes

- Fixes **Open Practice without signing in** so it safely switches to Practice instead of raising a StreamlitAPIException.
- Applies the same safe navigation pattern to every in-app Daily ↔ Practice shortcut so the same bug cannot appear from another button later.
- Keeps the Phase 2K.1 Roll 1 / Roll 2 clarity card exactly as shipped.
- No Daily, strategy, scoring, persistence, social, sharing, feedback, streak, or puzzle-generation behavior changed.
- No Supabase migration is required.

## Phase 2K.1.1 live-test goal

1. Upload the full current app to GitHub.
2. Open the app while signed out.
3. Press **Open Practice without signing in** and confirm Practice opens normally.
4. If today's Daily is already complete, test **Go to open Practice** and **View today's Daily leaderboard** as well.
5. Confirm the Roll 1 / Roll 2 clarity card is still present on Daily puzzles.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2K.1 — Roll Clarity Quick Fix

This is a deliberately small next-day usability patch based on live beta feedback. The Daily puzzle screen was already working well; the only problem was that some players were overlooking whether a decision came after Roll 1 or Roll 2.

## v43B Phase 2K.1 changes

- Adds a large, consistent roll-stage card **immediately above the Daily dice**.
- Roll 1 is shown as **🔵 ROLL 1 · First roll** with **2 rerolls remaining**.
- Roll 2 is shown as **🟢 ROLL 2 · Second roll** with **1 reroll remaining**.
- Uses distinct blue/green treatments so the stage can be recognized at a glance without redesigning the puzzle screen.
- Removes the old smaller Daily roll line from the question header so the same information is not duplicated in two places.
- Back/edit, saved answers, final review, scoring, friend groups, sharing, feedback, streaks, and Practice are unchanged.
- No new Supabase migration is required for this patch.

## Why this stays intentionally small

The beta group is already successfully using the app. This patch fixes the specific live usability issue without moving the scorecard, dice, progress bar, buttons, or any other established Daily controls.

## Phase 2K.1 live-test goal

1. Upload the full current app to GitHub.
2. Open tomorrow's Daily Challenge.
3. Confirm every Roll 1 question shows **ROLL 1 · First roll / 2 rerolls remaining** directly above the dice.
4. Confirm every Roll 2 question shows **ROLL 2 · Second roll / 1 reroll remaining** in the same location.
5. Confirm the rest of the Daily flow feels unchanged.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2K — Beta Readiness Pass

This checkpoint is intentionally small and player-facing. The core Daily, exact strategy, friend groups, saved attempts, sharing, and Practice systems remain unchanged; Phase 2K focuses on making the app easier to hand to a small group of outside testers.

## v43B Phase 2K changes

- Adds a low-profile **Help & feedback** section at the bottom of the app rather than another prominent home-screen feature.
- Beta testers can submit **Something confusing**, **Bug / something broke**, **Idea / suggestion**, or **Account / PIN help** feedback directly into the Yahtzee Coach Supabase project.
- Feedback automatically records the app release and current app section; signed-in feedback is associated with the player's existing ID without asking them to enter private information.
- The feedback form explicitly warns players **not to include their PIN or other private information**.
- Returning-player login now includes a small **Forgot your PIN?** explanation. Full PIN recovery is intentionally not implemented yet; testers are told to contact Mike/their inviter without sharing the PIN itself.
- The existing participation-streak calculation is now surfaced as a lightweight **Daily streak** message before and after the Daily.
- The within-the-10 exact streak metric is renamed **Best Exact Run** so players do not confuse it with the multi-day Daily streak.
- Friend leaderboards now have intentional asynchronous states: **first to finish**, **waiting for friends**, **everyone's in / final standings**, and **only member so far**.
- Before starting the Daily, a group member can see at a glance whether nobody, some friends, or everyone has finished yet without seeing any scores or strategy spoilers.
- The beta/version label remains tucked inside **Help & feedback** rather than appearing in normal play.

## One-time database migration required

Existing Supabase projects should run `v43b_phase2k_beta_feedback_migration.sql` once before testers use the new feedback form. It creates only the beta feedback inbox and does not alter players, Daily attempts, answers, groups, scoring, or leaderboards.

The migration is safe to run more than once. A fresh install can use the updated `v43b_schema.sql` directly.

## What is intentionally NOT changed

- Exact strategy recommendations and scoring are unchanged.
- Daily puzzle composition/version remains `43A-bank42.6`.
- One attempt per player/day and pre-submit Back/edit rules are unchanged.
- Real friend groups, invite links, leaderboards, and spoiler-free sharing are unchanged.
- Practice remains account-free.
- Full self-service PIN reset/recovery is not part of this beta pass.
- The iPhone Home Screen icon issue remains on the backburner; the browser favicon/custom icon assets remain in place, but Phase 2K does not spend more development time fighting the Streamlit/iOS Web Clip limitation.

## Phase 2K live-test goal

1. Run the one-time Phase 2K Supabase migration.
2. Upload the full current app to GitHub.
3. Confirm **Help & feedback** appears quietly at the bottom rather than competing with Daily/Practice.
4. Send one test feedback message and confirm it appears in Supabase's `beta_feedback` table.
5. Complete/return to a Daily and confirm the multi-day **Daily streak** message appears without cluttering the result hero.
6. Test a group where only one or some members have finished and confirm the waiting language feels natural.
7. Invite a few friends and let their behavior—not more speculative features—drive the next priorities.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2I — Home Navigation + Full-Text Share Fix

This checkpoint fixes two live usability issues from the Phase 2H/2G polish pass without changing any competitive or strategy behavior.

## v43B Phase 2I changes

- **Add to Home Screen is no longer a prominent card/button on the Daily or Practice page.**
- The main navigation now reads, in order: **Daily Challenge · Practice · 📲 Add to Home Screen**.
- Selecting the third option opens a dedicated Home Screen page with the custom teacher-die icon and simple tabs for **iPhone/iPad, Android, and Computer**.
- The dead-looking custom install action button has been removed entirely. The dedicated page gives the real browser/OS steps instead of pretending the site can force the system installer.
- The web-app icon/title metadata is still injected automatically, but that JavaScript now runs through top-level `st.html(...)` instead of an iframe component.
- **Share result now hands the native share sheet one complete text payload.**
- The Yahtzee Coach URL remains the final line of that text, but is no longer sent as a separate `url` field that some Messages/share targets were prioritizing over the score.
- The Daily share controls also run through top-level `st.html(...)` rather than an iframe, which keeps the browser share/clipboard call in the page context.
- **Copy score** still copies the same full spoiler-free result and now has an additional legacy clipboard fallback if the modern clipboard API is blocked.
- No Supabase schema changes are required for this phase.

## What is intentionally NOT changed

- Daily puzzle composition/version remains `43A-bank42.6`.
- Exact strategy and scoring are unchanged.
- Permanent players, one official Daily attempt, back/edit-before-submit, friend groups, invite links, and live leaderboards are unchanged.
- The Wordle-style square thresholds are unchanged.
- The final Home Screen install/add action is still controlled by the user's browser and operating system.

## Phase 2I live-test goal

1. Upload the full current app to GitHub.
2. Confirm the top navigation shows **Daily Challenge**, **Practice**, then **📲 Add to Home Screen**.
3. Confirm no large install card appears underneath Daily Challenge or Practice anymore.
4. Open **📲 Add to Home Screen** and confirm the teacher-die icon plus device tabs appear.
5. Open an already-completed Daily and press **Share result**.
6. Choose Messages/text and confirm the message contains the **entire score block and colored squares**, with the Yahtzee Coach URL only as the final line.
7. Try **Copy score** and paste it into a text to confirm the same full result is copied.

---

## Previous checkpoint — v43B Phase 2H

Phase 2H attempted to keep a custom Install/Add button and show device instructions when a direct browser install prompt was unavailable. Live testing showed that this control was still unreliable inside Streamlit's embedded component environment. Phase 2I supersedes that approach: installation is now a native third navigation destination with no fake action button to fail.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2G — Spoiler-Free Daily Result Sharing

This checkpoint adds the Wordle-style social payoff to the completed Daily Challenge.
The exact strategy engine, Daily puzzle composition, permanent players, saved Daily attempts, friend groups, invite links, editable pre-submit review, and home-screen icon/install polish remain intact.

## v43B Phase 2G changes

- Completed Daily results now include a **Share your Daily** card.
- The card creates a compact **two-row, 10-square result grid**, one square for each decision.
- Result colors are spoiler-free and describe decision quality rather than the dice/hold itself:
  - 🟩 exact
  - 🟨 essentially optimal (within 0.10 EV)
  - 🟧 close (within 1.00 EV)
  - 🟥 meaningful miss (more than 1.00 EV)
- Shared text also includes **total EV lost**, **exact holds**, and **best exact streak**.
- If the player is in a friend group, the share can include the player's **current group rank among completed players**.
- **Share result** opens the device's native share sheet when supported.
- **Copy score** copies the full formatted result for pasting into Messages, group chats, email, etc.
- If native sharing is unavailable, Share result falls back to copying the score.
- Shared results intentionally contain **no dice, chosen holds, exact answers, scenario names, or coaching**, so friends can safely share before others play.
- The Yahtzee Coach app link is included at the bottom of the copied/shared result.
- No Supabase schema changes are required for this phase.

## Example share

🎲 Yahtzee Coach Daily — Aug 9, 2026  
0.42 EV lost · 8/10 exact  
🟩🟩🟨🟩🟩  
🟩🟧🟩🟩🟩  
🔥 Best exact streak: 5  
🏆 Group rank right now: #1 of 3  
🟩 exact · 🟨 essentially optimal · 🟧 close · 🟥 miss

## What is intentionally NOT changed

- Daily puzzle composition/version remains `43A-bank42.6`.
- The exact policy and strategy recommendations are unchanged.
- One official Daily attempt per player per day remains enforced.
- Back/edit remains available only before final submission; sharing appears only after the result is locked.
- Friend-group rank in a shared result is explicitly labeled **right now** because standings can change as more friends finish.
- Practice remains open and account-free.

## Phase 2G live-test goal

1. Upload the full current app to GitHub.
2. Complete / reopen today's already-completed Daily result.
3. Confirm the new **Share your Daily** card appears.
4. Confirm the 10 colored squares match the quality of the 10 completed decisions without revealing answers.
5. Tap **Copy score**, paste it into a text message, and confirm the formatting survives.
6. Tap **Share result** on a phone and confirm the native share sheet opens when supported.
7. If you are in a friend group, confirm the copied text shows the current group rank.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2F — Custom App Icon + Smarter Home-Screen Install

This checkpoint upgrades the phone/home-screen experience around the working Phase 2E app.
The exact strategy engine, Daily puzzle composition, persistent players, saved Daily attempts, real friend groups, and invite links all remain intact.

## v43B Phase 2F changes

- The Home Screen flow now uses the chosen **cartoon teacher-die mascot icon**.
- The app injects **Apple touch icon** and **web app metadata** automatically so iPhone/iPad Home Screen saves can use the branded icon and launch title.
- The install/help card now detects when Yahtzee Coach is already running in **standalone / installed mode** and changes its message accordingly.
- On browsers that expose the standard **beforeinstallprompt** event, the card can now open the browser's install prompt directly.
- When a direct install prompt is not available, the card gives concise platform-specific guidance for **iPhone / iPad (Safari)**, **Android (Chrome)**, and **desktop Chrome/Edge**.
- Adds a **Copy app link** control so players can text the app to themselves or a friend.
- No Supabase schema changes are required for this phase.
- Friend groups, real leaderboards, Practice, Daily back/edit review, and one-attempt-per-day protections are unchanged.

## What is intentionally NOT changed

- Daily puzzle composition/version remains `43A-bank42.6`.
- The exact policy and strategy recommendations are unchanged.
- Phones still require the user to confirm the final operating-system **Add to Home Screen / Install** step.
- Practice remains open and account-free.
- PIN recovery and group-admin/delete tools are still future polish items.
- Participation streak calculations exist in the persistence layer but are not yet surfaced prominently.

## Phase 2F live-test goal

1. Upload the full current app to GitHub.
2. Open Yahtzee Coach on a phone.
3. Confirm the **Add Yahtzee Coach to your Home Screen** card shows the new mascot icon.
4. On iPhone/iPad, use the guided **Share → Add to Home Screen** path and confirm the saved icon is the custom teacher-die.
5. On a device/browser that already treats Yahtzee Coach like an installed app, confirm the card switches to **Already added** messaging.
6. Optional: try the **Copy app link** button and text the app to yourself or a friend.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2E — Invite Links + Editable Daily Review + Home-Screen Polish

This checkpoint turns the successful Phase 2D social system into a much smoother friend-facing experience.
The exact strategy engine, Daily puzzle composition, real friend groups, permanent player identity, and one-attempt-per-day rule remain intact.

## v43B Phase 2E changes

- Every friend group now has a **shareable invite URL** in addition to its short join code.
- Group members get both **Share invite** and **Copy invite link** controls.
- Opening an invite URL sends a new friend directly into the Daily/player flow with the group invite already queued.
- A new player can create a display name + PIN, or a returning player can sign in, and then Yahtzee Coach **automatically joins that invited group**.
- The invite query parameter is cleared after a successful join so normal app navigation resumes cleanly.
- Daily Challenge now has a visible **Back** button.
- Saved Daily choices can be revised before the player final-submits the ten-question set.
- Back/edit does **not** reveal grades, EV loss, optimal holds, strategy labels, or coaching.
- After Question 10, the player sees a **final no-feedback review** of all ten chosen holds.
- The review screen can jump directly back to any question for correction.
- **Submit final Daily Challenge** is now the permanent lock point. After final submission, the ten answers are immutable and the normal result/leaderboard/coaching screen unlocks.
- Refresh/cross-device resume is preserved: saved draft choices still restore from Supabase before final submission.
- The app home area now includes **Add Yahtzee Coach to your Home Screen** guidance for iPhone/iPad, Android, and desktop browsers.
- Friend groups, live leaderboards, real group question stats, Practice, and exact strategy remain unchanged.

## One-time database migration required

Phase 2C/2D intentionally made every saved answer immutable immediately. Phase 2E changes the lock point to the player's explicit final submission, so previously saved answer rows must be allowed to update **only while the parent Daily attempt is incomplete**.

Existing Supabase projects must run `v43b_phase2e_migration.sql` once in the Supabase SQL Editor before testing Back/edit.
The migration is safe to run more than once and preserves these protections:

- one attempt per player/challenge
- first-pass answers still save sequentially
- official answers remain exact-solver-only
- question number / puzzle identity cannot be changed
- answer rows cannot be deleted
- completed Daily attempts cannot be revised

`v43b_schema.sql` has also been updated so a brand-new v43B database would receive the Phase 2E behavior directly.

## What is intentionally NOT changed

- Daily puzzle composition/version remains `43A-bank42.6`.
- The exact policy and strategy recommendations are unchanged.
- The Daily still allows only one official attempt per player per day.
- No feedback appears while answers remain editable.
- Practice remains open and account-free.
- PIN recovery and group-admin/delete tools are still future polish items.
- Participation streak calculations exist in the persistence layer but are not yet surfaced prominently.

## Phase 2E live-test goal

1. Run the one-time `v43b_phase2e_migration.sql` in Supabase.
2. Upload the full current app to GitHub.
3. In a friend group, use **Copy invite link** or **Share invite** and open the link in a fresh/private browser.
4. Create/sign in as a test player and confirm the player joins the group automatically without manually entering the code.
5. Start the Daily, save at least three answers, then use **Back** to change an earlier hold.
6. Refresh or sign out/in and confirm the revised saved answer is still there.
7. Complete all ten and confirm the no-feedback review appears before the score.
8. Edit one question from that review, return to review, then final-submit.
9. Confirm the completed result is locked and the real friend leaderboard still works.
10. On a phone, open **Add Yahtzee Coach to your Home Screen** and follow the device-specific install steps.

---

## Previous checkpoint

# Yahtzee Coach v43B Phase 2D — Real Friend Groups + Live Leaderboards

This checkpoint turns the Daily Challenge social layer from a demo into real shared competition.
The permanent-player and persistent-attempt systems from Phase 2B/2C remain intact, and the exact
strategy engine, exact policy, Daily puzzle composition, and Practice behavior remain locked.

## v43B Phase 2D changes

- Signed-in players can **create a friend group** and receive a short invite code.
- Other permanent players can **join the group with that code**; codes are case-insensitive.
- Group creators are automatically members.
- Players can belong to more than one group and select which group's standings they want to view.
- The Daily results screen now uses the **real Supabase leaderboard** instead of the seven simulated v43A rows.
- Only **completed official Daily attempts** appear on the leaderboard; partial scores never leak during a run.
- Leaderboard order remains locked to: lowest total EV loss, then most exact holds, then lowest worst miss.
- The results screen shows how many group members have completed today's Daily and refreshes when the player returns.
- “Today's killer” and “Most solved / Unanimous” cards now use **real completed group answers**.
- Friend-group member names and the group's invite code are visible to group members.
- Adds `list_group_members()` to both the reference persistence contract and Supabase production backend.
- Adds `v43b_social_tests.py` and expands persistence/UI tests for real social behavior.
- The old simulated friend helpers remain only in `daily_challenge.py` for historical regression coverage; the live app no longer imports or displays them.
- No Supabase schema migration is required for this patch; the `friend_groups` and `group_members` tables were installed in the original v43B schema.

## Daily puzzle variety audit

The Daily selector was re-audited before this release because repeated broad scenario names can make different decisions feel similar.
The underlying puzzles are varying well, so the locked v42.6 composition was **not changed**.

- August 2026 31-day regression: **308 of 310 underlying decisions were unique**.
- There were **0 exact underlying puzzle repeats on consecutive days** across that month.
- Each Daily used **7–9 distinct strategy families** in the 10-question set.
- A separate 60-day spot audit produced **586 unique underlying decisions out of 600** (97.7%).
- Only **4 of 600** decisions repeated an underlying puzzle seen in the previous seven days (0.7%).
- Every Daily still preserves the locked **5 Roll 1 / 5 Roll 2** and **2 Opening / 3 Midgame / 3 Late Game / 2 True Endgame** structure.

The repeated feeling is mostly from intentionally reusable scenario labels such as “Matching Dice Pressure,” “Straight Structure,” and “Full House Puzzle.” The actual dice + scorecard + game-state decisions underneath those labels are overwhelmingly different.

## What is intentionally NOT changed yet

- Participation streak calculations exist in the persistence layer but are not yet surfaced prominently in the player UI.
- There is not yet a player/group deletion or group-admin screen.
- PIN recovery is not available yet.
- Exact solver behavior is unchanged.
- Daily puzzle composition/version remains `43A-bank42.6`.
- Practice behavior is unchanged and still works without signing in.

## Phase 2D live-test goal

1. Sign in to the player that already completed today's persistent Daily.
2. Create a friend group and confirm an invite code appears.
3. Confirm your already-completed Daily immediately appears as the group's first real leaderboard row.
4. Sign out and create/sign in as another test player (or use a friend's player).
5. Join the group with the invite code and confirm the member count increases.
6. If that second player completes today's Daily, return to the first player and confirm both real rows are ranked together.

Once this passes live, the remaining v43B social polish can focus on streak display, richer return-home/status information, and group/player management rather than core persistence.

---

## Previous checkpoint: v43B Phase 2C — Persistent Daily Attempts

This checkpoint turns the permanent-player system into a true saved Daily Challenge.
The exact strategy engine, exact policy, Daily puzzle composition, and Practice behavior remain locked.

## v43B Phase 2C changes

- Starting the Daily Challenge now creates the player's **one official attempt for that day** in Supabase.
- The database uniqueness rule enforces one attempt per player / challenge even if two tabs or devices try to start at once.
- Every answer is written to Supabase **before** the local UI advances to the next question.
- Locked answers are immutable and remain exact-solver-only.
- Refreshing, leaving the app, signing out, or switching devices no longer loses Daily progress.
- After signing back in, the app restores the saved attempt and continues at the next unanswered question.
- Completed attempts restore the full result/review screen after a later sign-in.
- Question 10 completion is self-healing: if the tenth answer saves but finalization is interrupted, the next load safely finalizes the already-locked attempt.
- The old prototype **Reset today's local demo attempt** control is removed. Official attempts cannot be reset.
- Local held-die widget state is cleared when switching players/dates so an unsubmitted hold cannot leak from one player to another.
- The Daily UI now explicitly shows how many answers are safely saved.
- Adds `v43b_daily_attempt_ui_tests.py` for the live persistence wiring.
- No Supabase schema migration is required for this patch; it activates the attempt/answer tables already installed during the v43B setup.

## What is intentionally NOT changed yet

- The seven friend leaderboard rows are still deterministic simulated players.
- Real friend groups, join codes, real group leaderboards, streak display, and real group question stats are not visible yet.
- Player identity still uses the lightweight display-name + PIN flow; users sign back in to restore a session on another device.
- Exact solver behavior is unchanged.
- Daily puzzle composition/version remains `43A-bank42.6`.
- Practice behavior is unchanged and still works without signing in.

## Phase 2C live-test goal

1. Sign in to the same player that passed Phase 2B.
2. Start today's Daily Challenge.
3. Lock two or three answers.
4. Refresh/close the app or sign out.
5. Return and sign in with the same player.
6. Confirm the challenge resumes at the next unanswered question with the earlier answers still locked.
7. Finish all ten.
8. Leave and return again; confirm the completed result/review restores instead of offering a second attempt.

Once this passes live, the next major v43B step can replace the simulated friend leaderboard with real groups and real completed-player results.

---

# Yahtzee Coach v43B Phase 2B — Persistent Player Identity

This checkpoint turns the working Supabase connection into the first visible v43B feature:
**permanent Daily Challenge players**. The exact strategy engine, exact policy, Daily puzzle
composition, and Practice behavior remain locked.

## v43B Phase 2B changes

- Adds a polished **Create player / Returning player** gate for Daily Challenge.
- New players choose a public display name and private 4–12 digit PIN.
- Returning players sign back in with the same display name + PIN.
- Display names remain case-insensitively unique so returning-player lookup is unambiguous.
- PINs are masked in the UI and stored in Supabase only as salted `scrypt` hashes — never plaintext.
- Player identity is stored in the existing `players` table through the trusted Streamlit backend.
- The active player is kept in per-user Streamlit Session State during the current app session.
- Daily Challenge now requires a player identity; **Practice remains available without signing in**.
- Adds a visible signed-in player status and **Sign out** control.
- Switching players clears the local Daily preview attempt so one player's session state cannot be
  carried into another player's run.
- Keeps the hidden `?dbcheck=1` Supabase preflight, now labeled Phase 2B.
- Adds `v43b_identity_tests.py` for identity-specific regression coverage.

## What is intentionally NOT changed yet

- Daily answers are still session-local in this Phase 2B live test.
- One official attempt per player/day is not connected to the live UI yet.
- Cross-device / refresh resume is not connected to the live UI yet.
- The friend leaderboard still uses the deterministic v43A demo players.
- Friend groups, join codes, real group leaderboards, streaks, and group question stats are not visible yet.
- Exact solver behavior is unchanged.
- Daily puzzle composition/version is unchanged.
- Practice behavior is unchanged.

## Phase 2B live-test goal

After deployment, verify the smallest real identity loop before attempt persistence is enabled:

1. Open Daily Challenge and create a player.
2. Confirm the app shows the new player as signed in.
3. Sign out.
4. Use **Returning player** with the same display name + PIN.
5. Confirm the same player returns successfully.
6. Confirm **Open Practice without signing in** still works.

Once this passes live, the next patch can safely connect the Daily attempt itself to Supabase:
one attempt per player/day, locked-answer saving, and interruption resume.

---

# Yahtzee Coach v43B Phase 2A3 — Supabase URL Compatibility Fix

This checkpoint begins the live v43B persistence rollout while preserving the locked
v43A.1 Daily Challenge and v42.6 Practice strategy behavior.

## v43B Phase 2A3 changes

- Adds the v43B persistence contract in `daily_store.py`.
- Adds the production Supabase backend in `supabase_daily_store.py`.
- Adds `supabase` to `requirements.txt`.
- Includes the Supabase/Postgres schema in `v43b_schema.sql`.
- Includes the v43B persistence regression suite in `v43b_persistence_tests.py`.
- Keeps the hidden database preflight at `?dbcheck=1`.
- Fixes the first live Supabase preflight failure (`PGRST125: Invalid path specified in request URL`).
- Automatically normalizes a Supabase REST/Data API endpoint such as
  `https://<project>.supabase.co/rest/v1` back to the base Project URL expected by `supabase-py`.
- The preflight reports when that safe URL correction was applied.
- Keeps exception detail developer-only so setup problems can be diagnosed without changing normal player-facing UI.
- Cleans generated `__pycache__` / `.pyc` artifacts from the release package.

## What is intentionally NOT changed yet

- No player login/create-player UI is active yet.
- Daily Challenge still uses the v43A.1 session-local attempt flow and demo leaderboard.
- Exact solver behavior is unchanged.
- Daily puzzle composition/version is unchanged.
- Practice behavior is unchanged.

## v43B deployment status

Supabase tables have been created and Streamlit secrets are expected to contain
`SUPABASE_URL` and `SUPABASE_SECRET_KEY`. The current checkpoint exists only to verify the
Streamlit-to-Supabase connection safely before persistent player identity is enabled. Phase 2A3
adds compatibility for either the base Project URL or the REST/Data API URL form in Streamlit Secrets.

---

## Previous checkpoint: v43A.1

v43A.1 keeps the complete v42.6 Practice experience intact and refines the first
playable version of **Daily Challenge** after live desktop/mobile feedback.

The purpose of v43A.1 is to make Daily Challenge the main attraction and clean up
the competitive game loop before adding a real shared database in v43B.

## v43A.1 live-feedback changes

- Daily Challenge is now the first/default mode when the app loads.
- Practice remains available at any time.
- The large four-box rules summary was removed from the Daily intro.
- Daily rules are condensed into the hero with an optional **How the Daily Challenge works** expander.
- The 10-question segmented progress bar is larger and now shows percentage complete.
- The completed Daily screen has a direct **Go to open Practice** button.
- After switching to Practice, a completed Daily attempt shows a **View today's Daily leaderboard** return button.
- In v43A.1 that return behavior lasts for the active Streamlit session; v43B persistence will make the leaderboard available after leaving and reopening the app.

## Two modes

### Practice

Practice is unchanged from v42.6:

- unlimited Roll 1 / Roll 2 hold training
- 420 realistic/curated scorecard contexts
- all 252 canonical five-dice rolls available
- exact full-game strategy values
- grades, visible hold rank, personalized teaching, Session Coach, mastery,
  and achievements

### Daily Challenge

Every challenge date produces the same deterministic Daily 10 for everybody.
The current challenge clock uses **America/New_York (Eastern Time)**, so a new
challenge begins at midnight Eastern.

The Daily 10 preserves the v42.6 composition rules:

- exactly 10 decisions
- 5 Roll 1 and 5 Roll 2 decisions
- 2 Opening, 3 Midgame, 3 Late Game, 2 True Endgame
- 9 simulated-game scorecards + 1 curated edge case
- deliberate difficulty and strategy-family variety

During the official run the app deliberately hides:

- the strategy-family label
- the difficulty label
- the exact best hold
- the grade
- expected-value loss
- teaching feedback

The player simply sees the scorecard, roll number, and dice. Each answer is
locked before moving on.

After Question 10, the complete exact coaching unlocks for all ten questions.

## Scoring

Leaderboard order is:

1. **lowest total expected game points lost**
2. **most exact holds**
3. **lowest single worst miss**

Speed is intentionally not part of the ranking.

A perfect Daily Challenge is 0.00 total expected game points lost.

## v43A demo leaderboard

v43A does not connect an external database yet. Instead, it includes seven
**deterministic simulated friend results** so the complete social/results UX can
be tested now.

The user's row is scored by the real exact solver. The seven demo rows are
clearly labeled as prototype data in the UI.

The results screen includes:

- total EV lost
- exact holds out of 10
- best exact-hold streak
- friend rank
- prototype friend leaderboard
- “Today's killer” question
- most-solved / unanimous question
- full ten-question coaching review

## One-attempt and resume behavior in v43A

Within an active Streamlit session:

- answers are locked as they are submitted
- switching to Practice and back preserves Daily Challenge progress
- completing Question 10 locks the result
- the finished result remains available when switching modes

Because v43A deliberately has no database yet, a completely new Streamlit
session can start a fresh local attempt. A prototype-only reset button is also
available after completion for testing.

**v43B will move attempt state to the shared database**, enforcing one official
attempt per player/day and supporting true refresh/device resume.

## Competitive safety

Daily Challenge refuses to lock an answer if the exact solver is unavailable.
Unlike Practice, it does **not** silently accept the legacy heuristic fallback,
because competitive attempts must be scored identically for every player.

## Challenge versioning

The app creates a stable challenge-set id from:

- challenge date
- Daily Challenge version (`43A-bank42.6`)
- the ten deterministic puzzle ids

This provides the version hook v43B will store with leaderboard submissions.

## Validation

v43A adds focused Daily Challenge tests on top of the v42.6 suite:

- deterministic same-date Daily 10
- unique challenge ids
- 5/5 Roll 1/Roll 2 balance
- 9 realistic + 1 curated composition
- 2/3/3/2 game-stage composition
- Eastern-time date boundary
- exact scoring of all ten questions
- perfect 10/10 run = 0.00 EV lost
- deterministic demo leaderboard
- leaderboard ranking/tiebreak path
- group question statistics
- Daily mode hides coaching until completion
- Daily mode rejects heuristic fallback
- mobile Daily result grid protection

All existing exact-policy, expanded-bank, teaching, personalization, Session
Coach, mastery, mobile UI, strategy-regression, and published-strategy tests
remain passing.

## v43B next

Once the v43A loop feels right, v43B will replace the simulated friend data with:

- persistent player identity
- friend groups / join codes
- one official attempt per player/day
- cross-device resume
- real daily leaderboards
- participation streaks
- weekly standings
- group question statistics from actual players

The puzzle engine and scoring format are already designed so that connecting the
database does not require changing the underlying Daily Challenge.