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

    hero = results.index("daily-result-grid")
    share = results.index("📤 Share today's result")
    standings = results.index("### 🏆 Daily Standings")
    insights = results.index("### 🎯 Group Insights")
    grades = results.index("### 📝 Your 10 Grades")
    peek = results.index("_render_friend_pick_peek(active_group, board)")

    checks = [
        ('APP_RELEASE = "v43B Phase 2K.8.2"' in app, "release advances to Phase 2K.8.2"),
        (results.count("📤 Share today's result") == 1, "share result appears exactly once"),
        (hero < share < standings < insights < grades < peek, "share sits directly with the personal result before social results"),
        ('with st.expander("📤 Share today\'s result", expanded=False):' in results, "existing spoiler-free share stays collapsed until tapped"),
        ('render_daily_share_result(records, summary, rank=rank, completed_count=len(board))' in results, "share uses the existing result payload unchanged"),
        ("No comparison dashboard" in app, "friend-pick simplification remains intact"),
    ]
    for ok, message in checks:
        require(ok, message)
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
