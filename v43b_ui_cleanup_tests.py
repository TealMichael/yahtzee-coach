from __future__ import annotations

"""Focused v43B Phase 2J player-facing UI hierarchy checks."""

from pathlib import Path

ROOT = Path(__file__).parent


def _block(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    identity = _block(app, "def render_player_identity_gate():", "def render_player_status_bar():")
    intro = _block(app, "def render_daily_intro():", "def _daily_answer_at")
    results = _block(app, "def render_daily_results():", "def render_daily_mode():")
    share = _block(app, "def render_daily_share_result(", "def _daily_review_item")

    standings_pos = results.index('st.markdown("### 🏆 Daily Standings")')
    insights_pos = results.index('st.markdown("### 🎯 Group Insights")')
    review_pos = results.index('st.markdown("### 📝 Your 10 Grades")')
    share_pos = results.index('with st.expander("📤 Share today\'s result"')
    peek_pos = results.index("_render_friend_pick_peek(active_group, board)")
    manage_pos = results.index("render_friend_group_hub(")

    checks = [
        ("Returning Player is the first/default identity tab", 'st.tabs(["Returning Player", "Create Player"])' in identity),
        ("identity page removes version/database language", "v43B" not in identity and "Phase 2" not in identity and "database" not in identity and "secure hash" not in identity),
        ("identity page keeps simple private-PIN reassurance", "Your PIN is private." in identity),
        ("signed-in status is compact", 'st.caption(f"👤 **{name}**")' in app and "permanent v43B player" not in app),
        ("Daily intro removes prototype/version badges", "prototype-badge" not in intro and "v43B" not in intro and "official attempt" not in intro),
        ("completed hero removes saved/progress implementation chatter", "Challenge ID" not in results and "10/10 submitted" not in results and "100% saved" not in results),
        ("completed social hierarchy is standings then insights then own grades", standings_pos < insights_pos < review_pos),
        ("share sits with the result while friend peek stays below own grades", share_pos < standings_pos < insights_pos < review_pos < peek_pos < manage_pos),
        ("Your 10 Grades is above Invite & manage friends", review_pos < manage_pos and "👥 Invite & manage friends" in app),
        ("share card is compact by default", "Preview shared result" in share and "white-space:normal" not in share),
        ("completed lock copy is human-facing", "Today's Daily is complete. Come back tomorrow for a new set." in results),
        ("group leaderboard removes internal real-v43B wording", "Real v43B results" not in results and "official attempts" not in results),
        ("group insights use friendlier labels", "😈 Today's Killer" in results and "🎯 Everyone Nailed It" in results),
        ("main mode note is player-facing", "Today's 10-puzzle Daily Challenge" in app and "Daily Challenge first ·" not in app),
        ("native page icon is configured at startup", 'page_icon=APP_ICON_PATH' in app and 'APP_ICON_PATH = "apple_touch_icon.png"' in app),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
