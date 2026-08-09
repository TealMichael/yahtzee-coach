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