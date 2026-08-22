from pathlib import Path

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    require('APP_RELEASE = "v43B Phase 2K.12"' in app, "release label is Phase 2K.11.3")
    require('options=["Daily Challenge", "Practice", "My Player"]' in app, "top selector is Daily / Practice / My Player")
    require('📲 Add to Home Screen' not in app and 'def render_install_mode(' not in app, "Add-to-Home-Screen feature is removed")
    require('def render_my_player_mode()' in app, "My Player has a dedicated top-level page")
    require('if st.session_state.get("avatar_editor_open"):' in app[app.index('def render_my_player_mode'):], "My Player owns avatar editing")
    daily = app[app.index('def render_daily_mode():'):app.index('def render_my_player_mode():', app.index('def render_daily_mode():'))]
    require('render_player_status_bar()' not in daily and 'render_player_avatar_creator()' not in daily, "Daily no longer carries separate My Player/sign-out controls")
    creator = app[app.index('def render_player_avatar_creator():'):app.index('def render_player_identity_gate')]
    require('avatar_option_tile_html' not in creator, "creator does not stack giant option cards")
    require('selected_category = st.pills(' in creator and 'chosen_value = st.pills(' in creator, "creator uses compact wrapping text controls")
    require('st.session_state.app_mode = "My Player"' in app[app.index('def _activate_player'):app.index('def _sign_out_player')], "new players land in My Player creator")
    require('st.session_state.app_mode not in {"Daily Challenge", "Practice", "My Player"}' in app, "legacy mode session values are handled safely")
    print("Phase 2K.11.3 UI polish checks passed")


if __name__ == "__main__":
    run()
