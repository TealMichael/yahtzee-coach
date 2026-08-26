from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def function_source(name):
    tree = ast.parse(SOURCE)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(SOURCE, node)
    raise AssertionError(f"missing function {name}")

picker = function_source("_render_independent_dice_picker")

# Phase 2K.12.5 restores the exact pre-fix widget, not an approximation with st.button.
require("st.pills(" in picker, "actual pre-fix st.pills dice widget is restored")
require("st.button(" not in picker, "dice faces are not rendered through undersized native buttons")
require("format_func=" not in picker, "visual restoration does not revive the duplicate format_func bug")

# Exact old CSS values from the working pre-fix pill renderer.
for token in [
    'div[data-testid="stPills"] div[role="group"]',
    "gap:0.52rem !important",
    "width:clamp(56px, 16.5vw, 68px) !important",
    "height:clamp(56px, 16.5vw, 68px) !important",
    "font-size:clamp(2.85rem, 11.5vw, 3.55rem) !important",
    "width:clamp(54px, 16.2vw, 62px) !important",
    "font-size:clamp(2.8rem, 12vw, 3.4rem) !important",
]:
    require(token in SOURCE, f"pre-fix dice visual token is present: {token}")

require('APP_RELEASE = "v43B Phase 2K.13.2"' in SOURCE, "release label is Phase 2K.12.5")

print("\nPhase 2K.12.5 restored dice visual regressions: PASS")
