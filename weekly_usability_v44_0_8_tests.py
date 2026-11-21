"""v44.0.8 Offline UX checks — no Streamlit Cloud, Supabase, or real attempts.

Exercise authoritative score confirmation, failed-save retries, and unchanged
scoring/dice/persistence contracts using the deterministic in-memory store.
"""
import ast
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

from weekly_game_flow_ui_tests import setup
from weekly_game import CATEGORIES, scoring_options
import weekly_ui as ui

ROOT = Path(__file__).parent
APP = (ROOT / "app.py").read_text()
WEEKLY = (ROOT / "weekly_ui.py").read_text()


def _source_function_digest(source, names):
    root = ast.parse(source)
    result = {}
    for node in root.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            result[node.name] = sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
    return result


def test_saved_score_feedback_is_only_from_server_confirmed_round():
    fake, store, scope, game = setup()
    dice = ui._visual_dice(game, scope)
    scores = dict(zip(CATEGORIES, game["state"]["scores"]))
    selected = scoring_options(dice, scores)[0]
    ui._queue(scope, ui.action_request(game, {"kind": "score", "category": selected.category}))
    assert f"{scope}_score_notice" not in fake.session_state
    assert not store.calls
    assert ui._send_pending(store, scope)
    assert len(store.calls) == 1
    notice = fake.session_state[f"{scope}_score_notice"]
    assert notice == {
        "game_id": game["game_id"], "rounds_saved": 1,
        "category": selected.category, "points": selected.points, "bonus": 0,
    }
    fake.markdowns.clear()
    ui._play(store.public(), scope)
    assert any('role="status" aria-live="polite"' in m for m in fake.markdowns)
    assert any(f"+{selected.points} saved" in m for m in fake.markdowns)
    assert f"{scope}_score_notice" not in fake.session_state
    count = len(store.calls)
    fake.markdowns.clear()
    ui._play(store.public(), scope)
    assert not any('weekly-score-flash' in m for m in fake.markdowns)
    assert len(store.calls) == count  # Displaying a confirmation is read-only.


def test_failed_save_keeps_same_protected_request_and_does_not_claim_success():
    fake, store, scope, game = setup()
    dice = ui._visual_dice(game, scope)
    chosen = scoring_options(dice, dict(zip(CATEGORIES, game["state"]["scores"])))[0]
    ui._queue(scope, ui.action_request(game, {"kind": "score", "category": chosen.category}))
    original = dict(fake.session_state[f"{scope}_pending"])
    store.fail_call_number = 1
    assert ui._send_pending(store, scope) is False
    assert fake.session_state[f"{scope}_pending"] == original
    assert f"{scope}_score_notice" not in fake.session_state
    assert any('wasn\'t confirmed' in warning for warning in fake.warnings)
    store.fail_call_number = None
    assert ui._send_pending(store, scope)
    assert [call[0] for call in store.calls] == [original["request_id"]] * 2
    assert len(store.state.rounds) == 1
    assert f"{scope}_pending" not in fake.session_state


def test_spinner_is_transient_and_only_wraps_actual_mutation():
    fake, store, scope, game = setup()
    seen = []

    @contextmanager
    def spinner(label):
        seen.append(("show", label))
        yield
        seen.append(("hide", label))

    fake.spinner = spinner
    assert ui._send_pending(store, scope)  # Nothing queued; no spinner.
    assert seen == []
    selected = scoring_options(ui._visual_dice(game, scope),
                               dict(zip(CATEGORIES, game["state"]["scores"])))[0]
    ui._queue(scope, ui.action_request(game, {"kind": "score", "category": selected.category}))
    assert ui._send_pending(store, scope)
    assert seen == [("show", "Saving score…"), ("hide", "Saving score…")]


def test_contrast_hotfix_covers_daily_native_text_and_weekly_disabled_tiles():
    assert 'APP_PUBLIC_VERSION = "Yahtzee Coach · v44.0.8"' in APP
    assert '[data-testid="stCaptionContainer"] p' in APP
    assert '[data-testid="stExpander"] summary p' in APP
    assert '.daily-progress-copy b,.score-section-head,.score-section-title' in APP
    assert '.score-box .filled-value' in APP
    assert '.leaderboard-list .leaderboard-name' in APP
    assert '[class*="_filled"] button:disabled p strong' in WEEKLY
    assert '[class*="_open"] button:disabled p strong' in WEEKLY
    assert '[class*="_available_zero"] button:not(:disabled)' in WEEKLY
    assert 'color:#30415e!important;-webkit-text-fill-color:#30415e!important' in WEEKLY
    assert 'color:#16733c!important;-webkit-text-fill-color:#16733c!important' in WEEKLY


def test_no_player_facing_developer_instruction_in_leaderboard():
    tree = ast.parse(APP)
    leaderboard = next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                       and n.name == "render_leaderboard_cards")
    assert isinstance(leaderboard.body[0], ast.Expr)
    assert isinstance(leaderboard.body[0].value, ast.Constant)
    assert leaderboard.body[0].value.value.startswith("Render a clean")


def test_core_public_game_rules_and_saved_roll_functions_untouched():
    # Frozen AST digests from v44.0.7 (shipped in the preceding browser ZIP).
    # This is more durable than comparing entire version-labeled source files.
    expected = {'action_request': 'b861b5b3246f287e44fc595f5e004db8cfa994c2b422e1cc44a7f83c014814c6', '_queue_start': '419ee7d36759560d80014d3a50b99fff1a5eb046a835846c3ab091463f506364', '_new_visual_roll': '4e0be104655eb21a23c57b2ab4f8e138bb63689624b9f8009b404b8c7e0e8766', '_visual_dice': 'f9a8839405667e3017e748e47fca3f6bd9faf1e50297d28f6e2f576732b03419', '_queue_roll': 'd30396f9e0a010d2690a7e2f9ed6964bf34dbc482dbf7950c771c64ac6e28fe2', '_reveal_first_roll': '06b67d700f9466651bfdb65b21738383ab36279d95aab0947c1ec5a0ce07f0a5', '_friends': '3f2961e6dfad3fe3da938fccc7a8a2975d5f33e5e3373aa1b5501f95e113bbf0', '_render_weekly_tile_section': '7841bb8d3c4c0de9447040e31b433df355fb6b9d950d8b264654046bc156183c', '_scorecard_picker': 'c29517feee8b45a1d3f1d0a0df60254ddcfbb388f0978ee9bd718ad642a35037'}
    current = _source_function_digest(WEEKLY, expected.keys())
    assert current == expected
    assert 'def scoring_options' not in WEEKLY
    assert not list(ROOT.glob('RUN_THIS_ONCE_IN_SUPABASE_v44_0_8*.sql'))
