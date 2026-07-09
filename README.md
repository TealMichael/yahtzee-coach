# Yahtzee Coach - Game UI v21

Roll 1 / Roll 2 Yahtzee hold-strategy trainer.

## v21 playtest strategy + deck-variety patch

This update keeps the app UI, dice size, dice layout, scorecard layout, and report layout unchanged. It only patches collected v21 playtest strategy issues and adds session-level variety control for the titled practice deck.

What changed:

- Fixed Roll 2 four-of-a-kind cases so keeping all four matching dice does not lose to keeping only three
- Generalized the Upper Bonus Pressure pair-of-5s correction beyond the exact v20 scorecard
- Fixed the Chance Crossroads high-pair issue so a clean pair of 6s can beat attaching an extra 5 just for Chance fallback
- Preserved the older Full House two-pair rule so `[4, 4, 5, 5]` still wins when Full House is open
- Verified the low-triple case `[2, 2, 2, 5, 6]`; the engine can still prefer `[5, 6]` on that specific cramped card, so this was added as a verification case rather than blindly patched
- Added practice anti-repetition hooks so the app avoids repeating the same titled section or exact setup too soon
- Kept the v19 Roll 1 speed patch
- Kept the v18 expanded titled practice deck
- Kept the v16/v20 strategy corrections

## Titled sections

The expanded titled deck is still active:

1. Small Straight Spark
2. Large Straight Temptation
3. Full House Puzzle
4. Yahtzee Fever
5. Upper Bonus Pressure
6. Chance Crossroads
7. Four-of-a-Kind Forge
8. Joker Doorway
9. Endgame Weirdness
10. Open Board Fun

Each titled section has:

- 10 unique dice rolls
- 10 scorecard templates
- Roll 1 / Roll 2 weighting depending on the scenario

The app now tracks recent practice rounds during a session and tries to avoid showing the same title or exact setup too soon.

## How to run the tests

From the repo folder, run:

```bash
python strategy_tests.py
```

Expected result for this version:

```text
Total: 26 PASS / 0 FAIL
```

The tests check:

- Verhoeff-inspired Roll 2 straight correction
- Upper-section chase decisions
- v21 four-of-a-kind dominance cases
- v21 generalized Upper Bonus Pressure pair-of-5s cases
- v21 Chance Crossroads clean pair-of-6s case
- Low-triple verification case
- Full House/two-pair behavior
- Triple protection
- Low-pair avoidance
- Extra-Yahtzee / Joker awareness guardrail
- Coach report generation smoke tests
- Scope guard that keeps the app Roll 1 / Roll 2 only
- Expanded practice deck shape: 10 sections, 10 dice rolls each, 10 scorecards each
- Roll 1 speed guard for the formerly slow report path

## Files

Upload these five files to Streamlit/GitHub:

- `app.py`
- `yahtzee_engine.py`
- `strategy_tests.py`
- `requirements.txt`
- `README.md`

Do not upload `__pycache__`.
