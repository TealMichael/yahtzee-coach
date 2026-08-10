from __future__ import annotations

"""Regression checks for the Phase 2K.1.1 Streamlit navigation hotfix."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")

    checks = [
        ("safe app-mode callback exists", 'def _set_app_mode(mode: str):' in app),
        ("unsigned Practice uses callback", 'key="identity_to_practice"' in app and 'on_click=_set_app_mode' in app),
        ("Daily intro Practice uses callback", '"Open Practice",\n        use_container_width=True,\n        on_click=_set_app_mode' in app),
        ("completed Daily Practice uses callback", 'key="daily_to_practice"' in app and 'args=("Practice",)' in app),
        ("Practice leaderboard return uses callback", 'key="practice_to_daily_results"' in app and 'args=("Daily Challenge",)' in app),
        ("unsigned Practice no longer mutates widget state inline", 'if st.button("Open Practice without signing in"' not in app),
        ("completed Daily no longer mutates widget state inline", 'st.session_state.app_mode = "Practice"\n        st.rerun()' not in app),
        ("Roll clarity remains intact", 'ROLL 1 · First roll' in app and '2 rerolls remaining' in app and 'ROLL 2 · Second roll' in app and '1 reroll remaining' in app),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
