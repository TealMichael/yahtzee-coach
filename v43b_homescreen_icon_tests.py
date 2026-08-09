from __future__ import annotations

"""Focused v43B Phase 2F install/icon checks."""

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
        ("app loads compact icon paths", 'APP_ICON_192_PATH' in app and 'APP_ICON_512_PATH' in app and 'APPLE_TOUCH_ICON_PATH' in app),
        ("app injects home-screen metadata", 'def install_app_shell_metadata(' in app and 'apple-mobile-web-app-title' in app and 'application/manifest+json' in app),
        ("install card uses custom mascot icon", 'Use the new mascot icon' in app and 'home_icon_192.png' in app),
        ("install card handles installed mode", 'Already added' in app and 'display-mode: standalone' in app),
        ("install card supports browser install prompt when offered", 'beforeinstallprompt' in app and 'Install app now' in app),
        ("install card keeps iPhone manual path honest", 'Add to Home Screen' in app and 'Open as Web App' in app),
        ("install card can copy app link", 'Copy app link' in app and 'text it to yourself or a friend' in app),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
