"""v44.0.4 focused no-network, no-production Weekly/mobile regression checks."""
from pathlib import Path

from weekly_game_flow_ui_tests import setup
import weekly_ui as ui

APP = Path(__file__).with_name('app.py').read_text()
SOURCE = Path(ui.__file__).read_text()


def _buttons(st):
    return [label for label, _ in st.buttons]


def test_scorecard_confirmation_is_near_selected_tile_row():
    st, store, scope, game = setup()
    dice = ui._visual_dice(game, scope)
    ui._reveal_first_roll(scope, game)
    prefix = f"{scope}_{game['game_id']}_{game['revision']}"
    ui._scorecard_picker(game, scope, dice, True, prefix)
    assert not any(label.startswith('Confirm ') for label in _buttons(st))
    category = next(o for o in st.buttons if not o[1].get('disabled',False) and '_category_' in o[1].get('key',''))
    category[1]['on_click'](*category[1]['args'])
    st.buttons.clear()
    ui._scorecard_picker(game, scope, dice, True, prefix)
    buttons = _buttons(st)
    selected_index = buttons.index(category[0])
    confirm_index = next(i for i,label in enumerate(buttons) if label.startswith('Confirm '))
    assert selected_index < confirm_index <= selected_index + 3, 'Confirm must follow the selected three-tile Upper row'
    assert not store.calls, 'Selecting or viewing a score does not make Supabase calls'


def test_confirm_still_uses_protected_action_and_returns_to_dice():
    st, store, scope, game = setup()
    dice=ui._visual_dice(game,scope)
    ui._reveal_first_roll(scope,game)
    prefix=f"{scope}_{game['game_id']}_{game['revision']}"
    ui._scorecard_picker(game,scope,dice,True,prefix)
    category = next(o for o in st.buttons if not o[1].get('disabled',False) and '_category_' in o[1].get('key',''))
    category[1]['on_click'](*category[1]['args'])
    st.buttons.clear()
    ui._scorecard_picker(game,scope,dice,True,prefix)
    confirm = next(o for o in st.buttons if o[0].startswith('Confirm '))
    confirm[1]['on_click'](*confirm[1]['args'])
    assert store.calls == []
    assert ui._send_pending(store,scope)
    assert len(store.state.rounds)==1
    assert len(store.calls)==1 and store.calls[0][2]['kind']=='score'
    assert st.session_state[f'{scope}_scroll_after_score'] is True


def test_mobile_summary_only_after_dice_leave_view():
    assert "bar.classList.toggle('yc-mini-active', mobile && edge < 120)" in SOURCE
    assert "position:fixed!important" in SOURCE
    assert '.st-key-weekly_mobile_summary.yc-mini-active{display:block!important}' in SOURCE
    assert "scrollIntoView({behavior:'smooth', block:'start'})" in SOURCE
    assert 'weekly-play-head' in SOURCE


def test_compact_score_rows_keep_all_thirteen_and_touch_area():
    st,store,scope,game=setup()
    dice=ui._visual_dice(game,scope)
    ui._scorecard_picker(game,scope,dice,False,'test')
    rows=[x for x in st.buttons if '_category_' in x[1].get('key','')]
    assert len(rows)==13
    assert 'min-height:2.65rem!important' in SOURCE
    assert 'weekly-score-row-value' in SOURCE
    assert 'weekly-score-section-heading' in SOURCE


def test_player_instructions_short_and_saved_game_untouched():
    assert 'This reveals your already-saved first roll.' not in SOURCE
    assert 'Dice selections update locally.' not in SOURCE
    assert 'Tap Roll Dice to start.' in SOURCE
    assert '"kind":"score"' in SOURCE
    assert '"kind":"reroll"' in SOURCE
    assert 'def _new_visual_roll' in SOURCE


def test_mobile_header_and_yesterday_recap_preserved():
    assert 'APP_PUBLIC_VERSION = "Yahtzee Coach · v44.0.5"' in APP
    assert 'if mode == "Home":' in APP
    assert 'home_nav = None' in APP
    assert 'st.button("Practice", key="practice_nav"' in APP
    assert 'st.button("My Player", key="player_nav"' in APP
    assert 'personal_medal_moment_html(' in APP
    assert 'picture = picture.replace("class=\'moment ", "class=\'moment skip-now ", 1)' in APP
    assert 'components.html(picture, height=560, scrolling=False)' in APP
    assert 'render_yesterday_final_standings_if_needed' in APP
    assert '_home_yesterday_results()' in APP
    assert 'New Daily at midnight Eastern.' in APP


def test_weekly_header_compact_preserves_week_picker():
    assert 'weekly-page-title' in SOURCE
    assert 'st.selectbox("Challenge week"' in SOURCE
    assert 'label_visibility="collapsed"' in SOURCE
    assert 'No coaching during your official game' in SOURCE
