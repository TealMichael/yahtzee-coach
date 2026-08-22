from __future__ import annotations

"""Lightweight retro player-avatar helpers for Yahtzee Coach.

The avatar stays intentionally small and dynamic: chunky inline SVG primitives,
no video, no large sprite sheet, and no effect on any Yahtzee strategy/game code.
Phase 2K.12.1 hair-expansion hotfix adds independent hairstyle and hair-color with independent hairstyle and hair-color
choices while preserving the Phase 2K.11 JSON persistence contract.
"""

from hashlib import sha256
from html import escape
from typing import Mapping


AVATAR_CHOICES = {
    # These are visual silhouettes rather than gender labels. Every hair, outfit,
    # skin tone, accessory, and shoe choice works with either base style.
    "style": {
        "classic": "Classic",
        "soft": "Soft",
    },
    "hair": {
        "curly": "Curly",
        "spiky": "Spiky",
        "short": "Short",
        "sweep": "Side Sweep",
        "ponytail": "Ponytail",
        "bob": "Bob",
        "waves": "Long Waves",
        "bun": "High Bun",
        "braids": "Braids",
        "buzz": "Buzz",
        "pigtails": "Pigtails",
        "long_straight": "Long Straight",
        "low_ponytail": "Low Ponytail",
        "shoulder_wavy": "Shoulder-Length Wavy",
        "locs": "Locs / Twists",
    },
    "hair_color": {
        "black": "Black",
        "dark_brown": "Dark Brown",
        "brown": "Brown",
        "light_brown": "Light Brown",
        "blonde": "Blonde",
        "dirty_blonde": "Dirty Blonde",
        "auburn": "Auburn / Red",
        "gray_white": "Gray / White",
        "pink": "Pink",
        "purple": "Purple",
        "blue": "Blue",
        "teal": "Teal",
        "green": "Green",
    },
    "outfit": {
        "blue_tank": "Blue Sport",
        "red_tee": "Red Tee",
        "green_hoodie": "Green Hoodie",
        "black_zip": "Black Zip",
        "purple_tee": "Purple Tee",
        "pink_tee": "Pink Tee",
        "teal_sport": "Teal Sport",
        "purple_skirt": "Purple Skirt",
    },
    "skin": {
        "light": "Light",
        "warm": "Warm",
        "tan": "Tan",
        "brown": "Brown",
        "deep": "Deep",
        "dark": "Dark",
    },
    "accessory": {
        "none": "None",
        "white_headband": "White Headband",
        "red_headband": "Red Headband",
        "glasses": "Glasses",
        "wristbands": "Wristbands",
    },
    "shoes": {
        "blue": "Blue",
        "red": "Red",
        "black": "Black",
        "green": "Green",
        "white": "White",
    },
}

CATEGORY_LABELS = {
    "style": "CHARACTER",
    "hair": "HAIR STYLE",
    "hair_color": "HAIR COLOR",
    "outfit": "OUTFIT",
    "skin": "SKIN",
    "accessory": "ACCESSORY",
    "shoes": "SHOES",
}

CATEGORY_ICONS = {
    "style": "☺",
    "hair": "✦",
    "hair_color": "◆",
    "outfit": "▣",
    "skin": "●",
    "accessory": "★",
    "shoes": "▰",
}

DEFAULT_AVATAR = {
    "style": "classic",
    "hair": "spiky",
    "hair_color": "dark_brown",
    "outfit": "blue_tank",
    "skin": "warm",
    "accessory": "white_headband",
    "shoes": "blue",
}

_SKIN = {
    "light": ("#f7cfaa", "#e9ad7c"),
    "warm": ("#eeb07d", "#cf7d4d"),
    "tan": ("#d79b68", "#b96d43"),
    "brown": ("#ad704d", "#7f4934"),
    "deep": ("#845339", "#5f392a"),
    "dark": ("#5c392c", "#3d251e"),
}

