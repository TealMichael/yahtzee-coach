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

    require('st.markdown("**Customize**")' in creator, "creator keeps a clear Customize heading")
    require("st.pills(" not in creator, "creator category navigation no longer uses emoji-prone st.pills")
    require("CATEGORY_ICONS" not in creator, "creator navigation and selected-category header contain no symbol/emoji icons")
    require("for offset in range(0, len(category_options), 3)" in creator, "six categories render as a mobile-safe three-column grid")
    require('st.columns(3)' in creator, "category navigation uses three equal native-button columns")
    require('type="primary" if selected else "secondary"' in creator, "selected category is highlighted with native button styling")
    for label in ("CHARACTER", "HAIR", "OUTFIT", "SKIN", "ACCESSORY", "SHOES"):
        require(label in (ROOT / "player_avatar.py").read_text(encoding="utf-8"), f"plain-text category label {label} remains available")

    print("Phase 2K.11.2 mobile creator navigation hotfix checks passed")


if __name__ == "__main__":
    run()
