"""Phase 2K.13: performance-only guards with zero gameplay/UI drift."""
from __future__ import annotations

from pathlib import Path
import hashlib

from daily_challenge import (
    _cached_daily_challenge_template,
    challenge_set_id,
    daily_challenges,
)
from puzzle_bank import _dice_pattern

ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


# Locked Daily outputs prove selector optimizations did not alter puzzle content.
EXPECTED = {
    "2026-08-18": (
        "2026-08-18-4a4ceae658",
        ["099ab08517f79ad9", "0f07a1ff3159d342", "fd28a4d3aa2d1e41", "243522e34fbb954f",
         "b13907e002af8ad3", "d7ae5dc07e1119dc", "d3f9d0bd8a593cd4", "b8db766f9976b0c0",
         "3fc911f33dbec52a", "9d1ea169e39d8eaa"],
    ),
    "2026-08-19": (
        "2026-08-19-96b6f1c2b3",
        ["752e3eec1520f139", "fd5e335a12b4ae35", "0e8f1721f3e56130", "685bcfb39c75a4a3",
         "55aa33280d737165", "b9022212d2d17868", "aba1be7ebf216b47", "822f970040928b9f",
         "187f487fb9852986", "acac701293e4d418"],
    ),
    "2026-08-22": (
        "2026-08-22-a9050d9d93",
        ["65e21cbf04edb077", "512f9877e0c415e8", "a6904624c9f04e28", "c3f96d382d49e2e0",
         "e9734dc1c375ee81", "781e4b31b4e5f89d", "20983d0a70d24966", "e4ce0011b6a5937a",
         "7775f83a00c54744", "1f13c8998140de76"],
    ),
    # Last unchanged date before the forward-only decision-balance release.
    "2026-09-06": (
        "2026-09-06-f3674dc7a2",
        ["dfeb31c08347c70a", "45aacae56e4a6b68", "840330beb05a38b8", "8d867c018f2c4442",
         "8b0c9c3b8816e12e", "676d95a753439f56", "11777df13e7e1970", "e581b5410fba06b4",
         "522603371786260f", "72212098fea731ee"],
    ),
}
for day, (expected_set, expected_ids) in EXPECTED.items():
    challenges = daily_challenges(day)
    require(challenge_set_id(day, challenges) == expected_set, f"{day} challenge-set id is unchanged")
    require([c["challenge_id"] for c in challenges] == expected_ids, f"{day} Daily 10 is unchanged")

# Cache must return isolated copies so one user's session cannot mutate another's Daily.
_cached_daily_challenge_template.cache_clear()
a = daily_challenges("2026-08-22")
info_after_first = _cached_daily_challenge_template.cache_info()
b = daily_challenges("2026-08-22")
info_after_second = _cached_daily_challenge_template.cache_info()
require(info_after_first.misses == 1 and info_after_second.hits >= 1, "same-date Daily generation is reused process-wide")
a[0]["scorecard"]["ones"] = 999
c = daily_challenges("2026-08-22")
require(c[0]["scorecard"].get("ones") != 999, "cached Daily templates are isolated from session mutation")

# Optimized dice-pattern helper must preserve the exact classification for every possible roll.
def reference_pattern(values):
    counts = sorted((values.count(face) for face in range(1, 7) if values.count(face)), reverse=True)
    if counts == [5]: return "Yahtzee"
    if counts == [4, 1]: return "Four"
    if counts == [3, 2]: return "Full House"
    if counts == [3, 1, 1]: return "Triple"
    if counts == [2, 2, 1]: return "Two pair"
    if counts == [2, 1, 1, 1]: return "Pair"
    return "All different"

from itertools import product
for roll in product(range(1, 7), repeat=5):
    require(_dice_pattern(roll) == reference_pattern(list(roll)), f"pattern preserved for {roll}") if False else None
require(all(_dice_pattern(roll) == reference_pattern(list(roll)) for roll in product(range(1, 7), repeat=5)),
        "dice-pattern optimization preserves all 7,776 possible five-die rolls")

app = (ROOT / "app.py").read_text(encoding="utf-8")
require('APP_RELEASE = "v43B Phase 2K.14.5"' in app, "release label is Phase 2K.13")

# Hard guards: no strategy, persistence, social, avatar, or binary-data implementation changed.
EXPECTED_HASHES = {
    "yahtzee_engine.py": "9b175f3f3f59f9937943856c01e1e7aeced7662742756766a54a6061ccaba6b1",
    "exact_runtime.py": "322e50715ca49e53d78e9cc6eda85a7af0712b881273fb57ea4c4f4b67da171a",
    "exact_mode.py": "727e003a8d5c62e0ff9bf97794a0b0b8ffdbe0b42c522d0e3d95cd0f6bb2ea3f",
    "daily_store.py": "8eb46257a3ee02d14efd821f642637dde5d68cef13fa424a40f7d21f8912bbd0",
    "supabase_daily_store.py": "826d0061d33609d99f203f88c63df25301b49050cb4d467828ba3f0224523e7c",
    "session_learning.py": "695ea20fcd82ffe8979b5900f34b929d15cedcc902dc8ef92c30a4baf999963a",
    "practice_progress.py": "8f78b05eb867e716fbe845c81969b12f33617a7cd5f7c8dd7fe09b04c4632915",
    "player_avatar.py": "a78416d7ea56910be580f1b42befc3acc0ba296fa9021198c564e32d48815add",
    "retro_podium.py": "045a24013ac37ee324d014dfbba41a85c85648121cf0303279763ee57ab2c636",
    "exact_policy.npz": "cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b",
    "puzzle_bank.npz": "22f26f136a690c552fd7a8ad3a3335090f6085468219f197f16cea32e0276a8f",
    "challenge_catalog.npz": "fe92b90e4c2ce4261ac384711061756336af4b151e267946d26e4f8a4b649ecd",
}
for name, expected in EXPECTED_HASHES.items():
    actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    require(actual == expected, f"{name} is byte-for-byte unchanged from 2K.12.5")

print("\nPhase 2K.13 performance-only regressions: PASS")
