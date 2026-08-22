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
require("st.columns(" not in picker, "dice picker no longer uses mobile-hostile st.columns")
require("horizontal=True" in picker, "dice picker uses Streamlit horizontal flex container")
require('horizontal_alignment="center"' in picker, "five dice are centered")
require('key=f"{key_prefix}_die_{die_index}"' in picker, "each physical die still has its own stable widget key")
require("on_click=_toggle_held_die" in picker, "independent die callback remains in place")
require('width="content"' in picker, "native button width defers to responsive dice CSS")
require("Phase 2K.12.4: restore the approved large-die look" in SOURCE, "mobile dice CSS remains release-scoped")
require("width:clamp(54px, 16.2vw, 62px)" in SOURCE and "max-width:380px" in SOURCE, "small-phone sizing is protected")
require('APP_RELEASE = "v43B Phase 2K.12.4"' in SOURCE, "release label is Phase 2K.12.4")

# Hard guard: the UI hotfix must not regress to pills or duplicate-label selection.
require("st.pills(" not in SOURCE, "dice input does not return to st.pills")

print("\nPhase 2K.12.3 mobile dice layout regressions: PASS")
