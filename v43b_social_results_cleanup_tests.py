from pathlib import Path

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def section(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b]


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    results = section(app, "def render_daily_results():", "def render_daily_mode():")
    leaderboard = section(app, "def render_leaderboard_cards", "def _share_square")
    peek = section(app, "def _render_friend_pick_peek", "def render_daily_results():")

    standings = results.index('st.markdown("### 🏆 Daily Standings")')
    insights = results.index('st.markdown("### 🎯 Group Insights")')
    grades = results.index('st.markdown("### 📝 Your 10 Grades")')
    share = results.index("Share today's result")
    friend_peek = results.index("_render_friend_pick_peek(active_group, board)")
    manage = results.index("render_friend_group_hub(")

    checks = [
        ('APP_RELEASE = "v43B Phase 2K.8.2"' in app, "release advances to Phase 2K.8.2"),
        (share < standings < insights < grades < friend_peek < manage, "share sits with the personal result before the calm social-results hierarchy"),
        ("on_click=_open_friend_review" not in leaderboard and "st.columns" not in leaderboard, "standings are no longer built from clickable name buttons or squeezed columns"),
        ("leaderboard-list" in leaderboard and "leaderboard-row" in leaderboard, "standings use uniform full-width leaderboard rows"),
        ("Lowest Points Lost wins." in leaderboard, "standings keep only the essential ranking explanation"),
        ("You made different" not in app and "friend-question-grid" not in peek, "side-by-side comparison analytics and tiny friend grid are gone"),
        ("for answer in answers:" in results and "_daily_review_item(answer)" in results, "player's own ten grades return as compact expandable rows"),
        ('label = f"Q{number} · {grade} · {loss:.2f} lost"' in app, "own grade labels are short and scan-friendly"),
        ("👀 Peek at a friend's picks" in peek and "No comparison dashboard" in peek, "friend feature is explicitly a simple optional peek"),
        ("See {selected_name}'s 10 picks" in peek, "friend choices load only after a specific button press"),
        ("Kept <b>{html.escape(kept)}</b>" in peek and 'payload.get("answers", [])' in peek, "friend peek lists the actual picks across all ten questions"),
        ("friend-pick-list" in peek and "✅ Best" in peek and "{loss:.2f} lost" in peek, "friend peek shows simple outcome rows instead of another coaching dashboard"),
        ("_render_daily_review_body" not in peek and "with st.expander(label" not in peek, "friend peek avoids nested detail panels and stays lightweight"),
        ("Finish your own Daily before reviewing a friend's choices." in (ROOT / "daily_store.py").read_text(), "spoiler protection still requires the viewer to finish first"),
        ("That player has not finished this Daily yet." in (ROOT / "daily_store.py").read_text(), "unfinished friends remain private"),
        ("render_leaderboard_cards(board, allow_review=False)" in app, "yesterday's final standings retain the clean shared leaderboard renderer"),
    ]
    for ok, message in checks:
        require(ok, message)
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
