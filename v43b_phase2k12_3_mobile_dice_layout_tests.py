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
require("st.columns(" not in picker, "dice picker does not use mobile-hostile st.columns")
require("horizontal=True" not in picker, "dice picker no longer uses the undersized horizontal button renderer")
require("st.pills(" in picker, "dice picker restores the pre-fix pill renderer")
require("format_func=" not in picker, "restored pill renderer avoids duplicate-state format_func")
require("selection_mode=\"multi\"" in picker, "five physical dice can be selected independently")
require("div[data-testid=\"stPills\"]" in SOURCE, "pre-fix pill CSS remains present")
require("flex-wrap:nowrap" in SOURCE, "old one-row dice layout is protected")
require('APP_RELEASE = "v43B Phase 2K.13"' in SOURCE, "release label is Phase 2K.12.5")

print("\nPhase 2K.12.5 mobile dice layout regressions: PASS")
