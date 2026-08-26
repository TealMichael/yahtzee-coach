# Yahtzee Coach v43B Phase 2K.13.4 — Podium Names + Detailed Math Hotfix

This small hotfix adds yesterday's medalist names to the ceremony and optional detailed calculations for supported Roll 1 endgame-straight decisions.

## Coaching behavior
- Daily exposes the extra calculation under a collapsed "See the math" control; Practice includes it inside Strategy details.
- The calculation includes next-roll outcome counts, both-reroll probabilities, expected straight value, the full-game margin, and upper-bonus feasibility.
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
Exact strategy, best holds, Points Lost, grading, puzzle selection, Daily/Practice flow, dice controls, auto-login, Supabase behavior, avatar designs, medal-award calculations, and protected data artifacts.

## Verification
61/61 automated suites pass. Medal-name/tie behavior and detailed math have dedicated regressions, and the exhaustive exact-policy audit still covers all 3,669,120 legal hold values.

## Ceremony behavior
- Yesterday's gold, silver, and bronze names appear beneath their medals.
- Competition-ranking ties remain accurate and long names truncate safely.

No Supabase migration is required.
