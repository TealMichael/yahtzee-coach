# Yahtzee Coach v39 — Personalized Teaching Pass

v39 keeps the exact dynamic-programming solver as the strategy source of truth and
makes the coaching respond directly to the player's chosen hold. The solver values,
compact exact policy, dice UI, scorecard, and practice generator are unchanged from
v38.

## What changed

The result now includes a prominent **Your idea vs. best idea** comparison:

- **Your idea** describes what the player's selected dice actually preserve or chase.
  The wording is intentionally cautious: it explains what the hold does rather than
  pretending the app can read the player's mind.
- **Exact best idea** explains the strategic plan behind the exact solver's hold in
  the context of the current scorecard.
- **Adjustment** gives one concrete action: protect additional dice, release weaker
  dice, swap the structure, or make no change when the player is already optimal.
- Near-ties get language such as **Tiny refinement** or **Small refinement** rather
  than being treated like major mistakes.
- Bigger expected-value losses use stronger coaching language such as **Clear
  adjustment** or **Major correction**.
- Exact-optimal choices are explicitly affirmed: the coach explains what the player
  recognized correctly, not just that the grade is A+.

The v38 teaching layers remain:

- Coach says strategic explanation
- Key Lesson card
- How close was it?
- expected game points / hold rank
- concrete dice differences
- top exact holds and expected-point gaps
- safe legacy fallback if exact lookup fails

## Personalized teaching examples protected by tests

Run:

`python personalized_teaching_tests.py`

The v39 focused suite checks that:

- a close two-pair choice preserves the player's good pair idea and suggests adding
  the second pair as a tiny refinement
- breaking four 5s gets a specific major correction to protect the other three 5s
- an exact-optimal triple is explained and affirmed as the correct plan
- a visible straight chase can be recognized as sensible while the scorecard still
  explains why another exact plan is better
- the three personalized messages are exposed in metadata for future session-level
  learning features

Result: **5 PASS / 0 FAIL**.

The v38 teaching suite also remains green: **6 PASS / 0 FAIL**.

## Exhaustive exact integration audit

Run:

`python exact_integration_tests.py`

Measured on v39:

- 40,824 / 40,824 state-roll policy records validated
- 707,616 legal-hold exact-value lookups validated
- 130 tied-best records handled correctly
- 40,824 / 40,824 exact-first report routes used exact mode; zero fallbacks
- every exact report includes the v39 personalized comparison plus the v38 teaching
  sections
- 100 / 100 deck templates covered (81 unique solver states)
- 20,000 / 20,000 generated practice rounds mapped to an exact state
- deliberate unsupported-state fallback: PASS
- missing/corrupt policy-load fallback: PASS
- 10,000 ranked exact lookups: about 0.350 s total, about 0.035 ms each

Legacy protection remains green:

- strategy regression suite: 26 PASS / 0 FAIL
- published strategy audit: 15 PASS / 0 FAIL
- Python compilation: PASS

## Developer diagnostics

`?solver=1` opens the hidden exact-mode diagnostics panel. `?shadow=1` remains an
alias. Exact should continue increasing while Fallbacks remains at 0 for the current
practice deck.

## Deployment files

Because the exact policy and engine did not change from v38, a working v38 live app
only needs these updated files at the GitHub repository root:

- `app.py`
- `exact_mode.py`
- `README.md` (recommended)

The package includes all unchanged files as well so it remains self-contained.
