from __future__ import annotations

"""Focused v43B Phase 2J spoiler-free Daily sharing checks."""

from pathlib import Path

ROOT = Path(__file__).parent


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    share_start = app.index("def render_daily_share_result")
    share_end = app.index("def _daily_review_item", share_start)
    share_block = app[share_start:share_end]
    text_start = app.index("def build_daily_share_text")
    text_end = share_start
    text_block = app[text_start:text_end]

    checks = [
        ("share square helper exists", "def _share_square(" in app),
        ("share uses four spoiler-free result colors", 'return "🟩"' in app and 'return "🟨"' in app and 'return "🟧"' in app and 'return "🟥"' in app),
        ("share text reports EV lost and exact count", "EV lost ·" in app and "/10 exact" in app),
        ("share text uses two rows of five", 'first_row = "".join(squares[:5])' in app and 'second_row = "".join(squares[5:10])' in app),
        ("share text includes best exact streak", "Best exact streak" in app),
        ("share text can include current group rank", "Group rank right now" in app),
        ("share text includes app link inside the text payload", "PUBLIC_APP_URL" in text_block),
        ("result screen renders share card only after completion", "render_daily_share_result(records, summary" in app and "def render_daily_results():" in app),
        ("native share button exists", "📤 Share result" in share_block and "navigator.share" in share_block),
        ("native share sends one full text payload", 'navigator.share({{text: shareText}})' in share_block),
        ("native share no longer supplies a separate URL field", 'url: appUrl' not in share_block and 'const appUrl' not in share_block),
        ("share runs in top-level Streamlit HTML instead of iframe", 'st.html(share_html, unsafe_allow_javascript=True)' in share_block and 'components.html' not in share_block),
        ("copy score fallback exists", "📋 Copy score" in share_block and "clipboard.writeText(shareText)" in share_block),
        ("copy has legacy fallback for blocked clipboard", "document.execCommand('copy')" in share_block),
        ("share card explicitly says spoiler-free", "Spoiler-free" in share_block),
        ("share text does not expose holds", "Your hold" not in text_block),
        ("share text does not expose exact best", "Exact best" not in text_block),
        ("share text does not expose scenario names", "scenario_name" not in text_block),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
