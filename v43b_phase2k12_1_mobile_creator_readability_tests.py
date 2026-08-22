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

    require('APP_RELEASE = "v43B Phase 2K.12.2"' in app, "release label is Phase 2K.12.2")
    require('selected_category = st.selectbox(' in creator, "category names use a full-width readable select box")
    require('chosen_value = st.selectbox(' in creator, "avatar choices use a full-width readable select box")
    require('selected_category = st.pills(' not in creator, "creator no longer squeezes category labels into pills")
    require('chosen_value = st.pills(' not in creator, "creator no longer squeezes choice labels into pills")
    require('format_func=lambda category: CATEGORY_LABELS[category].title()' in creator, "category names remain human readable")
    require('format_func=lambda value: choices[value]' in creator, "choice labels remain human readable")
    require('avatar_option_tile_html' not in creator, "fix does not bring back giant vertical option cards")
    require('st.session_state.avatar_draft = normalize_avatar_config(updated)' in creator, "choice changes still update the live avatar draft")
    print("Phase 2K.12.2 mobile creator readability checks passed")

if __name__ == "__main__":
    run()
