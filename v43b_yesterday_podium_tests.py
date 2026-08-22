from pathlib import Path

from daily_store import InMemoryDailyStore

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def complete(store, player_id, challenge_id, total_loss):
    attempt, _ = store.get_or_create_attempt(player_id, challenge_id)
    per_question = float(total_loss) / 10.0
    for q in range(1, 11):
        store.save_answer(attempt.attempt_id, question_number=q, puzzle_id=f"p{q}", chosen_hold=[1], optimal_hold=[1], points_lost=per_question, solver_source="exact")
    return store.complete_attempt(attempt.attempt_id)


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    checks = [
        ('APP_RELEASE = "v43B Phase 2K.12.2"' in app, "release advances to Phase 2K.11"),
        ("Yesterday's Final Standings" in app, "new-day recap remains clearly final"),
        ("_challenge_set_id_for_date(yesterday)" in app, "yesterday's deterministic challenge id is preserved"),
        ("personal_medal_moment_html(" in app and "components.html(ceremony" in app, "next-day recap uses personal Pixel Mike medal moment"),
        ("with st.expander(\"View yesterday's standings\", expanded=False):" in app, "full board stays available on demand"),
        ("YESTERDAY_RESULTS_STORAGE_PREFIX" in app and "window.localStorage.setItem(key, value)" in app, "once-per-day acknowledgement remains browser-local"),
        ("if len(members) > 1:" in app, "solo groups still avoid meaningless social medals"),
    ]
    for ok, message in checks:
        require(ok, message)

    store = InMemoryDailyStore()
    gold = store.create_player("Gold", "1111")
    silver = store.create_player("Silver", "2222")
    bronze = store.create_player("Bronze", "3333")
    fourth = store.create_player("Fourth", "4444")
    group = store.create_group(gold.player_id, "Podium Test")
    for player in (silver, bronze, fourth):
        store.join_group(player.player_id, group.join_code)
    store.ensure_challenge("yesterday-c1", "2026-08-20", "test", [f"p{i}" for i in range(1, 11)])
    complete(store, fourth.player_id, "yesterday-c1", 4.0)
    complete(store, bronze.player_id, "yesterday-c1", 3.0)
    complete(store, gold.player_id, "yesterday-c1", 1.0)
    complete(store, silver.player_id, "yesterday-c1", 2.0)
    board = store.leaderboard(group.group_id, "yesterday-c1")
    require([row["display_name"] for row in board] == ["Gold", "Silver", "Bronze", "Fourth"], "final board preserves official ranking order")
    require([row["rank"] for row in board[:3]] == [1, 2, 3], "personal medal rank maps directly from official board")
    print("Yesterday final standings + personal medal moment checks passed")


if __name__ == "__main__":
    run()
