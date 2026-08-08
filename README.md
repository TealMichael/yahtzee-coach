# Yahtzee Coach v38 — Teaching Experience Pass

v38 keeps the exact dynamic-programming solver as the primary strategy engine and
upgrades the player-facing coaching around that exact answer. The solver values
and compact policy table are unchanged from v37; the improvement is in how the
app explains, grades, and teaches each decision.

## What changed

- Exact Roll 1 and Roll 2 recommendations remain the source of truth.
- The main **Coach says** message now explains the visible strategic reason behind
  the exact hold instead of merely saying that it has the highest value.
- A new **Key lesson** card turns each result into a reusable Yahtzee idea.
- A new **How close was it?** explanation distinguishes near-ties from meaningful
  mistakes so players do not overlearn tiny solver differences.
- Expected-value language is translated as **expected game points** and explicitly
  defined as average final-game score across future rolls and optimal decisions.
- The coach now compares the player's hold with the exact hold in concrete dice
  terms: which dice are additionally protected or released.
- Explanations recognize common strategic structures including:
  - made hands
  - four matching dice
  - triples
  - two-pair Full House paths
  - four-die and three-die straight cores
  - useful upper-section pairs
  - constrained/endgame single-die holds
  - full rerolls / flexibility decisions
- The full report shows the top three exact holds and their expected-point gaps.
- Tied exact-optimal holds are still treated as equally correct.
- The letter grade remains a teaching rubric based on exact expected game points
  lost.
- The legacy heuristic coach remains only as a safe fallback.
- Dice size, dice behavior, scorecard layout, session flow, and practice generator
  are unchanged.

## Teaching examples protected by tests

`python teaching_experience_tests.py`

The focused teaching suite checks that:

- a 0.16-point two-pair decision is described as a near-tie rather than a bad move
- breaking four 5s receives a clear “protect four matching dice” lesson
- cramped scorecards explain why a lone useful upper die can beat a prettier pair
- four-die straight cores are explicitly taught as premium structures
- every exact report includes closeness, good thinking, why the exact hold wins,
  a teaching takeaway, top exact alternatives, and a final recommendation

Result: **6 PASS / 0 FAIL**.

## Exhaustive exact integration audit

`python exact_integration_tests.py`

Measured on the v38 package:

- 40,824 / 40,824 state-roll policy records validated
- 707,616 legal-hold exact-value lookups validated
- 130 tied-best records handled correctly
- 40,824 / 40,824 exact-first report routes used exact mode; zero fallbacks
- every exact report produced the new teaching sections
- 100 / 100 deck templates covered (81 unique solver states)
- 20,000 / 20,000 generated practice rounds mapped to an exact state
- deliberate unsupported-state fallback: PASS
- missing/corrupt policy-load fallback: PASS
- 10,000 ranked exact lookups: about 0.355 s total, about 0.036 ms each

Legacy protection remains green:

- strategy regression suite: 26 PASS / 0 FAIL
- published strategy audit: 15 PASS / 0 FAIL
- Python compilation: PASS

## Developer diagnostics

`?solver=1` opens the hidden exact-mode diagnostics panel. `?shadow=1` remains
an alias. Exact should continue increasing while Fallbacks remains at 0 for the
current practice deck.

## Deployment files

Because the exact policy itself did not change from v37, an existing v37 live
app only needs these updated files at the GitHub repository root:

- `app.py`
- `exact_mode.py`
- `README.md` (recommended)

The package also includes the unchanged policy, engine, requirements, and test
files so it remains self-contained.
