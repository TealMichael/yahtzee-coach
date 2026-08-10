from __future__ import annotations

"""Focused v43B Phase 2K.1 Roll 1 / Roll 2 visibility checks."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")

    checks = [
        ("release label advanced", 'APP_RELEASE = "v43B Phase 2K.2"' in app),
        ("Roll 1 has high-visibility label", '🔵 ROLL 1 · First roll' in app),
        ("Roll 1 states two rerolls remaining", '2 rerolls remaining' in app),
        ("Roll 2 has high-visibility label", '🟢 ROLL 2 · Second roll' in app),
        ("Roll 2 states one reroll remaining", '1 reroll remaining' in app),
        ("Roll 1 and Roll 2 use distinct styles", '.daily-roll-stage.roll-1' in app and '.daily-roll-stage.roll-2' in app),
        ("roll stage is rendered immediately before dice instructions", "render_scorecard(challenge[\"scorecard\"])" in app and "daily-roll-stage" in app and "Tap dice to hold" in app),
        ("old subtle Daily roll line removed from official question card", "f\"<div class='round-line'>Roll {challenge['roll_number']} of 3" not in app),
        ("Daily Back/edit behavior preserved", '"← Back"' in app and 'Save changes & next' in app),
        ("Daily no-feedback competitive protection preserved", 'no coaching is revealed' in app.lower()),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
