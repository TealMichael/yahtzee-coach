# v43B Phase 2K.14.6 — Full House Math + Clearer Coaching

Literal baseline: packaged 2K.14.5. This release changes coaching explanations only.

## Full House decisions

The existing card now distinguishes a two-pair chase from protecting a made
25-point Full House. It compares completion odds for the actual roll horizon,
the relevant open upper box, and the current upper-bonus benchmark. Correct
answers receive the same comparison against the instructive alternative.

For supported final-reroll comparisons, the existing expanded calculation also
shows average highest immediate raw score across the open boxes. This statistic
excludes bonuses and future value; it is not the model's recommended category
selection. We use it to identify cases where this-turn and remaining-game
preferences reverse. Roll 1 comparisons do not label next-roll values as whole-turn
values. Extra-Yahtzee/Joker positions keep their specialized explanation.

Reported case: keep both pairs has 33.3% Full House odds versus 9.3%; keeping
Fives gives 42.1% chance of 15+ Fives versus 16.7%. The current upper subtotal of
9 plus three of each remaining face reaches exactly 63. Immediate raw-score
averages are 15.00 versus 14.88, while the unchanged remaining-game values are
139.82115173339844 versus 141.605712890625 in favor of keeping Fives.

## Other clarity corrections

- Reachable, Dead, and Earned upper bonuses get explicit numerical context.
- Three-of-a-face odds are not overall bonus probability.
- Matching-category expected points include zero on misses and the dice total
  on qualifying hands; completion chance alone does not describe their value.
- Scoring paths cannot be added: only one category is filled per turn.
- Roll 1 category-specific plans can choose different final holds.
- Isolated straight payoff differences are no longer presented as a decomposition
  of the full-game margin. Low-pair prose no longer calls a face benchmark bonus safety.

## Scope and validation

The existing table rows, styling, renderer, navigation and expansions stay intact.
No change to solver, policy, ranking, Points Lost, grading, puzzle selection,
Daily activation dates, scorecard realism, authentication, database, dice or medals.
Runtime changes: new coaching_math.py, three explanation functions in exact_mode.py,
and app.py version label only. No app UI functions change.

Regression coverage includes independent enumeration of all final rolls for the
reported immediate-score comparison, exact policy values, bank/chase distinctions,
correct/incorrect answers, both roll horizons, closed boxes, bonus states, practical
ties, preserved Joker guidance, and synthetic Daily rendering of the explanation.
Existing 840-position coaching audits and full gameplay/selection suites are retained.
UI checks are automated Streamlit checks, not physical iPhone testing.
See the final release handoff for results from the extracted delivery ZIP.

Whole-file coaching checksums and release-label expectations advance deliberately.
Strategy and category-calculation functions and the exact policy remain unchanged.
The older AST guard now excludes the separately corrected straight-detail prose
function as well; it continues protecting the non-presentation engine code.

## GitHub browser installation

For an existing 2K.14.5 installation, extract the browser patch and upload the
files INSIDE UPLOAD_TO_GITHUB into the repository folder containing app.py.
Leave unchanged files in place. The full app ZIP is supplied for preservation.
No Supabase step. Coaching activates on installation; no new Daily schedule change.

Commit: v43B Phase 2K.14.6 - explain Full House tradeoffs and scoring math
