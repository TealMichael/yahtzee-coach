# Yahtzee Coach - Game UI v17

Roll 1 / Roll 2 Yahtzee hold-strategy trainer.

## v17 testing-file update

The app/UI and strategy engine are unchanged from v16. This update adds a dedicated testing file:

- `strategy_tests.py`

This file gives us a stable regression checklist before future strategy changes. It tests:

- Verhoeff-inspired Roll 2 straight correction
- Upper-section chase decisions
- Full House/two-pair behavior
- Triple protection
- Low-pair avoidance
- Extra-Yahtzee / Joker awareness guardrail
- Coach report generation smoke tests
- Scope guard that keeps the app Roll 1 / Roll 2 only

## How to run the tests

From the repo folder, run:

```bash
python strategy_tests.py
```

Expected result for this version:

```text
Total: 16 PASS / 0 FAIL
```

## Files

Upload these five files to Streamlit/GitHub:

- `app.py`
- `yahtzee_engine.py`
- `strategy_tests.py`
- `requirements.txt`
- `README.md`

Do not upload `__pycache__`.
