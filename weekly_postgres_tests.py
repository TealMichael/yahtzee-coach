"""Behavioral tests against an isolated real PostgreSQL database.

Development dependencies: pip install pgserver==0.1.4 'psycopg[binary]'
No production connection, data, credentials or Supabase account is used.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from uuid import uuid4

from daily_store import hash_device_token_secret
from weekly_game import (
    CATEGORIES, GameExpired, GameState, InvalidAction, StaleState,
    apply_action, current_week_id, generate_schedule, scoring_options,
)
from weekly_store import (
    SupabaseWeeklyStore, WeeklyAccessDenied, WeeklyActor, WeeklyAuthRequired,
    WeeklyGameNotFound, WeeklyReplayLocked, WeeklyStoreError,
)

try:
    import pgserver
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:
    pgserver = psycopg = None


class IsolatedPostgres:
    """Use pgserver's binaries over loopback TCP (no Unix sockets required)."""
    def __init__(self, root):
        self.root = Path(root)
        binaries = Path(pgserver.__file__).parent / "pginstall" / "bin"
        data = self.root / "data"
        subprocess.run([str(binaries / "initdb"), "-D", str(data), "--username=yc_test",
            "--auth=trust", "--no-locale", "--encoding=UTF8"], check=True, capture_output=True)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.uri = f"postgresql://yc_test@127.0.0.1:{port}/postgres"
        self.log = (self.root / "postgres.log").open("w")
        self.process = subprocess.Popen([str(binaries / "postgres"), "-D", str(data),
            "-h", "127.0.0.1", "-p", str(port), "-c", "unix_socket_directories=",
            "-c", "fsync=off", "-c", "max_connections=30"], stdout=self.log, stderr=subprocess.STDOUT)
        for _ in range(100):
            if self.process.poll() is not None:
                raise RuntimeError((self.root / "postgres.log").read_text())
            try:
                with psycopg.connect(self.uri, connect_timeout=1):
                    return
            except psycopg.OperationalError:
                time.sleep(0.05)
        self.cleanup()
        raise RuntimeError("Local test PostgreSQL did not start")

    def cleanup(self):
        self.process.terminate()
        self.process.wait(timeout=10)
        self.log.close()


class PgClient:
    """Tiny transport adapter; all auth, persistence and privacy run in SQL."""
    def __init__(self, uri, *, after_context=None):
        self.uri = uri
        self.after_context = after_context

    def rpc(self, name, params):
        if name != "yc_weekly_rpc":
            raise AssertionError(name)

        def execute():
            with psycopg.connect(self.uri, autocommit=True) as conn:
                conn.execute("set role service_role")
                row = conn.execute("select public.yc_weekly_rpc(%s::uuid,%s::text,%s::uuid,%s::text,%s::jsonb)", (
                    params["p_session_id"], params["p_token_hash"], params["p_player_id"],
                    params["p_operation"], Jsonb(params["p_payload"]),
                )).fetchone()
            if params["p_operation"] == "context" and self.after_context:
                self.after_context()
            return SimpleNamespace(data=row[0])
        return SimpleNamespace(execute=execute)


