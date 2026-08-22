from __future__ import annotations

"""Regression checks for the Phase 2K.11.3 retirement of the install-mode UI."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    checks = [
        ("main navigation is Daily / Practice / My Player", 'options=["Daily Challenge", "Practice", "My Player"]' in app),
        ("Daily remains first/default mode", 'st.session_state.app_mode = "Daily Challenge"' in app),
        ("legacy Add-to-Home-Screen navigation is removed", '📲 Add to Home Screen' not in app),
        ("legacy install page renderer is removed", 'def render_install_mode(' not in app),
        ("legacy install metadata injection is removed", 'def install_app_shell_metadata(' not in app and 'apple-mobile-web-app-title' not in app),
        ("old browser-session install mode safely falls back to Daily", 'st.session_state.app_mode not in {"Daily Challenge", "Practice", "My Player"}' in app),
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
