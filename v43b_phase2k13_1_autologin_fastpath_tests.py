# v44: approved six-puzzle format fingerprints refreshed; historical outputs and exact policy remain locked.
"""Phase 2K.13.1: remembered-login cookie fast-path guards."""
from __future__ import annotations

from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


require('APP_RELEASE = "v44.0 Weekly Challenge + Daily Six"' in APP, "release label is Phase 2K.13.1")

# The durable localStorage token must heal the first-party cookie so later fresh
# Streamlit connections can restore identity from the initial request.
bridge = APP[APP.index('_remember_storage_component ='):APP.index('_yesterday_results_storage_component =')]
require('document.cookie = `${cookieName}=${stored}; Path=/; Max-Age=${cookieMaxAge}; SameSite=Lax; Secure`' in bridge,
        "localStorage read synchronizes the fast first-party cookie")
require('document.cookie = `${cookieName}=; Path=/; Max-Age=0;' in bridge,
        "localStorage delete also clears the fast cookie")
require('"cookie_name": REMEMBER_COOKIE_NAME' in APP and '"cookie_max_age": REMEMBER_COOKIE_MAX_AGE' in APP,
        "cookie metadata is passed only to the browser bridge")

# A valid initial-request cookie must restore before the Components-v2 bridge is
# mounted, eliminating the bridge state update/rerun on future fresh launches.
start = APP.rindex('\ninitialize_state()\n')
main = APP[start:]
require(main.index('_restore_remembered_cookie_fast_path(_remember_cookie_token)') < main.index('render_remember_storage_bridge()'),
        "cookie authentication is attempted before localStorage is mounted")
require('if _remember_cookie_restored:' in main and '_remember_storage_state = {"token": "", "ready": True}' in main,
        "valid cookie path skips localStorage component mounting")

fast = APP[APP.index('def _restore_remembered_cookie_fast_path'):APP.index('def _restore_remembered_player')]
require(fast.index('authenticate_device_session(token)') < fast.index('st.session_state.remember_restore_checked = True'),
        "cookie is marked checked only after successful authentication")
require('if player is None:' in fast and 'return False' in fast,
        "stale cookie falls through instead of blocking localStorage recovery")
require('_restore_remembered_player(_remember_storage_state, cookie_token="")' in main,
        "fallback explicitly ignores an already-tried stale cookie")

# Security/behavior invariants.
require('return_pin' not in bridge, "PIN is never exposed to the browser remember bridge")
require('SameSite=Lax; Secure' in bridge, "healed cookie remains secure and same-site")
require('_queue_remember_cookie_delete()' in APP and 'revoke_device_session(token)' in APP,
        "sign-out still revokes server session and clears browser credentials")

# Hard freeze: this speedup must not touch gameplay, UI engines, persistence, or data banks.
EXPECTED_HASHES = {
    "yahtzee_engine.py": "9b175f3f3f59f9937943856c01e1e7aeced7662742756766a54a6061ccaba6b1",
    "exact_runtime.py": "322e50715ca49e53d78e9cc6eda85a7af0712b881273fb57ea4c4f4b67da171a",
    "exact_mode.py": "05b7b6db72d2a9fc8ca12852f1deae64e330cc48cdaa66e851f83c27ef333aaf",
    "puzzle_bank.py": "3616c5161828fcaa8adea853e4c2737bf2aaa693187b3c7caa801abe13bd8fbb",
    "daily_challenge.py": "e0177cf3b54fedb4b32383a01fe6ac9c6d1049db585f14d85d1d51220e126373",
    "daily_store.py": "771b7d0070226f853df4563dc6c75af27b3fb6d3317f5b8de06d1d82555c4916",
    "supabase_daily_store.py": "32a68b623e7e8af6e8e4a3a120f2c1c102138ae8f724718bfd059deb65a23d1f",
    "session_learning.py": "695ea20fcd82ffe8979b5900f34b929d15cedcc902dc8ef92c30a4baf999963a",
    "practice_progress.py": "8f78b05eb867e716fbe845c81969b12f33617a7cd5f7c8dd7fe09b04c4632915",
    "player_avatar.py": "a78416d7ea56910be580f1b42befc3acc0ba296fa9021198c564e32d48815add",
    "retro_podium.py": "168c8535403ece792a916dfd58723f521c0e0b0e61474dc5ada33953d23c6f2f",
    "exact_policy.npz": "cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b",
    "puzzle_bank.npz": "22f26f136a690c552fd7a8ad3a3335090f6085468219f197f16cea32e0276a8f",
    "challenge_catalog.npz": "fe92b90e4c2ce4261ac384711061756336af4b151e267946d26e4f8a4b649ecd",
    "requirements.txt": "70028a998b64b9ec45b936c9842ead5c4fd169fb0ae7a70d28a143fd5c6d92d0",
}
for name, expected in EXPECTED_HASHES.items():
    actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    require(actual == expected, f"{name} is byte-for-byte unchanged from Phase 2K.13")

print("\nPhase 2K.13.1 remembered-login fast-path regressions: PASS")
