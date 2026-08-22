from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")
OLD_SOURCE = Path('/mnt/data/yc_dice_old/UPLOAD_TO_GITHUB/app.py').read_text(encoding='utf-8') if Path('/mnt/data/yc_dice_old/UPLOAD_TO_GITHUB/app.py').exists() else ''


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

# Duplicate-safe interaction remains position keyed.
require('key=f"{key_prefix}_die_{die_index}"' in picker, "each physical die retains its own widget key")
require("on_click=_toggle_held_die" in picker, "independent die callback remains in place")
require("st.pills(" not in SOURCE, "dice input does not regress to st.pills")
require("st.columns(" not in picker, "dice input does not regress to mobile-hostile columns")

# Visual target is explicitly restored from the approved pre-bug dice sizing.
require("Phase 2K.12.4: restore the approved large-die look" in SOURCE, "large-die restoration CSS is release scoped")
require('div[class*="st-key-daily_dice_"][class*="_die_"]' in SOURCE, "daily dice are styled through stable per-widget key classes")
require('div[class*="st-key-practice_dice_"][class*="_die_"]' in SOURCE, "practice dice are styled through stable per-widget key classes")
require("width:clamp(58px, 17vw, 68px)" in SOURCE, "normal dice restore approved 58-68px sizing")
require("height:clamp(58px, 17vw, 68px)" in SOURCE, "normal dice restore approved square height")
require("font-size:clamp(3.05rem, 13vw, 3.9rem)" in SOURCE, "die face glyphs restore approved large size")
require("width:clamp(54px, 16.2vw, 62px)" in SOURCE, "small-phone dice restore approved responsive sizing")
require("font-size:clamp(2.8rem, 12vw, 3.4rem)" in SOURCE, "small-phone die faces remain large")
require('width="content"' in picker, "native button width no longer fights CSS sizing")
require('APP_RELEASE = "v43B Phase 2K.12.4"' in SOURCE, "release label is Phase 2K.12.4")

# If the baseline is available, assert the critical dimensions are literally the same values.
if OLD_SOURCE:
    for token in [
        "width:clamp(58px, 17vw, 68px)",
        "height:clamp(58px, 17vw, 68px)",
        "font-size:clamp(3.05rem, 13vw, 3.9rem)",
        "width:clamp(54px, 16.2vw, 62px)",
        "font-size:clamp(2.8rem, 12vw, 3.4rem)",
    ]:
        require(token in OLD_SOURCE and token in SOURCE, f"restored CSS token matches pre-bug dice: {token}")

print("\nPhase 2K.12.4 restored dice visual regressions: PASS")
