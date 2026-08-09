from __future__ import annotations

"""Focused v43B Phase 2I install/navigation regression checks."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    checks = [
        ("Home Screen is a third main navigation choice", 'options=["Daily Challenge", "Practice", "📲 Add to Home Screen"]' in app),
        ("Daily remains first/default mode", 'st.session_state.app_mode = "Daily Challenge"' in app),
        ("install content is no longer injected on Daily/Practice home", 'render_install_app_control()' not in app),
        ("install mode uses native Streamlit UI", 'def render_install_mode(' in app and 'st.tabs(["🍎 iPhone / iPad", "🤖 Android", "💻 Computer"])' in app),
        ("custom mascot icon is visible in install mode", 'st.image(str(APP_ICON_512_PATH)' in app),
        ("iPhone instructions name required Safari path", 'Tap the **Share** button' in app and '**Add to Home Screen**' in app and '**Open as Web App**' in app),
        ("Android instructions are present", '**Add to Home screen** or **Install app**' in app),
        ("desktop Chrome path is present", 'Cast, save, and share → Install page as app' in app),
        ("Mac Safari path is present", 'File → Add to Dock' in app),
        ("no fake install action button remains", 'Show install steps' not in app and 'Install app now' not in app),
    ]
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
