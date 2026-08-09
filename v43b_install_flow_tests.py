from __future__ import annotations

"""Focused v43B Phase 2H install-flow regression checks."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    checks = [
        ("install button opens visible instructions fallback", "showSteps(stepHtml(platform()))" in app and "ycInstallSteps" in app),
        ("iPhone fallback names Share and Add to Home Screen", "Share" in app and "Add to Home Screen" in app and "Open as Web App" in app),
        ("desktop Chrome fallback names current install menu", "Cast, save, and share" in app and "Install page as app" in app),
        ("Mac Safari fallback names Add to Dock", "File → Add to Dock" in app),
        ("direct browser prompt still supported when available", "beforeinstallprompt" in app and "promptEvent.prompt()" in app),
        ("direct prompt rejection falls back to instructions", "result.outcome === 'accepted'" in app and "showSteps(stepHtml(platform()))" in app),
        ("installed-mode detection remains", "display-mode: standalone" in app and "Already added" in app),
        ("custom mascot icon remains in install card", "Use the new mascot icon" in app and "home_icon_192.png" in app),
        ("copy app link remains", "Copy app link" in app and "navigator.clipboard" in app),
        ("install UI no longer implies no-op fallback", "Tap the green button for the exact steps for this device." in app and "Install steps opened below." in app),
    ]
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