_HAIR_COLOR = {
    # Natural shades
    "black": ("#17191f", "#343944"),
    "dark_brown": ("#4f2a1b", "#75432a"),
    "brown": ("#70401f", "#a66b34"),
    "light_brown": ("#9a6638", "#c48a50"),
    "blonde": ("#d9a742", "#f2cf72"),
    "dirty_blonde": ("#a7864a", "#ccb06d"),
    "auburn": ("#8b3f27", "#c1623c"),
    "gray_white": ("#a9adb7", "#e2e5ea"),
    # Fun shades requested by the player group
    "pink": ("#c94f86", "#ef83b0"),
    "purple": ("#6f4aa7", "#a27ad2"),
    "blue": ("#315ca8", "#5e91df"),
    "teal": ("#197f82", "#4fb7b2"),
    "green": ("#3d7f45", "#6eb66d"),
}

# Before 2K.12.2, hair color was baked into each hairstyle. When an older saved
# avatar has no `hair_color`, use the closest old shade so existing players keep
# looking familiar until they intentionally choose a new color.
_LEGACY_HAIR_COLOR_BY_STYLE = {
    "curly": "brown",
    "spiky": "dark_brown",
    "short": "black",
    "sweep": "blonde",
    "ponytail": "dark_brown",
    "bob": "black",
    "waves": "brown",
    "bun": "dark_brown",
    "braids": "black",
    "buzz": "light_brown",
    "pigtails": "brown",
    "long_straight": "dark_brown",
    "low_ponytail": "dark_brown",
    "shoulder_wavy": "brown",
    "locs": "black",
}


_OUTFIT = {
    "blue_tank": ("#f8fafc", "#2563a8", "#1f4e85"),
    "red_tee": ("#dc3f36", "#ef6358", "#222831"),
    "green_hoodie": ("#2f8f4e", "#54ad69", "#27313a"),
    "black_zip": ("#1d2430", "#374151", "#d54b40"),
    "purple_tee": ("#7352ad", "#9778cf", "#282536"),
    "pink_tee": ("#efb4c5", "#f6ccda", "#334155"),
    "teal_sport": ("#e8fbfa", "#2b9a96", "#236b70"),
    "purple_skirt": ("#7d57b3", "#ae8ad7", "#3a2b55"),
}

_SHOES = {
    "blue": "#2563a8",
    "red": "#cf4438",
    "black": "#1f2937",
    "green": "#3c8b55",
    "white": "#e8edf2",
}


def normalize_avatar_config(config: Mapping | None) -> dict[str, str]:
    raw = dict(config or {})
    normalized: dict[str, str] = {}
    for category, choices in AVATAR_CHOICES.items():
        if category == "hair_color" and not raw.get("hair_color"):
            hair_style = str(raw.get("hair") or DEFAULT_AVATAR["hair"])
            value = _LEGACY_HAIR_COLOR_BY_STYLE.get(hair_style, DEFAULT_AVATAR["hair_color"])
        else:
            value = str(raw.get(category) or DEFAULT_AVATAR[category])
        normalized[category] = value if value in choices else DEFAULT_AVATAR[category]
    return normalized


def default_avatar_for_player(player_id: str | None) -> dict[str, str]:
    """Return a stable unsaved default so legacy players do not all look identical."""
    if not player_id:
        return dict(DEFAULT_AVATAR)
    digest = sha256(str(player_id).encode("utf-8")).digest()
    # Keep the original categories on the same digest bytes they used before the
    # hair-color expansion so an unsaved legacy player's look does not reshuffle.
    result = {}
    for index, category in enumerate(("hair", "outfit", "skin", "accessory", "shoes")):
        keys = list(AVATAR_CHOICES[category])
        result[category] = keys[digest[index] % len(keys)]
    style_keys = list(AVATAR_CHOICES["style"])
    result["style"] = style_keys[digest[5] % len(style_keys)]
    result["hair_color"] = _LEGACY_HAIR_COLOR_BY_STYLE.get(result["hair"], DEFAULT_AVATAR["hair_color"])
    return normalize_avatar_config(result)


