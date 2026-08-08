# Yahtzee Coach v37 — Exact Mode

v37 promotes the precomputed dynamic-programming policy from shadow mode to the
primary live strategy engine for the current practice deck.

## What changed

- Exact Roll 1 and Roll 2 recommendations are now player-facing.
- The current practice deck's 100 scorecard templates collapse to 81 unique
  solver states; every one is included in `exact_policy.npz`.
- Every canonical five-dice roll (252) is covered for both Roll 1 and Roll 2.
- Tied exact-optimal holds are treated as equally correct.
- The letter grade is a coaching rubric based on exact expected points lost.
  The optimal-hold recommendation and expected values come directly from the
  exact solver.
- The legacy heuristic coach remains as a safe fallback if a future app state
  is not present in the compact policy table.
- The dice UI, scorecard layout, session flow, and practice generator are not
  changed.

## Exhaustive integration audit

`python exact_integration_tests.py`

Measured on the v37 package:

- 40,824 / 40,824 state-roll policy records validated
- 707,616 legal-hold exact-value lookups validated
- 130 tied-best records handled correctly
- 40,824 / 40,824 exact-first report routes used exact mode; zero fallbacks
- 100 / 100 deck templates covered (81 unique solver states)
- 20,000 / 20,000 generated practice rounds mapped to an exact state
- deliberate unsupported-state test successfully routed to legacy fallback
- missing/corrupt policy-load test successfully routed to legacy fallback
- 10,000 ranked exact lookups: about 0.339 s total, about 0.034 ms each
- policy load: about 0.013 s locally

Legacy regression protection also remains green:

- strategy regression suite: 26 PASS / 0 FAIL
- published strategy audit: 15 PASS / 0 FAIL
- Python compilation: PASS

## Developer diagnostics

The former shadow query parameter still works for convenience:

`?shadow=1`

`?solver=1` also works. The hidden panel now reports how many submitted rounds
used exact mode versus the legacy fallback.

## Deployment files

The live app needs these files at the GitHub repository root:

- `app.py`
- `yahtzee_engine.py`
- `exact_mode.py`
- `exact_policy.npz`
- `requirements.txt`

`README.md` and the test files are optional for Streamlit but useful to keep in
the repository.
