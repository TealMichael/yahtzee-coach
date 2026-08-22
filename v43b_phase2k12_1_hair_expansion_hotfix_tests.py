from pathlib import Path
from xml.etree import ElementTree as ET

from player_avatar import AVATAR_CHOICES, DEFAULT_AVATAR, avatar_svg, normalize_avatar_config

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    expected_new_styles = {
        "pigtails", "long_straight", "low_ponytail", "shoulder_wavy", "locs"
    }
    require(expected_new_styles.issubset(AVATAR_CHOICES["hair"]), "five additional hairstyles are available")
    require(len(AVATAR_CHOICES["hair"]) == 15, "creator now offers 15 hairstyles")

    natural = {
        "black", "dark_brown", "brown", "light_brown", "blonde",
        "dirty_blonde", "auburn", "gray_white",
    }
    fun = {"pink", "purple", "blue", "teal", "green"}
    require(natural.issubset(AVATAR_CHOICES["hair_color"]), "eight natural hair colors are available")
    require(fun.issubset(AVATAR_CHOICES["hair_color"]), "five fun hair colors are available")
    require(len(AVATAR_CHOICES["hair_color"]) == 13, "creator now offers 13 hair colors")

    # Old saved JSON had no hair_color. It must continue to load safely and keep
    # roughly the old baked-in shade rather than changing everybody's appearance.
    old_blonde = normalize_avatar_config({
        "style": "soft", "hair": "sweep", "outfit": "pink_tee",
        "skin": "warm", "accessory": "none", "shoes": "white",
    })
    require(old_blonde["hair_color"] == "blonde", "legacy Side Sweep keeps its old blonde appearance")
    old_braids = normalize_avatar_config({
        "style": "classic", "hair": "braids", "outfit": "blue_tank",
        "skin": "brown", "accessory": "none", "shoes": "blue",
    })
    require(old_braids["hair_color"] == "black", "legacy Braids keep their old black appearance")

    # Every hairstyle/color combination must render on both base silhouettes in
    # every player pose used by My Player and medal ceremonies.
    rendered = 0
    for base_style in AVATAR_CHOICES["style"]:
        for hair in AVATAR_CHOICES["hair"]:
            for color in AVATAR_CHOICES["hair_color"]:
                cfg = dict(DEFAULT_AVATAR)
                cfg["style"] = base_style
                cfg["hair"] = hair
                cfg["hair_color"] = color
                for pose in ("idle", "receive", "celebrate"):
                    svg = avatar_svg(cfg, pose=pose, title=f"{base_style}-{hair}-{color}-{pose}")
                    ET.fromstring(svg)
                    require("<svg" in svg, f"renders {base_style}/{hair}/{color}/{pose}")
                    rendered += 1
    require(rendered == 2 * 15 * 13 * 3, "all 1,170 hairstyle/color/pose combinations render safely")

    # The proven mobile-safe creator pattern stays in place; Hair Color simply
    # appears as another category because the editor reads AVATAR_CHOICES.
    start = app.index("def render_player_avatar_creator")
    end = app.index("def render_player_identity_gate", start)
    creator = app[start:end]
    require("category_options = list(AVATAR_CHOICES)" in creator, "Hair Color automatically appears in creator categories")
    require("selected_category = st.selectbox(" in creator and "chosen_value = st.selectbox(" in creator, "mobile-safe full-label controls remain unchanged")
    require("st.pills(" not in creator, "hair expansion does not bring back squeezed mobile pills")

    print("Phase 2K.12.1 hair expansion hotfix checks passed")


if __name__ == "__main__":
    run()
