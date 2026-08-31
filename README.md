# Yahtzee Coach v43B Phase 2K.14 — Daily Spotlight + What If

This release keeps the official Daily Ten fast and competitive, then adds one optional learning moment at the top of the player's completed-ten review.

## Player experience
- “Your Daily Spotlight” selects one interesting decision from that player's ten.
- A correct answer can be selected when it contains the strongest lesson.
- The selector avoids practical ties, vague solver prose, and simply choosing the largest mistake.
- The full coaching remains closed until “Explore this decision” is tapped.
- When a verified variation exists, “Change one thing” changes one scorecard box while preserving the dice and roll.
- The player chooses again, then sees whether the best hold changes and how the exact margin changes.
- The follow-up is unscored and never affects the Daily attempt, standings, sharing, grades, or streaks.
- The app does not force a What If when the exact policy does not provide a useful one-box comparison.

## Variety behavior
The existing Daily selector remains unchanged. It already provides soft weekly family balance, 5–7 families per day, a 5/5 Roll 1–Roll 2 split, two true endgames, and the established occasional Bank-It-or-Break-It schedule. Phase 2K.14 adds regression coverage around those rules rather than a visible quota.

## Unchanged
Exact strategy, best holds, Points Lost, grades, all official Daily puzzles and challenge IDs, Practice, dice controls, persistence, auto-login, Supabase behavior, social results, avatar designs, medal ceremony, and medal calculations.

## Verification
63/63 automated suites pass. The new coverage includes real Streamlit widget interaction on 1.52.2, duplicate-die selection, exact counterfactual recomputation, 42-day variety and learning audits, read-only state checks, and unchanged Daily fingerprints. The exhaustive policy audit still verifies all 3,669,120 legal hold values.

No Supabase migration is required.
