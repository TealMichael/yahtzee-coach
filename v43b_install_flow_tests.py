from __future__ import annotations

"""Regression checks for the Phase 2K.11.3 retirement of the install-mode UI."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    checks = [
        ("Home exposes Daily and Weekly challenge tiles", '_home_tile("Daily Challenge"' in app and '_home_tile("Weekly Challenge"' in app),
        ("Home is default and original Daily gameplay remains", 'st.session_state.app_mode = "Home"' in app and 'elif mode == "Daily Challenge"' in app),
        ("legacy Add-to-Home-Screen navigation is removed", '📲 Add to Home Screen' not in app),
        ("legacy install page renderer is removed", 'def render_install_mode(' not in app),
        ("legacy install metadata injection is removed", 'def install_app_shell_metadata(' not in app and 'apple-mobile-web-app-title' not in app),
        ("legacy browser modes safely fall back to Home", 'st.session_state.app_mode not in {"Home", "Daily Challenge", "Weekly", "Practice", "My Player"}' in app),
        ("public app URL remains for invites/sharing", 'PUBLIC_APP_URL = "https://teals-yahtzee-coach.streamlit.app/"' in app),
    ]
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
