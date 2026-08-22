from pathlib import Path

APP = Path(__file__).with_name("app.py").read_text()

checks = [
    ("practice progress imported", "from practice_progress import build_practice_progress, newly_unlocked_badges" in APP),
    ("four-part progress rail", "progress-kicker'>Streak" in APP and "progress-kicker'>Avg loss" in APP),
    ("badge unlock renderer", "def render_new_badges():" in APP and "Achievement unlocked" in APP),
    ("mastery renderer", "def render_practice_momentum(records):" in APP and "Strategy mastery" in APP),
    ("new badge delta on submit", "newly_unlocked_badges(" in APP and "before_solver_history" in APP),
    ("new badges reset each round", "st.session_state.new_badges = []" in APP),
    ("mobile progress becomes two by two", ".progress-rail { grid-template-columns:repeat(2, minmax(0,1fr));" in APP),
    ("mobile mastery polish", ".mastery-card { padding:0.64rem 0.66rem;" in APP),
    ("visible hold rank preserved", "🏆 Hold rank:" in APP and "class='rank-chip'" in APP),
    ("independent dice buttons preserved", "_render_independent_dice_picker(" in APP and "toggle_die_index(" in APP),
    ("duplicate dice protection preserved", 'key=f"{key_prefix}_die_{die_index}"' in APP),
    ("scroll guard preserved", "install_dice_scroll_guard()" in APP),
]

failed = []
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
    if not ok:
        failed.append(name)
if failed:
    raise SystemExit(f"{len(failed)} v42 UI checks failed: {', '.join(failed)}")
print(f"\n{len(checks)} PASS / 0 FAIL")
