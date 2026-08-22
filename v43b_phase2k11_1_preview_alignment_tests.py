from pathlib import Path

from player_avatar import avatar_option_tile_html, avatar_preview_html, medal_counter_html
from retro_podium import personal_medal_moment_html

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    avatar = (ROOT / "player_avatar.py").read_text(encoding="utf-8")
    retro = (ROOT / "retro_podium.py").read_text(encoding="utf-8")

    require('APP_RELEASE = "v43B Phase 2K.12.1"' in app, "visual alignment patch has its own release label")
    require("CREATE YOUR PLAYER" in app and "Tap a category, choose a style" in app, "creator keeps the approved light retro direction in a tighter mobile layout")
    require("avatar_creator_category_" in app and "chosen_value = st.selectbox(" in app, "creator keeps category-first customization with readable mobile controls")
    require("grid-template-columns:repeat(3,1fr)" in avatar, "medal counter keeps clean three-column preview layout")
    require("pose == \"give\"" in avatar and "pose == \"receive\"" in avatar, "sprites include dedicated medal-handoff poses")
    require("background:#fff9ea" in retro and ".stadium" not in retro and "confetti" not in retro.lower(), "medal moment stays light and simple with no stadium production")
    require("text-shadow:3px 0 #172033" in retro and "ALL-TIME MEDALS" in retro, "medal moment follows approved preview typography and collection panel")

    cfg = {"hair": "curly", "outfit": "pink_tee", "skin": "warm", "accessory": "none", "shoes": "blue"}
    require("LIVE PREVIEW" in avatar_preview_html(cfg, player_name="Mike", setup_complete=False), "creator preview has the intended live-preview treatment")
    require("✓" in avatar_option_tile_html("hair", "curly", cfg, selected=True), "selected avatar choice gets a visible check state")
    require("GOLD" in medal_counter_html({"gold": 3, "silver": 2, "bronze": 1}), "creator medal collection uses the same visual language")

    board = [
        {"player_id": "me", "display_name": "Mike", "rank": 1},
        {"player_id": "friend", "display_name": "Jenny", "rank": 2},
    ]
    html = personal_medal_moment_html(
        board,
        active_player_id="me",
        active_player_name="Mike",
        group_name="Friends",
        date_label="August 20, 2026",
        avatar_config=cfg,
        medal_totals={"gold": 3, "silver": 2, "bronze": 1},
    )
    require("YOU WON YESTERDAY!" in html and "PIXEL MIKE" in html and "Mike" in html, "personal handoff keeps the approved simple story")
    require("SKIP ›" in html and "prefers-reduced-motion" in html and "<audio" not in html.lower(), "visual polish preserves skip, reduced motion, and silence")

    print("Phase 2K.11.1 preview-art alignment checks passed")


if __name__ == "__main__":
    run()
