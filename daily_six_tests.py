"""Six-puzzle generation, historical identity, store and presentation behavior."""
import ast
from collections import Counter
from datetime import date, timedelta
from copy import deepcopy
import html
from pathlib import Path
from types import SimpleNamespace
import unittest

from daily_challenge import daily_challenges, challenge_set_id, registered_daily_challenges, summarize_attempt
from daily_store import InMemoryDailyStore, DailyStoreError, AttemptAlreadyComplete
from perfect_ten import is_perfect_ten
from retro_podium import personal_medal_moment_html
from daily_spotlight import select_spotlight


class DailySixTests(unittest.TestCase):
    def test_eight_weeks_balanced_deterministic_and_not_ten_slice(self):
        family_counts=[]
        for offset in range(56):
            day=str(date(2026,11,13)+timedelta(days=offset))
            six=daily_challenges(day,6);ten=daily_challenges(day,10)
            self.assertEqual(len(six),6)
            self.assertEqual(Counter(c['roll_number'] for c in six),{1:3,2:3})
            self.assertEqual(Counter(c['stage'] for c in six),{'Opening':1,'Midgame':2,'Late Game':2,'True Endgame':1})
            difficulty=Counter(c['difficulty'] for c in six)
            self.assertEqual([difficulty[k] for k in ('Clear','Medium','Hard')],[1,2,2])
            self.assertEqual(difficulty['Punishing']+difficulty['Knife-edge'],1)
            families=Counter(c['skill_tag'] for c in six)
            self.assertGreaterEqual(len(families),4);self.assertLessEqual(max(families.values()),2)
            family_counts.append(len(families))
            self.assertEqual(len({c['bank_state_key'] for c in six}),6)
            self.assertEqual(len({c['challenge_id'] for c in six}),6)
            self.assertEqual(six,daily_challenges(day,6))
            self.assertNotEqual(challenge_set_id(day,six),challenge_set_id(day,ten))
            self.assertNotEqual([c['bank_state_key'] for c in six],[c['bank_state_key'] for c in ten[:6]])
        print('56-day six-puzzle audit: skill families per day',min(family_counts),max(family_counts),round(sum(family_counts)/56,2))

    def test_cache_is_count_aware_and_returns_independent_copies(self):
        day='2026-11-20';six=daily_challenges(day,6);old=deepcopy(six)
        six[0]['dice'][0]=99
        self.assertEqual(daily_challenges(day,6),old)
        self.assertEqual(len(daily_challenges(day)),10)

    def test_registered_ten_survives_an_earlier_effective_date(self):
        store=InMemoryDailyStore();day='2026-11-14';old=daily_challenges(day)
        store.ensure_challenge(challenge_set_id(day,old),day,old[0]['daily_version'],[c['challenge_id'] for c in old])
        store.six_effective_date='2026-11-13'
        self.assertEqual(registered_daily_challenges(day,store),old)
        self.assertEqual(len(registered_daily_challenges('2026-11-15',store)),6)
        self.assertEqual(len(registered_daily_challenges('2026-11-12',store)),10)

    def test_registered_identity_mismatch_fails_closed(self):
        store=InMemoryDailyStore();store.ensure_challenge('wrong','2026-11-14','old',[str(i) for i in range(10)])
        with self.assertRaises(ValueError): registered_daily_challenges('2026-11-14',store)

    def test_memory_store_handles_both_lengths_and_preserves_results(self):
        store=InMemoryDailyStore();a=store.create_player('Alice','1234');b=store.create_player('Bobby','5678')
        group=store.create_group(a.player_id,'Friends');store.join_group(b.player_id,group.join_code)
        for count,day in [(10,'2026-11-12'),(6,'2026-11-13')]:
            puzzles=daily_challenges(day,count)
            c=store.ensure_challenge(challenge_set_id(day,puzzles),day,puzzles[0]['daily_version'],[p['challenge_id'] for p in puzzles])
            for player in (a,b):
                attempt,_=store.get_or_create_attempt(player.player_id,c.challenge_id)
                for n in range(1,count+1):
                    with self.assertRaises(DailyStoreError):store.complete_attempt(attempt.attempt_id)
                    store.save_answer(attempt.attempt_id,question_number=n,puzzle_id=c.puzzle_ids[n-1],chosen_hold=[2],optimal_hold=[2],points_lost=0)
                with self.assertRaises(ValueError):
                    store.save_answer(attempt.attempt_id,question_number=count+1,puzzle_id='extra',chosen_hold=[],optimal_hold=[],points_lost=0)
                store.revise_answer(attempt.attempt_id,question_number=count,puzzle_id=c.puzzle_ids[-1],chosen_hold=[2],optimal_hold=[2],points_lost=0)
                done=store.complete_attempt(attempt.attempt_id)
                self.assertEqual(done.exact_count,count)
                self.assertIsNone(store.get_resume_state(player.player_id,c.challenge_id).next_question_number)
                self.assertEqual(store.get_or_create_attempt(player.player_id,c.challenge_id),(done,False))
                with self.assertRaises(AttemptAlreadyComplete):
                    store.revise_answer(attempt.attempt_id,question_number=1,puzzle_id=c.puzzle_ids[0],chosen_hold=[],optimal_hold=[],points_lost=0)
            review=store.group_player_daily_review(group.group_id,c.challenge_id,a.player_id,b.player_id)
            self.assertEqual(len(review['answers']),count)
            self.assertEqual(len(store.group_question_stats(group.group_id,c.challenge_id)),count)
            self.assertEqual([r['rank'] for r in store.leaderboard(group.group_id,c.challenge_id)],[1,1])
        self.assertEqual(store.current_participation_streak(a.player_id,'2026-11-13'),2)
        self.assertEqual(store.player_medal_totals(a.player_id,group.group_id,'2026-11-13')['gold'],2)

    def test_six_is_not_perfect_ten_and_both_ceremonies_are_accurate(self):
        for count,word in [(6,'six'),(10,'ten')]:
            summary=summarize_attempt([{'points_lost':0}]*count)
            self.assertEqual(is_perfect_ten(summary),count==10)
            doc=personal_medal_moment_html([{'player_id':'p','display_name':'Player','rank':1,'exact_count':count}],
                active_player_id='p',active_player_name='Player',group_name='Friends',date_label='Yesterday',avatar_config={},medal_totals={},question_count=count)
            self.assertIn(f'perfect {word}',doc)

    def test_share_and_standings_use_correct_length_and_escape_names(self):
        source=Path(__file__).with_name('app.py').read_text();tree=ast.parse(source)
        names={'_daily_count','build_daily_share_text','render_leaderboard_cards'}
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        rendered=[]
        class Expander:
            def __enter__(self):pass
            def __exit__(self,*args):pass
        state=type('State',(dict,),{'__getattr__':dict.__getitem__})(daily_date_key='today',active_player_id='p',daily_challenges=[{}]*6)
        env={'st':SimpleNamespace(session_state=state,markdown=lambda t,**k:rendered.append(t),expander=lambda *a,**k:Expander(),caption=lambda *a:None),
            'html':html,'is_perfect_ten':is_perfect_ten,'_daily_date_label':lambda x:x,'_share_square':lambda x:'🟩','PUBLIC_APP_URL':'https://example.com'}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'app.py','exec'),env)
        for count,word in [(6,'SIX'),(10,'TEN')]:
            summary=summarize_attempt([{'points_lost':0}]*count)
            text=env['build_daily_share_text']([{}]*count,summary)
            self.assertIn(f'{count}/{count} best holds',text)
            self.assertIn(f'PERFECT {word}',text)
            self.assertEqual([len(l) for l in text.splitlines() if l.startswith('🟩') and 'best' not in l],[count//2]*2)
            rendered.clear()
            env['render_leaderboard_cards']([{'rank':1,'player_id':'p','display_name':'<Player>','total_ev_loss':0,'exact_count':count}],question_count=count)
            self.assertIn(f'{count}/{count} best',rendered[0]);self.assertIn('&lt;Player&gt;',rendered[0])

    def test_six_spotlight_remains_optional_and_post_completion(self):
        answers=[]
        for n in range(1,7):
            answers.append({'challenge':{'daily_number':n,'daily_date':'2026-11-13','dice':[2,2,3,3,5],'scorecard':{'full_house':None}},
                'solver_record':{'source':'exact','points_lost':.5,'simple_why':'The two pairs offer a useful full-house route.',
                    'coaching_family':'two_pair_full_house_tradeoff'}})
        before=deepcopy(answers)
        self.assertIsNone(select_spotlight(answers,completed=False))
        self.assertIsNotNone(select_spotlight(answers,completed=True))
        self.assertEqual(answers,before)
        self.assertIsNone(select_spotlight(answers[:5],completed=True))


if __name__=='__main__': unittest.main(verbosity=2)
