# Yahtzee Coach v43B Phase 2K.14.2 — Turn-Aware Comparison Cards

This release replaces long comparative coaching paragraphs with a compact visual that shows why one hold wins without changing any strategy value.

## Player experience

- Every reviewed decision receives a responsive side-by-side evidence card.
- The winner, expected-point margin, hold rank, player hold, and comparison hold appear first.
- One to five decision-relevant rows compare the two plans: upper-box value, bonus benchmark, straight chances, straight payoff, matching-hand routes, Full House value, Chance, and reroll flexibility.
- Color highlights show which plan owns each advantage; split tradeoffs are labeled honestly.
- Roll 1 evidence follows both remaining rerolls through Roll 3. Roll 2 evidence follows the final reroll.
- A short “why it wins” summary connects the statistics to the exact full-game result.
- Deeper derivations remain collapsed under “See the math.”
- Practice, Daily Review, friend reviews, Daily Spotlight, and What If use the same card.
- In the Daily Ten, the existing question expander opens the complete card directly—there is no second coaching click.

## Reported example

For `1,1,4,5,6` on Roll 1 with Chance scored 13, keep 5 remains exact best. Keep `1,1` remains #8 of 24 and 0.77 Points Lost.

The card credits the pair’s stronger three-Ones benchmark (66.5% versus 35.8% for three Fives), then shows why the 5 still wins: through Roll 3 it produces stronger Small/Large Straight routes (39.4% / 14.6% versus 26.9% / 6.0%), approximately 4.50 more expected straight points, and one extra fresh die. The summary explains that the upper shortfall is recoverable while the lower-section opportunity is larger.

## Unchanged

Exact policy, best holds, Points Lost, grades, Daily puzzles and challenge IDs, scoring, dice controls, persistence, auto-login, Supabase behavior, social results, avatars, medal ceremony, and medal calculations.

## Verification

66/66 automated suites pass. New coverage verifies the reported probabilities and values, 840 varied nonoptimal decisions, 840 correct decisions, one-to-five-row evidence selection, the existing one-click Daily review flow, and real Streamlit interactions. The exhaustive 3,669,120-hold policy audit remains green.

No Supabase migration is required.
