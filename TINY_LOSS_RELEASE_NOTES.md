# v43B Phase 2K.14.13 — Tiny-Loss Display Hotfix

Baseline: the complete, working 2K.14.12 release. Presentation only.

## Fixed

Q5's keep 4 lost 0.003757476806640625 expected points versus keep 1,4,5.
The app used that nonzero value for grading, but displayed 0.00. The screen
therefore appeared to penalize a zero-loss answer.

- The question heading now reads `Q5 · A · <0.01 points lost`.
- The shared Daily/Practice comparison card shows `<0.01 expected points`,
  without a misleading plus-zero or plus-less-than sign.
- Its explanation says the holds are effectively tied and the player's choice
  was excellent, while acknowledging the tiny mathematical edge.
- Full hold rankings and report explanations no longer label a tiny positive
  deficit as zero. The report's numeric loss line retains additional decimal
  precision so it remains parseable as a number.
- Real zero still displays `0.00`. Ordinary two-decimal values are unchanged.
  The `<0.01` treatment applies to positive values whose two-decimal display
  would otherwise be `0.00`, not to all near-ties or all losses under 0.10.

## Unchanged

The raw Q5 loss remains 0.003757476806640625. Its grade stays A, rank stays
#2 of 16, and its share square stays yellow. It still does not count as an
exact-best hold and still interrupts an exact-best streak. This release does
not broaden perfect-ten eligibility or change historical scores.

No solver, hold ranking, Points Lost, grading, tie tolerance, Daily composition,
saved answer, database, authentication, medal or celebration changes.
The comparison table and responsive styling are unchanged. The existing
question expander and full-ranking disclosure remain in place.

## Runtime scope

- `app.py`: version and the affected presentation strings/HTML escaping.
- `exact_mode.py`: formatting of small loss values and proportional wording.
- `loss_display.py`: new tiny, presentation-only number formatter.

Other changed files are documentation, the new screenshot regression, and
existing regression version/hash/text guards updated for this intentional
presentation change. The exact strategy class has a separate unchanged AST
fingerprint, and the policy/data artifacts remain byte-identical to 2K.14.12.

## Tests

The new regression recreates the screenshot, checks the raw loss and grade,
verifies the question label and shared rendered card, tests rounding boundaries
and exact-zero behavior, and confirms the yellow square and streak behavior
are unchanged. Existing Daily/Practice and ranking suites remain included.
Validation uses the established Streamlit 1.52.2 test environment. No dependency
pin or requirement change is included. Physical phone testing is not claimed.

## Installation

Apply the browser-upload ZIP over 2K.14.12. Extract it and upload the contents
of `UPLOAD_TO_GITHUB` into the existing repository root, replacing matching
files. Do not upload the ZIP itself or create a nested UPLOAD_TO_GITHUB folder.
The full ZIP is the complete cumulative app and includes the prior coaching
improvements. Refresh the app after deployment to rebuild review text.

No Supabase SQL, secrets, account reset or replay of the Daily is required.

## Commit

```text
v43B Phase 2K.14.13 - clarify tiny nonzero points lost
```
