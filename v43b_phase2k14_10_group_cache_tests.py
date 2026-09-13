"""Reproduce stale-class serialization and verify the real cache boundary."""
import ast
from datetime import datetime, timezone
import importlib
from pathlib import Path
import pickle
from types import SimpleNamespace
import daily_store
import streamlit as st

ROOT=Path(__file__).parent


def run():
    old=daily_store.GroupRecord('g','Friends <&>','JOIN','p',datetime(2026,9,13,8,30,tzinfo=timezone.utc))
    importlib.reload(daily_store)
    try:
        pickle.dumps([old])
    except pickle.PicklingError:
        pass
    else:
        raise AssertionError('Stale class failure was not reproduced')
    @st.cache_data(show_spinner=False)
    def original_boundary():
        return [old]
    from streamlit.runtime.caching.cache_errors import UnserializableReturnValueError
    try:
        original_boundary()
    except UnserializableReturnValueError:
        pass
    else:
        raise AssertionError('Expected the screenshot serialization error')
    finally:
        original_boundary.clear()
    tree=ast.parse((ROOT/'app.py').read_text())
    names={'_cached_player_group_rows','_cached_player_groups','_clear_social_caches','_real_group_context'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    calls=[]
    def list_groups(player_id):
        calls.append(player_id)
        if player_id=='error':raise RuntimeError('database unavailable')
        return [] if player_id=='empty' else [old]
    env={'st':st,'datetime':datetime,'GroupRecord':daily_store.GroupRecord,
        'load_daily_store':lambda:SimpleNamespace(list_groups=list_groups)}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ROOT/'app.py'),'exec'),env)
    env['_cached_player_group_rows'].clear()
    first=env['_cached_player_groups']('p')
    second=env['_cached_player_groups']('p')
    assert calls==['p'] and first==second and first is not second
    assert type(first[0]) is daily_store.GroupRecord
    for field in ('group_id','group_name','join_code','created_by_player_id','created_at'):
        assert getattr(first[0],field)==getattr(old,field)
    rows=env['_cached_player_group_rows']('p')
    assert pickle.loads(pickle.dumps(rows))==rows
    rows[0]['group_name']='changed locally'
    assert env['_cached_player_groups']('p')[0].group_name=='Friends <&>'
    assert env['_cached_player_groups']('empty')==[]
    env['_cached_player_groups']('other')
    assert calls==['p','empty','other']
    for _ in range(2):
        try:env['_cached_player_groups']('error')
        except RuntimeError:pass
        else:raise AssertionError('Real database failure must not become empty success')
    assert calls.count('error')==2
    for name in ('_cached_group_members','_cached_group_leaderboard','_cached_group_question_stats',
        '_cached_group_daily_snapshot','_cached_group_player_daily_review','_cached_participation_streak',
        '_cached_player_profile','_cached_player_medal_totals'):
        env[name]=SimpleNamespace(clear=lambda:None)
    env['_clear_social_caches']();env['_cached_player_groups']('p')
    assert calls.count('p')==2
    env['_load_player_groups']=lambda:(_ for _ in ()).throw(AssertionError('duplicate group read'))
    env['_select_active_group']=lambda groups:groups[0] if groups else None
    assert env['_real_group_context'](groups=[])==(None,[],[],[])
    env['st']=SimpleNamespace(session_state=SimpleNamespace(daily_set_id='today',get=lambda key:'p'))
    env['_cached_group_daily_snapshot']=lambda *_:{'members':[{'player_id':'p'}],
        'leaderboard':[{'player_id':'p','rank':1}], 'question_stats':[{'question_number':1}]}
    group,members,board,stats=env['_real_group_context'](groups=first)
    assert group.group_id=='g' and board[0]['is_user'] and members and stats
    result=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='render_daily_results')
    assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_real_group_context'
        and any(k.arg=='groups' for k in n.keywords) for n in ast.walk(result))
    env['_cached_player_group_rows'].clear()
    print('PASS original Streamlit error reproduced; plain-data cache, object restoration, hits, isolation, invalidation, error retry and one group read verified')

if __name__=='__main__':run()
