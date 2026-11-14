"""v44.0.3: Offline Weekly playability and persistence tests, no production data.

Use an isolated Streamlit shim and the *real* game rules to exercise UI actions.
No Supabase, personal accounts, or official games are ever contacted.
"""
import ast
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys
from types import ModuleType
from uuid import uuid4
from zoneinfo import ZoneInfo

# No Streamlit dependency required for the pure offline checks.
shim = ModuleType('streamlit')
shim.fragment = lambda f: f
sys.modules.setdefault('streamlit', shim)

import weekly_ui as ui
from weekly_game import generate_schedule, new_game, apply_action, scoring_options, CATEGORIES
from weekly_store import WeeklyStoreError

class FakeSt:
    def __init__(self):
        self.session_state={}
        self.buttons=[]
        self.markdowns=[]
        self.captions=[]
        self.pills_count=0
        self.warnings=[]
        self.dashboard_called=0
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def container(self,*,key):return self
    def columns(self,spec,**kwargs):return [self]*(spec if isinstance(spec,int) else len(spec))
    def markdown(self,txt,**kwargs):self.markdowns.append(txt)
    def progress(self,*args,**kwargs):pass
    def caption(self,txt):self.captions.append(txt)
    def button(self,label,**kwargs):self.buttons.append((label,kwargs));return False
    def pills(self,label,*,options,key,**kwargs):
        self.pills_count+=1
        return self.session_state.get(key,[])
    def warning(self,txt):self.warnings.append(txt)
    def rerun(self):pass

class SavedStore:
    def __init__(self):
        self.schedule=generate_schedule('2026-11-09',secret=b'0'*32)
        self.now=datetime(2026,11,14,12,tzinfo=ZoneInfo('America/New_York'))
        self.state=new_game(self.schedule,now=self.now)
        self.game_id=str(uuid4())
        self.calls=[]
        self.fail_call_number=None
        self.receipts={}
    def public(self):
        return {'game_id':self.game_id,'week_id':'2026-11-09','mode':'official',
                'state':self.state.to_dict(),'revision':self.state.revision,
                'total_score':self.state.totals['total'], 'started_at':'2026-11-14T12:00:00-05:00',
                'updated_at':'2026-11-14T12:00:00-05:00','completed_at':None}
    def act(self,game_id,*,expected_revision,request_id,action):
        self.calls.append((request_id,expected_revision,action))
        if self.fail_call_number==len(self.calls):raise WeeklyStoreError('simulated failure')
        if request_id in self.receipts:return self.receipts[request_id]
        self.state=apply_action(self.state,self.schedule,action,expected_revision=expected_revision,now=self.now)
        game=self.public()
        self.receipts[request_id]=game
        return game


def setup():
    fake=FakeSt(); ui.st=fake
    store=SavedStore(); scope='weekly_test'
    game=store.public()
    return fake,store,scope,game


def test_exact_daily_pill_visual_renderer_with_position_unique_duplicate_faces():
    app=Path(__file__).with_name('app.py').read_text()
    assert 'selected_options = st.pills(' in app
    src=Path(ui.__file__).read_text()
    assert 'chosen = st.pills(' in src
    assert 'selection_mode="multi"' in src
    values=[2,2,3,2,5]
    choices=ui._dice_pill_options(values)
    assert len(set(choices))==5
    assert all(choices[i].replace('\u200b','')==ui.FACES[values[i]-1] for i in range(5))
    assert ui._selected_die_indices(values,[choices[1],choices[3]])==[1,3]


def test_first_roll_is_explicit_reveal_without_supabase_mutation():
    st,store,scope,game=setup()
    ui._play(game,scope)
    assert st.pills_count==0
    first=next((label,kwargs) for label,kwargs in st.buttons if 'Roll Dice · 1 of 3' in label)
    assert all('Confirm' not in label or kwargs.get('disabled') for label,kwargs in st.buttons)
    assert not store.calls
    first[1]['on_click'](*first[1]['args'])
    st.buttons.clear()
    ui._play(game,scope)
    assert st.pills_count==1
    assert any('Roll Dice · 2 of 3' in label for label,_ in st.buttons)
    assert not store.calls


def test_held_positions_stay_in_place_even_with_duplicate_faces():
    st,store,scope,game=setup()
    previous=[2,1,2,5,6]
    after={'game_id':game['game_id'],'state':{'rounds':[], 'rolls':[{'dice':sorted(previous)},
                 {'dice':[2,2,3,4,5]}]}}
    result=ui._new_visual_roll(after,scope,previous,[2,3])
    assert result[2]==2 and result[3]==5
    assert Counter(result)==Counter([2,2,3,4,5])
    assert result[0] != 2 or result[1] != 1 or result[4] != 6  # rolled positions may change


