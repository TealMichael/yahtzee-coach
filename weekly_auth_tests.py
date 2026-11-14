"""Login integration keeps optional browser persistence separate from Weekly auth."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class Session(dict):
    def __getattr__(self,k): return self[k]
    def __setattr__(self,k,v): self[k]=v


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.store=Mock()
        self.store.create_device_session.return_value='temporary-credential'
        self.session=Session(active_device_token='old-account-token')
        self.remember=Mock(return_value=True)
        self.delete=Mock()
        self.scope={'st':SimpleNamespace(session_state=self.session),
                    'load_daily_store':lambda:self.store,
                    '_remember_this_device':self.remember,
                    '_queue_remember_cookie_delete':self.delete}
        tree=ast.parse(Path(__file__).with_name('app.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_establish_player_session')
        exec(compile(ast.Module(body=[node],type_ignores=[]),'app.py','exec'),self.scope)

    def test_nonremembered_login_uses_one_day_server_only_session(self):
        self.assertTrue(self.scope['_establish_player_session']('player',False))
        self.store.create_device_session.assert_called_once_with('player',1)
        self.assertEqual(self.session.active_device_token,'temporary-credential')
        self.remember.assert_not_called()
        self.delete.assert_called_once()

    def test_remembered_login_keeps_existing_browser_path(self):
        self.assertTrue(self.scope['_establish_player_session']('player',True))
        self.remember.assert_called_once_with('player')
        self.store.create_device_session.assert_not_called()
        self.delete.assert_not_called()
        self.assertIsNone(self.session.active_device_token)

    def test_failed_temporary_session_never_keeps_previous_token(self):
        self.store.create_device_session.side_effect=RuntimeError('sensitive transport detail')
        self.assertFalse(self.scope['_establish_player_session']('player',False))
        self.assertIsNone(self.session.active_device_token)
        self.assertNotIn('sensitive',self.session.player_auth_flash)

if __name__=='__main__': unittest.main(verbosity=2)
