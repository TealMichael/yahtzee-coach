"""Query budgets, complete history, targeted invalidation and identical scoring facts."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, date, timedelta, timezone
from copy import deepcopy
import ast
import itertools

from daily_store import hash_device_token_secret
from supabase_daily_store import SupabaseDailyStore

ROOT=Path(__file__).resolve().parent

class Query:
    def __init__(self,client,table):
        self.client=client;self.table=table;self.filters=[];self.columns='*';self.start=0;self.end=None;self.sort=None;self.count=False
    def select(self,columns,*args,**kwargs): self.columns=columns;self.count=kwargs.get('count')=='exact';return self
    def eq(self,key,value):self.filters.append(lambda r:r.get(key)==value);return self
    def gt(self,key,value):self.filters.append(lambda r:r.get(key)>value);return self
    def in_(self,key,values):
        assert len(values)<=100 or self.table!='daily_challenges','Unbounded history URL'
        self.filters.append(lambda r:r.get(key) in values);return self
    def order(self,key,*args,**kwargs):self.sort=key;return self
    def range(self,start,end):self.start=start;self.end=end;return self
    def limit(self,n):self.end=n-1;return self
    def execute(self):
        self.client.calls.append((self.table,self.columns,self.start,self.end))
        rows=[deepcopy(r) for r in self.client.data[self.table] if all(f(r) for f in self.filters)]
        if self.sort:rows.sort(key=lambda r:r[self.sort])
        total=len(rows);n=self.client.cap if self.end is None else min(self.client.cap,self.end-self.start+1)
        rows=rows[self.start:self.start+n]
        if 'player:players(' in self.columns:
            for row in rows:row['player']=next((deepcopy(p) for p in self.client.data['players'] if p['player_id']==row['player_id']),None)
        if 'answers:daily_answers(' in self.columns:
            for row in rows:row['answers']=[deepcopy(a) for a in self.client.data['daily_answers'] if a['attempt_id']==row['attempt_id']]
        return SimpleNamespace(data=rows,count=total if self.count else None)
class Client:
    def __init__(self,data,cap=1000):self.data=data;self.cap=cap;self.calls=[]
    def table(self,name):return Query(self,name)

def store_for(data,cap=1000):
    store=SupabaseDailyStore.__new__(SupabaseDailyStore);store.client=Client(data,cap);store.admin_player_id='p0';return store

def main():
    stamp='2020-01-01T00:00:00+00:00'
    players=[dict(player_id=f'p{i}',display_name=f'Player {i}',created_at=stamp) for i in range(10)]
    token='s.'+'x'*43
    data=dict(players=players,player_sessions=[dict(session_id='s',player_id='p0',token_hash=hash_device_token_secret('x'*43),expires_at=None,revoked_at=None)],daily_attempts=[],daily_answers=[],daily_challenges=[],group_members=[dict(group_id='g',player_id=f'p{i}',joined_at=stamp) for i in range(10)],friend_groups=[dict(group_id='g',group_name='Friends',join_code='TEAL',created_by_player_id='p0',created_at=stamp)])
    store=store_for(data)
    assert store.authenticate_device_session(token).player_id=='p0' and len(store.client.calls)==1
    assert store.authenticate_device_session('s.'+'y'*43) is None
    data['player_sessions'][0]['revoked_at']=stamp
    assert store.authenticate_device_session(token) is None
    data['player_sessions'][0]['revoked_at']=None
    data['player_sessions'][0]['expires_at']=stamp
    assert store.authenticate_device_session(token) is None
    data['player_sessions'][0]['expires_at']=None
    attempt=dict(attempt_id='a',player_id='p0',challenge_id='c',started_at=stamp,completed_at=None,total_ev_loss=None,exact_count=None,worst_miss=None,best_exact_streak=None)
    data['daily_attempts']=[attempt]
    for q in (3,1,2):
        data['daily_answers'].append(dict(attempt_id='a',question_number=q,puzzle_id=str(q),chosen_hold=[5],optimal_hold=[5],points_lost=0,exact=True,solver_source='exact',submitted_at=stamp))
    store.client.calls.clear();resume=store.get_resume_state('p0','c')
    assert len(store.client.calls)==1 and [a.question_number for a in resume.answers]==[1,2,3] and resume.next_question_number==4
    data['daily_attempts'][0]['completed_at']=stamp
    assert store.get_resume_state('p0','c').next_question_number is None
    assert store.get_resume_state('missing','c') is None
    data['daily_attempts']=[];data['daily_answers']=[]
    today=date(2026,9,12)
    for day in range(120):
        when=today-timedelta(days=119-day);cid=f'c{day:04d}'
        data['daily_challenges'].append(dict(challenge_id=cid,challenge_date=when.isoformat()))
        for i in range(10):
            data['daily_attempts'].append(dict(attempt_id=f'a{day:04d}-{i}',player_id=f'p{i}',challenge_id=cid,completed_at=when.isoformat()+'T12:00:00+00:00',total_ev_loss=0 if i==1 and day%3==0 else i))
    for cap in (17,1000,10000):
        store=store_for(data,cap)
        totals=store.player_medal_totals('p0','g',today.isoformat())
        assert totals==dict(gold=120,silver=0,bronze=0,total=120),(cap,totals)
        assert store.player_medal_totals('p1','g',today.isoformat())==dict(gold=40,silver=80,bronze=0,total=120)
        assert store.player_medal_totals('p2','g',today.isoformat())==dict(gold=0,silver=0,bronze=120,total=120)
    data['daily_attempts']=[];data['daily_challenges']=[]
    for day in range(1201):
        when=today-timedelta(days=1200-day);cid=f'c{day:04d}'
        data['daily_challenges'].append(dict(challenge_id=cid,challenge_date=when.isoformat()))
        data['daily_attempts'].append(dict(attempt_id=f'a{day:04d}',player_id='p0',challenge_id=cid,completed_at=when.isoformat()+'T12:00:00+00:00'))
    store=store_for(data,100)
    assert store.current_participation_streak('p0',today.isoformat())==1201
    data['daily_attempts'][-2]['completed_at']=None
    assert store.current_participation_streak('p0',today.isoformat())==1

    source=(ROOT/'app.py').read_text();tree=ast.parse(source)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_clear_completed_daily_caches')
    class Cache:
        def __init__(self):self.calls=[]
        def clear(self,*args):self.calls.append(args)
    env={'st':SimpleNamespace(session_state=SimpleNamespace(active_player_id='p0',daily_set_id='c',daily_date_key='2026-09-12')),'_cached_player_groups':lambda _: [SimpleNamespace(group_id='g'),SimpleNamespace(group_id='h')]}
    caches=['_cached_group_daily_snapshot','_cached_group_leaderboard','_cached_group_question_stats','_cached_participation_streak','_cached_player_profile','_cached_player_medal_totals']
    env.update({name:Cache() for name in caches});exec(compile(ast.Module(body=[fn],type_ignores=[]),'cache-test','exec'),env)
    env['_clear_completed_daily_caches']()
    for name in caches[:3]:assert env[name].calls==[('g','c'),('h','c')]
    assert env[caches[3]].calls==[('p0','2026-09-12')]
    assert env[caches[4]].calls==env[caches[5]].calls==[]
    def failure(_):raise RuntimeError('network unavailable')
    env['_cached_player_groups']=failure;env['_clear_completed_daily_caches']()
    for name in caches[:3]:assert env[name].calls[-1]==()

    import exact_mode as e
    from hashlib import sha256
    calculation=next(n for n in ast.parse((ROOT/"exact_mode.py").read_text()).body if isinstance(n,ast.FunctionDef) and n.name=="_cached_evidence_category_result")
    assert sha256(ast.dump(ast.Module(body=calculation.body,type_ignores=[])).encode()).hexdigest()=='7782d148ffcad359666d15351d4ee2b3b58ca475b72e647a26f25d70a3d7a79d'
    for dice in itertools.combinations_with_replacement(range(1,7),5):
        for category in (*e.CATEGORIES,'best_straight'):
            assert e._evidence_category_result(list(dice),category)==e._cached_evidence_category_result.__wrapped__(dice,category)
    assert e._cached_evidence_category_result.cache_info().currsize<=4096
    assert 'member_snapshot=(active_group.group_id, members)' in source
    print('PASS one-read auth/resume; tamper, expiry, revocation; 1200 group attempts under three API caps; competition ties; 1201-day streak; scoped invalidation and network failure; all 3528 scoring facts identical')

if __name__=='__main__':main()