@unittest.skipUnless(pgserver and psycopg, "Install development dependencies for real PostgreSQL tests")
class WeeklyPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="yc-pg-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.pg = IsolatedPostgres(cls.temp.name)
        cls.addClassCleanup(cls.pg.cleanup)
        cls.uri = cls.pg.uri
        cls.admin = psycopg.connect(cls.uri, autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        cls.admin.execute("create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls")
        root = Path(__file__).resolve().parent
        # This binary distribution omits pgcrypto. PostgreSQL 16 has the only
        # used primitive (gen_random_uuid) built in; the migration is unedited.
        baseline = (root / "v43b_schema.sql").read_text().replace("create extension if not exists pgcrypto;", "")
        cls.admin.execute(baseline)
        cls.admin.execute((root / "RUN_THIS_ONCE_IN_SUPABASE_Phase2K14_7.sql").read_text())
        cls.migration = (root / "v43b_weekly_v1_migration.sql").read_text()
        cls.admin.execute(cls.migration)
        cls.wk = current_week_id(datetime.now(timezone.utc))

    def setUp(self):
        self.admin.execute("truncate public.players cascade")
        self.admin.execute("truncate public.yc_weekly_challenges cascade")
        self.alice, self.alice_store = self.player("Alice")
        self.bob, self.bob_store = self.player("Bob")
        self.cara, self.cara_store = self.player("Cara")
        self.group = str(uuid4())
        self.admin.execute("insert into public.friend_groups(group_id,group_name,join_code,created_by_player_id) values(%s,'Friends','WEEKLY',%s)", (self.group, self.alice.player_id))
        for actor in (self.alice, self.bob):
            self.admin.execute("insert into public.group_members(group_id,player_id) values(%s,%s)", (self.group, actor.player_id))

    def player(self, name):
        player_id, session_id, secret = str(uuid4()), str(uuid4()), str(uuid4()) + str(uuid4())
        self.admin.execute("insert into public.players(player_id,display_name,display_name_key,pin_hash) values(%s,%s,%s,'scrypt$test')", (player_id, name, name.lower()))
        self.admin.execute("insert into public.player_sessions(session_id,player_id,token_hash,expires_at) values(%s,%s,%s,null)", (session_id, player_id, hash_device_token_secret(secret)))
        actor = WeeklyActor.from_token(player_id, session_id + "." + secret)
        return actor, SupabaseWeeklyStore(PgClient(self.uri), actor)

    def start(self, store=None):
        return (store or self.alice_store).start_official(self.wk)

    def act(self, game, action, store=None, request_id=None):
        return (store or self.alice_store).act(game["game_id"], expected_revision=game["revision"],
            request_id=request_id or str(uuid4()), action=action)

    def finish(self, game, store=None, *, strategy="first", rounds=13):
        while game["completed_at"] is None and len(game["state"]["rounds"]) < rounds:
            state = game["state"]
            opts = scoring_options(state["rolls"][-1]["dice"], dict(zip(CATEGORIES, state["scores"])))
            choice = max(opts, key=lambda o: o.points) if strategy == "max" else opts[0]
            game = self.act(game, {"kind": "score", "category": choice.category}, store)
        return game

    def replay(self, store=None, **kwargs):
        store = store or self.alice_store
        prior = store.dashboard(self.wk)["replay"]
        return store.start_replay(self.wk, expected_replay_id=prior["game_id"] if prior else None, **kwargs)

    def raw(self, actor, operation, payload):
        return PgClient(self.uri).rpc("yc_weekly_rpc", {
            "p_session_id": actor.session_id, "p_token_hash": actor.token_hash,
            "p_player_id": actor.player_id, "p_operation": operation, "p_payload": payload,
        }).execute().data

    def test_migration_can_rerun_without_changing_games_or_schedules(self):
        game = self.start()
        before = self.admin.execute("select private_schedule from public.yc_weekly_challenges").fetchone()[0]
        self.admin.execute(self.migration)
        self.assertEqual(self.start(), game)
        self.assertEqual(self.admin.execute("select private_schedule from public.yc_weekly_challenges").fetchone()[0], before)

    def test_one_official_game_and_first_stored_schedule_wins(self):
        first = self.start()
        self.assertEqual(self.start(), first)
        other = self.start(self.bob_store)
        self.assertEqual(first["state"], other["state"])
        count = self.admin.execute("select count(*) from public.yc_weekly_games where player_id=%s", (self.alice.player_id,)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_concurrent_start_requests_converge(self):
        barrier = threading.Barrier(6)
        def start(_):
            barrier.wait()
            return SupabaseWeeklyStore(PgClient(self.uri), self.alice).start_official(self.wk)
        with ThreadPoolExecutor(max_workers=6) as pool:
            games = list(pool.map(start, range(6)))
        self.assertEqual(len({g["game_id"] for g in games}), 1)
        self.assertTrue(all(g["state"] == games[0]["state"] for g in games))

    def test_concurrent_players_share_one_schedule(self):
        barrier = threading.Barrier(2)
        def start(actor):
            barrier.wait()
            return SupabaseWeeklyStore(PgClient(self.uri), actor).start_official(self.wk)
        with ThreadPoolExecutor(max_workers=2) as pool:
            games = list(pool.map(start, (self.alice, self.bob)))
        self.assertEqual(games[0]["state"], games[1]["state"])
        self.assertEqual(self.admin.execute("select count(*) from public.yc_weekly_challenges").fetchone()[0], 1)

    def test_hold_and_reroll_restore_from_fresh_store(self):
        game = self.start()
        held = game["state"]["rolls"][0]["dice"][:2]
        game = self.act(game, {"kind": "hold", "held": held})
        fresh = SupabaseWeeklyStore(PgClient(self.uri), self.alice)
        self.assertEqual(fresh.dashboard(self.wk)["official"], game)
        game = self.act(game, {"kind": "reroll"}, fresh)
        self.assertEqual(len(game["state"]["rolls"]), 2)
        self.assertEqual(fresh.dashboard(self.wk)["official"], game)

    def test_immediate_retry_returns_same_saved_result(self):
        original = self.start()
        req = str(uuid4())
        after = self.act(original, {"kind": "reroll"}, request_id=req)
        repeated = self.act(original, {"kind": "reroll"}, request_id=req)
        self.assertEqual(repeated, after)
        with self.assertRaises(InvalidAction):
            self.act(original, {"kind": "hold", "held": []}, request_id=req)

    def test_older_retry_is_stale_and_never_executes_again(self):
        original = self.start()
        req = str(uuid4())
        after = self.act(original, {"kind": "reroll"}, request_id=req)
        later = self.act(after, {"kind": "reroll"})
        with self.assertRaises(StaleState):
            self.act(original, {"kind": "reroll"}, request_id=req)
        self.assertEqual(self.alice_store.dashboard(self.wk)["official"], later)

    def test_simultaneous_different_requests_commit_only_once(self):
        game = self.start()
        barrier = threading.Barrier(2)
        def submit(_):
            store = SupabaseWeeklyStore(PgClient(self.uri, after_context=barrier.wait), self.alice)
            try:
                return self.act(game, {"kind": "reroll"}, store)
            except StaleState:
                return "stale"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
        self.assertEqual(results.count("stale"), 1)
        self.assertEqual(self.alice_store.dashboard(self.wk)["official"]["revision"], 1)

    def test_simultaneous_identical_retry_commits_once(self):
        game = self.start()
        req, barrier = str(uuid4()), threading.Barrier(2)
        def submit(_):
            store = SupabaseWeeklyStore(PgClient(self.uri, after_context=barrier.wait), self.alice)
            return self.act(game, {"kind": "reroll"}, store, req)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["revision"], 1)

    def test_complete_and_retry_thirteenth_score(self):
        game = self.finish(self.start(), rounds=12)
        category = next(c for c, s in zip(CATEGORIES, game["state"]["scores"]) if s is None)
        req = str(uuid4())
        result = self.act(game, {"kind": "score", "category": category}, request_id=req)
        self.assertIsNotNone(result["completed_at"])
        self.assertEqual(self.act(game, {"kind": "score", "category": category}, request_id=req), result)
        self.assertEqual(self.start(), result)
        with self.assertRaises(psycopg.Error):
            self.admin.execute("update public.yc_weekly_games set total_score=0 where game_id=%s", (result["game_id"],))

    def test_foreign_game_id_cannot_be_read_or_changed(self):
        game = self.start(self.bob_store)
        with self.assertRaises(WeeklyGameNotFound):
            self.act(game, {"kind": "reroll"})
        with self.assertRaises(psycopg.Error):
            self.raw(self.alice, "context", {"game_id": game["game_id"]})

    def test_token_must_match_actor_and_be_live(self):
        wrong_actor = WeeklyActor(self.bob.player_id, self.alice.session_id, self.alice.token_hash)
        with self.assertRaises(WeeklyAuthRequired):
            SupabaseWeeklyStore(PgClient(self.uri), wrong_actor).dashboard(self.wk)
        wrong_hash = WeeklyActor(self.alice.player_id, self.alice.session_id, "0" * 64)
        with self.assertRaises(WeeklyAuthRequired):
            SupabaseWeeklyStore(PgClient(self.uri), wrong_hash).dashboard(self.wk)
        self.admin.execute("update public.player_sessions set revoked_at=clock_timestamp() where session_id=%s", (self.alice.session_id,))
        with self.assertRaises(WeeklyAuthRequired):
            self.alice_store.dashboard(self.wk)

    def test_expired_session_rejected_on_every_operation(self):
        game = self.start()
        self.admin.execute("update public.player_sessions set created_at=clock_timestamp()-interval '2 days', expires_at=clock_timestamp()-interval '1 day' where session_id=%s", (self.alice.session_id,))
        for call in (lambda: self.alice_store.history(), lambda: self.alice_store.standings(self.wk,self.group),
                     lambda: self.alice_store.dashboard(self.wk), lambda: self.act(game,{"kind":"reroll"}),
                     lambda: self.alice_store.start_replay(self.wk, expected_replay_id=None), lambda: self.start()):
            with self.assertRaises(WeeklyAuthRequired): call()

    def test_session_revoked_between_read_and_commit_blocks_write(self):
        game = self.start()
        def revoke():
            self.admin.execute("update public.player_sessions set revoked_at=clock_timestamp() where session_id=%s", (self.alice.session_id,))
        store = SupabaseWeeklyStore(PgClient(self.uri, after_context=revoke), self.alice)
        with self.assertRaises(WeeklyAuthRequired):
            self.act(game, {"kind":"reroll"}, store)
        self.assertEqual(self.admin.execute("select revision from public.yc_weekly_games where game_id=%s", (game["game_id"],)).fetchone()[0], 0)

    def test_cutoff_rechecked_at_commit(self):
        game = self.start()
        def close_week():
            # Test-owner fixture advances the stored cutoff after the read.
            # Production service/browser roles cannot alter challenge metadata.
            self.admin.execute("update public.yc_weekly_challenges set ends_at=clock_timestamp() where week_id=%s", (self.wk,))
        store = SupabaseWeeklyStore(PgClient(self.uri, after_context=close_week), self.alice)
        with self.assertRaises(GameExpired):
            self.act(game, {"kind":"reroll"}, store)
        self.assertEqual(self.alice_store.dashboard(self.wk)["official"], game)

    def test_friend_scores_hidden_until_viewer_completes(self):
        self.finish(self.start(self.bob_store), self.bob_store)
        board = self.alice_store.standings(self.wk, self.group)
        self.assertEqual(set(board), {"group_id","group_name","completed_friends","unlocked","standings"})
        self.assertEqual(board["completed_friends"], 1)
        self.assertFalse(board["unlocked"])
        self.assertEqual(board["standings"], [])
        self.assertNotIn(self.bob.player_id, json.dumps(board))
        game = self.start()
        self.assertEqual(self.alice_store.dashboard(self.wk)["groups"][0], board)
        self.finish(game)
        board = self.alice_store.standings(self.wk, self.group)
        self.assertTrue(board["unlocked"])
        self.assertEqual(len(board["standings"]), 2)
        self.assertEqual([r["rank"] for r in board["standings"]], [1,1])

    def test_membership_checked_again_after_removal(self):
        self.finish(self.start(self.bob_store), self.bob_store)
        self.finish(self.start())
        self.admin.execute("delete from public.group_members where group_id=%s and player_id=%s", (self.group, self.alice.player_id))
        with self.assertRaises(WeeklyAccessDenied):
            self.alice_store.standings(self.wk, self.group)
        self.assertEqual(self.alice_store.dashboard(self.wk)["groups"], [])
        with self.assertRaises(WeeklyAccessDenied):
            self.cara_store.standings(self.wk, self.group)

    def test_one_official_result_is_reused_across_groups(self):
        game = self.finish(self.start())
        other = str(uuid4())
        self.admin.execute("insert into public.friend_groups(group_id,group_name,join_code,created_by_player_id) values(%s,'Other','OTHER',%s)", (other, self.alice.player_id))
        self.admin.execute("insert into public.group_members(group_id,player_id) values(%s,%s)", (other,self.alice.player_id))
        boards = self.alice_store.dashboard(self.wk)["groups"]
        self.assertEqual(len(boards),2)
        self.assertTrue(all(b["standings"][0]["score"] == game["total_score"] for b in boards))
        self.assertEqual(self.admin.execute("select count(*) from public.yc_weekly_games where player_id=%s and mode='official'", (self.alice.player_id,)).fetchone()[0],1)

    def test_replays_locked_before_official_completion(self):
        with self.assertRaises(WeeklyReplayLocked):
            self.replay()
        self.start()
        with self.assertRaises(WeeklyReplayLocked):
            self.replay()

    def test_replays_bounded_and_cannot_change_official(self):
        official = self.finish(self.start())
        scores = []
        for strategy in ("first", "max", "first"):
            replay = self.replay()
            self.assertEqual(self.replay(), replay)
            self.assertEqual(replay["state"]["rolls"][0], official["state"]["rounds"][0]["rolls"][0])
            replay = self.finish(replay, strategy=strategy)
            scores.append(replay["total_score"])
        dashboard = self.alice_store.dashboard(self.wk)
        self.assertEqual(dashboard["official"],official)
        self.assertEqual(dashboard["replay_summary"]["completed_count"],3)
        self.assertEqual(dashboard["replay_summary"]["best_score"],max(scores))
        self.assertEqual(dashboard["replay_summary"]["latest_score"],scores[-1])
        self.assertEqual(self.admin.execute("select count(*) from public.yc_weekly_games where player_id=%s", (self.alice.player_id,)).fetchone()[0],2)
        self.assertEqual(self.admin.execute("select count(*) from public.yc_weekly_replay_summaries").fetchone()[0],1)

    def test_replay_completion_retry_does_not_increment_summary_twice(self):
        self.finish(self.start())
        replay = self.finish(self.replay(), rounds=12)
        category = next(c for c,v in zip(CATEGORIES,replay["state"]["scores"]) if v is None)
        req = str(uuid4())
        result = self.act(replay,{"kind":"score","category":category},request_id=req)
        self.assertEqual(self.act(replay,{"kind":"score","category":category},request_id=req),result)
        self.assertEqual(self.alice_store.dashboard(self.wk)["replay_summary"]["completed_count"],1)

    def test_anonymous_authenticated_and_service_table_reads_are_denied(self):
        self.start()
        for role in ("anon","authenticated","service_role"):
            for table in ("yc_weekly_challenges","yc_weekly_games","yc_weekly_replay_summaries"):
                with psycopg.connect(self.uri,autocommit=True) as conn:
                    conn.execute(f"set role {role}")
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        conn.execute(f"select * from public.{table}")

    def test_browser_roles_cannot_call_rpc_even_with_valid_token(self):
        for role in ("anon","authenticated"):
            with psycopg.connect(self.uri,autocommit=True) as conn:
                conn.execute(f"set role {role}")
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    conn.execute("select public.yc_weekly_rpc(%s::uuid,%s,%s::uuid,'dashboard',%s)",
                        (self.alice.session_id,self.alice.token_hash,self.alice.player_id,Jsonb({"week_id":self.wk})))

    def test_private_helpers_cannot_be_called_directly(self):
        with psycopg.connect(self.uri,autocommit=True) as conn:
            conn.execute("set role service_role")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("select public.yc_weekly_board(%s::uuid,%s::date,%s::uuid)", (self.alice.player_id,self.wk,self.group))

    def test_rpc_rejects_reclassification_of_official(self):
        game = self.start()
        context = self.raw(self.alice,"context",{"game_id":game["game_id"]})
        schedule = __import__('weekly_game').DiceSchedule.from_private_dict(context["schedule"])
        state = GameState.from_dict(game["state"],schedule)
        next_state = apply_action(state,schedule,{"kind":"reroll"},expected_revision=0,now=datetime.now(timezone.utc)).to_dict()
        next_state["mode"] = "practice"
        with self.assertRaises(psycopg.Error):
            self.raw(self.alice,"commit",{"game_id":game["game_id"],"request_id":str(uuid4()),
                "expected_revision":0,"action":{"kind":"reroll"},"next_state":next_state})
        self.assertEqual(self.alice_store.dashboard(self.wk)["official"],game)

    def test_delayed_replay_start_cannot_reset_newer_completed_replay(self):
        self.finish(self.start())
        req = str(uuid4())
        first = self.alice_store.start_replay(self.wk, expected_replay_id=None, request_id=req)
        self.assertEqual(self.alice_store.start_replay(self.wk, expected_replay_id=None, request_id=req), first)
        self.finish(first)
        second = self.finish(self.replay())
        with self.assertRaises(StaleState):
            self.alice_store.start_replay(self.wk, expected_replay_id=None, request_id=req)
        self.assertEqual(self.alice_store.dashboard(self.wk)["replay"], second)

    def test_hold_values_are_canonical_and_retry_order_independent(self):
        game = self.start()
        held = game["state"]["rolls"][-1]["dice"][:3]
        req = str(uuid4())
        after = self.act(game, {"kind":"hold", "held":held[::-1]}, request_id=req)
        self.assertEqual(after["state"]["held"], sorted(held))
        self.assertEqual(self.act(game, {"kind":"hold", "held":held}, request_id=req), after)

    def test_no_new_official_after_stored_cutoff(self):
        self.start(self.bob_store)
        self.admin.execute("update public.yc_weekly_challenges set ends_at=clock_timestamp() where week_id=%s", (self.wk,))
        with self.assertRaises(GameExpired):
            self.start()
        self.assertIsNone(self.alice_store.dashboard(self.wk)["official"])

    def test_locked_row_wait_cannot_cross_cutoff_and_commit(self):
        game = self.start()
        context_ready = threading.Event()
        store = SupabaseWeeklyStore(PgClient(self.uri, after_context=context_ready.set), self.alice)
        # Context must finish first; then acquire the lock before the commit.
        proceed = threading.Event()
        store._client.after_context = lambda: (context_ready.set(), proceed.wait(5))
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.act, game, {"kind":"reroll"}, store)
            self.assertTrue(context_ready.wait(5))
            with psycopg.connect(self.uri) as conn:
                conn.execute("select 1 from public.yc_weekly_games where game_id=%s for update", (game["game_id"],))
                self.admin.execute("update public.yc_weekly_challenges set ends_at=clock_timestamp()+interval '0.15 second' where week_id=%s", (self.wk,))
                proceed.set()
                time.sleep(0.25)
            with self.assertRaises(GameExpired): future.result(timeout=5)
        self.assertEqual(self.alice_store.dashboard(self.wk)["official"], game)

    def test_expired_unfinished_has_no_board_score_and_retry_is_safe(self):
        game = self.start()
        req = str(uuid4())
        after = self.act(game, {"kind":"reroll"}, request_id=req)
        self.finish(self.start(self.bob_store), self.bob_store)
        self.admin.execute("update public.yc_weekly_challenges set ends_at=clock_timestamp() where week_id=%s", (self.wk,))
        self.assertEqual(self.act(game, {"kind":"reroll"}, request_id=req), after)
        with self.assertRaises(GameExpired): self.act(after, {"kind":"score", "category":"chance"})
        board = self.bob_store.standings(self.wk,self.group)
        self.assertEqual(len(board["standings"]), 1)
        self.assertEqual(board["standings"][0]["player_id"],self.bob.player_id)
        self.assertFalse(self.alice_store.standings(self.wk,self.group)["unlocked"])

    def test_service_role_cannot_directly_write_weekly_tables(self):
        game = self.start()
        with psycopg.connect(self.uri,autocommit=True) as conn:
            conn.execute("set role service_role")
            for sql in (
                "update public.yc_weekly_games set total_score=999",
                "delete from public.yc_weekly_games",
                "update public.yc_weekly_challenges set ends_at=ends_at+interval '1 day'",
                "delete from public.yc_weekly_replay_summaries",
            ):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege): conn.execute(sql)
        self.assertEqual(self.alice_store.dashboard(self.wk)["official"],game)

    def test_history_is_own_only_and_public_responses_have_no_pools(self):
        alice = self.start()
        self.start(self.bob_store)
        self.assertEqual(len(self.alice_store.history()),1)
        payloads = [alice,self.alice_store.dashboard(self.wk),self.alice_store.history(),self.alice_store.standings(self.wk,self.group)]
        for payload in payloads:
            text = json.dumps(payload)
            for forbidden in ('"pools"','"private_schedule"','"token_hash"','"session_id"','"secret"'):
                self.assertNotIn(forbidden,text)


class TransportTests(unittest.TestCase):
    def test_database_error_text_is_not_exposed(self):
        class Client:
            def rpc(self,*args,**kwargs):
                raise RuntimeError('private_schedule SECRET SQL arguments leaked here')
        actor = WeeklyActor(str(uuid4()),str(uuid4()),"0"*64)
        with self.assertRaises(WeeklyStoreError) as caught:
            SupabaseWeeklyStore(Client(),actor).dashboard("2026-11-09")
        self.assertNotIn("SECRET",str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)

    def test_actor_repr_hides_credential(self):
        actor = WeeklyActor(str(uuid4()),str(uuid4()),"a"*64)
        self.assertNotIn(actor.token_hash,repr(actor))
        self.assertNotIn(actor.session_id,repr(actor))


if __name__ == "__main__":
    unittest.main(verbosity=2)
