"""Local QA only: synthetic accounts and an isolated temporary PostgreSQL server.

Run `streamlit run qa_weekly_app.py`. Never configure production credentials.
Uses production Weekly widgets, rules, store and SQL through a local RPC adapter.
The dashboard belongs only to synthetic Alice; Bob is an already-finished friend.
"""
import atexit
import ast
from pathlib import Path
from uuid import uuid4
import streamlit as st
from weekly_postgres_tests import PgClient, WeeklyPostgresTests
from weekly_store import SupabaseWeeklyStore
from weekly_ui import render_weekly

st.set_page_config(page_title="Weekly local QA", layout="centered")
# Apply the actual application's global CSS, so local mobile checks include it.
for node in ast.parse(Path(__file__).with_name("app.py").read_text()).body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call = node.value
        if (isinstance(call.func, ast.Attribute) and call.func.attr == "markdown"
            and call.args and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str) and "<style>" in call.args[0].value):
            st.markdown(call.args[0].value, unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def fixture(qa_id):
    # A fresh class keeps each AppTest/browser fixture's connection lifecycle apart.
    fixture_type = type("LocalWeeklyFixture", (WeeklyPostgresTests,), {})
    fixture_type.setUpClass()
    atexit.register(fixture_type.doClassCleanups)
    item = fixture_type("runTest")
    item.setUp()
    item.finish(item.start(item.bob_store), item.bob_store)
    return item

if "qa_id" not in st.session_state:
    st.session_state.qa_id = str(uuid4())
qa = fixture(st.session_state.qa_id)
st.session_state.qa_fixture = qa  # Server-only inspection for AppTest.

class QaTransport(PgClient):
    def rpc(self, name, params):
        call = super().rpc(name, params)
        execute = call.execute
        def run():
            result = execute()
            if params['p_operation'] == 'commit' and st.session_state.get('qa_lose_response'):
                st.session_state.qa_lose_response = False
                raise ConnectionError('Synthetic lost commit response')
            return result
        call.execute = run
        return call

store = SupabaseWeeklyStore(QaTransport(qa.uri), qa.alice)
st.caption("Local QA · synthetic players · isolated database")
render_weekly(store, qa.alice.player_id)
