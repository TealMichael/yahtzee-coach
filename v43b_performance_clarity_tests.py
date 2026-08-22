from pathlib import Path

ROOT = Path(__file__).parent


def section(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b]


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    store = (ROOT / "supabase_daily_store.py").read_text(encoding="utf-8")
    schema = (ROOT / "v43b_schema.sql").read_text(encoding="utf-8")
    phase2e = (ROOT / "v43b_phase2e_migration.sql").read_text(encoding="utf-8")
    puzzle = (ROOT / "puzzle_bank.py").read_text(encoding="utf-8")

    save = section(store, "    def save_answer(", "    def revise_answer(")
    revise = section(store, "    def revise_answer(", "    def complete_attempt(")
    results = section(app, "def render_daily_results():", "def render_daily_mode():")
    submission = section(app, "def render_daily_submission_review():", "def _leaderboard_frame(")
    score_box = section(app, "def score_box_html", "def score_grid_html")

    checks = [
        ("release is Phase 2K.9.1", 'APP_RELEASE = "v43B Phase 2K.12.2"' in app),
        ("Daily dice controls are fragment-scoped", "@st.fragment\ndef _daily_choice_fragment" in app),
        ("Practice dice controls are fragment-scoped", "@st.fragment\ndef _practice_choice_fragment" in app),
        ("old full-rerun dice guard is no longer installed", app.count("install_dice_scroll_guard()") == 1),
        ("new Daily save has no read-before-write attempt lookup", "_require_attempt_row" not in save and "_answers_for_attempt" not in save),
        ("new Daily save has no redundant challenge read", 'table("daily_challenges")' not in save),
        ("new Daily save is one insert request", '.table("daily_answers").insert(payload).select("*").execute()' in save),
        ("revision has no read-before-write queries", "_require_attempt_row" not in revise and "_answers_for_attempt" not in revise and 'table("daily_challenges")' not in revise),
        ("database insert trigger remains authoritative", "guard_daily_answer_insert" in schema and "Expected Daily question" in schema and "Puzzle ID does not match" in schema),
        ("database update trigger remains authoritative", "guard_daily_answer_update" in phase2e and "Completed Daily answers cannot be changed" in phase2e),
        ("batched group result snapshot exists", "def group_daily_snapshot" in store),
        ("live result UI uses batched group snapshot", "_cached_group_daily_snapshot" in app and 'snapshot.get("question_stats"' in app),
        ("decision scorecard restores original compact labels", "CATEGORY_SCORECARD = dict(CATEGORY_SHORT)" in app and '"three_of_a_kind": "3K"' in app and '"small_straight": "SS"' in app and "CATEGORY_SCORECARD.get" in score_box),
        ("lower scorecard stays four columns on mobile", app.count(".score-grid.lower { grid-template-columns:repeat(4") >= 2),
        ("main Daily metric says Points Lost", "Points Lost" in results and "EV Lost" not in results),
        ("main Daily result says Best Holds", "Best Holds" in results and "Best Streak" in results),
        ("Daily puzzle removes developer-facing no-hint card", "No strategy label or difficulty hint is shown during the official run." not in app),
        ("Daily progress removes redundant percent", "daily-progress-percent" not in app and 'status_text = "Finished" if complete else f"{saved} saved"' in app),
        ("final review uses cards instead of a dataframe", "daily-review-choice" in submission and "st.dataframe" not in submission),
        ("completed review renders compact grade rows with expandable coaching", 'st.markdown("### 📝 Your 10 Grades")' in results and "for answer in answers:" in results and "_daily_review_item(answer)" in results),
        ("leaderboard uses mobile-friendly rows without forced friend review", "render_leaderboard_cards(board, allow_review=False)" in results and "st.dataframe(_leaderboard_frame(board)" not in results),
        ("Practice scenario copy avoids old jargon", all(term not in puzzle for term in ["carrying option value", "escape valve here", "reroll flexibility", "damage-control Yahtzee", "exact destinations"])),
        ("exact solver remains the required official scorer", 'if solver_record.get("source") != "exact"' in app and 'solver_source="exact"' in app),
        ("exact policy file remains unchanged in routing", 'EXACT_POLICY_PATH = Path(__file__).with_name("exact_policy.npz")' in app),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
