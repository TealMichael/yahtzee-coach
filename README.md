# Yahtzee Coach v43B Phase 2K.13.3 — Wife-Approved Optimal Coaching

This release extends comparative coaching to correct answers and adds deeper Roll 1 endgame-straight explanations without changing the model or UI.

## Coaching behavior
- Correct answers compare against the alternative a player is most likely to wonder about.
- Two-pair Full House decisions compare keeping both pairs with the winning hold.
- Made Full Houses explain the exact bank-versus-break tradeoff.
- Roll 1 endgames can compare straight completion odds across both remaining rerolls, not only the next roll.
- Compares the player's plan with the exact model's plan instead of merely declaring the winner.
- Uses exact, relevant one-reroll probabilities when they make the tradeoff understandable.
- Connects the choice to the actual open scorecard and upper-bonus state.
- Preserves stronger situation-specific coaching for made hands, Joker rules, dead bonuses, endgames, and other established families.
- Honestly identifies microscopic full-game distinctions when no simple visible statistic explains the edge.
- Treats 0.10 Points Lost or less as a practical tie while still reporting the exact answer.

## Unchanged
Exact strategy, best holds, Points Lost, grading, puzzle selection, Daily/Practice flow, controls, visual layout, auto-login, Supabase behavior, avatars, medals, and protected data artifacts.

## Verification
60/60 automated suites pass. The audits cover 840 correct decisions and 840 varied nonoptimal decisions, and the exhaustive exact-policy audit still covers all 3,669,120 legal hold values.

No Supabase migration is required.
