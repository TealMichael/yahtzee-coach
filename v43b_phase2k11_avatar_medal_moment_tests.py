from datetime import datetime, timezone
from pathlib import Path

from daily_store import InMemoryDailyStore
from player_avatar import AVATAR_CHOICES, avatar_svg, default_avatar_for_player, normalize_avatar_config
from retro_podium import medal_moment_copy, personal_medal_moment_html

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def complete(store, player_id, challenge_id, total_loss):
    attempt, _ = store.get_or_create_attempt(player_id, challenge_id)
    per = float(total_loss) / 10.0
    challenge = store.challenges[challenge_id]
    for q in range(1, 11):
        store.save_answer(
            attempt.attempt_id,
            question_number=q,
            puzzle_id=challenge.puzzle_ids[q - 1],
            chosen_hold=[1],
            optimal_hold=[1],
            points_lost=per,
            solver_source="exact",
        )
    return store.complete_attempt(attempt.attempt_id)


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    migration = (ROOT / "v43b_phase2k11_player_avatar_migration.sql").read_text(encoding="utf-8")
    retro = (ROOT / "retro_podium.py").read_text(encoding="utf-8")

    require('APP_RELEASE = "v43B Phase 2K.11.2"' in app, "release advances to Phase 2K.11.1 visual alignment patch")
    require("CREATE YOUR PLAYER" in app and "🎲 Randomize player" in app, "light avatar creator is available")
    for category in ("hair", "outfit", "skin", "accessory", "shoes"):
        require(category in AVATAR_CHOICES and len(AVATAR_CHOICES[category]) >= 4, f"{category} has a small useful option set")
    require("avatar_config jsonb" in migration and "avatar_setup_complete" in migration, "avatar choices persist with one additive migration")
    require("player_medal_totals" in app and "_cached_player_medal_totals" in app, "medal history is derived from Daily results")
    require("personal_medal_moment_html" in app, "app uses the simpler personal medal moment")
    require(".stadium-light" not in retro and ".podium-step" not in retro and "confettiFall" not in retro, "busy stadium/podium movie is removed")

    bad = {"hair": "not-real", "skin": "dark", "outfit": "red_tee", "accessory": "none", "shoes": "white"}
    normalized = normalize_avatar_config(bad)
    require(normalized["hair"] != "not-real" and normalized["skin"] == "dark", "avatar config fails safely to supported choices")
    require(default_avatar_for_player("abc") == default_avatar_for_player("abc"), "legacy-player default avatar is stable")
    svg = avatar_svg({"hair": "curly", "outfit": "pink_tee", "skin": "light", "accessory": "glasses", "shoes": "red"})
    require("<svg" in svg and "shape-rendering:crispEdges" in svg, "avatar renders as lightweight crisp inline pixel SVG")

    fixed_now = lambda: datetime(2026, 8, 17, 16, 0, tzinfo=timezone.utc)
    store = InMemoryDailyStore(now_factory=fixed_now, join_code_factory=lambda: "MEDAL1")
    me = store.create_player("Mike", "1111")
    friend = store.create_player("Jenny", "2222")
    third = store.create_player("Paul", "3333")
    group = store.create_group(me.player_id, "Friends")
    store.join_group(friend.player_id, group.join_code)
    store.join_group(third.player_id, group.join_code)

    profile = store.get_player_profile(me.player_id)
    require(not profile["avatar_setup_complete"], "legacy/new player can start with avatar setup incomplete")
    saved = store.save_player_avatar(me.player_id, {"hair": "curly", "outfit": "red_tee", "skin": "warm", "accessory": "none", "shoes": "black"})
    require(saved["avatar_setup_complete"] and saved["avatar_config"]["hair"] == "curly", "avatar save round-trips through store contract")

    # Three finalized group days: tie-for-gold, silver, bronze.
    for idx, day in enumerate(("2026-08-18", "2026-08-19", "2026-08-20"), start=1):
        cid = f"c{idx}"
        store.ensure_challenge(cid, day, "test", [f"{cid}-p{i}" for i in range(1, 11)])
    complete(store, me.player_id, "c1", 1.771)
    complete(store, friend.player_id, "c1", 1.774)  # both display 1.77 -> shared gold
    complete(store, third.player_id, "c1", 2.72)
    complete(store, friend.player_id, "c2", 1.0)
    complete(store, me.player_id, "c2", 2.0)
    complete(store, third.player_id, "c2", 3.0)
    complete(store, friend.player_id, "c3", 1.0)
    complete(store, third.player_id, "c3", 2.0)
    complete(store, me.player_id, "c3", 3.0)

    medals = store.player_medal_totals(me.player_id, group.group_id, "2026-08-20")
    require(medals == {"gold": 1, "silver": 1, "bronze": 1, "total": 3}, "all-time medal counter follows real tie-aware leaderboard results")
    earlier = store.player_medal_totals(me.player_id, group.group_id, "2026-08-19")
    require(earlier["bronze"] == 0 and earlier["total"] == 2, "medal counter respects finalized through-date cutoff")

    # A historical duplicate challenge version for one date must never award a second medal.
    store.ensure_challenge("c2-alt", "2026-08-19", "alt", [f"c2-alt-p{i}" for i in range(1, 11)])
    complete(store, me.player_id, "c2-alt", 0.5)
    complete(store, friend.player_id, "c2-alt", 4.0)
    require(store.player_medal_totals(me.player_id, group.group_id, "2026-08-20")["total"] == 3, "one calendar day cannot double-count medals across historical challenge versions")

    board = store.leaderboard(group.group_id, "c1")
    title, sub, rank = medal_moment_copy(board, me.player_id)
    require(rank == 1 and title == "TIED FOR GOLD!", "personal ceremony handles shared gold directly")
    moment = personal_medal_moment_html(
        board,
        active_player_id=me.player_id,
        active_player_name="Mike <T>",
        group_name="Friends & Family",
        date_label="August 18, 2026",
        avatar_config=saved["avatar_config"],
        medal_totals=medals,
    )
    require("PIXEL MIKE" in moment and "Mike &lt;T&gt;" in moment, "Pixel Mike hands the medal to the signed-in player's escaped sprite")
    require("ALL-TIME MEDALS" in moment and "🥇" in moment and "🥈" in moment and "🥉" in moment, "all-time medal totals sit in every personal result moment")
    require("SKIP ›" in moment and "prefers-reduced-motion" in moment and "<audio" not in moment.lower(), "medal moment stays skippable, accessible, and silent")

    print("Phase 2K.11 player avatar + personal medal moment checks passed")


if __name__ == "__main__":
    run()
