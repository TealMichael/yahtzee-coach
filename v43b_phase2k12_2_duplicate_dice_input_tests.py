"""Phase 2K.12.5 regression tests for duplicate-safe dice input."""
from __future__ import annotations

import ast
from pathlib import Path

APP_PATH = Path(__file__).with_name("app.py")
SOURCE = APP_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def load_functions(*names):
    wanted = []
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            wanted.append(node)
    missing = set(names) - {node.name for node in wanted}
    if missing:
        raise AssertionError(f"Missing helper functions: {sorted(missing)}")
    module = ast.Module(body=wanted, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        "DICE_FACE": {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"},
    }
    exec(compile(module, str(APP_PATH), "exec"), namespace)
    return [namespace[name] for name in names]


(
    _normalize,
    selected_hold_from_indices,
    hold_indices_from_values,
    unique_dice_label,
    _dice_pill_options,
    _indices_from_dice_pill_selection,
) = load_functions(
    "_normalize_die_indices",
    "selected_hold_from_indices",
    "hold_indices_from_values",
    "unique_dice_label",
    "_dice_pill_options",
    "_indices_from_dice_pill_selection",
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


# Real reported case: visually identical duplicate faces must be distinct underlying pills.
dice = [2, 3, 3, 4, 4]
options = _dice_pill_options(dice)
require(len(options) == 5 and len(set(options)) == 5, "all five physical dice have unique underlying pill values")
require(options[1].replace("\u200b", "") == options[2].replace("\u200b", "") == "⚂", "duplicate 3s remain visually identical")
require(options[3].replace("\u200b", "") == options[4].replace("\u200b", "") == "⚃", "duplicate 4s remain visually identical")

selected = [options[0], options[1], options[3]]
indices = _indices_from_dice_pill_selection(dice, selected)
require(indices == [0, 1, 3], "2,3,3,4,4 maps exactly the three tapped physical pills")
require(selected_hold_from_indices(dice, indices) == [2, 3, 4], "one tapped 3 saves as one 3, not two")

selected.append(options[2])
indices = _indices_from_dice_pill_selection(dice, selected)
require(selected_hold_from_indices(dice, indices) == [2, 3, 3, 4], "second 3 appears only after its own pill is selected")

# Nightmare case: five identical faces are still five independently addressable options.
dice = [6, 6, 6, 6, 6]
options = _dice_pill_options(dice)
require(len(set(options)) == 5, "five sixes remain five distinct underlying pill options")
for count in range(1, 6):
    indices = _indices_from_dice_pill_selection(dice, options[:count])
    require(indices == list(range(count)), f"all-six roll can select exactly {count} physical dice")
    require(selected_hold_from_indices(dice, indices) == [6] * count, f"all-six roll saves exactly {count} sixes")

# Back/Edit reconstruction remains multiplicity-safe.
dice = [2, 3, 3, 4, 4]
saved_hold = [2, 3, 4]
restored = hold_indices_from_values(dice, saved_hold)
require(selected_hold_from_indices(dice, restored) == saved_hold, "Back/Edit preserves duplicate multiplicity")

# Source contract: restore the old pill UI but eliminate the buggy format_func path.
picker_start = SOURCE.index("def _render_independent_dice_picker")
picker_end = SOURCE.index("\ndef extract_line", picker_start)
picker = SOURCE[picker_start:picker_end]
require("st.pills(" in picker, "dice input uses the original large st.pills renderer")
require("format_func=" not in picker, "dice input does not use the old buggy format_func path")
require("options=options" in picker, "unique pill strings are the actual widget options")
require("_indices_from_dice_pill_selection" in picker, "pill selections map back to physical positions")
require('chosen_hold=selected_hold' in SOURCE, "Daily persistence saves exact selected hold multiplicity")
require('APP_RELEASE = "v43B Phase 2K.14"' in SOURCE, "release label is Phase 2K.12.5")

print("\nPhase 2K.12.5 duplicate-dice input regressions: PASS")
