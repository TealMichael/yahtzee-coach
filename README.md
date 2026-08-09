# Yahtzee Coach v43A.1 — Daily Challenge UI Refinement

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
