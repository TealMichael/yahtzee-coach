"""v44.0.5 offline verification: phone two-tile hub, Daily-style Weekly grid, safety.

Do not use a live Supabase project or a player's real Weekly official game.
"""
from pathlib import Path
from collections import Counter

from weekly_game_flow_ui_tests import setup
from weekly_game import CATEGORIES, scoring_options
import weekly_ui as ui

APP = Path(__file__).with_name('app.py').read_text()
WEEKLY = Path(ui.__file__).read_text()


def test_mobile_home_is_force_two_equal_columns_not_native_phone_stack():
    assert 'display:flex!important;flex-direction:row!important;flex-wrap:nowrap!important;' in APP
    assert 'width:calc(50% - .24rem)!important' in APP
    assert '.yc-head-full{display:inline}.yc-head-mobile{display:none}' in APP
    assert "yc-head-mobile" in APP and "title.split()[0]" in APP
    assert 'yc-home' not in APP or 'yc_home_tiles' in APP


def test_home_actions_still_only_navigate_and_do_not_start_a_weekly_game():
    start = APP.index('def _home_tile(')
    end = APP.index('def render_challenge_hub(', start)
    body = APP[start:end]
    assert 'on_click=_set_app_mode' in body
    assert 'start_official(' not in body
    assert 'start_replay(' not in body
    assert 'st.button(' in body


def test_weekly_grid_uses_daily_short_codes_and_matching_mobile_shape():
    assert ui.WEEKLY_DAILY_LABELS == (
        '1s','2s','3s','4s','5s','6s','3K','4K','FH','SS','LS','YTZ','CH')
    assert 'count = 3 if section == "upper" else 4' in WEEKLY
    assert 'weekly_score_grid_upper' in WEEKLY or 'weekly_score_grid_{section}' in WEEKLY
    assert 'flex-wrap:nowrap!important' in WEEKLY
    assert 'min-height:3.2rem!important' in WEEKLY


def test_all_thirteen_categories_in_normal_daily_style_grid_without_roll():
    st, store, scope, game = setup()
    dice = ui._visual_dice(game, scope)
    ui._scorecard_picker(game, scope, dice, False, 'release')
    opts = [(label,kw) for label,kw in st.buttons if '_category_' in kw.get('key','')]
    assert len(opts)==13
    assert all(kw['disabled'] for label,kw in opts)
    assert all('OPEN' in label for label,kw in opts)
    assert not any(label.startswith('Confirm ') for label,kw in st.buttons)
    assert not store.calls


def test_saved_zero_is_rendered_as_a_filled_score_not_open():
    st, store, scope, game = setup()
    scores = dict(zip(CATEGORIES,game['state']['scores']))
    scores['ones'] = 0
    label, enabled, status = ui._scorecard_tile_label('ones',0,scores,{},False)
    assert '**0**' in label and 'OPEN' not in label
    assert not enabled and status == 'filled'


def test_revealed_legal_scores_previewed_but_selection_is_local():
    st, store, scope, game = setup()
    dice = ui._visual_dice(game, scope)
    ui._reveal_first_roll(scope, game)
    ui._scorecard_picker(game, scope, dice, True, 'release')
    buttons = [(label,kw) for label,kw in st.buttons if '_category_' in kw.get('key','')]
    assert len(buttons) == 13
    options = scoring_options(dice,dict(zip(CATEGORIES,game['state']['scores'])))
    assert len([kw for label,kw in buttons if not kw['disabled']]) == len(options)
    label,params = next((label,kw) for label,kw in buttons if not kw['disabled'])
    assert '**+' in label
    params['on_click'](*params['args'])
    assert not store.calls
    st.buttons.clear()
    ui._scorecard_picker(game, scope, dice, True, 'release')
    confirm = [(label,kw) for label,kw in st.buttons if label.startswith('Confirm ')]
    assert len(confirm) == 1
    assert not store.calls


def test_confirm_does_not_save_until_authoritative_pending_action():
    st, store, scope, game = setup()
    dice = ui._visual_dice(game, scope)
    ui._reveal_first_roll(scope, game)
    ui._scorecard_picker(game, scope, dice, True, 'release')
    label, params = next((label,kw) for label,kw in st.buttons
                         if '_category_' in kw.get('key','') and not kw['disabled'])
    params['on_click'](*params['args'])
    st.buttons.clear()
    ui._scorecard_picker(game, scope, dice, True, 'release')
    label,params = next((label,kw) for label,kw in st.buttons if label.startswith('Confirm '))
    params['on_click'](*params['args'])
    assert len(store.calls)==0
    assert ui._send_pending(store, scope)
    assert len(store.calls)==1 and store.calls[0][2]['kind']=='score'
    assert len(store.state.rounds)==1


def test_weekly_dice_and_hidden_stream_safeguards_are_untouched():
    assert 'chosen = st.pills(' in WEEKLY
    assert 'selected_positions = held_positions(' in WEEKLY
    assert '"kind":"reroll"' in WEEKLY
    assert '"kind":"score"' in WEEKLY
    assert 'def _visual_dice(' in WEEKLY
    assert 'future pools' not in WEEKLY.lower()
    assert 'from weekly_game import (' in WEEKLY


def test_release_label_and_no_new_supabase_migration():
    assert 'Yahtzee Coach · v44.0.5' in APP
    assert 'RUN_THIS_ONCE_IN_SUPABASE_v44_0_5' not in APP
