from pathlib import Path

ROOT = Path(__file__).parent


def section(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b]


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    render_scorecard = section(app, "def render_scorecard(scorecard):", "def install_dice_scroll_guard")
    daily = section(app, "def render_daily_question():", "def render_daily_submission_review")
    daily_choice = section(app, "@st.fragment\ndef _daily_choice_fragment", "def render_daily_question")
    practice = section(app, "def render_practice_mode", "def render_help_feedback")

    checks = [
        ("release is Phase 2K.8", 'APP_RELEASE = "v43B Phase 2K.8"' in app),
        ("full scorecard remains always visible", "st.expander" not in render_scorecard),
        ("duplicate open-category chips are removed from live scorecard", "open_chips_html" not in render_scorecard),
        ("scorecard shows actual upper subtotal against 63", "Upper: {upper_total} / 63" in render_scorecard),
        ("upper scorecard remains 3 columns on phones", ".score-grid { grid-template-columns:repeat(3" in app),
        ("lower scorecard remains 4 columns on phones", app.count(".score-grid.lower { grid-template-columns:repeat(4") >= 2),
        ("compact upper labels restored", all(f'"{k}": "{v}"' in app for k, v in [("ones","1s"),("twos","2s"),("sixes","6s")])),
        ("original short lower labels restored for readability", "CATEGORY_SCORECARD = dict(CATEGORY_SHORT)" in app and all(f'"{k}": "{v}"' in app for k, v in [("three_of_a_kind","3K"),("full_house","FH"),("small_straight","SS"),("large_straight","LS")])),
        ("roll banner is compact single-row flex", "padding:0.38rem 0.58rem" in app and ".daily-roll-stage-sub { display:none; }" in app),
        ("Daily shows roll before scorecard", daily.index("daily-roll-stage") < daily.index('render_scorecard(challenge["scorecard"])')),
        ("Daily decision prompt is one compact line", "Which dice would you keep? <span class='muted'>Tap to select.</span>" in daily_choice and "Your choice saves when you move forward" not in daily_choice),
        ("Practice decision prompt is one compact line", "Which dice would you keep? <span class='muted'>Tap to select.</span>" in practice and "Leave all five unselected" not in practice),
        ("full category names are still retained for coaching", '"three_of_a_kind": "Three of a Kind"' in app and '"large_straight": "Large Straight"' in app),
        ("exact math hardening remains active", "EXPECTED_EXACT_POLICY_SHA256" in (ROOT / "exact_mode.py").read_text(encoding="utf-8")),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
