# Yahtzee Coach - Game UI v18

Roll 1 / Roll 2 Yahtzee hold-strategy trainer.

## v18 expanded titled practice deck

This update keeps the app UI exactly as-is and expands the practice generator.

What changed:

- Titled spicy deck is now the full practice source: `SPICY_PRACTICE_RATE = 1.00`
- Expanded from 7 titled sections to 10 titled sections
- Each section now has 10 unique dice rolls
- Each section now has 10 scorecard templates
- Added more whole-scorecard states, including upper-pressure, Chance-pressure, endgame, Four-of-a-Kind, and extra-Yahtzee/Joker-style situations
- Strategy engine remains v16/v17 logic
- App UI/dice layout unchanged

## Titled sections

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
Total: 17 PASS / 0 FAIL
```

The tests check:

- Verhoeff-inspired Roll 2 straight correction
- Upper-section chase decisions
- Full House/two-pair behavior
- Triple protection
- Low-pair avoidance
- Extra-Yahtzee / Joker awareness guardrail
- Coach report generation smoke tests
- Scope guard that keeps the app Roll 1 / Roll 2 only
- Expanded practice deck shape: 10 sections, 10 dice rolls each, 10 scorecards each

## Files

Upload these five files to Streamlit/GitHub:

- `app.py`
- `yahtzee_engine.py`
- `strategy_tests.py`
- `requirements.txt`
- `README.md`

Do not upload `__pycache__`.