def _hair_svg(style: str, base: str, hi: str) -> str:
    """Blocky silhouettes that remain readable at small phone sizes."""
    if style == "curly":
        return (
            f'<rect x="20" y="14" width="5" height="9" fill="{base}"/><rect x="24" y="10" width="8" height="10" fill="{base}"/>'
            f'<rect x="30" y="8" width="8" height="11" fill="{base}"/><rect x="37" y="9" width="8" height="10" fill="{base}"/>'
            f'<rect x="44" y="11" width="8" height="11" fill="{base}"/><rect x="50" y="16" width="5" height="10" fill="{base}"/>'
            f'<rect x="25" y="12" width="5" height="5" fill="{hi}"/><rect x="35" y="10" width="5" height="5" fill="{hi}"/><rect x="45" y="13" width="5" height="5" fill="{hi}"/>'
        )
    if style == "spiky":
        return (
            f'<path d="M20 24V15h5V9l5 4 4-7 5 7 6-7 1 8 7-5-2 10h5v8h-6v-6h-6v-3h-8v2h-6v-3h-5v7z" fill="{base}"/>'
            f'<rect x="27" y="12" width="5" height="4" fill="{hi}"/><rect x="39" y="11" width="5" height="4" fill="{hi}"/>'
        )
    if style == "short":
        return f'<rect x="21" y="15" width="33" height="11" fill="{base}"/><rect x="25" y="11" width="25" height="8" fill="{base}"/><rect x="30" y="13" width="15" height="3" fill="{hi}"/>'
    if style == "sweep":
        return f'<path d="M19 25V18h5v-5h7V9h20v4h5v7h-8l-5-4-7 2-7 4-5 4z" fill="{base}"/><path d="M31 11h18v4h-8l-10 4z" fill="{hi}"/>'
    if style == "ponytail":
        return (
            f'<rect x="22" y="11" width="31" height="15" fill="{base}"/><rect x="49" y="18" width="8" height="14" fill="{base}"/>'
            f'<rect x="55" y="27" width="8" height="16" fill="{base}"/><rect x="59" y="39" width="7" height="10" fill="{base}"/>'
            f'<rect x="28" y="12" width="17" height="4" fill="{hi}"/><rect x="56" y="29" width="4" height="9" fill="{hi}"/>'
        )
    if style == "bob":
        return (
            f'<rect x="20" y="13" width="35" height="14" fill="{base}"/><rect x="18" y="20" width="8" height="23" fill="{base}"/>'
            f'<rect x="50" y="20" width="8" height="23" fill="{base}"/><rect x="25" y="11" width="26" height="7" fill="{base}"/>'
            f'<rect x="29" y="13" width="17" height="4" fill="{hi}"/>'
        )
    if style == "waves":
        return (
            f'<rect x="19" y="14" width="7" height="31" fill="{base}"/><rect x="50" y="14" width="7" height="31" fill="{base}"/>'
            f'<rect x="23" y="10" width="30" height="14" fill="{base}"/><rect x="16" y="31" width="7" height="9" fill="{base}"/>'
            f'<rect x="53" y="34" width="7" height="9" fill="{base}"/><rect x="29" y="12" width="18" height="4" fill="{hi}"/>'
        )
    if style == "bun":
        return (
            f'<rect x="23" y="13" width="31" height="14" fill="{base}"/><rect x="29" y="9" width="20" height="8" fill="{base}"/>'
            f'<rect x="33" y="3" width="13" height="9" fill="{base}"/><rect x="36" y="1" width="8" height="5" fill="{base}"/>'
            f'<rect x="35" y="5" width="8" height="4" fill="{hi}"/><rect x="29" y="14" width="18" height="4" fill="{hi}"/>'
        )
    if style == "braids":
        return (
            f'<rect x="22" y="11" width="32" height="15" fill="{base}"/><rect x="17" y="22" width="7" height="25" fill="{base}"/>'
            f'<rect x="52" y="22" width="7" height="25" fill="{base}"/><rect x="15" y="42" width="6" height="8" fill="{hi}"/>'
            f'<rect x="55" y="42" width="6" height="8" fill="{hi}"/><rect x="29" y="12" width="18" height="4" fill="{hi}"/>'
        )
    if style == "pigtails":
        return (
            f'<rect x="22" y="11" width="32" height="15" fill="{base}"/><rect x="15" y="19" width="10" height="10" fill="{base}"/>'
            f'<rect x="51" y="19" width="10" height="10" fill="{base}"/><rect x="11" y="25" width="9" height="19" fill="{base}"/>'
            f'<rect x="56" y="25" width="9" height="19" fill="{base}"/><rect x="13" y="28" width="5" height="9" fill="{hi}"/>'
            f'<rect x="58" y="28" width="5" height="9" fill="{hi}"/><rect x="29" y="12" width="18" height="4" fill="{hi}"/>'
        )
    if style == "long_straight":
        return (
            f'<rect x="20" y="11" width="36" height="16" fill="{base}"/><rect x="17" y="21" width="9" height="31" fill="{base}"/>'
            f'<rect x="50" y="21" width="9" height="31" fill="{base}"/><rect x="25" y="9" width="27" height="7" fill="{base}"/>'
            f'<rect x="29" y="11" width="18" height="4" fill="{hi}"/><rect x="19" y="33" width="4" height="15" fill="{hi}"/>'
        )
    if style == "low_ponytail":
        return (
            f'<rect x="22" y="11" width="32" height="15" fill="{base}"/><rect x="50" y="20" width="8" height="12" fill="{base}"/>'
            f'<rect x="55" y="29" width="8" height="21" fill="{base}"/><rect x="59" y="45" width="7" height="8" fill="{base}"/>'
            f'<rect x="29" y="12" width="18" height="4" fill="{hi}"/><rect x="57" y="31" width="4" height="12" fill="{hi}"/>'
        )
    if style == "shoulder_wavy":
        return (
            f'<rect x="20" y="11" width="36" height="16" fill="{base}"/><rect x="17" y="21" width="9" height="23" fill="{base}"/>'
            f'<rect x="50" y="21" width="9" height="23" fill="{base}"/><rect x="15" y="35" width="8" height="8" fill="{base}"/>'
            f'<rect x="53" y="37" width="8" height="8" fill="{base}"/><rect x="29" y="12" width="18" height="4" fill="{hi}"/>'
        )
    if style == "locs":
        return (
            f'<rect x="22" y="10" width="32" height="16" fill="{base}"/><rect x="17" y="18" width="7" height="29" fill="{base}"/>'
            f'<rect x="27" y="20" width="6" height="31" fill="{base}"/><rect x="43" y="20" width="6" height="31" fill="{base}"/>'
            f'<rect x="52" y="18" width="7" height="29" fill="{base}"/><rect x="18" y="28" width="4" height="4" fill="{hi}"/>'
            f'<rect x="28" y="34" width="4" height="4" fill="{hi}"/><rect x="44" y="29" width="4" height="4" fill="{hi}"/>'
            f'<rect x="53" y="36" width="4" height="4" fill="{hi}"/>'
        )
    return f'<rect x="22" y="15" width="31" height="10" fill="{base}"/><rect x="27" y="11" width="21" height="7" fill="{base}"/><rect x="30" y="13" width="15" height="3" fill="{hi}"/>'


