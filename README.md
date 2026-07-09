# Yahtzee Coach — Game UI v5

A Streamlit web app for practicing Yahtzee Roll 1 and Roll 2 hold decisions.

## v5 changes

- Fixed duplicate dice tapping bug: duplicate values like multiple 4s can now be selected separately.
- Dice picker now uses one compact row of tappable dice instead of giant stacked buttons.
- Dice look like dice again, with selected/held dice intended to show in red.
- Removed clunky oversized gray section bars and replaced them with lighter section labels/cards.
- Current scorecard remains above the dice selection.

## Files

- `app.py` — Streamlit app interface
- `yahtzee_engine.py` — strategy engine and practice generator
- `requirements.txt` — dependencies
- `README.md` — this file

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
