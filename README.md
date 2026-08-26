# Yahtzee Coach v43B Phase 2K.13.2 — General Comparative Coaching

This release improves coaching throughout Daily and Practice without changing the model or the experience around it.

## Coaching behavior
- Compares the player's plan with the exact model's plan instead of merely declaring the winner.
- Uses exact, relevant one-reroll probabilities when they make the tradeoff understandable.
- Connects the choice to the actual open scorecard and upper-bonus state.
- Preserves stronger situation-specific coaching for made hands, Joker rules, dead bonuses, endgames, and other established families.
- Honestly identifies microscopic full-game distinctions when no simple visible statistic explains the edge.
- Treats 0.10 Points Lost or less as a practical tie while still reporting the exact answer.

## Unchanged
Exact strategy, best holds, Points Lost, grading, puzzle selection, Daily/Practice flow, controls, visual layout, auto-login, Supabase behavior, avatars, medals, and protected data artifacts.

## Verification
59/59 automated suites pass. The coaching audit covers 840 varied positions across 19 families, and the exhaustive exact-policy audit still covers all 3,669,120 legal hold values.

No Supabase migration is required.
