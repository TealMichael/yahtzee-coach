# Yahtzee Coach - Game UI v20

Roll 1 / Roll 2 Yahtzee hold-strategy trainer.

## v20 Upper Bonus Pressure strategy patch

This update keeps the app UI exactly as-is, keeps the v19 speed patch, and adds one targeted strategy correction for an Upper Bonus Pressure case.

What changed:

- Corrected the Roll 2 case `[1, 4, 5, 5, 6]` with `1s=0, 2s=4, 3s=6` so the best hold is the clean high pair `[5, 5]`
- Reduced overvaluing mostly-Chance fallback holds like `[4, 5, 5, 6]` when the upper bonus is behind pace but still alive
- Added a regression test for this exact case
- Kept Roll 1 report generation much faster
- Replaced repeated raw roll permutations with compressed unique outcome distributions
- Cached final category decisions used inside Roll 1 lookahead
- Cached category scoring for repeated dice states
- Kept the expanded v18 titled practice deck
- Kept the v16 strategy patch, including the Verhoeff-style straight correction
- Dice size, dice layout, scorecard, and report layout are unchanged

## Titled sections

The v18 expanded titled deck is still active:

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

This creates at least 1,000 base titled combinations before roll-number weighting.

## How to run the tests

From the repo folder, run:

```bash
python strategy_tests.py
```

Expected result for this version:

```text
Total: 20 PASS / 0 FAIL
```

The tests check:

- Verhoeff-inspired Roll 2 straight correction
- Upper-section chase decisions, including the Upper Bonus Pressure pair-of-5s correction
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
