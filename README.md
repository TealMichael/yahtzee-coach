# Yahtzee Coach

A Streamlit web app for practicing Yahtzee Roll 1 and Roll 2 hold decisions.

## Files

- `app.py` — Streamlit interface
- `yahtzee_engine.py` — strategy engine, practice generator, and coach reports
- `requirements.txt` — Python packages needed by Streamlit Cloud

## Deploy on Streamlit Community Cloud

1. Upload these files to the root of your GitHub repository.
2. In Streamlit Community Cloud, create a new app.
3. Choose your repository.
4. Set the main file path to `app.py`.
5. Deploy.

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

## July 8/9 mobile polish

- Dice are selected by clicking individual dice checkboxes instead of choosing from a long list.
- Scorecard is shown in a compact mobile-friendly grid.
- Coach report is summarized in a cleaner grade card.
- Full detailed report is still available in an expander.
- Session now tracks average letter grade.
