# Yahtzee Coach v42.5 — Expanded Puzzle Universe / Daily Challenge Readiness

v42.5 keeps the complete v42 practice-momentum, mastery, mobile UI, exact solver,
grading, personalized teaching, and Session Coach experience. The change is
underneath the practice generator: Unlimited Practice now draws from a much
broader exact-policy universe instead of the older 81-state / 79-dice curated
practice footprint.

This is the bridge between v42 and the planned shared Daily Challenge.

## What changed

### 1. Exact scorecard contexts expanded from 81 to 420

All 81 previously supported exact states are preserved. The new bank deliberately
adds the strategy areas that were underrepresented:

- **60 Opening** contexts (10–13 boxes open)
- **120 Midgame** contexts (6–9 boxes open)
- **120 Late Game** contexts (3–5 boxes open)
- **120 True Endgame** contexts (1–2 boxes open)

True endgame was the biggest prior blind spot. v42.5 includes **58 one-box-left**
contexts and **62 two-box-left** contexts.

### 2. Every upper-bonus condition is represented

The 420 scorecard contexts include:

- **125 On Pace**
- **79 Under Pressure**
- **62 Ahead**
- **72 Bonus Earned**
- **82 Bonus Dead / mathematically unreachable**

The visible teaching layer now explicitly understands the last two cases. It no
longer talks as though the 35-point bonus is still a reason to protect upper dice
when the bonus is already secured or cannot be reached.

### 3. All Yahtzee states are represented

- **201 Yahtzee open** contexts
- **128 Yahtzee zeroed** contexts
- **91 Yahtzee scored for 50** contexts

The teaching layer now calls out the extra-Yahtzee / Joker window when a 50-point
Yahtzee is already on the card.

### 4. All 252 canonical five-dice rolls are available

The old titled deck explicitly listed 79 unique dice structures. v42.5 can use
**all 252 canonical five-dice outcomes** for every selected scorecard context and
for both Roll 1 and Roll 2.

That creates:

- **420 scorecard contexts**
- **252 canonical dice rolls**
- **2 roll stages**
- **211,680 exact state/roll situations**
- **3,669,120 legal hold values** stored and audited

The exact recommendation still comes from the completed full-game dynamic solver.
No heuristic recommendation has replaced it.

### 5. Expanded strategy tags and difficulty metadata

Every exact situation is tagged for future challenge construction using strategy
families such as:

- Matching Dice
- Straight Structure
- Full House
- Upper Bonus
- Bonus Secured
- Bonus Is Gone
- Chance Timing
- Joker / Extra Yahtzee
- Flexible Board

Situations also receive a difficulty label based on the exact gap between the
best hold and the next genuinely worse hold:

- Knife-edge
- Hard
- Medium
- Clear
- Punishing

These tags are not used to alter the solver. They are selection metadata so a
Daily 10 can be intentionally balanced rather than randomly easy or brutal.

### 6. Unlimited Practice now uses the expanded bank

The UI is still the approved v42 / v41.1 interface. The difference is that new
practice rounds are selected from the expanded exact universe.

Practice selection intentionally balances game stage, Roll 1 vs Roll 2, and
strategy family instead of allowing the largest dice family to dominate.

The original v42 titled deck remains in `yahtzee_engine.py` as a safety fallback.

### 7. Daily Challenge selector is ready, but not exposed yet

`puzzle_bank.py` now contains a deterministic `generate_daily_challenge_set()`
function. Given the same date, it creates the same ten puzzles for every player.

The current Daily-10 design guarantees:

- exactly **10 unique situations**
- **5 Roll 1 + 5 Roll 2**
- **2 Opening + 3 Midgame + 3 Late Game + 2 True Endgame**
- broad strategy-family coverage (normally 6+ distinct skills)
- a deliberate difficulty mix
- stable challenge IDs derived from date + bank version + puzzle state

A 31-day simulation produced **310 unique challenge IDs across 310 slots**.

v42.5 does **not** add the shared leaderboard/database yet. v43 can use this
selector as the common puzzle source and store only player/group/submission data.

## Runtime files added

- `puzzle_bank.py` — expanded practice generator + deterministic Daily-10 selector
- `puzzle_bank.npz` — 420 human-readable scorecard contexts and metadata
- `challenge_catalog.npz` — 211,680 tagged exact puzzle situations
- `exact_policy.npz` — expanded exact live policy for all 420 contexts

Audit/support files:

- `puzzle_bank_audit.json`
- `puzzle_bank_contexts.csv`
- `puzzle_bank_tests.py`
- `advanced_context_teaching_tests.py`

## Validation

Key v42.5 checks:

- 420 / 420 expanded scorecard contexts map to exact policy states
- 81 / 81 previous exact states preserved
- all 252 canonical dice rolls represented
- both Roll 1 and Roll 2 represented
- **211,680** exact state/roll policy situations
- **3,669,120** legal hold values structurally audited
- **20,000 / 20,000** generated practice rounds used exact mode
- 20,000 sampled public exact analyses/value lookups passed
- 840 representative exact-first teaching reports used zero fallbacks
- exact ranked lookup remains about **0.04 ms** locally after load
- Daily-10 deterministic/balance tests passed
- 31-day Daily-10 simulation passed
- advanced teaching checks passed for bonus-secured, bonus-dead, Joker,
  true-endgame, and Chance-timing contexts
- strategy regression suite: **26 PASS / 0 FAIL**
- published strategy audit: **15 PASS / 0 FAIL**
- teaching, personalized teaching, Session Coach, practice-momentum, mobile/UI
  protection tests all pass

Run the new readiness tests with:

```bash
python puzzle_bank_tests.py
python advanced_context_teaching_tests.py
python exact_integration_tests.py
```

The established suites remain available as well.

## Deployment from v42 / v41.1

Because the exact policy and practice source expanded, this update requires more
than an `app.py` swap. Upload these files to the **root** of the GitHub repo:

- `app.py`
- `exact_mode.py`
- `exact_policy.npz`
- `puzzle_bank.py`
- `puzzle_bank.npz`
- `challenge_catalog.npz`
- `session_learning.py`
- `README.md` (recommended)

The three `.npz` files must sit beside `app.py`; do not place them in a subfolder.

Suggested commit message:

`Expand exact puzzle universe for Daily Challenge - v42.5`

After Streamlit redeploys, confirm that normal practice loads, exact fallbacks
remain at 0 in `?solver=1`, and a handful of rounds include noticeably broader
scorecard contexts (including true endgames / bonus-secured / bonus-dead cases).
