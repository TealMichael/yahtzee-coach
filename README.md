# Yahtzee Coach – Game UI v7

Hold Strategy Trainer focused on Roll 1 and Roll 2 dice-hold decisions.

## v7 changes

- Removed the unnecessary Session details bar.
- Replaced the Streamlit pills dice picker with five true dice buttons.
- Duplicate dice are now selected by position, so every matching die works independently.
- Dice are larger and easier to tap.
- Held dice still turn red.
- The scorecard stays above dice selection.
- Next Round scrolls to the very top of the page.
- Fast smoke tests still pass: 9/9.

## Files

- `app.py` – Streamlit interface
- `yahtzee_engine.py` – strategy engine and reports
- `requirements.txt` – app dependencies

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
