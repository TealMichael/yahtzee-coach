"""v44.0.6 cosmetic Weekly polish: offline, no live project or real attempts."""
from pathlib import Path
from types import SimpleNamespace

from weekly_game_flow_ui_tests import setup
import weekly_ui as ui

SRC = Path(ui.__file__).read_text()
APP = Path(__file__).with_name('app.py').read_text()


def test_round_three_uses_a_status_panel_instead_of_collapsing_roll_slot():
    fake, store, scope, game = setup()
    ui._reveal_first_roll(scope, game)
    game = store.act(game['game_id'], expected_revision=0, request_id='local-test-roll2', action={'kind':'reroll'})
    game = store.act(game['game_id'], expected_revision=1, request_id='local-test-roll3', action={'kind':'reroll'})
    fake.buttons.clear()
    ui._play(game, scope)
    assert any('weekly-final-roll-banner' in value for value in fake.markdowns)
    assert any('Final roll — choose a score' in value for value in fake.markdowns)
    assert not any('Roll Dice · 4' in name for name,_ in fake.buttons)
    assert len([1 for name, props in fake.buttons if '_category_' in props.get('key','')])==13
    assert len(store.calls)==2  # The UI itself must not save a new action.


def test_saved_zero_and_zero_point_offers_still_legal():
    fake, store, scope, game = setup()
    dice = ui._visual_dice(game, scope)
    ui._reveal_first_roll(scope, game)
    ui._scorecard_picker(game, scope, dice, True, 'polish')
    available = [name for name, props in fake.buttons if '_category_' in props.get('key','') and not props['disabled']]
    assert available
    assert any('**+0**' in name for name in available)
    assert any('**+' in name and '**+0**' not in name for name in available)
    assert 'options[category].points > 0' in SRC
    assert '_available_gain' in SRC and '_available_zero' in SRC
    assert store.calls == []


def test_roll_animation_restarts_in_mobile_webkit_without_changing_saved_dice():
    fake, store, scope, game = setup()
    capture = []
    fake.components = SimpleNamespace(v1=SimpleNamespace(html=lambda s,**kw: capture.append((s,kw))))
    ui._mobile_summary_visibility_watcher(False, animate_indices=(0,2,4), animation_token='example-game:revision-3')
    assert len(capture)==1
    script = capture[0][0]
    assert '[0, 2, 4]' in script
    assert 'example-game:revision-3' in script
    assert 'die.style.setProperty' in script and 'void die.offsetWidth' in script
    assert "prefers-reduced-motion: reduce" in script
    assert '__ycWeeklyLastAnimated' in script
    assert 'SCROLL_AFTER_SCORE' not in script
    assert 'ROLL_POSITIONS' not in script and 'ROLL_TOKEN' not in script
    assert store.calls == []


def test_rendered_animation_is_only_for_unheld_dice():
    css=ui._roll_animation_css([1,3])
    assert 'button:nth-child(2)' in css and 'button:nth-child(4)' in css
    assert 'button:nth-child(1)' not in css and 'button:nth-child(3)' not in css
    assert 'weekly-face-shuffle' in css
    assert 'fetch(' not in css


def test_no_database_migration_and_version_only_cosmetic_changes():
    assert 'APP_PUBLIC_VERSION = "Yahtzee Coach · v44.0.7"' in APP
    assert 'def _new_visual_roll' in SRC
    assert 'def _send_pending' in SRC
    assert 'def _queue_roll' in SRC
    assert 'def action_request' in SRC
    assert '"kind":"score"' in SRC
    assert '"kind":"reroll"' in SRC
