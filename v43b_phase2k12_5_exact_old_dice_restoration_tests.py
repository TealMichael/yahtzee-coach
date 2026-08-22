"""Guard the exact old dice renderer + duplicate-safe underlying values."""
from pathlib import Path
import ast
import hashlib
import re

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def function_source(name):
    tree = ast.parse(SOURCE)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(SOURCE, node)
    raise AssertionError(f"missing function {name}")

picker = function_source("_render_independent_dice_picker")
options = function_source("_dice_pill_options")
mapper = function_source("_indices_from_dice_pill_selection")


# Byte-for-byte guard for the exact pre-fix pill CSS block from Phase 2K.12.1.
match = re.search(
    r'/\* V10 dice picker: one tight row of large tappable dice using Streamlit pills\. \*/(.*?)(?=\n\s*/\* Old HTML dice styles)',
    SOURCE,
    re.S,
)
require(match is not None, "pre-fix pill CSS block is present")
css_hash = hashlib.sha256(match.group(0).encode("utf-8")).hexdigest()
require(
    css_hash == "c0680cd8b1e88523f694f066c08adc37f75e736dd7d1927fc75fce5e17cd1828",
    "pre-fix pill CSS block is byte-for-byte identical to Phase 2K.12.1",
)

require("st.pills(" in picker, "exact old dice widget family restored")
require('key=widget_key' in picker and 'widget_key = f"{key_prefix}_pills_v2"' in picker, "Daily/Practice dice widgets have stable per-puzzle keys")
require("format_func=" not in picker, "no format_func is used")
require("unique_dice_label" in options, "each physical die receives a visually invisible unique suffix")
require("index_by_option" in mapper, "unique options map directly back to physical die indices")
require('key_text == f"{dice_key_prefix}_pills_v2"' in SOURCE, "Back/Edit clears the pill widget before restoring saved state")

# Hard reject the two failed intermediate implementations.
require('horizontal=True' not in picker, "2K.12.3/4 horizontal button implementation is gone")
require('key=f"{key_prefix}_die_{die_index}"' not in picker, "per-button renderer is gone from live picker")

print("\nPhase 2K.12.5 exact old dice restoration regressions: PASS")
