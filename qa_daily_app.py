"""Local full-app fixture. Synthetic players, no production secrets or service.

Run with Streamlit for manual QA, or AppTest for the real login/Daily/Weekly UI.
Fixture-only database activation is moved to today to exercise six immediately.
"""
import atexit
from pathlib import Path
import runpy
from unittest.mock import patch
from uuid import uuid4
import streamlit as st

from daily_six_postgres_tests import DailySixPostgresTests
from supabase_daily_store import SupabaseDailyStore


@st.cache_resource(show_spinner=False)
def fixture(qa_id, count):
    kind=type('LocalDailyFixture',(DailySixPostgresTests,),{})
    kind.setUpClass();atexit.register(kind.doClassCleanups)
    item=kind('runTest');item.setUp()
    # Synthetic fixture only: the installed app never alters its rollout date.
    item.admin.execute("update yc_daily_format_config set six_effective_date=%s,activated_at=now()",(item.today if count==6 else item.today.replace(year=item.today.year+1),))
    item.admin.execute('update players set avatar_setup_complete=true')
    return item


if 'qa_id' not in st.session_state: st.session_state.qa_id=str(uuid4())
qa=fixture(st.session_state.qa_id,st.session_state.get('qa_daily_count',6))
st.session_state.qa_fixture=qa
with patch.object(SupabaseDailyStore,'from_secrets',return_value=qa.store), patch.object(st,'secrets',{}):
    runpy.run_path(str(Path(__file__).with_name('app.py')),run_name='__main__')
