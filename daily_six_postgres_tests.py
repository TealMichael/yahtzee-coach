"""Real local SQL + production SupabaseDailyStore tests; no live credentials.

PgDailyClient translates the existing table transport to parameterized local
SQL. Production store logic, constraints, triggers and migrations are unedited.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from daily_challenge import daily_challenges, challenge_set_id, registered_daily_challenges
from daily_store import DailyStoreError, AttemptAlreadyComplete, ChallengeMismatch
from supabase_daily_store import SupabaseDailyStore
from weekly_postgres_tests import IsolatedPostgres

ROOT = Path(__file__).resolve().parent


class PgQuery:
    def __init__(self, client, table):
        self.client, self.table_name = client, table
        self.filters, self.params = [], []
        self.columns, self.payload, self.operation = '*', None, 'select'
        self.sort, self.cap, self.offset = None, 1000, 0
    def select(self, columns='*', **kwargs): self.columns=columns; return self
    def eq(self, key, value):
        self.filters.append(sql.SQL('{} = %s').format(sql.Identifier(key))); self.params.append(value); return self
    def gt(self, key, value):
        self.filters.append(sql.SQL('{} > %s').format(sql.Identifier(key))); self.params.append(value); return self
    def in_(self, key, values):
        self.filters.append(sql.SQL('{}::text = any(%s)').format(sql.Identifier(key))); self.params.append([str(v) for v in values]); return self
    def order(self, key, desc=False): self.sort=sql.Identifier(key)+sql.SQL(' desc' if desc else ' asc'); return self
    def limit(self, n): self.cap=n; return self
    def range(self, start, end): self.offset=start; self.cap=end-start+1; return self
    def insert(self, payload): self.operation='insert'; self.payload=payload; return self
    def update(self, payload): self.operation='update'; self.payload=payload; return self
    def execute(self):
        table=sql.Identifier('public', self.table_name)
        where=sql.SQL(' where ')+sql.SQL(' and ').join(self.filters) if self.filters else sql.SQL('')
        params=list(self.params)
        if self.operation=='select':
            q=sql.SQL('select * from {}').format(table)+where
            if self.sort: q+=sql.SQL(' order by ')+self.sort
            q+=sql.SQL(' limit %s offset %s'); params.extend([self.cap,self.offset])
        else:
            keys=list(self.payload)
            values=[Jsonb(v) if isinstance(v,(list,dict)) else v for v in self.payload.values()]
            if self.operation=='insert':
                q=sql.SQL('insert into {} ({}) values ({}) returning *').format(table,
                    sql.SQL(',').join(map(sql.Identifier,keys)),sql.SQL(',').join(sql.Placeholder() for _ in keys))
                params=values
            else:
                q=sql.SQL('update {} set ').format(table)+sql.SQL(',').join(sql.Identifier(k)+sql.SQL('=%s') for k in keys)+where+sql.SQL(' returning *')
                params=values+params
        with psycopg.connect(self.client.uri, autocommit=True) as conn:
            conn.execute('set role service_role')
            # All result types match JSON responses from PostgREST.
            if self.operation=='select':
                rows=[r[0] for r in conn.execute(sql.SQL('select row_to_json(t) from (')+q+sql.SQL(') t'),params)]
            else:
                rows=[r[0] for r in conn.execute(sql.SQL('with t as (')+q+sql.SQL(') select row_to_json(t) from t'),params)]
        for row in rows:
            if 'answers:daily_answers(' in self.columns:
                row['answers']=PgQuery(self.client,'daily_answers').eq('attempt_id',row['attempt_id']).execute().data
            if 'player:players(' in self.columns:
                players=PgQuery(self.client,'players').eq('player_id',row['player_id']).execute().data
                row['player']=players[0] if players else None
        return SimpleNamespace(data=rows,count=len(rows))


class PgDailyClient:
    def __init__(self, uri): self.uri=uri
    def table(self, name): return PgQuery(self,name)
    def rpc(self, name, params):
        if name=='yc_weekly_rpc':
            from weekly_postgres_tests import PgClient
            return PgClient(self.uri).rpc(name,params)
        assert name=='yc_daily_format'
        def execute():
            with psycopg.connect(self.uri,autocommit=True) as conn:
                conn.execute('set role service_role')
                result=conn.execute('select public.yc_daily_format(%s::date)',(params['p_day'],)).fetchone()[0]
            return SimpleNamespace(data=result)
        return SimpleNamespace(execute=execute)


class DailySixPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='yc-daily-six-');cls.addClassCleanup(cls.temp.cleanup)
        cls.pg=IsolatedPostgres(cls.temp.name);cls.addClassCleanup(cls.pg.cleanup)
        cls.uri=cls.pg.uri
        cls.admin=psycopg.connect(cls.uri,autocommit=True);cls.addClassCleanup(cls.admin.close)
        cls.admin.execute('create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls')
        cls.admin.execute((ROOT/'v43b_schema.sql').read_text().replace('create extension if not exists pgcrypto;',''))
        cls.admin.execute((ROOT/'RUN_THIS_ONCE_IN_SUPABASE_Phase2K14_7.sql').read_text())
        cls.admin.execute('grant all on all tables in schema public to service_role')
        cls.migration=(ROOT/'v43b_daily_six_v1_migration.sql').read_text()
        cls.admin.execute((ROOT/'RUN_THIS_ONCE_IN_SUPABASE_v44_0.sql').read_text())
        cls.today=cls.admin.execute("select (clock_timestamp() at time zone 'America/New_York')::date").fetchone()[0]

    def setUp(self):
        self.admin.execute('truncate public.players cascade; truncate public.daily_challenges cascade; update public.yc_daily_format_config set six_effective_date=null,activated_at=null')
        self.store=SupabaseDailyStore.__new__(SupabaseDailyStore)
        self.store.client=PgDailyClient(self.uri);self.store.admin_player_id=''
        self.alice=self.store.create_player('Alice','2468')
        self.bob=self.store.create_player('Bob','1357')
        self.group=self.store.create_group(self.alice.player_id,'Friends')
        self.store.join_group(self.bob.player_id,self.group.join_code)

    def challenge(self, day):
        key=str(day);puzzles=registered_daily_challenges(key,self.store)
        c=self.store.ensure_challenge(challenge_set_id(key,puzzles),key,puzzles[0]['daily_version'],[p['challenge_id'] for p in puzzles])
        return c

    def answer(self, attempt, challenge, n, loss=0):
        return self.store.save_answer(attempt.attempt_id,question_number=n,puzzle_id=challenge.puzzle_ids[n-1],chosen_hold=[2],optimal_hold=[2],points_lost=loss)

    def finish(self, challenge, player=None):
        a,_=self.store.get_or_create_attempt((player or self.alice).player_id,challenge.challenge_id)
        for n in range(1,len(challenge.puzzle_ids)+1): self.answer(a,challenge,n)
        return self.store.complete_attempt(a.attempt_id)

    def test_first_new_app_load_activates_next_midnight_once(self):
        self.assertIsNone(self.admin.execute('select six_effective_date from public.yc_daily_format_config').fetchone()[0])
        m=self.store.daily_format(str(self.today));self.assertEqual(m['question_count'],10)
        self.assertEqual(m['six_effective_date'],str(self.today+timedelta(days=1)))
        self.admin.execute(self.migration)
        self.assertEqual(self.store.daily_format(str(self.today)),m)
        self.assertEqual(self.store.daily_format(str(self.today+timedelta(days=1)))['question_count'],6)

    def test_old_code_can_register_ten_before_activation_but_not_after_cutover(self):
        day=self.today
        puzzles=daily_challenges(str(day))
        old=self.store.ensure_challenge(challenge_set_id(str(day),puzzles),str(day),puzzles[0]['daily_version'],[p['challenge_id'] for p in puzzles])
        self.store.daily_format(str(day))
        self.assertEqual(self.store.daily_format(str(day))['challenge_id'],old.challenge_id)
        day+=timedelta(days=1);puzzles=daily_challenges(str(day))
        with self.assertRaises(Exception):
            self.store.ensure_challenge(challenge_set_id(str(day),puzzles),str(day),puzzles[0]['daily_version'],[p['challenge_id'] for p in puzzles])

    def test_existing_future_ten_record_is_retained(self):
        day=self.today+timedelta(days=2);p=daily_challenges(str(day))
        c=self.store.ensure_challenge(challenge_set_id(str(day),p),str(day),p[0]['daily_version'],[x['challenge_id'] for x in p])
        self.assertEqual(self.store.daily_format(str(day))['question_count'],10)
        self.assertEqual(registered_daily_challenges(str(day),self.store),p)
        self.assertEqual(self.finish(c).exact_count,10)

    def test_old_ten_and_new_six_resume_complete_review_medals_streak(self):
        for day,count in [(self.today,10),(self.today+timedelta(days=1),6)]:
            c=self.challenge(day);self.assertEqual(len(c.puzzle_ids),count)
            a,created=self.store.get_or_create_attempt(self.alice.player_id,c.challenge_id);self.assertTrue(created)
            for n in range(1,count+1):
                self.answer(a,c,n)
                resumed=self.store.get_resume_state(self.alice.player_id,c.challenge_id)
                self.assertEqual(len(resumed.answers),n)
            self.store.revise_answer(a.attempt_id,question_number=count,puzzle_id=c.puzzle_ids[-1],chosen_hold=[3],optimal_hold=[2],points_lost=.5)
            result=self.store.complete_attempt(a.attempt_id);self.assertEqual(result.exact_count,count-1)
            self.assertEqual(result.total_ev_loss,.5)
            self.assertEqual(self.store.complete_attempt(a.attempt_id),result)
            with self.assertRaises(AttemptAlreadyComplete):
                self.store.revise_answer(a.attempt_id,question_number=1,puzzle_id=c.puzzle_ids[0],chosen_hold=[],optimal_hold=[2],points_lost=1)
            with self.assertRaises(DailyStoreError):
                self.store.group_player_daily_review(self.group.group_id,c.challenge_id,self.bob.player_id,self.alice.player_id)
            self.finish(c,self.bob)
            review=self.store.group_player_daily_review(self.group.group_id,c.challenge_id,self.bob.player_id,self.alice.player_id)
            self.assertEqual(len(review['answers']),count)
            self.assertEqual(len(self.store.group_question_stats(self.group.group_id,c.challenge_id)),count)
            snapshot=self.store.group_daily_snapshot(self.group.group_id,c.challenge_id)
            self.assertEqual(len(snapshot['question_stats']),count)
            self.assertEqual(snapshot['leaderboard'][0]['player_id'],self.bob.player_id)
        self.assertEqual(self.store.current_participation_streak(self.alice.player_id,str(self.today+timedelta(days=1))),2)
        self.assertEqual(self.store.player_medal_totals(self.bob.player_id,self.group.group_id,str(self.today+timedelta(days=1)))['gold'],2)

    def test_seventh_answer_and_early_completion_refused(self):
        c=self.challenge(self.today+timedelta(days=1));a,_=self.store.get_or_create_attempt(self.alice.player_id,c.challenge_id)
        for n in range(1,6): self.answer(a,c,n)
        with self.assertRaises(DailyStoreError):self.store.complete_attempt(a.attempt_id)
        with self.assertRaises(psycopg.Error):
            self.admin.execute('update daily_attempts set completed_at=now(),total_ev_loss=0,exact_count=5,worst_miss=0,best_exact_streak=5 where attempt_id=%s',(a.attempt_id,))
        self.answer(a,c,6)
        with self.assertRaises(ChallengeMismatch):
            self.store.save_answer(a.attempt_id,question_number=7,puzzle_id='invented',chosen_hold=[],optimal_hold=[],points_lost=0)
        self.assertEqual(self.store.complete_attempt(a.attempt_id).exact_count,6)

    def test_completed_summary_and_challenge_immutable(self):
        c=self.challenge(self.today+timedelta(days=1));a=self.finish(c)
        for query,args in [
            ('update daily_attempts set exact_count=0 where attempt_id=%s',(a.attempt_id,)),
            ('update daily_challenges set challenge_version=%s where challenge_id=%s',('changed',c.challenge_id)),
            ('delete from daily_answers where attempt_id=%s',(a.attempt_id,))]:
            with self.assertRaises(psycopg.Error):self.admin.execute(query,args)

    def test_migration_rerun_preserves_mixed_history_and_activation(self):
        old=self.challenge(self.today);new=self.challenge(self.today+timedelta(days=1));self.finish(old);self.finish(new)
        before=self.admin.execute('select row_to_json(t) from daily_attempts t order by challenge_id').fetchall()
        config=self.admin.execute('select * from yc_daily_format_config').fetchall()
        self.admin.execute(self.migration)
        self.assertEqual(self.admin.execute('select row_to_json(t) from daily_attempts t order by challenge_id').fetchall(),before)
        self.assertEqual(self.admin.execute('select * from yc_daily_format_config').fetchall(),config)

    def test_simultaneous_format_requests_have_one_boundary(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(lambda _:self.store.daily_format(str(self.today+timedelta(days=1))),range(12)))
        self.assertTrue(all(r==results[0] for r in results));self.assertEqual(results[0]['question_count'],6)

    def test_simultaneous_challenge_registration_converges(self):
        day=str(self.today+timedelta(days=1));puzzles=registered_daily_challenges(day,self.store)
        cid=challenge_set_id(day,puzzles)
        def register(_):
            return self.store.ensure_challenge(cid,day,puzzles[0]['daily_version'],[p['challenge_id'] for p in puzzles])
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(register,range(12)))
        self.assertEqual({r.challenge_id for r in results},{cid})
        self.assertEqual(self.admin.execute('select count(*) from daily_challenges').fetchone()[0],1)

    def test_browser_roles_cannot_read_or_change_daily_format(self):
        for role in ('anon','authenticated'):
            for query in ('select * from yc_daily_format_config','select yc_daily_format(current_date)',"update yc_daily_format_config set six_effective_date=current_date"):
                with psycopg.connect(self.uri,autocommit=True) as conn:
                    conn.execute(sql.SQL('set role {}').format(sql.Identifier(role)))
                    with self.assertRaises(psycopg.Error):conn.execute(query)


if __name__=='__main__': unittest.main(verbosity=2)
