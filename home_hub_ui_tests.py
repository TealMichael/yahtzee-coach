"""v44.0.1 read-only home status and regression contracts (no Streamlit needed).

Run with: python -m pytest -q home_hub_ui_tests.py
"""
import ast
from pathlib import Path
from types import SimpleNamespace

SRC = Path(__file__).with_name('app.py').read_text()
TREE = ast.parse(SRC)
HOME_FUNCTIONS = {'_home_registered_daily', '_home_daily_status', '_home_weekly_status', '_set_app_mode'}


class State(dict):
    def __getattr__(self, key):
        return self[key]
    def __setattr__(self, key, value):
        self[key] = value


class Query:
    def __init__(self, row):
        self.row = row
    def select(self, *args):
        return self
    def eq(self, *args):
        return self
    def limit(self, *args):
        return self
    def execute(self):
        return SimpleNamespace(data=[self.row] if self.row else [])


class FakeStore:
    def __init__(self, record, resume):
        self.client = self
        self.record = record
        self.resume = resume
        self.reads = []
    def table(self, name):
        assert name == 'daily_challenges'
        self.reads.append('registration_read')
        return Query(self.record)
    def get_resume_state(self, player_id, challenge_id):
        self.reads.append('attempt_read')
        assert player_id == 'p1'
        assert challenge_id == 'daily-key'
        return self.resume


def env(record=None, resume=None, official=None, weekly_failure=False, active='p1', token='session.valid'):
    store = FakeStore(record, resume)
    state = State(active_player_id=active, active_device_token=token, daily_date_key='2026-11-14')
    ns = {'st': SimpleNamespace(session_state=state, cache_data=lambda **kw: lambda fn: fn),
          'load_daily_store': lambda: store, 'current_week_id': lambda: '2026-11-09'}
    class WeeklyActor:
        @classmethod
        def from_token(cls, player_id, value):
            assert (player_id, value) == ('p1', 'session.valid')
            return cls()
    class WeeklyStore:
        def __init__(self, client, actor):
            assert client is store
        def dashboard(self, week):
            assert week == '2026-11-09'
            store.reads.append('weekly_dashboard_read')
            if weekly_failure:
                raise RuntimeError('unavailable')
            return {'official': official}
    ns.update(WeeklyActor=WeeklyActor, SupabaseWeeklyStore=WeeklyStore)
    nodes = []
    for item in TREE.body:
        if isinstance(item, ast.FunctionDef) and item.name in HOME_FUNCTIONS:
            item = ast.FunctionDef(name=item.name, args=item.args, body=item.body,
                                   decorator_list=[], returns=item.returns,
                                   type_comment=None)
            nodes.append(item)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), 'app.py', 'exec'), ns)
    return ns, store


def test_home_is_default_but_daily_weekly_modes_still_exist():
    assert 'st.session_state.app_mode = "Home"' in SRC
    assert 'elif mode == "Daily Challenge"' in SRC
    assert 'elif mode == "Weekly"' in SRC
    assert 'render_daily_mode()' in SRC
    assert 'render_weekly_mode()' in SRC


def test_daily_only_reads_and_supports_six_or_ten():
    for count in (6, 10):
        ns, store = env({'challenge_id': 'daily-key', 'puzzle_ids': list(range(count))})
        r = ns['_home_daily_status']()
        assert (r['value'], r['total'], r['action']) == ('0', str(count), 'Play Daily')
        assert store.reads == ['registration_read', 'attempt_read']


def test_daily_resumes_and_uses_saved_answers():
    resume = SimpleNamespace(answers=[1, 2, 3], attempt=SimpleNamespace(complete=False))
    ns, store = env({'challenge_id': 'daily-key', 'puzzle_ids': list(range(6))}, resume)
    result = ns['_home_daily_status']()
    assert result['value'] == '3' and result['total'] == '6' and result['action'] == 'Continue Daily'
    assert store.reads == ['registration_read', 'attempt_read']


def test_daily_complete_shows_results_without_new_attempt():
    resume = SimpleNamespace(answers=list(range(6)), attempt=SimpleNamespace(complete=True))
    ns, store = env({'challenge_id': 'daily-key', 'puzzle_ids': list(range(6))}, resume)
    result = ns['_home_daily_status']()
    assert (result['value'], result['total'], result['action']) == ('6', '6', 'View Daily Results')
    assert store.reads == ['registration_read', 'attempt_read']


def test_unregistered_daily_does_not_activate_six_and_does_not_guess():
    ns, store = env()
    result = ns['_home_daily_status']()
    assert result['value'] == '—' and result['total'] == '—'
    assert store.reads == ['registration_read']


def test_weekly_one_official_state_transitions():
    examples = [
        (None, ('0', '1', 'Play Weekly')),
        ({'completed_at': None, 'state': {'rounds': [1,2,3,4]}}, ('4', '13', 'Resume Weekly')),
        ({'completed_at': '2026-11-14T12:00:00Z', 'total_score': 151,
          'state': {'rounds': list(range(13))}}, ('1', '1', 'View Standings')),
    ]
    for official, expected in examples:
        ns, store = env(official=official)
        result = ns['_home_weekly_status']()
        assert (result['value'], result['total'], result['action']) == expected
        if official and official.get('completed_at'):
            assert result['detail'] == '151 pts · official score locked'
        assert store.reads == ['weekly_dashboard_read']


def test_weekly_failure_not_false_zero_or_started_attempt():
    ns, store = env(weekly_failure=True)
    result = ns['_home_weekly_status']()
    assert result['value'] == '—'
    assert store.reads == ['weekly_dashboard_read']


def test_guest_does_not_query_private_progress():
    ns, store = env(active=None)
    assert ns['_home_daily_status']()['action'] == 'Sign in for Daily'
    assert ns['_home_weekly_status']()['action'] == 'Sign in for Weekly'
    assert store.reads == []


def test_click_navigation_only_updates_page_state():
    ns, store = env()
    for choice in ['Home', 'Daily Challenge', 'Weekly', 'Practice', 'My Player']:
        ns['_set_app_mode'](choice)
        assert ns['st'].session_state.app_mode == choice
    assert store.reads == []


def test_home_does_not_call_mutating_game_start_or_daily_format():
    # Function-level regression guard: reading status must not create or commit attempts.
    names = ['_home_registered_daily', '_home_daily_status', '_home_weekly_status',
             '_home_yesterday_results', '_home_tile', 'render_challenge_hub']
    for fn in TREE.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in names:
            source = ast.get_source_segment(SRC, fn)
            for banned in ('start_official(', 'start_persistent_daily_attempt(',
                           'get_or_create_attempt(', 'save_answer(', '.act(', 'daily_format('):
                # Avoid harmless mentions in comments/docstrings by inspecting calls.
                pass
            call_names = []
            for n in ast.walk(fn):
                if isinstance(n, ast.Call):
                    target = n.func
                    call_names.append(target.attr if isinstance(target, ast.Attribute) else target.id if isinstance(target, ast.Name) else '')
            assert not set(call_names) & {'start_official', 'start_persistent_daily_attempt',
                                          'get_or_create_attempt', 'save_answer', 'act', 'daily_format'}
