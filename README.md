# Yahtzee Coach v43B Phase 2H — Install Button Fix + Clear Device Steps

This checkpoint fixes the home-screen/install control after live testing showed that tapping **Install / Add** could appear to do nothing on both phones and computers.
The exact strategy engine, Daily sharing, friend groups, persistent attempts, invite links, and custom mascot icon remain intact.

## v43B Phase 2H changes

- The install control no longer silently falls back when the browser does not provide a native install prompt.
- On **iPhone / iPad**, the green button now opens a clearly visible in-app instruction panel with the required **Share → Add to Home Screen → Open as Web App → Add** sequence.
- On **Android**, the fallback panel shows the Chrome **⋮ → Add to Home screen / Install app** path.
- On **desktop Chrome**, the panel shows **⋮ → Cast, save, and share → Install page as app**.
- On **Mac Safari**, the panel also shows **File → Add to Dock**.
- If the browser actually exposes a native `beforeinstallprompt` event, Yahtzee Coach still uses the direct system install prompt.
- If that prompt is declined or fails, the app immediately falls back to the visible manual steps instead of appearing unresponsive.
- The custom teacher-die mascot icon, installed-mode detection, and **Copy app link** control remain.
- No Supabase schema changes are required for this phase.

## Why the previous button appeared broken

The Phase 2F/2G button could directly prompt only when the browser had already granted the page a native install event. When that event was unavailable, clicking the button merely repeated guidance that was already visible, so there was little or no visible response. Phase 2H makes that fallback explicit and interactive.

## What is intentionally NOT changed

- Daily puzzle composition/version remains `43A-bank42.6`.
- Exact policy and strategy recommendations are unchanged.
- iPhone/iPad still requires the final Apple-controlled Home Screen confirmation taps.
- Browser-controlled desktop install menus cannot be opened programmatically when the browser does not expose its install event.
- Daily result sharing, real friend groups, back/edit review, persistence, and Practice are unchanged.

## Phase 2H live-test goal

1. Upload the full current app to GitHub.
2. On your phone, tap the green install button and confirm a clear device-specific instruction panel opens underneath it.
3. On iPhone/iPad Safari, follow Share → Add to Home Screen → Open as Web App → Add and confirm the mascot icon appears.
4. On your computer, tap the green button and confirm the Chrome/Edge or Mac instructions visibly open.
5. If your browser offers a native install prompt, confirm the button opens that prompt instead.
6. Confirm Daily result sharing and the rest of the app still behave normally.

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