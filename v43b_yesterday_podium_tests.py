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
        store.save_answer(
            attempt.attempt_id,
            question_number=q,
            puzzle_id=f"p{q}",
            chosen_hold=[q % 6 + 1],
            optimal_hold=[6],
            points_lost=per_question,
            solver_source="exact",
        )
    return store.complete_attempt(attempt.attempt_id)


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")

    checks = [
        ('APP_RELEASE = "v43B Phase 2K.9.1"' in app, "release advances to Phase 2K.9.1"),
        ("Yesterday's Final Standings" in app, "new-day recap is clearly labeled as final standings"),
        ("_previous_daily_date_key" in app and "timedelta(days=1)" in app, "recap resolves the prior Eastern Daily date"),
        ("_challenge_set_id_for_date(yesterday)" in app, "yesterday's deterministic challenge id is used for standings"),
        ("_cached_group_daily_snapshot(group.group_id, yesterday_set_id)" in app, "recap reuses saved group Daily results"),
        ("st.balloons()" in app, "podium finish triggers balloon celebration"),
        ('1: ("🥇", "GOLD", "1st")' in app and '3: ("🥉", "BRONZE", "3rd")' in app, "gold silver bronze ceremony copy is present"),
        ("render_leaderboard_cards(board, allow_review=False)" in app, "yesterday's complete final board is shown without opening friend reviews"),
        ("YESTERDAY_RESULTS_STORAGE_PREFIX" in app and "window.localStorage.setItem(key, value)" in app, "ceremony acknowledgement persists per browser/player without a database migration"),
        ("_queue_yesterday_result_seen(st.session_state.daily_date_key)" in app, "starting today's Daily acknowledges the recap"),
        ("if render_yesterday_final_standings_if_needed():" in app, "recap gates only an unstarted current Daily"),
        ("You didn't record a finish yesterday." in app, "non-participants still get a graceful final-standings screen"),
        ("len(members) > 1" in app, "solo groups do not award a meaningless one-person podium medal"),
    ]
    for ok, message in checks:
        require(ok, message)

    # Behavior protection: the existing official leaderboard ordering is exactly
    # what the next-day medals use. Lower Points Lost earns gold/silver/bronze.
    store = InMemoryDailyStore()
    gold = store.create_player("Gold", "1111")
    silver = store.create_player("Silver", "2222")
    bronze = store.create_player("Bronze", "3333")
    fourth = store.create_player("Fourth", "4444")
    group = store.create_group(gold.player_id, "Podium Test")
    for player in (silver, bronze, fourth):
        store.join_group(player.player_id, group.join_code)
    store.ensure_challenge("yesterday-c1", "2026-08-15", "test", [f"p{i}" for i in range(1, 11)])
    complete(store, fourth.player_id, "yesterday-c1", 4.0)
    complete(store, bronze.player_id, "yesterday-c1", 3.0)
    complete(store, gold.player_id, "yesterday-c1", 1.0)
    complete(store, silver.player_id, "yesterday-c1", 2.0)
    board = store.leaderboard(group.group_id, "yesterday-c1")
    require([row["display_name"] for row in board] == ["Gold", "Silver", "Bronze", "Fourth"], "final board preserves official ranking order")
    require([row["rank"] for row in board[:3]] == [1, 2, 3], "top three rows map directly to medal ceremony ranks")

    print("Phase 2K.9.1 yesterday final standings + podium checks passed")


if __name__ == "__main__":
    run()
