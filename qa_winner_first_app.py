"""Local-only QA harness for the reported winner-first Daily review."""
import ast
import html
from pathlib import Path
import re

import streamlit as st
from exact_mode import ExactPolicyTable, build_exact_report


ROOT = Path(__file__).resolve().parent
source = (ROOT / "app.py").read_text(encoding="utf-8")
tree = ast.parse(source)
names = {
    "DICE_FACE", "CATEGORY_SHORT", "CATEGORY_SCORECARD",
    "UPPER_CATEGORIES", "LOWER_CATEGORIES", "extract_line", "extract_section",
    "score_box_html", "score_grid_html", "render_comparison_card", "_render_daily_review_body",
}
nodes = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in names:
        nodes.append(node)
    elif isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id in names for target in node.targets
    ):
        nodes.append(node)
CATEGORY_DISPLAY = {}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / "app.py"), "exec"))

scorecard = {
    "ones": None, "twos": None, "threes": None,
    "fours": None, "fives": None, "sixes": None,
    "three_of_a_kind": None, "four_of_a_kind": None,
    "full_house": None, "small_straight": None,
    "large_straight": None, "yahtzee": None, "chance": 13,
}
report, record = build_exact_report(
    ExactPolicyTable(ROOT / "exact_policy.npz"),
    dice=[1, 1, 4, 5, 6], scorecard=scorecard, user_hold=[1, 1], roll_number=1,
)
answer = {
    "challenge": {
        "stage": "Opening", "roll_number": 1, "skill_tag": "Straight Structure",
        "dice": [1, 1, 4, 5, 6], "scorecard": scorecard,
    },
    "solver_record": record,
    "report": report,
}

st.caption("Local QA · synthetic decision · no database")
_render_daily_review_body(answer)
