"""Focused v44.0.2 checks: saved-data dice animations and visible scorecards.

No Streamlit installation or live Supabase service is needed. These checks
execute the production rendering helpers using a minimal fake Streamlit host.
"""
from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

from weekly_game import (CATEGORIES, CATEGORY_LABELS, generate_schedule,
                         new_game, apply_action, score_totals, scoring_options)

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / 'weekly_ui.py').read_text()
APP = (ROOT / 'app.py').read_text()


class FakeSt:
    def __init__(self):
        self.session_state = {}
        self.markdowns = []
        self.buttons = []
        self.containers = []
        self.layouts = []
        self.expanders = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def container(self, *, key):
        self.containers.append(key)
        return self

    def columns(self, spec, **kwargs):
        self.layouts.append(spec)
        return [self] * (spec if isinstance(spec, int) else len(spec))

    def markdown(self, text, **kwargs):
        self.markdowns.append(text)

    def caption(self, text):
        pass

    def progress(self, value, **kwargs):
        pass

    def button(self, label, **kwargs):
        self.buttons.append((label, kwargs))
        return False

    def selectbox(self, label, **kwargs):
        return None

    def expander(self, label, **kwargs):
        self.expanders.append(label)
        return self


def ui_helpers(fake):
    needed = {'_scorecard', '_roll_animation_css', '_play', '_queue', 'action_request',
              'held_positions', '_send_pending'}
    tree = ast.parse(SOURCE)
    pieces = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in needed]
    assert len(pieces) == len(needed), 'missing expected Weekly function'
    scope = {'st':fake, 'Counter':Counter, 'CATEGORIES':CATEGORIES,
             'CATEGORY_LABELS':CATEGORY_LABELS, 'score_totals':score_totals,
             'scoring_options':scoring_options, 'FACES':('⚀','⚁','⚂','⚃','⚄','⚅'),
             'json': __import__('json'), 'uuid5':__import__('uuid').uuid5,
             'NAMESPACE_URL':__import__('uuid').NAMESPACE_URL,
             'WeeklyAuthRequired':type('WeeklyAuthRequired',(Exception,),{}),
             'StaleState':type('StaleState',(Exception,),{}),
             'GameExpired':type('GameExpired',(Exception,),{}),
             'GameComplete':type('GameComplete',(Exception,),{}),
             'WeeklyGameNotFound':type('WeeklyGameNotFound',(Exception,),{}),
             'InvalidAction':type('InvalidAction',(Exception,),{}),
             'WeeklyStoreError':type('WeeklyStoreError',(Exception,),{}),
             'WeeklyGameError':type('WeeklyGameError',(Exception,),{})}
    exec(compile(ast.Module(body=pieces, type_ignores=[]), 'weekly_ui_helpers', 'exec'),scope)
    return scope


def synthetic_game(*, reroll=False):
    now = datetime(2026,11,14,12,tzinfo=ZoneInfo('America/New_York'))
    sched = generate_schedule('2026-11-09', secret=b'weekly-ui-test-secret-only-not-production!')
    state = new_game(sched, now=now)
    if reroll:
        face = state.dice[0]
        state = apply_action(state,sched,{'kind':'hold','held':[face]},
                             expected_revision=state.revision,now=now)
        state = apply_action(state,sched,{'kind':'reroll'},
                             expected_revision=state.revision,now=now)
    return {'game_id':str(uuid4()), 'week_id':'2026-11-09',
            'revision':state.revision,'state':state.to_dict(),
            'total_score':state.totals['total']}


def test_live_scorecard_is_always_rendered_in_play_without_expander():
    st=FakeSt()
    h=ui_helpers(st)
    h['_play'](synthetic_game(), 'weekly_player')
    markup='\n'.join(st.markdowns)
    assert 'weekly-scorecard-panel' in markup
    assert 'Your saved weekly scores' in markup
    assert '0/13 filled' in markup
    assert not st.expanders
    assert st.containers.index('weekly_mobile_summary') < st.containers.index('weekly_play_layout')
    assert st.layouts[0] == [1.07,0.93]
    assert 5 in st.layouts
    assert 'Score this round' in [label for label,_ in st.buttons]
    assert 'Roll remaining dice' in [label for label,_ in st.buttons]


def test_roll_shuffles_only_unheld_physical_dice_and_consumes_ui_marker():
    st=FakeSt()
    h=ui_helpers(st)
    game=synthetic_game(reroll=True)
    scope='weekly_player'
    st.session_state[f'{scope}_animate_roll']=(game['game_id'],game['revision'])
    h['_play'](game,scope)
    css='\n'.join(st.markdowns)
    held_indices=set(h['held_positions'](
        game['state']['rolls'][-1]['dice'],game['state']['rolls'][-1]['held_before']))
    for i in range(5):
        selector=f':nth-child({i+1})'
        if i in held_indices:
            assert selector not in css
        else:
            assert selector in css
    assert 'weekly-face-shuffle' in css
    assert f'{scope}_animate_roll' not in st.session_state
    st.markdowns.clear()
    h['_play'](game,scope)
    assert 'weekly-face-shuffle' not in '\n'.join(st.markdowns)


def test_ui_does_not_request_new_dice_in_animation():
    st=FakeSt()
    h=ui_helpers(st)
    css=h['_roll_animation_css']([0,2,4])
    assert all(f':nth-child({i})' in css for i in (1,3,5))
    assert all(f':nth-child({i})' not in css for i in (2,4))
    assert '⚀' in css
    assert 'request' not in css.lower()
    assert 'fetch' not in css.lower()


def test_scorecard_displays_saved_zero_and_upper_bonus_progress():
    st=FakeSt()
    h=ui_helpers(st)
    game=synthetic_game()
    state=game['state']
    state['scores']=[0,0,None,None,None,None]+[None]*7
    h['_scorecard'](state)
    html='\n'.join(st.markdowns)
    assert html.count('weekly-score-filled') == 2
    assert html.count('weekly-score-open') == 11
    assert '0/63' in html
    assert '2/13 filled' in html
    assert '>0</td>' in html
    assert '—' in html


def test_successful_reroll_marks_only_ui_while_hold_does_not():
    st=FakeSt()
    h=ui_helpers(st)
    game=synthetic_game()
    scope='weekly_player'
    class SavedStore:
        def __init__(self):self.actions=[]
        def act(self, game_id, **kwargs):self.actions.append(kwargs)
    store=SavedStore()
    for kind, expected_marker in [('hold',False),('reroll',True)]:
        st.session_state[f'{scope}_pending']={
            'operation':'act','game_id':game['game_id'],'week_id':game['week_id'],
            'request_id':str(uuid4()),'expected_revision':3,
            'action':{'kind':kind, **({'held':[]} if kind=='hold' else {})}}
        assert h['_send_pending'](store,scope) is True
        assert (f'{scope}_animate_roll' in st.session_state)==expected_marker
    assert len(store.actions)==2
    assert all('request_id' in call for call in store.actions)


def test_mobile_sticky_summary_reduced_motion_and_release_version():
    assert 'position:sticky!important' in SOURCE
    assert 'prefers-reduced-motion:reduce' in SOURCE
    assert 'flex:0 0 100%!important' in SOURCE
    assert 'st.expander("Your scorecard"' not in SOURCE
    assert 'with st.expander("Official scorecard")' not in SOURCE
    assert 'APP_PUBLIC_VERSION = "Yahtzee Coach · v44.0.2"' in APP
