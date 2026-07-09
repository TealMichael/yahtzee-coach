# Yahtzee Coach - Game UI v16

Roll 1 / Roll 2 Yahtzee hold-strategy trainer.

## v16 strategy patch

The UI is intentionally unchanged from the working version. This update tightens the strategy engine only:

- Adds a Verhoeff-inspired early-game straight flexibility correction.
- Fixes the article-style Roll 2 case `[1,1,3,4,6]` so the coach prefers `[3,4]` instead of over-keeping `[3,4,6]`.
- Makes upper-section bonus valuation more asymmetric, so Fours/Fives/Sixes shortfalls matter more than Ones/Twos shortfalls.
- Adds a slightly stronger opportunity-cost penalty for using Chance while the upper bonus is still alive.
- Adds minimum extra-Yahtzee / Joker-rule awareness inside Roll 1 / Roll 2 final-reroll valuation.
- Keeps the proven Roll 1 fast path for app speed.

## Files

Upload these four files to Streamlit/GitHub:

- `app.py`
- `yahtzee_engine.py`
- `requirements.txt`
- `README.md`

Do not upload `__pycache__`.
