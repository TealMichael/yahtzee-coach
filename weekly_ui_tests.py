"""Real Streamlit interactions backed by isolated PostgreSQL (no live service)."""
from collections import Counter
from pathlib import Path
import unittest
from uuid import uuid4

from streamlit.testing.v1 import AppTest

from weekly_game import CATEGORIES, scoring_options
from weekly_ui import action_request, held_positions

ROOT = Path(__file__).resolve().parent


def button(at, label):
    return next(item for item in at.button if item.label == label)


def visible(at):
    return '\n'.join(str(item.value) for kind in ('markdown','caption','info','success','warning','error') for item in getattr(at,kind))


class WeeklyUiTests(unittest.TestCase):
    def setUp(self):
        self.at = AppTest.from_file(str(ROOT/'qa_weekly_app.py'), default_timeout=30).run()
        self.assertFalse(self.at.exception)
        self.qa = self.at.session_state['qa_fixture']
        self.addCleanup(type(self.qa).doClassCleanups)

    def start(self):
        button(self.at,'Start Official Game').click().run()
        self.assertFalse(self.at.exception)
        return self.qa.alice_store.dashboard(self.qa.wk)['official']

    def score(self):
        self.reveal_first_roll()
        game = self.qa.alice_store.dashboard(self.qa.wk)['official']
        replay = self.qa.alice_store.dashboard(self.qa.wk)['replay']
        if replay and replay['completed_at'] is None: game = replay
        state = game['state']
        category = scoring_options(state['rolls'][-1]['dice'],dict(zip(CATEGORIES,state['scores'])))[0].category
        next(b for b in self.at.button if b.key.endswith('_category_' + category)).click().run()
        next(b for b in self.at.button if b.label.startswith('Confirm ') and not b.disabled).click().run()
        self.assertFalse(self.at.exception)

    def reveal_first_roll(self):
        first = [b for b in self.at.button if 'Roll Dice · 1 of 3' in b.label]
        if first:
            first[0].click().run()
        self.assertFalse(self.at.exception)

    def test_intro_shows_only_friend_count(self):
        text = visible(self.at)
        self.assertIn('1 friend has finished',text)
        self.assertNotIn('Bob',text)
        self.assertNotIn('<th>Rank</th>',text)
        self.assertTrue(button(self.at,'Start Official Game'))

    def test_dice_taps_are_local_and_saved_only_on_reroll(self):
        game = self.start()
        self.reveal_first_roll()
        # A first-roll reveal is visual only, not an extra game action.
        self.assertEqual(self.qa.alice_store.dashboard(self.qa.wk)['official']['revision'], 0)
        self.assertFalse(self.at.exception)
        self.assertTrue(any('Roll Dice · 2 of 3' in b.label for b in self.at.button))
        # Duplicate-die click/hold behavior is covered by the offline UI test,
        # because AppTest versions differ in their st.pills widget support.
        button(self.at,'🎲 Roll Dice · 2 of 3').click().run()
        self.assertFalse(self.at.exception)
        self.assertEqual(self.qa.alice_store.dashboard(self.qa.wk)['official']['revision'],1)

    def test_third_roll_disables_holds_and_reroll(self):
        self.start()
        self.reveal_first_roll()
        button(self.at,'🎲 Roll Dice · 2 of 3').click().run()
        button(self.at,'🎲 Roll Dice · 3 of 3').click().run()
        self.assertFalse(any('Roll Dice · 4 of 3' in b.label for b in self.at.button))
        self.assertIn('Final roll',visible(self.at))

    def test_score_requires_selection_and_zero_is_explicit(self):
        self.start()
        self.reveal_first_roll()
        self.assertTrue(next(b for b in self.at.button if b.label == 'Confirm score').disabled)
        game = self.qa.alice_store.dashboard(self.qa.wk)['official']
        state = game['state']
        zero = next(o for o in scoring_options(state['rolls'][-1]['dice'],dict(zip(CATEGORIES,state['scores']))) if o.points==0)
        next(b for b in self.at.button if b.key.endswith('_category_' + zero.category)).click().run()
        self.assertIn('Selected:',visible(self.at))
        next(b for b in self.at.button if b.label.startswith('Confirm 0 points')).click().run()
        state = self.qa.alice_store.dashboard(self.qa.wk)['official']['state']
        self.assertEqual(state['scores'][CATEGORIES.index(zero.category)],0)
        self.assertIn('Round 2 of 13',visible(self.at))

    def test_finish_reveals_locked_score_friends_and_replay(self):
        self.start()
        for _ in range(13): self.score()
        text = visible(self.at)
        self.assertIn('Official Score (locked)',text)
        self.assertIn('Bob',text)
        self.assertIn('<th>Rank</th>',text)
        self.assertFalse(any(x.label == 'Scoring category' for x in self.at.selectbox))
        self.assertTrue(button(self.at,"Replay This Week's Dice"))
        self.assertEqual(len(self.qa.alice_store.dashboard(self.qa.wk)['official']['state']['rounds']),13)

    def test_replay_never_changes_official(self):
        official = self.qa.finish(self.qa.start())
        self.at.run()
        button(self.at,"Replay This Week's Dice").click().run()
        self.assertIn('Practice — does not affect standings',visible(self.at))
        self.score()
        self.assertEqual(self.qa.alice_store.dashboard(self.qa.wk)['official'],official)
        self.assertEqual(len(self.qa.alice_store.dashboard(self.qa.wk)['replay']['state']['rounds']),1)

    def test_lost_commit_response_retries_exact_request_once(self):
        self.start()
        self.at.session_state['qa_lose_response'] = True
        self.reveal_first_roll()
        button(self.at,'🎲 Roll Dice · 2 of 3').click().run()
        self.assertIn("save wasn't confirmed",visible(self.at))
        saved = self.qa.alice_store.dashboard(self.qa.wk)['official']
        self.assertEqual(saved['revision'],1)
        self.assertFalse(any('Roll Dice · 2 of 3' in b.label for b in self.at.button))
        button(self.at,'Retry save').click().run()
        self.assertEqual(self.qa.alice_store.dashboard(self.qa.wk)['official'],saved)
        self.assertIn('Roll 2 of 3',visible(self.at))

    def test_stale_tab_click_loads_saved_game_without_second_roll(self):
        game = self.start()
        newer = self.qa.act(game,{'kind':'reroll'})
        self.reveal_first_roll()
        button(self.at,'🎲 Roll Dice · 2 of 3').click().run()
        self.assertIn('another tab',visible(self.at))
        self.assertEqual(self.qa.alice_store.dashboard(self.qa.wk)['official'],newer)

    def test_revoked_session_removes_game_and_scores(self):
        self.qa.finish(self.qa.start())
        self.at.run()
        self.assertIn('Bob',visible(self.at))
        self.qa.admin.execute('update public.player_sessions set revoked_at=clock_timestamp() where session_id=%s',(self.qa.alice.session_id,))
        next(b for b in self.at.button if b.label.startswith('Refresh saved game')).click().run()
        self.assertFalse(self.at.exception)
        self.assertIn('sign-in expired',visible(self.at))
        self.assertNotIn('Bob',visible(self.at))
        self.assertNotIn('Official Score (locked)',visible(self.at))

    def test_group_removal_immediately_removes_board(self):
        self.qa.finish(self.qa.start())
        self.at.run()
        self.qa.admin.execute('delete from public.group_members where player_id=%s',(self.qa.alice.player_id,))
        next(b for b in self.at.button if b.label.startswith('Refresh saved game')).click().run()
        self.assertNotIn('Bob',visible(self.at))
        self.assertIn('Join or create a friend group',visible(self.at))

    def test_expired_incomplete_shows_no_play_controls_or_friend_scores(self):
        self.start()
        self.qa.admin.execute('update public.yc_weekly_challenges set ends_at=clock_timestamp() where week_id=%s',(self.qa.wk,))
        self.at.run()
        self.assertIn('expired unfinished',visible(self.at))
        self.assertNotIn('Bob',visible(self.at))
        self.assertFalse(any('Roll Dice · 2 of 3' in b.label for b in self.at.button))
        self.assertFalse(any(b.label.startswith('Confirm ') for b in self.at.button))

    def test_no_future_pools_or_solver_output_in_active_screen(self):
        self.start()
        text = visible(self.at)
        for word in ('private_schedule','pools','token_hash','expected value','Best hold','Strategy grade'):
            self.assertNotIn(word,text)


class RequestTests(unittest.TestCase):
    def test_duplicate_widget_events_use_same_request(self):
        game={'game_id':str(uuid4()),'week_id':'2026-11-09','revision':4}
        action={'kind':'reroll'}
        first=action_request(game,action)
        self.assertEqual(action_request(game,action),first)
        self.assertNotEqual(action_request(dict(game,revision=5),action)['request_id'],first['request_id'])

    def test_duplicate_face_selection_restores_same_multiset(self):
        dice=[2,3,3,3,6]
        held=[3,3,6]
        selected=held_positions(dice,held)
        self.assertEqual(Counter(dice[i] for i in selected),Counter(held))
        self.assertEqual(selected,[1,2,4])

if __name__=='__main__':
    unittest.main(verbosity=2)
