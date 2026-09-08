# v43B Phase 2K.14.5 — Simulated Scorecard Realism

Literal baseline: revised 2K.14.4 Balance + Coaching full-app ZIP.

## Change

Simulated histories with Chance still open are excluded if Threes, Fours,
Fives, or Sixes contains zero and the upper bonus is still mathematically
reachable but unearned. This is a teaching-state plausibility rule, not a
claim that scratching an upper category is always strategically wrong.

Ones/Twos zeros remain allowed. Higher-upper zeros remain allowed when Chance
is filled or the bonus is Dead or Earned. Curated Edge Cases retain their
existing exemption. Existing passed-up-Yahtzee history filtering remains active.

Four of the 420 raw contexts meet the new predicate. The source bank remains
intact for solver coverage and historical Dailies; selection filters the states.
Daily-eligible situations after realism filtering: 193,551 before; 191,699 now.

## Activation

Practice applies the rule on installation. Daily applies it beginning September
9, 2026 America/New_York. Earlier dates retain the original filter, content,
ordering, challenge IDs, and version. New Dailies use version 43B-bank42.6-2K14-5.
Install before that date. If installing later, request a new forward-only date.
No Supabase step is required.

## Unchanged

The solver, exact policy, category math, rankings, Points Lost, coaching text,
comparison layout, dice, login, database behavior, avatars and medals are untouched.
Daily balance selection preferences remain unchanged; they operate on the
new eligible candidate pool after activation. Practice selection uses the same
workflow and adds only the narrower state eligibility rule.

Runtime changes: puzzle_bank.py (filter and dated Daily routing),
daily_challenge.py (dated version), app.py (release label only).

## Regression coverage

The existing raw-bank realism regression now checks generated eligibility
instead of requiring disallowed upper-zero histories to remain eligible.
Coverage includes all six faces, used/open Chance, reachable/Dead/Earned bonus,
curated exceptions, all 420 stored states, 400 Practice draws, 600 future Daily
puzzles, hard Daily composition, and historical challenge fingerprints.
Existing whole-file checksums were updated only for the two changed generator
modules; strategy and policy checksums remain unchanged. Release-label assertions
advance to 2K.14.5. See the final release handoff for packaged test results.

## GitHub browser installation

Extract the browser patch ZIP. Upload the files INSIDE UPLOAD_TO_GITHUB to the
repository folder containing app.py using Add file > Upload files. Do not upload
the ZIP itself or create an extra enclosing folder. Leave unchanged files in place.
The patch is for the revised 2K.14.4 installation; the complete ZIP is also provided.

Commit: `v43B Phase 2K.14.5 - filter implausible upper-zero histories`
