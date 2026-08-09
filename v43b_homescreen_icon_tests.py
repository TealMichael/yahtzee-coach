from __future__ import annotations

"""Focused v43B Phase 2J Home Screen icon/metadata checks."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    icon192 = ROOT / "home_icon_192.png"
    icon512 = ROOT / "home_icon_512.png"
    apple = ROOT / "apple_touch_icon.png"

    checks = [
        ("install icon files exist", icon192.exists() and icon512.exists() and apple.exists()),
        ("install icon files are non-trivial", icon192.stat().st_size > 10000 and icon512.stat().st_size > 10000 and apple.stat().st_size > 10000),
        ("app uses native Streamlit page icon path", 'page_icon=APP_ICON_PATH' in app and 'APP_ICON_PATH = "apple_touch_icon.png"' in app),
        ("app injects real public home-screen icon URLs", 'def install_app_shell_metadata(' in app and 'apple-mobile-web-app-title' in app and 'raw.githubusercontent.com/TealMichael/yahtzee-coach/main/' in app and 'apple_touch_icon.png' in app),
        ("metadata injection uses top-level st.html instead of iframe", 'st.html(html_block, unsafe_allow_javascript=True)' in app),
        ("install mode displays custom mascot icon", 'st.image(str(APP_ICON_512_PATH)' in app),
        ("install mode keeps iPhone manual path honest", 'Add to Home Screen' in app and 'Open as Web App' in app and 'cannot press Add to Home Screen automatically' in app),
        ("install mode is intentionally secondary navigation", 'options=["Daily Challenge", "Practice", "📲 Add to Home Screen"]' in app),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
