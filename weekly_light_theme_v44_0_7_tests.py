"""Visual-only v44.0.7 regression checks. No network, Streamlit session, or database."""
import hashlib
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent
APP = (ROOT/'app.py').read_text()
WEEKLY = (ROOT/'weekly_ui.py').read_text()
THEME = tomllib.loads((ROOT/'.streamlit/config.toml').read_text())['theme']


def _luminance(hex_color):
    value = [int(hex_color[i:i+2], 16)/255.0 for i in (1,3,5)]
    linear = [v/12.92 if v <= .04045 else ((v + .055)/1.055)**2.4 for v in value]
    return sum(a*b for a,b in zip(linear,(.2126,.7152,.0722)))


def _contrast(one,two):
    a,b=sorted((_luminance(one),_luminance(two)),reverse=True)
    return (a+.05)/(b+.05)


def test_uses_a_single_light_theme_for_browser_and_streamlit_dark_override():
    assert THEME['base']=='light'
    for k in ('primaryColor','backgroundColor','secondaryBackgroundColor','textColor'):
        assert THEME['dark'][k]==THEME[k]
    assert THEME['backgroundColor']=='#FFFFFF'
    assert THEME['textColor']=='#142344'
    assert THEME['primaryColor']=='#B82E42'
    assert 'color-scheme: light !important' in APP
    assert '[data-testid="stAppViewContainer"]' in APP
    assert '[data-testid="stMain"]' in APP


def test_scorecard_filled_unfilled_zero_and_positive_text_contrast():
    assert _contrast('#142344','#f3f5f8')>=7
    assert _contrast('#536078','#FFFFFF')>=4.5
    assert _contrast('#16733c','#FFFFFF')>=4.5
    assert _contrast('#142344','#FFFFFF')>=7
    assert '-webkit-text-fill-color:#142344!important' in WEEKLY
    assert '-webkit-text-fill-color:#16733c!important' in WEEKLY
    assert '-webkit-text-fill-color:#536078!important' in WEEKLY
    assert 'button:disabled *' in WEEKLY
    assert 'opacity:1!important;filter:none!important' in WEEKLY
    assert 'weekly_score_tile_' in WEEKLY
    assert 'background:#fff2f4!important' in WEEKLY


def test_overlays_not_forced_white_and_daily_dice_style_preserved():
    assert 'Do not override the deliberately dark navy results/podium components.' in APP
    assert 'color-scheme: light !important' in APP
    assert 'div[data-testid="stButtonGroup"] button' in APP
    assert '_available_gain' in WEEKLY and '_available_zero' in WEEKLY
    assert 'weekly-final-roll-banner' in WEEKLY
    assert 'weekly-die-bounce' in WEEKLY
    assert 'WEEKLY_DAILY_LABELS' in WEEKLY
    assert 'APP_PUBLIC_VERSION = "Yahtzee Coach · v44.0.8"' in APP


def test_core_scoring_and_saved_action_guards_still_present():
    # The old whole-file SHA contract applied to a visual-only v44.0.7 release.
    # v44.0.8 changes presentation and confirmed-save feedback, not the engine.
    assert 'st.button(label, key=f"{prefix}_category_{category}"' in WEEKLY
    assert 'on_click=_choose_category' in WEEKLY
    assert 'on_click=_queue' in WEEKLY
    assert 'action_request(game, {"kind":"score", "category":category})' in WEEKLY
    assert 'store.act(request["game_id"], expected_revision=request["expected_revision"]' in WEEKLY
    assert 'request_id=request["request_id"]' in WEEKLY
    assert 'st.session_state.pop(key, None)' in WEEKLY
    assert 'Retry save' in WEEKLY
    assert 'APP_PUBLIC_VERSION = "Yahtzee Coach · v44.0.8"' in APP


def test_theme_contains_no_secrets_or_db_settings():
    theme=(ROOT/'.streamlit/config.toml').read_text().lower()
    assert '[theme]' in theme
    for secret in ('service_role','apikey','api_key','password','database_url','supabase','[server]','[browser]'):
        assert secret not in theme
