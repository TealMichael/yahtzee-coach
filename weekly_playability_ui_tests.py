"""Regression checks for the always-visible v44 scorecard and v44.0.3 Daily-style dice.

Does not access production Supabase or use a real Weekly attempt.
"""
from pathlib import Path
from weekly_game_flow_ui_tests import setup
from weekly_game import CATEGORIES
import weekly_ui as ui

SOURCE=Path(ui.__file__).read_text()
APP=Path(__file__).with_name('app.py').read_text()


def test_live_scorecard_is_always_rendered_during_play():
    st,store,scope,game=setup()
    ui._play(game,scope)
    assert any('weekly-scorecard-heading' in line for line in st.markdowns)
    assert any('Upper section' in line for line in st.markdowns)
    assert any('Lower section' in line for line in st.markdowns)
    assert any('Upper bonus' in line for line in st.markdowns)
    assert len([x for x in st.buttons if '_category_' in x[1].get('key','')])==13
    assert 'with st.expander("Your scorecard"' not in SOURCE


def test_roll_animation_targets_only_unheld_physical_dice():
    css=ui._roll_animation_css([0,2,4])
    assert all(f'button:nth-child({n})' in css for n in (1,3,5))
    assert all(f'button:nth-child({n})' not in css for n in (2,4))
    assert 'weekly-face-shuffle' in css
    assert 'fetch(' not in css and 'request(' not in css


def test_scorecard_retains_zero_scores_as_filled():
    st,store,scope,game=setup()
    state=game['state'].copy()
    state['scores']=[0,0]+[None]*11
    ui._scorecard(state)
    html='\n'.join(st.markdowns)
    assert html.count('weekly-score-filled')==2
    assert html.count('weekly-score-open')==11
    assert '2/13 filled' in html
    assert '>0</td>' in html
    assert '0/63' in html


def test_mobile_sticky_summary_reduced_motion_and_version():
    assert 'position:fixed!important' in SOURCE
    assert 'prefers-reduced-motion:reduce' in SOURCE
    assert 'flex:0 0 100%!important' in SOURCE
    assert 'weekly_scorecard_interactive' in SOURCE
    assert 'APP_PUBLIC_VERSION = "Yahtzee Coach · v44.0.4"' in APP
