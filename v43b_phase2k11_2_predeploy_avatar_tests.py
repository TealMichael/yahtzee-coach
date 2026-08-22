from pathlib import Path
from xml.etree import ElementTree as ET
import hashlib

from player_avatar import AVATAR_CHOICES, DEFAULT_AVATAR, avatar_svg, normalize_avatar_config

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")

    require('APP_RELEASE = "v43B Phase 2K.12"' in app, "UI polish release has its own release label")
    require(set(AVATAR_CHOICES["style"]) == {"classic", "soft"}, "creator offers two unlabeled base character silhouettes")
    for hair in ("ponytail", "bob", "waves", "bun", "braids"):
        require(hair in AVATAR_CHOICES["hair"], f"inclusive hairstyle {hair} is available")
    require("purple_skirt" in AVATAR_CHOICES["outfit"] and "teal_sport" in AVATAR_CHOICES["outfit"], "creator has broader outfit choices")

    legacy = normalize_avatar_config({"hair": "curly", "outfit": "red_tee", "skin": "warm", "accessory": "none", "shoes": "black"})
    require(legacy["style"] == "classic" and legacy["hair"] == "curly", "older saved avatar JSON gains a safe default style without migration")

    rendered = 0
    # Every non-style option is exercised against BOTH base silhouettes in every
    # player ceremony pose, so one future hair/outfit cannot quietly break only
    # the Classic or Soft character.
    for style in AVATAR_CHOICES["style"]:
        for pose in ("idle", "receive", "celebrate"):
            cfg = dict(DEFAULT_AVATAR)
            cfg["style"] = style
            ET.fromstring(avatar_svg(cfg, pose=pose, title=f"style-{style}-{pose}"))
            rendered += 1
        for category, choices in AVATAR_CHOICES.items():
            if category == "style":
                continue
            for value in choices:
                cfg = dict(DEFAULT_AVATAR)
                cfg["style"] = style
                cfg[category] = value
                for pose in ("idle", "receive", "celebrate"):
                    svg = avatar_svg(cfg, pose=pose, title=f"{style}-{category}-{value}-{pose}")
                    ET.fromstring(svg)
                    require("<svg" in svg and "shape-rendering:crispEdges" in svg, f"{style}: {category}={value} renders safely in {pose} pose")
                    rendered += 1
    require(rendered >= 200, "avatar regression covers every creator option on both character styles across every player ceremony pose")

    require("_avatar_medal_group_choice" in app and "avatar_medal_group_" in app, "My Player has its own group-by-group medal cabinet selector")
    require("Medals are tracked separately for each friend group." in app, "multi-group medal meaning is explained clearly")
    require("chosen_id != st.session_state.get(\"active_group_id\")" not in app[app.index("def _avatar_medal_group_choice"):app.index("def render_player_avatar_creator")], "medal cabinet browsing cannot switch the active Daily group")

    expected = {
        "yahtzee_engine.py": "9b175f3f3f59f9937943856c01e1e7aeced7662742756766a54a6061ccaba6b1",
        "exact_runtime.py": "322e50715ca49e53d78e9cc6eda85a7af0712b881273fb57ea4c4f4b67da171a",
        "exact_mode.py": "890d61c50db221e6d8b535413375ecf7eab974741131386186f88017f005a017",
        "daily_store.py": "8eb46257a3ee02d14efd821f642637dde5d68cef13fa424a40f7d21f8912bbd0",
        "supabase_daily_store.py": "826d0061d33609d99f203f88c63df25301b49050cb4d467828ba3f0224523e7c",
        "session_learning.py": "695ea20fcd82ffe8979b5900f34b929d15cedcc902dc8ef92c30a4baf999963a",
        "practice_progress.py": "8f78b05eb867e716fbe845c81969b12f33617a7cd5f7c8dd7fe09b04c4632915",
        "exact_policy.npz": "cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b",
        "puzzle_bank.npz": "22f26f136a690c552fd7a8ad3a3335090f6085468219f197f16cea32e0276a8f",
        "challenge_catalog.npz": "fe92b90e4c2ce4261ac384711061756336af4b151e267946d26e4f8a4b649ecd",
    }
    for name, digest in expected.items():
        require(sha(name) == digest, f"protected non-generator file unchanged: {name}")

    require((ROOT / "RUN_THIS_ONCE_IN_SUPABASE_Phase2K11.sql").exists(), "existing Phase 2K.11 avatar migration remains the only required schema step")
    require(not (ROOT / "RUN_THIS_ONCE_IN_SUPABASE_Phase2K11_2.sql").exists(), "2K.11.2 requires no new Supabase migration")

    print("Phase 2K.11.2 pre-deployment avatar + medal cabinet checks passed")


if __name__ == "__main__":
    run()
