"""Full production app journey through synthetic local SQL and real widgets."""
from pathlib import Path
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parent


def button(at,label): return next(b for b in at.button if b.label==label)
def visible(at): return '\n'.join(str(x.value) for kind in ('markdown','success','warning','error','caption','info') for x in getattr(at,kind) if not str(x.value).lstrip().startswith('<style>'))


class DailySixUiTests(unittest.TestCase):
    def setUp(self):
        st.cache_resource.clear();st.cache_data.clear()

    def open(self,count=6,remember=False,yesterday=False):
        at=AppTest.from_file(str(ROOT/'qa_daily_app.py'),default_timeout=45)
        at.session_state['qa_daily_count']=count;at.run()
        self.assertFalse(at.exception)
        self.qa=at.session_state['qa_fixture'];self.addCleanup(type(self.qa).doClassCleanups)
        if yesterday:
            self.qa.finish(self.qa.challenge(self.qa.today-timedelta(days=1)))
        at.text_input(key='returning_player_name').set_value('Alice')
        at.text_input(key='returning_player_pin').set_value('2468')
        at.checkbox(key='returning_player_remember').set_value(remember)
        button(at,'Sign in').click().run()
        self.assertFalse(at.exception);self.assertFalse(at.error)
        self.assertEqual(len(at.session_state['daily_challenges']),count)
        if not yesterday:
            self.assertIn(f'{count // 2} Roll 1 · {count // 2} Roll 2', visible(at))
        return at

    def save_questions(self,at,count,start=0):
        for i in range(start,count):
            self.assertIn(f'Question {i+1} of {count}',visible(at))
            self.assertFalse(at.session_state['daily_completed'])
            button(at,'Save & next' if i<count-1 else f'Save & review all {count}').click().run()
            self.assertFalse(at.exception);self.assertFalse(at.error)

    def test_full_six_journey_edit_submit_and_navigation(self):
        at=self.open(6)
        self.assertTrue(at.session_state['active_device_token'])
        button(at,"Start today's Daily Challenge").click().run()
        button(at,'Save & next').click().run()
        attempt=at.session_state['daily_attempt_id']
        at.radio(key='app_mode').set_value('Weekly').run()
        self.assertFalse(at.exception);self.assertTrue(button(at,'Start Official Game'))
        button(at,'Start Official Game').click().run()
        self.assertIn('Round 1 of 13',visible(at))
        dice=next(b for b in at.button if b.key and b.key.endswith('_die_1'))
        dice.click().run()
        at.radio(key='app_mode').set_value('Practice').run()
        self.assertFalse(at.exception)
        at.radio(key='app_mode').set_value('Daily Challenge').run()
        self.assertEqual(at.session_state['daily_attempt_id'],attempt)
        self.save_questions(at,6,start=1)
        self.assertIn('Check your 6 choices',visible(at))
        self.assertIn('No grades, Points Lost, or best answers are shown yet',visible(at))
        self.assertEqual(len(at.selectbox(key='daily_review_edit_question').options),6)
        at.selectbox(key='daily_review_edit_question').set_value(2).run()
        button(at,'✏️ Edit selected question').click().run()
        self.assertIn('Question 2 of 6',visible(at))
        button(at,'Save changes & return to review').click().run()
        button(at,'🏁 Submit final Daily Challenge').click().run()
        self.assertFalse(at.exception);self.assertFalse(at.error)
        self.assertTrue(at.session_state['daily_completed'])
        self.assertIn('/6',visible(at));self.assertNotIn('/10 best',visible(at))
        self.assertIn('Your 6 Grades',visible(at))
        self.assertEqual(self.qa.store.get_resume_state(self.qa.alice.player_id,at.session_state['daily_set_id']).attempt.attempt_id,attempt)
        at.radio(key='app_mode').set_value('Weekly').run()
        self.assertIn('Round 1 of 13',visible(at));self.assertFalse(at.exception)
        self.assertNotIn('Held: none',visible(at))
        at.radio(key='app_mode').set_value('My Player').run();self.assertFalse(at.exception)
        old_token=at.session_state['active_device_token']
        button(at,'Sign out').click().run();self.assertFalse(at.exception)
        self.assertIsNone(self.qa.store.authenticate_device_session(old_token))
        self.assertIsNone(at.session_state['active_player_id'])
        at.text_input(key='returning_player_name').set_value('Bob')
        at.text_input(key='returning_player_pin').set_value('1357')
        at.checkbox(key='returning_player_remember').set_value(False)
        button(at,'Sign in').click().run()
        at.radio(key='app_mode').set_value('Weekly').run()
        self.assertFalse(at.exception);self.assertTrue(button(at,'Start Official Game'))
        self.assertNotIn('Held:',visible(at))

    def check_interrupted_start(self, *, yesterday):
        at=self.open(6,yesterday=yesterday)
        original=self.qa.store.get_resume_state
        interrupted=[]
        def interrupt_once(player_id, challenge_id):
            result=original(player_id,challenge_id)
            if result is not None and not interrupted:
                interrupted.append(result.attempt.attempt_id)
                st.rerun()
            return result
        with patch.object(self.qa.store,'get_resume_state',side_effect=interrupt_once):
            button(at,"🎲 PLAY TODAY'S DAILY →" if yesterday else "Start today's Daily Challenge").click().run()
        self.assertFalse(at.exception);self.assertFalse(at.error)
        self.assertTrue(interrupted)
        self.assertTrue(at.session_state['daily_started'])
        self.assertFalse(at.session_state['daily_start_requested'])
        self.assertEqual(at.session_state['daily_attempt_id'],interrupted[0])
        self.assertIn('Question 1 of 6',visible(at))
        count=self.qa.admin.execute('select count(*) from daily_attempts where challenge_id=%s',(at.session_state['daily_set_id'],)).fetchone()[0]
        self.assertEqual(count,1)

    def test_daily_start_recovers_from_rerun_after_attempt_creation(self):
        self.check_interrupted_start(yesterday=False)

    def test_recap_start_recovers_from_rerun_after_attempt_creation(self):
        # AppTest has no browser to acknowledge the localStorage component.
        component=st.components.v2.component
        def browser_ready(name,*args,**kwargs):
            if name=='yahtzee_yesterday_results_storage':
                return lambda **kw: SimpleNamespace(payload='{"value":"","ready":true,"ack":""}')
            return component(name,*args,**kwargs)
        with patch.object(st.components.v2,'component',side_effect=browser_ready):
            self.check_interrupted_start(yesterday=True)

    def test_signin_survives_component_rerun_and_rejects_bad_pin(self):
        at=AppTest.from_file(str(ROOT/'qa_daily_app.py'),default_timeout=45).run()
        qa=at.session_state['qa_fixture'];self.addCleanup(type(qa).doClassCleanups)
        at.text_input(key='returning_player_name').set_value('Alice')
        at.text_input(key='returning_player_pin').set_value('9999')
        button(at,'Sign in').click().run()
        self.assertIsNone(at.session_state['active_player_id'])
        self.assertIn('Display name or PIN did not match.',visible(at))
        at.text_input(key='returning_player_name').set_value('Alice')
        at.text_input(key='returning_player_pin').set_value('2468')
        at.checkbox(key='returning_player_remember').set_value(False)
        component=st.components.v2.component
        interrupted=[]
        def interrupt_after_callback(name,*args,**kwargs):
            if not interrupted:
                interrupted.append(True)
                st.rerun()
            return component(name,*args,**kwargs)
        with patch.object(st.components.v2,'component',side_effect=interrupt_after_callback):
            button(at,'Sign in').click().run()
        self.assertTrue(interrupted)
        self.assertFalse(at.exception);self.assertFalse(at.error)
        self.assertEqual(at.session_state['active_player_id'],qa.alice.player_id)
        self.assertTrue(at.session_state['active_device_token'])

    def test_legacy_ten_review_and_submit_remain_complete(self):
        at=self.open(10,remember=True)
        self.assertTrue(at.session_state['active_device_token'])
        button(at,"Start today's Daily Challenge").click().run()
        self.save_questions(at,10)
        self.assertIn('Check your 10 choices',visible(at))
        self.assertEqual(len(at.selectbox(key='daily_review_edit_question').options),10)
        button(at,'← Back to Question 10').click().run()
        self.assertIn('Question 10 of 10',visible(at))
        button(at,'Save changes & return to review').click().run()
        button(at,'🏁 Submit final Daily Challenge').click().run()
        self.assertFalse(at.exception);self.assertFalse(at.error)
        self.assertTrue(at.session_state['daily_completed']);self.assertIn('Your 10 Grades',visible(at))


if __name__=='__main__': unittest.main(verbosity=2)
