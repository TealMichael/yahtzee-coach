"""Local-only QA harness: real review/widget functions, synthetic completed Daily.

Run: streamlit run qa_spotlight_app.py
No login, database, public deployment or real-player records are involved.
"""
import ast
import html
from pathlib import Path
import re

import streamlit as st
from exact_mode import ExactPolicyTable, verify_exact_policy_fingerprint
from v43b_phase2k14_daily_spotlight_tests import answer_set

st.set_page_config(page_title="Daily Spotlight QA", layout="centered")
ROOT = Path(__file__).resolve().parent
EXACT_POLICY_PATH = ROOT / "exact_policy.npz"
source = (ROOT / "app.py").read_text()
tree = ast.parse(source)
names = {
    "APP_RELEASE", "DICE_FACE", "CATEGORY_SHORT", "CATEGORY_SCORECARD",
    "UPPER_CATEGORIES", "LOWER_CATEGORIES",
    "load_exact_policy", "_normalize_die_indices", "unique_dice_label",
    "_dice_pill_options", "_indices_from_dice_pill_selection",
    "_render_independent_dice_picker", "extract_line", "extract_section",
    "score_box_html", "score_grid_html", "render_comparison_card", "_render_daily_review_body",
    "_daily_review_item", "render_daily_spotlight", "_toggle_daily_spotlight_open",
    "_mark_daily_spotlight_variation", "_reveal_daily_spotlight_answer",
    "_render_daily_spotlight_content",
}
nodes = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in names:
        nodes.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
        nodes.append(node)
    elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call = node.value
        if (isinstance(call.func, ast.Attribute) and call.func.attr == "markdown"
                and call.args and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str) and "<style>" in call.args[0].value):
            nodes.append(node)
CATEGORY_DISPLAY = {}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / "app.py"), "exec"))

if "daily_answers" not in st.session_state:
    st.session_state.daily_answers = answer_set("2026-08-28")
    st.session_state.daily_date_key = "2026-08-28"
    st.session_state.daily_set_id = "qa-2026-08-28"
    st.session_state.daily_attempt_id = "qa-attempt"
    st.session_state.active_player_id = "qa-player"
    st.session_state.daily_completed = True

if st.query_params.get("narrow") == "1":
    st.markdown("<style>.stMainBlockContainer{max-width:390px!important;padding-left:12px!important;padding-right:12px!important}</style>", unsafe_allow_html=True)
st.caption("Local QA · synthetic completed Daily · no database")
st.markdown("### 📝 Your 10 Grades")
render_daily_spotlight()
st.caption("Tap any question to open its full coaching.")
for answer in st.session_state.daily_answers:
    _daily_review_item(answer)
