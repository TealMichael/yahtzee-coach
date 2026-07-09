# Yahtzee Coach

A Streamlit web app for practicing Yahtzee Roll 1 and Roll 2 hold decisions.

## Files

- `app.py` — Streamlit interface
- `yahtzee_engine.py` — strategy engine, practice generator, and coach reports
- `requirements.txt` — Python packages needed by Streamlit Cloud

## Deploy on Streamlit Community Cloud

1. Upload these files to the root of your GitHub repository.
2. In Streamlit Community Cloud, create or manage your app.
3. Choose this repository.
4. Set the main file path to `app.py`.
5. Deploy or reboot.

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Current scope

This app teaches dice-hold strategy only:

- Roll 1 hold decisions
- Roll 2 hold decisions
- No Roll 3 scoring mode
- No full-game simulator

## Game UI v3

- Dice are selected by tapping dice buttons instead of using a long list or checkboxes.
- The scorecard is organized into compact Upper and Lower sections.
- The top of the app only shows the important session stats: rounds and average grade.
- Coach feedback is shorter and more game-like.
- Full detailed report is still available in an expander.
