# Yahtzee Coach v42.6 — Realistic Game-State Pass

v42.6 keeps the complete v42.5 exact solver, expanded 252-roll puzzle universe,
mobile UI, grading, personalized teaching, Session Coach, mastery, and Daily-10
readiness. The change is the **scorecard source**: practice no longer feels like
it was assembled from strategically convenient boxes.

The goal of this pass is simple: **hard decisions on believable scorecards**.

## What changed

### 1. 85% of scorecard contexts now come from actual simulated game histories

The bank still contains **420 exact scorecard contexts**, but the representative
scorecards are now:

- **357 (85%) Simulated Game** snapshots
- **63 (15%) Curated Edge Case** snapshots

The simulated cards were produced by playing **4,000 complete turn-by-turn games**
from an empty scorecard. Each turn rolls dice, makes two hold decisions, rolls
again, and legally scores one category before the next snapshot is captured.

This means a normal practice scorecard is no longer created by saying things
like “make the bonus dead and leave Chance open.” It is a state an actual game
simulation reached.

The simulator deliberately uses multiple human-style player profiles:

- **Strong** — usually makes the strongest-looking move, with occasional close alternatives
- **Regular** — mostly sensible play with more second-best / human choices
- **Messy** — still plausible, but more willing to make a questionable sacrifice

The bank intentionally does **not** make every prior turn computer-perfect.

### 2. Human-looking imperfections are preserved

Real scorecards sometimes contain choices such as zeroing an upper box while
Chance remains open. v42.6 allows those situations when they arise from the
simulated history instead of treating every imperfection as invalid.

The final 420-context bank contains, among other examples:

- **27** contexts with at least one zeroed upper box while Chance is still open
- **68** contexts where Chance has already been used with 7+ boxes still open
- **303** contexts containing at least one non-cookie-cutter upper-section result

Those are not random corruptions. The 357 simulated contexts are snapshots after
real simulated turns, with legal category scores and one category closed per turn.

### 3. The strategic coverage from v42.5 is retained

The game-stage balance remains:

- **60 Opening** contexts (10–13 boxes open)
- **120 Midgame** contexts (6–9 open)
- **120 Late Game** contexts (3–5 open)
- **120 True Endgame** contexts (1–2 open)

All upper-bonus states remain represented:

- On Pace
- Under Pressure
- Ahead
- Bonus Earned
- Bonus Dead / mathematically unreachable

All Yahtzee states remain represented:

- Yahtzee open
- Yahtzee zeroed
- Yahtzee scored for 50 / bonus live

All **81** exact states from the original v42 practice deck remain supported.

### 4. The complete dice universe remains available

v42.6 still supports:

- **420 scorecard contexts**
- **252 canonical five-dice rolls**
- **Roll 1 and Roll 2**
- **211,680 exact state/roll situations**
- **3,669,120 legal hold values**

The exact full-game solver remains the source of truth for recommendations.
The realism simulator only creates believable *scorecard histories*; it does not
replace or weaken the exact strategy engine.

### 5. Unlimited Practice now targets the realistic mix

Practice draws scorecards at approximately:

- **85% Simulated Game**
- **15% Curated Edge Case**

It still balances game stage, Roll 1 / Roll 2, and strategy family so the harder
v42.5 decision variety remains intact. Rare conditions such as a live extra-Yahtzee
bonus or already-secured upper bonus are deliberately downweighted unless that
condition is the lesson being practiced.

The curated 15% is intentional. Rare or awkward states can be excellent teaching
problems even if they do not occur often in ordinary play.

### 6. Daily Challenge readiness is more realistic too

The deterministic Daily-10 selector remains hidden until the shared v43 social
layer is built. It now selects:

- **9 realistic simulated-game scorecards**
- **1 curated edge case**
- **5 Roll 1 + 5 Roll 2**
- **2 Opening + 3 Midgame + 3 Late Game + 2 True Endgame**
- a deliberate difficulty mix
- broad strategy-family coverage

The same date still recreates the same ten challenge IDs for every player.

## Final bank audit

- 420 scorecard contexts
- 357 simulated / 63 curated
- 85.0% realistic-game share
- 81 / 81 original v42 exact states preserved
- 252 / 252 canonical dice rolls
- 211,680 Roll-1/Roll-2 puzzle situations
- 3,669,120 exact legal-hold values
- 200,148 Daily-Challenge-eligible situations

See `puzzle_bank_audit.json` and `puzzle_bank_contexts.csv` for the full audit.

## Runtime files

- `puzzle_bank.py` — realistic practice generator + deterministic Daily-10 selector
- `puzzle_bank.npz` — 420 scorecards plus origin/profile/history metadata
- `challenge_catalog.npz` — 211,680 tagged exact puzzle situations
- `exact_policy.npz` — exact live policy for all 420 selected scorecard states

Support/audit files:

- `puzzle_bank_audit.json`
- `puzzle_bank_contexts.csv`
- `puzzle_bank_tests.py`
- `advanced_context_teaching_tests.py`
- `exact_integration_tests.py`

## Deployment from v42.5

Only the puzzle-bank branch changed. Upload these files to the **root** of the
GitHub repo:

- `exact_policy.npz`
- `puzzle_bank.py`
- `puzzle_bank.npz`
- `challenge_catalog.npz`
- `README.md` (recommended)

`app.py`, `exact_mode.py`, `session_learning.py`, the dice UI, grading, teaching
cards, and mastery system are unchanged from v42.5.

Suggested commit message:

`Make expanded scorecards realistic - v42.6`

After Streamlit redeploys, play 10–15 normal practice rounds. The strategic
difficulty should feel like v42.5, while the scorecards should look much more
like snapshots from real games.

The shared Daily Challenge leaderboard/database is still the planned v43 step.
