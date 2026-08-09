from __future__ import annotations

"""Focused v43B Phase 2G spoiler-free Daily sharing checks."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")

    checks = [
        ("share square helper exists", "def _share_square(" in app),
        ("share uses four spoiler-free result colors", 'return "🟩"' in app and 'return "🟨"' in app and 'return "🟧"' in app and 'return "🟥"' in app),
        ("share text reports EV lost and exact count", "EV lost ·" in app and "/10 exact" in app),
        ("share text uses two rows of five", 'first_row = "".join(squares[:5])' in app and 'second_row = "".join(squares[5:10])' in app),
        ("share text includes best exact streak", "Best exact streak" in app),
        ("share text can include current group rank", "Group rank right now" in app),
        ("share text includes app link", "PUBLIC_APP_URL" in app and 'lines.extend([' in app),
        ("result screen renders share card only after completion", "render_daily_share_result(records, summary" in app and "def render_daily_results():" in app),
        ("native share button exists", "📤 Share result" in app and "nav.share" in app),
        ("copy score fallback exists", "📋 Copy score" in app and "clipboard.writeText(shareText)" in app),
        ("share card explicitly says spoiler-free", "Spoiler-free result" in app),
        ("share text does not expose holds", "build_daily_share_text" in app and "Your hold" not in app[app.index("def build_daily_share_text"):app.index("def render_daily_share_result")]),
        ("share text does not expose exact best", "Exact best" not in app[app.index("def build_daily_share_text"):app.index("def render_daily_share_result")]),
        ("share text does not expose scenario names", "scenario_name" not in app[app.index("def build_daily_share_text"):app.index("def render_daily_share_result")]),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