def test_one_die_tap_produces_zero_database_actions_then_roll_saves_protected_chain():
    st,store,scope,game=setup()
    shown=ui._visual_dice(game,scope)
    options=ui._dice_pill_options(shown)
    pill_key='test_dice'; st.session_state[pill_key]=[options[2]]
    assert store.calls==[]
    ui._queue_roll(scope,game,shown,pill_key)
    pending=st.session_state[f'{scope}_pending']
    assert [r['action']['kind'] for r in pending['requests']]==['hold','reroll']
    assert [r['expected_revision'] for r in pending['requests']]==[0,1]
    assert ui._send_pending(store,scope)
    assert [x[2]['kind'] for x in store.calls]==['hold','reroll']
    result=store.public()
    saved=ui._visual_dice(result,scope)
    assert saved[2]==shown[2]
    assert Counter(saved)==Counter(result['state']['rolls'][-1]['dice'])
    assert st.session_state[f'{scope}_animate_roll'][2]==(0,1,3,4)
    assert st.session_state[f'{scope}_visual_held'][(game['game_id'],1,2)]==[2]


def test_unchanged_holds_require_only_one_authenticated_reroll():
    st,store,scope,game=setup()
    shown=ui._visual_dice(game,scope)
    pill_key='pills';st.session_state[pill_key]=[]
    ui._queue_roll(scope,game,shown,pill_key)
    assert [r['action']['kind'] for r in st.session_state[f'{scope}_pending']['requests']]==['reroll']
    assert ui._send_pending(store,scope)
    assert len(store.calls)==1


def test_interrupted_roll_retries_second_step_without_repeating_first_commit():
    st,store,scope,game=setup()
    shown=ui._visual_dice(game,scope)
    pill_key='pills';st.session_state[pill_key]=[ui._dice_pill_options(shown)[0]]
    ui._queue_roll(scope,game,shown,pill_key)
    store.fail_call_number=2
    assert not ui._send_pending(store,scope)
    assert store.state.revision==1
    assert st.session_state[f'{scope}_pending']['step']==1
    assert 'save wasn\'t confirmed' in st.warnings[-1]
    store.fail_call_number=None
    assert ui._send_pending(store,scope)
    assert store.state.revision==2
    assert [x[2]['kind'] for x in store.calls]==['hold','reroll','reroll']
    assert store.calls[1][0]==store.calls[2][0]


def test_tappable_scorecard_does_not_save_until_confirmation():
    st,store,scope,game=setup()
    shown=ui._visual_dice(game,scope)
    ui._reveal_first_roll(scope,game)
    prefix=f'{scope}_{game["game_id"]}_{game["revision"]}'
    ui._scorecard_picker(game,scope,shown,True,prefix)
    category_buttons=[(label,k) for label,k in st.buttons if '_category_' in k.get('key','')]
    assert len(category_buttons)==13
    enabled=[(label,k) for label,k in category_buttons if not k['disabled']]
    assert enabled
    selected_label,params=enabled[0]
    params['on_click'](*params['args'])
    assert store.calls==[]
    st.buttons.clear()
    ui._scorecard_picker(game,scope,shown,True,prefix)
    confirm=next((label,k) for label,k in st.buttons if label.startswith('Confirm '))
    assert confirm[1].get('disabled', False) is False
    confirm[1]['on_click'](*confirm[1]['args'])
    assert store.calls==[]
    assert ui._send_pending(store,scope)
    assert store.state.revision==1
    assert len(store.state.rounds)==1


def test_saved_zero_and_joker_scoring_still_come_from_existing_engine():
    st,store,scope,game=setup()
    dice=ui._visual_dice(game,scope)
    options=scoring_options(dice,dict(zip(CATEGORIES,game['state']['scores'])))
    assert len(options)==13
    assert any(o.points==0 for o in options)
    assert 'def scoring_options' not in Path(ui.__file__).read_text()


def test_source_guards_performance_and_mobile_visibility():
    source=Path(ui.__file__).read_text()
    assert '@st.fragment\ndef render_weekly' in source
    assert 'history_key not in st.session_state' in source
    assert 'entry["data"]' in source
    assert 'st.session_state.get(f"{scope}_dashboard_cache")' in source
    assert 'position:fixed!important' in source
    assert 'weekly_scorecard_interactive' in source
    assert 'APP_PUBLIC_VERSION = "Yahtzee Coach · v44.0.5"' in Path(__file__).with_name('app.py').read_text()
