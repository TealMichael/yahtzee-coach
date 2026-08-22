from __future__ import annotations

"""Current icon regression after the optional install-mode UI was retired."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    apple = ROOT / "apple_touch_icon.png"
    checks = [
        ("app icon asset still exists", apple.exists() and apple.stat().st_size > 10000),
        ("Streamlit page keeps the custom dice icon", 'page_icon=APP_ICON_PATH' in app and 'APP_ICON_PATH = "apple_touch_icon.png"' in app),
        ("install-only metadata injection is gone", 'install_app_shell_metadata' not in app and 'apple-mobile-web-app-title' not in app),
        ("install-only navigation is gone", 'Add to Home Screen' not in app),
        ("My Player owns the third top-level slot", 'options=["Daily Challenge", "Practice", "My Player"]' in app),
    ]
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
