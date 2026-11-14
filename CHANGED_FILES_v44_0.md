# v44.0 changes

This is the final browser-upload release based on v43B Phase 2K.14.14.
See INSTALL_v44_0.md before uploading. Browser and phone-width checks passed.
Final verification also fixed an interrupted Daily start and corrected the intro roll counts.

## Application files

| File | Change |
|---|---|
| app.py | Weekly navigation and login integration; count-aware Daily flow and awards; fix My Player sign-out callback; preserve Daily start intent across background reruns |
| weekly_game.py | New 13-round rules and private deterministic dice schedule |
| weekly_store.py | New actor-scoped transactional persistence and privacy boundary |
| weekly_ui.py | New Weekly play, resume, review, standings and replay screens |
| daily_challenge.py | Separate six-puzzle version, count-aware cache and persisted identity resolution |
| puzzle_bank.py | New balanced six-puzzle plan; legacy ten-puzzle selection preserved |
| daily_store.py | Reference persistence supports both lengths |
| supabase_daily_store.py | Persisted format lookup and count-aware completion/review; answer saves retain one-write path |
| daily_spotlight.py | Post-completion spotlight accepts valid six- or ten-puzzle results |
| retro_podium.py | Yesterday's ceremony labels Perfect Six and Perfect Ten correctly |

## Database files

- RUN_THIS_ONCE_IN_SUPABASE_v44_0.sql — complete installation file, combining the two below.
- v43b_weekly_v1_migration.sql — private Weekly tables, RPC, permissions and transaction guards.
- v43b_daily_six_v1_migration.sql — persistent midnight activation, format and completion guards.

Run only the combined file for the upgrade; the component files are retained for review.

## Documentation and test files

The browser folder includes the new behavioral tests, local fixtures, browser
checker, development-only dependency list, and all updated existing test files.
Existing source/hash assertions were updated only for the approved format,
navigation and release label. The frozen policy and historical-output checks
remain. The 17 inherited failure cases were retained.

## Exact changed/new file list

- `CHANGED_FILES_v44_0.md`
- `DEPLOYMENT_STEPS.txt`
- `GITHUB_COMMIT_MESSAGE.txt`
- `HANDOFF_BUILD_NOTE.txt`
- `INSTALL_v44_0.md`
- `README.md`
- `RUN_THIS_ONCE_IN_SUPABASE_v44_0.sql`
- `VALIDATION_v44_0.md`
- `app.py`
- `daily_challenge.py`
- `daily_six_postgres_tests.py`
- `daily_six_tests.py`
- `daily_six_ui_tests.py`
- `daily_spotlight.py`
- `daily_store.py`
- `puzzle_bank.py`
- `qa_daily_app.py`
- `qa_weekly_app.py`
- `requirements-dev.txt`
- `retro_podium.py`
- `supabase_daily_store.py`
- `v43a_integration_tests.py`
- `v43b_beta_readiness_tests.py`
- `v43b_coaching_semantic_hotfix_tests.py`
- `v43b_compact_decision_layout_tests.py`
- `v43b_daily_six_v1_migration.sql`
- `v43b_deployment_safety_hotfix_tests.py`
- `v43b_homescreen_icon_tests.py`
- `v43b_install_flow_tests.py`
- `v43b_login_autofill_hotfix_tests.py`
- `v43b_math_hardening_tests.py`
- `v43b_performance_clarity_tests.py`
- `v43b_phase2k10_retro_podium_tests.py`
- `v43b_phase2k11_1_preview_alignment_tests.py`
- `v43b_phase2k11_2_predeploy_avatar_tests.py`
- `v43b_phase2k11_3_ui_polish_tests.py`
- `v43b_phase2k11_avatar_medal_moment_tests.py`
- `v43b_phase2k12_1_mobile_creator_readability_tests.py`
- `v43b_phase2k12_2_duplicate_dice_input_tests.py`
- `v43b_phase2k12_3_mobile_dice_layout_tests.py`
- `v43b_phase2k12_4_restore_dice_visual_tests.py`
- `v43b_phase2k13_1_autologin_fastpath_tests.py`
- `v43b_phase2k13_3_optimal_choice_coaching_tests.py`
- `v43b_phase2k13_4_medal_names_math_tests.py`
- `v43b_phase2k13_performance_only_tests.py`
- `v43b_phase2k14_11_perfect_ten_tests.py`
- `v43b_phase2k14_1_winner_first_clarity_tests.py`
- `v43b_phase2k14_2_turn_aware_comparison_cards_tests.py`
- `v43b_phase2k14_3_full_hold_rankings_tests.py`
- `v43b_phase2k14_4_daily_balance_tests.py`
- `v43b_phase2k14_daily_spotlight_tests.py`
- `v43b_phase2k9_1_tie_ranking_tests.py`
- `v43b_remember_login_reliability_tests.py`
- `v43b_roll_clarity_tests.py`
- `v43b_scorecard_friend_review_tests.py`
- `v43b_share_results_tests.py`
- `v43b_ui_cleanup_tests.py`
- `v43b_usability_tests.py`
- `v43b_weekly_v1_migration.sql`
- `v43b_yesterday_podium_tests.py`
- `weekly_auth_tests.py`
- `weekly_browser_check.py`
- `weekly_game.py`
- `weekly_game_tests.py`
- `weekly_postgres_tests.py`
- `weekly_store.py`
- `weekly_ui.py`
- `weekly_ui_tests.py`
