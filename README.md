# Yahtzee Coach v43B Phase 2K.14.4 — Daily Decision Balance

Daily selection now balances actual straight-related and upper-pair decisions
across labels. Starts September 7, 2026 (Eastern Daily date); install before then.
Practice, coaching and UI are unchanged. No Supabase migration.

See **BALANCE_RELEASE_NOTES.md** for definitions, limitations, before/after
results, performance and deployment details. **DAILY_BALANCE_AUDIT.json** contains
all 56 date-by-date results for both selectors. 68/68 release suites pass.

## Previous release: Phase 2K.14.3 (retained features)

This targeted cleanup makes the expanded ranking section player-facing while preserving the approved comparison card and every strategy value from Phase 2K.14.2.

## What changed

- The disclosure now reads **📐 See full hold rankings**.
- Ranked holds appear first and remain fully dynamic.
- The best hold is labeled **Best**; alternatives show how many expected points they trail.
- The player's lower-ranked hold remains visible when it falls outside the top three.
- Developer-facing exact-policy language has been removed from the player view.
- A subtle **About the math** note explains that scoring-path evidence and full-scorecard rankings answer different questions.
- Useful position-specific calculations remain available beneath the rankings when a decision has them.

## Coaching flow

**Comparison → Why it wins → Takeaway → Full hold rankings**

Players can see the decision, understand it, learn the lesson, and then verify the complete ranking without encountering engine-oriented prose.

## Unchanged

The comparison table, winner explanation, Takeaway, coaching evidence, exact category calculations, exact policy, best holds, hold ranks, Points Lost, grades, Daily puzzles and challenge IDs, scoring, dice controls, persistence, auto-login, Supabase behavior, social results, avatars, medal ceremony, and medal calculations.

## Verification

67/67 automated suites pass. New coverage verifies dynamic ranking content, expected-point margins, disclosure order, player-facing copy, shared Daily/Practice rendering, responsive styling, and byte-for-byte strategy preservation. The exhaustive 3,669,120-hold policy audit remains green.

No Supabase migration is required.