def avatar_svg(config: Mapping | None, *, width: int = 150, pose: str = "idle", title: str = "Player") -> str:
    """Render the saved player as a deliberately small, crisp retro sprite.

    Base `style` changes the face/shoulder silhouette without imposing a gender
    label. Every other creator choice remains compatible with both styles.
    Poses are visual-only and never touch gameplay state.
    """
    cfg = normalize_avatar_config(config)
    skin, skin_shadow = _SKIN[cfg["skin"]]
    hair, hair_hi = _HAIR_COLOR[cfg["hair_color"]]
    outfit, outfit_hi, lower = _OUTFIT[cfg["outfit"]]
    shoes = _SHOES[cfg["shoes"]]
    soft = cfg["style"] == "soft"
    lift = -2 if pose in {"celebrate", "receive"} else 0

    torso_x, torso_w = (25, 26) if soft else (23, 30)
    lower_x, lower_w = (28, 20) if soft else (27, 22)
    arm_left_x, arm_right_x = (20, 50) if soft else (18, 52)
    head_x, head_w = (23, 30) if soft else (22, 32)
    eye_left_x, eye_right_x = (28, 43) if soft else (26, 44)

    if cfg["outfit"] in {"blue_tank", "teal_sport"}:
        torso = (
            f'<rect x="{torso_x + 3}" y="49" width="{torso_w - 6}" height="18" fill="{outfit}"/>'
            f'<rect x="{torso_x + 3}" y="49" width="4" height="18" fill="{outfit_hi}"/><rect x="{torso_x + torso_w - 7}" y="49" width="4" height="18" fill="{outfit_hi}"/>'
            f'<rect x="{lower_x}" y="65" width="{lower_w}" height="12" fill="{lower}"/>'
        )
    elif cfg["outfit"] == "green_hoodie":
        torso = (
            f'<rect x="{torso_x}" y="48" width="{torso_w}" height="23" fill="{outfit}"/><rect x="{torso_x + 4}" y="50" width="{torso_w - 8}" height="4" fill="{outfit_hi}"/>'
            f'<rect x="37" y="49" width="2" height="18" fill="#e5e7eb"/><rect x="{lower_x}" y="69" width="{lower_w}" height="8" fill="{lower}"/>'
        )
    elif cfg["outfit"] == "black_zip":
        torso = (
            f'<rect x="{torso_x}" y="48" width="{torso_w}" height="22" fill="{outfit}"/><rect x="37" y="48" width="2" height="20" fill="{outfit_hi}"/>'
            f'<rect x="{lower_x}" y="69" width="{lower_w}" height="8" fill="{lower}"/>'
        )
    elif cfg["outfit"] == "purple_skirt":
        torso = (
            f'<rect x="{torso_x}" y="49" width="{torso_w}" height="18" fill="{outfit}"/><rect x="{torso_x + 3}" y="50" width="{torso_w - 6}" height="4" fill="{outfit_hi}"/>'
            f'<path d="M{lower_x} 66h{lower_w}l4 12H{lower_x - 4}z" fill="{lower}"/><rect x="31" y="77" width="5" height="4" fill="#202938"/><rect x="41" y="77" width="5" height="4" fill="#202938"/>'
        )
    else:
        torso = (
            f'<rect x="{torso_x}" y="49" width="{torso_w}" height="20" fill="{outfit}"/><rect x="{torso_x + 3}" y="50" width="{torso_w - 6}" height="4" fill="{outfit_hi}"/>'
            f'<rect x="{lower_x}" y="68" width="{lower_w}" height="9" fill="{lower}"/>'
        )

    if pose == "give":
        left_arm = f'<rect x="{arm_left_x}" y="51" width="7" height="18" fill="{skin}"/><rect x="{arm_left_x}" y="65" width="7" height="5" fill="{skin_shadow}"/>'
        right_arm = f'<rect x="{arm_right_x}" y="51" width="11" height="7" fill="{skin}"/><rect x="{arm_right_x + 9}" y="52" width="11" height="7" fill="{skin}"/><rect x="{arm_right_x + 16}" y="53" width="6" height="6" fill="{skin_shadow}"/>'
    elif pose == "receive":
        left_arm = f'<rect x="7" y="52" width="13" height="7" fill="{skin}"/><rect x="18" y="51" width="9" height="7" fill="{skin}"/><rect x="7" y="53" width="6" height="6" fill="{skin_shadow}"/>'
        right_arm = f'<rect x="{arm_right_x}" y="49" width="7" height="12" fill="{skin}"/><rect x="{arm_right_x + 5}" y="43" width="7" height="11" fill="{skin}"/><rect x="{arm_right_x + 6}" y="41" width="6" height="6" fill="{skin_shadow}"/>'
    elif pose == "celebrate":
        left_arm = f'<rect x="{arm_left_x - 1}" y="48" width="7" height="13" fill="{skin}"/><rect x="{arm_left_x - 6}" y="42" width="7" height="11" fill="{skin}"/><rect x="{arm_left_x - 7}" y="40" width="6" height="6" fill="{skin_shadow}"/>'
        right_arm = f'<rect x="{arm_right_x}" y="48" width="7" height="13" fill="{skin}"/><rect x="{arm_right_x + 5}" y="42" width="7" height="11" fill="{skin}"/><rect x="{arm_right_x + 7}" y="40" width="6" height="6" fill="{skin_shadow}"/>'
    else:
        left_arm = f'<rect x="{arm_left_x}" y="51" width="7" height="18" fill="{skin}"/><rect x="{arm_left_x}" y="65" width="7" height="5" fill="{skin_shadow}"/>'
        right_arm = f'<rect x="{arm_right_x}" y="51" width="7" height="18" fill="{skin}"/><rect x="{arm_right_x}" y="65" width="7" height="5" fill="{skin_shadow}"/>'

    accessories = ""
    if cfg["accessory"] == "white_headband":
        accessories += '<rect x="21" y="21" width="32" height="5" fill="#f8fafc"/><rect x="49" y="25" width="7" height="3" fill="#cbd5e1"/>'
    elif cfg["accessory"] == "red_headband":
        accessories += '<rect x="21" y="21" width="32" height="5" fill="#dc3f36"/><rect x="49" y="25" width="7" height="3" fill="#8f251f"/>'
    elif cfg["accessory"] == "glasses":
        accessories += '<rect x="26" y="31" width="10" height="7" fill="none" stroke="#111827" stroke-width="3"/><rect x="41" y="31" width="10" height="7" fill="none" stroke="#111827" stroke-width="3"/><rect x="36" y="33" width="5" height="2" fill="#111827"/>'
    elif cfg["accessory"] == "wristbands":
        accessories += f'<rect x="{arm_left_x}" y="59" width="7" height="4" fill="#f8fafc"/><rect x="{arm_right_x}" y="59" width="7" height="4" fill="#f8fafc"/>'

    if soft:
        face = (
            f'<rect x="{head_x}" y="21" width="{head_w}" height="27" fill="{skin}"/><rect x="26" y="48" width="24" height="3" fill="{skin_shadow}" opacity=".45"/>'
            f'<rect x="{eye_left_x}" y="32" width="7" height="8" fill="#f8fafc"/><rect x="{eye_right_x}" y="32" width="7" height="8" fill="#f8fafc"/>'
            f'<rect x="{eye_left_x + 3}" y="34" width="3" height="5" fill="#111827"/><rect x="{eye_right_x}" y="34" width="3" height="5" fill="#111827"/>'
            '<rect x="27" y="30" width="5" height="2" fill="#4b2b24"/><rect x="45" y="30" width="5" height="2" fill="#4b2b24"/>'
            '<rect x="35" y="42" width="8" height="3" fill="#8b3f31"/><rect x="38" y="44" width="5" height="2" fill="#fff" opacity=".8"/>'
        )
    else:
        face = (
            f'<rect x="{head_x}" y="21" width="{head_w}" height="30" fill="{skin}"/><rect x="22" y="44" width="32" height="7" fill="{skin_shadow}" opacity=".38"/>'
            f'<rect x="{eye_left_x}" y="32" width="7" height="8" fill="#f8fafc"/><rect x="{eye_right_x}" y="32" width="7" height="8" fill="#f8fafc"/>'
            f'<rect x="{eye_left_x + 3}" y="34" width="3" height="5" fill="#111827"/><rect x="{eye_right_x}" y="34" width="3" height="5" fill="#111827"/>'
            '<rect x="35" y="42" width="8" height="3" fill="#8b3f31"/><rect x="38" y="44" width="5" height="2" fill="#fff" opacity=".8"/>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 76 94" width="{int(width)}" role="img" aria-label="{escape(title)}" style="image-rendering:pixelated;shape-rendering:crispEdges">
      <ellipse cx="38" cy="89" rx="22" ry="4" fill="#0f172a" opacity=".16"/>
      <g transform="translate(0 {lift})">
        <rect x="27" y="75" width="9" height="10" fill="{skin_shadow}"/><rect x="41" y="75" width="9" height="10" fill="{skin_shadow}"/>
        <rect x="23" y="82" width="15" height="7" fill="{shoes}"/><rect x="39" y="82" width="15" height="7" fill="{shoes}"/>
        <rect x="23" y="86" width="15" height="3" fill="#f8fafc"/><rect x="39" y="86" width="15" height="3" fill="#f8fafc"/>
        {torso}{left_arm}{right_arm}
        {face}
        {_hair_svg(cfg['hair'], hair, hair_hi)}
        {accessories}
      </g>
    </svg>'''


def avatar_preview_html(config: Mapping | None, *, player_name: str = "Your Player", setup_complete: bool = True) -> str:
    status = "YOUR SAVED PLAYER" if setup_complete else "LIVE PREVIEW"
    return f"""
    <div class="yc-avatar-preview-card" style="border:3px solid #172033;border-radius:18px;padding:12px 14px 10px;text-align:center;background:#fffdf7;box-shadow:5px 5px 0 #d9d2c3;color:#172033">
      <div style="font:1000 11px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.12em;color:#64748b">🎮 {escape(status)}</div>
      <div style="margin:1px auto -3px;min-height:190px;display:grid;place-items:center">{avatar_svg(config, width=190, title=player_name)}</div>
      <div style="display:inline-block;background:#172033;color:#fffdf7;padding:5px 12px;font:1000 12px ui-monospace,SFMono-Regular,Menlo,monospace;box-shadow:3px 3px 0 #94a3b8">{escape(player_name)}</div>
    </div>"""


def avatar_option_tile_html(category: str, value: str, config: Mapping | None, *, selected: bool = False) -> str:
    """Small visual tile used above the native, reliable Streamlit choice button."""
    category = str(category)
    value = str(value)
    cfg = normalize_avatar_config(config)
    if category not in AVATAR_CHOICES or value not in AVATAR_CHOICES[category]:
        return ""
    cfg[category] = value
    label = AVATAR_CHOICES[category][value]
    border = "#f2b718" if selected else "#d8d3c9"
    bg = "#fff9e8" if selected else "#fffdf7"
    check = "<span style='position:absolute;right:5px;top:4px;width:18px;height:18px;border-radius:50%;background:#22a447;color:white;font:900 12px system-ui;display:grid;place-items:center'>✓</span>" if selected else ""
    return f"""
    <div style="position:relative;border:3px solid {border};background:{bg};border-radius:12px;min-height:112px;padding:5px 3px 7px;text-align:center;box-shadow:2px 2px 0 #e5e0d6;color:#172033">
      {check}
      <div style="height:78px;display:grid;place-items:center;overflow:hidden">{avatar_svg(cfg, width=72, title=label)}</div>
      <div style="font:900 9px/1.05 ui-monospace,SFMono-Regular,Menlo,monospace;min-height:19px;display:flex;align-items:center;justify-content:center;padding:0 2px">{escape(label).upper()}</div>
    </div>"""


def medal_counter_html(totals: Mapping | None, *, group_name: str = "") -> str:
    values = dict(totals or {})
    gold = int(values.get("gold") or 0)
    silver = int(values.get("silver") or 0)
    bronze = int(values.get("bronze") or 0)
    suffix = f" · {escape(group_name)}" if group_name else ""
    return f"""
    <div style="margin:10px 0 4px;border:3px solid #172033;border-radius:14px;background:#18223a;color:#fffdf7;box-shadow:4px 4px 0 #aab4c3;padding:9px 10px">
      <div style="text-align:center;font:1000 10px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.08em;margin-bottom:6px">ALL-TIME MEDALS{suffix}</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);text-align:center;gap:4px">
        <div style="border-right:1px dashed #526079"><div style="font-size:24px">🥇</div><div style="font:1000 9px ui-monospace;color:#ffd23f">GOLD</div><div style="font:1000 22px ui-monospace">{gold}</div></div>
        <div style="border-right:1px dashed #526079"><div style="font-size:24px">🥈</div><div style="font:1000 9px ui-monospace;color:#e5e7eb">SILVER</div><div style="font:1000 22px ui-monospace">{silver}</div></div>
        <div><div style="font-size:24px">🥉</div><div style="font:1000 9px ui-monospace;color:#e28a3e">BRONZE</div><div style="font:1000 22px ui-monospace">{bronze}</div></div>
      </div>
    </div>"""
