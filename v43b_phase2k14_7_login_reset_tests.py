"""Persistent-token lifecycle, admin authorization, RPC boundary and rendered reset flow."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast
import copy

from daily_store import InMemoryDailyStore, hash_pin, verify_pin, hash_device_token_secret
from supabase_daily_store import SupabaseDailyStore

ROOT=Path(__file__).resolve().parent

def main():
    clock=[datetime(2026,9,12,tzinfo=timezone.utc)]
    memory=InMemoryDailyStore(now_factory=lambda:clock[0])
    mike=memory.create_player('Mike','2468'); paul=memory.create_player('Paul','1357')
    token=memory.create_device_session(paul.player_id)
    clock[0]+=timedelta(days=365*40)
    assert memory.authenticate_device_session(token).player_id==paul.player_id
    sid,secret=token.split('.',1)
    assert memory.authenticate_device_session(sid+'.'+'x'*43) is None
    memory.revoke_device_session(token)
    assert memory.authenticate_device_session(token) is None
    timed=memory.create_device_session(paul.player_id,30)
    clock[0]+=timedelta(days=31)
    assert memory.authenticate_device_session(timed) is None

    class Query:
        def __init__(self, client, table): self.client=client; self.table=table; self.filters={}
        def select(self,*args): return self
        def eq(self,key,value): self.filters[key]=value; return self
        def limit(self,*args): return self
        def order(self,*args): return self
        def insert(self,payload): self.client.inserted=payload; self.inserted=True; return self
        def execute(self):
            if getattr(self,"inserted",False): return SimpleNamespace(data=[{"session_id":"new-device"}])
            rows=self.client.players if self.table=='players' else self.client.sessions
            return SimpleNamespace(data=[copy.copy(r) for r in rows if all(r.get(k)==v for k,v in self.filters.items())])
    class Client:
        def __init__(self):
            self.players=[dict(player_id=p.player_id,display_name=p.display_name,created_at=p.created_at.isoformat(),pin_hash=memory.players[p.player_id].pin_hash) for p in (mike,paul)]
            self.sessions=[dict(session_id='device',player_id=paul.player_id,token_hash=hash_device_token_secret('x'*43),expires_at=None,revoked_at=None)]
            self.calls=[]
        def table(self,name): return Query(self,name)
        def rpc(self,name,args):
            self.calls.append((name,args)); return SimpleNamespace(execute=lambda:SimpleNamespace(data=True))
    store=SupabaseDailyStore.__new__(SupabaseDailyStore);store.client=Client();store.admin_player_id=mike.player_id
    persistent=store.create_device_session(paul.player_id)
    assert persistent.startswith('new-device.') and store.client.inserted['expires_at'] is None
    assert persistent.split('.',1)[1] not in store.client.inserted.values()
    assert store.authenticate_device_session('device.'+'x'*43).player_id==paul.player_id
    assert store.authenticate_device_session('device.'+'y'*43) is None
    store.client.sessions[0]['revoked_at']='2026-09-12T00:00:00Z'
    assert store.authenticate_device_session('device.'+'x'*43) is None
    store.client.sessions[0]['revoked_at']=None
    for expiry in ['2001-01-01T00:00:00Z','malformed']:
        store.client.sessions[0]['expires_at']=expiry
        assert store.authenticate_device_session('device.'+'x'*43) is None
    for actor,pin in [(paul.player_id,'1357'),(mike.player_id,'bad'),(mike.player_id,'9999')]:
        try: store.admin_reset_pin(actor,pin,paul.player_id)
        except PermissionError: pass
        else: raise AssertionError('Unauthorized reset')
    assert not store.client.calls
    try:store.list_reset_players(paul.player_id)
    except PermissionError:pass
    else:raise AssertionError('Unauthorized listing')
    assert len(store.list_reset_players(mike.player_id))==2
    with patch('supabase_daily_store.secrets.randbelow',return_value=1234):
        new_pin=store.admin_reset_pin(mike.player_id,'2468',paul.player_id)
    assert new_pin=='001234'
    name,args=store.client.calls[-1]
    assert name=='yahtzee_admin_reset_pin' and args['target_id']==paul.player_id
    assert verify_pin(new_pin,args['new_pin_hash']) and not verify_pin('1357',args['new_pin_hash'])
    assert new_pin not in args.values() and '2468' not in args.values()
    store.admin_player_id=''
    try:store.admin_reset_pin(mike.player_id,'2468',paul.player_id)
    except PermissionError:pass
    else:raise AssertionError('Unconfigured admin')

    sql=(ROOT/'RUN_THIS_ONCE_IN_SUPABASE_Phase2K14_7.sql').read_text()
    for text in ['alter column expires_at drop not null','expires_at > now()', 'revoked_at is null', 'for update', 'security invoker', 'from public, anon, authenticated','to service_role']:
        assert text in sql,text
    app=(ROOT/'app.py').read_text()
    assert app.count('"Keep me logged in"')==2
    assert 'for 30 days' not in app and 'REMEMBER_DEVICE_DAYS = None' in app
    tree=ast.parse(app)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='render_pin_admin')
    source=ast.get_source_segment(app,fn)
    from streamlit.testing.v1 import AppTest
    harness='''import streamlit as st
from types import SimpleNamespace
st.session_state.setdefault('active_player_id','admin')
class Store:
    def list_reset_players(self,actor):
        return [SimpleNamespace(player_id='paul',display_name='Paul'),SimpleNamespace(player_id='jenny',display_name='Jenny')]
    def admin_reset_pin(self,actor,pin,target):
        if pin!='2468':raise PermissionError()
        st.session_state['last_reset']=target
        return '001234'
def load_daily_store():return Store()
'''+source+'\nrender_pin_admin()\n'
    at=AppTest.from_string(harness);at.secrets['YAHTZEE_ADMIN_PLAYER_ID']='admin';at.run()
    assert not at.exception and len(at.selectbox)==1 and 'last_reset' not in at.session_state
    at.text_input[0].input('bad');at.button[0].click().run()
    assert at.error and 'last_reset' not in at.session_state
    at.selectbox[0].select('jenny');at.text_input[0].input('2468');at.button[0].click().run()
    assert not at.exception and at.session_state['last_reset']=='jenny'
    assert at.code[0].value=='001234' and 'Jenny' in at.success[0].value
    at.run();assert len(at.code)==0
    at.session_state['active_player_id']='paul';at.run();assert len(at.selectbox)==0
    at.secrets['YAHTZEE_ADMIN_PLAYER_ID']='';at.run();assert len(at.selectbox)==0
    print('PASS persistent sessions, expiry compatibility, tamper/revocation, admin-only reset, current PIN, hashed RPC, migration guardrails and UI form flow')

if __name__=='__main__':main()
