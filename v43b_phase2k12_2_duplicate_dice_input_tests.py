"""Phase 2K.12.2 regression tests for position-keyed duplicate-die input."""
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
    namespace = {}
    exec(compile(module, str(APP_PATH), "exec"), namespace)
    return [namespace[name] for name in names]


_normalize, toggle_die_index, selected_hold_from_indices, hold_indices_from_values = load_functions(
    "_normalize_die_indices",
    "toggle_die_index",
    "selected_hold_from_indices",
    "hold_indices_from_values",
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


# The real-world reported case: 2,3,3,4,4. One physical 3 must stay one 3.
dice = [2, 3, 3, 4, 4]
selected = []
for index in (0, 1, 3):
    selected = toggle_die_index(selected, index, len(dice))
require(selected == [0, 1, 3], "2,3,3,4,4 keeps exactly the three tapped physical dice")
require(selected_hold_from_indices(dice, selected) == [2, 3, 4], "one tapped 3 saves as one 3, not two")

# Tapping the other identical 3 is a separate action and produces the second 3 only then.
selected = toggle_die_index(selected, 2, len(dice))
require(selected == [0, 1, 2, 3], "second identical 3 has its own position state")
require(selected_hold_from_indices(dice, selected) == [2, 3, 3, 4], "second 3 appears only after its own tap")
selected = toggle_die_index(selected, 1, len(dice))
require(selected_hold_from_indices(dice, selected) == [2, 3, 4], "releasing first 3 leaves the independently selected second 3")

# Another duplicate-heavy family.
dice = [5, 5, 5, 6, 6]
selected = []
for index in (1, 4):
    selected = toggle_die_index(selected, index, len(dice))
require(selected == [1, 4], "5,5,5,6,6 supports individual matching-die selection")
require(selected_hold_from_indices(dice, selected) == [5, 6], "duplicate-heavy hold preserves exact multiplicity")

# Nightmare case: all five faces identical. Every position must still be independently selectable.
dice = [6, 6, 6, 6, 6]
selected = []
for expected_count, index in enumerate(range(5), start=1):
    selected = toggle_die_index(selected, index, len(dice))
    require(len(selected) == expected_count, f"all-six roll can select exactly {expected_count} physical dice")
    require(selected_hold_from_indices(dice, selected) == [6] * expected_count, f"all-six roll saves exactly {expected_count} sixes")
for expected_count, index in zip(range(4, -1, -1), range(5)):
    selected = toggle_die_index(selected, index, len(dice))
    require(len(selected) == expected_count, f"all-six roll can release back to exactly {expected_count} physical dice")

# Back/Edit reconstruction is multiplicity-safe even though saved holds store values, not identities.
dice = [2, 3, 3, 4, 4]
saved_hold = [2, 3, 4]
restored = hold_indices_from_values(dice, saved_hold)
require(len(restored) == 3, "Back/Edit restores three physical dice for a three-die saved hold")
require(selected_hold_from_indices(dice, restored) == saved_hold, "Back/Edit preserves duplicate multiplicity exactly")

# Source-level UI contract: no value-keyed pills; both modes use the position-keyed picker.
require("st.pills(" not in SOURCE, "Daily and Practice no longer use st.pills for dice input")
require('key=f"{key_prefix}_die_{die_index}"' in SOURCE, "each die button key contains its physical position")
require(SOURCE.count("_render_independent_dice_picker(") >= 3, "shared independent picker is used by Daily and Practice")
require('chosen_hold=selected_hold' in SOURCE, "Daily persistence saves the exact selected hold multiplicity")
require('st-key-daily_dice_' in SOURCE and 'st-key-practice_dice_' in SOURCE, "scroll guard/styling recognizes both independent pickers")
require('APP_RELEASE = "v43B Phase 2K.12.2"' in SOURCE, "release label bumped to Phase 2K.12.2")

print("\nPhase 2K.12.2 duplicate-dice input regressions: PASS")
