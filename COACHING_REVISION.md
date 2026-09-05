# v43B Phase 2K.14.4 — Coaching Clarity Revision

Replacement for the original uninstalled Daily Decision Balance package.
Literal revision baseline: its complete packaged ZIP. All Daily balance code,
including the September 7, 2026 Eastern activation date, is unchanged.

## Changes

- Generic comparisons show the same upper category on both sides, including
  multiple relevant held faces, instead of silently choosing a different face.
- Chance can appear whenever open and meaningfully different, not just endgames.
- Generic straight evidence uses one row, leaving room for other scoring paths.
- Three-of-a-face odds are labeled as such, not called overall bonus pace.
  The specialized low-pair card retains its calculations but marks different-face
  benchmark comparisons as split rather than declaring an overall bonus winner.
- Generic summaries describe observed strengths separately from the full-game
  margin. No invented 'deeper scorecard sequencing' explanation when evidence
  does not isolate the cause. Correct answers and practical ties use this too.

The reported Roll 2 case retains keep 5,6 first, keep 5 second, and exactly
0.400543212890625 Points Lost. Its five rows show Fives, Sixes, straight chances,
Three of a Kind, and Chance. Separate scoring-path expectations must not be added.

## Scope protection

Only exact_mode.py changes at runtime versus the original 2K.14.4 ZIP.
AST comparison identifies exactly four changed functions: _comparison_topic,
_generic_comparison_rows, _low_pair_open_board_card, _build_comparison_card.
All solver and exact category-specific calculation functions remain identical.
All other runtime files, including app.py and the Daily balance patch, are identical.
The approved styling, renderer, disclosure, controls and navigation are unchanged.

Existing whole-file coaching checksum tests were advanced to the revised file
hash; the exact policy checksum is unchanged. Two old display assertions were
updated for the intentional benchmark label and split comparison. New regression
checks the reported values, same-category comparisons, row cap, honest language,
and left/right evidence symmetry across both roll stages.

UI tests are automated Streamlit checks, not a physical iPhone test.
Source validation: all 69 suites passed (66 in the initial batch, then the three
Streamlit suites after restoring the missing test dependency). Streamlit 1.63.0
was used for those UI checks; requirements.txt is unchanged. The new test also
hashes the baseline AST outside the four allowed functions, protecting all
strategy, report ranking, grading, and category calculations from logic drift.
No Supabase migration. Follow DEPLOYMENT_STEPS.txt before the activation date.

Commit: `v43B Phase 2K.14.4 - balance Daily puzzles and clarify coaching evidence`
