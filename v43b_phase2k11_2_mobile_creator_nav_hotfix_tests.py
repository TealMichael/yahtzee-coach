from pathlib import Path

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    start = app.index("def render_player_avatar_creator")
    end = app.index("def render_player_identity_gate", start)
    creator = app[start:end]

    require("CATEGORY_ICONS" not in creator, "creator contains no emoji/symbol category icons")
    require('selected_category = st.selectbox(' in creator, "creator uses a mobile-safe readable category select box")
    require('format_func=lambda category: CATEGORY_LABELS[category].title()' in creator, "category selector shows full plain readable text")
    require('chosen_value = st.selectbox(' in creator, "choices use a mobile-safe readable select box instead of squeezed pills or giant cards")
    require("avatar_option_tile_html" not in creator, "mobile creator no longer renders a full-size card for every option")
    require('st.columns(3)' not in creator, "mobile creator no longer relies on three-column controls that stack vertically")
    for label in ("CHARACTER", "HAIR", "OUTFIT", "SKIN", "ACCESSORY", "SHOES"):
        require(label in (ROOT / "player_avatar.py").read_text(encoding="utf-8"), f"plain-text category label {label} remains available")

    print("Mobile creator navigation safety checks passed")


if __name__ == "__main__":
    run()
