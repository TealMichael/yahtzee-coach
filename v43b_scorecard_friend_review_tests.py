from pathlib import Path

from daily_store import DailyStoreError, GroupNotFound, InMemoryDailyStore

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def complete(store, player_id, challenge_id, losses=None):
    attempt, _ = store.get_or_create_attempt(player_id, challenge_id)
    losses = losses or [0.0] * 10
    for q in range(1, 11):
        store.save_answer(
            attempt.attempt_id,
            question_number=q,
            puzzle_id=f"p{q}",
            chosen_hold=[q % 6 + 1],
            optimal_hold=[6],
            points_lost=float(losses[q - 1]),
            solver_source="exact",
        )
    store.complete_attempt(attempt.attempt_id)
    return attempt


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    backend = (ROOT / "supabase_daily_store.py").read_text(encoding="utf-8")
    contract = (ROOT / "daily_store.py").read_text(encoding="utf-8")

    checks = [
        ('APP_RELEASE = "v43B Phase 2K.12.1"' in app, "release advances to Phase 2K.9.1"),
        ("CATEGORY_SCORECARD = dict(CATEGORY_SHORT)" in app, "live scorecard restores original short labels"),
        ("font-size:1.02rem; font-weight:950" in app, "score values are larger than compact 2K.6.1 layout"),
        ("min-height:2.45rem" in app, "score boxes are slightly larger while retaining compact grid"),
        (app.count(".score-grid.lower { grid-template-columns:repeat(4") >= 2, "lower scorecard remains four columns on phones"),
        ("open_chips_html" not in app[app.index("def render_scorecard(scorecard):"):app.index("def install_dice_scroll_guard")], "no duplicate open-box row returns"),
        ("def group_player_daily_review" in contract and "def group_player_daily_review" in backend, "friend-review persistence path exists in both stores"),
        ("Finish your own Daily before reviewing a friend's choices." in contract and "Finish your own Daily before reviewing a friend's choices." in backend, "store blocks spoilers until viewer finishes"),
        ("That player has not finished this Daily yet." in contract and "That player has not finished this Daily yet." in backend, "store blocks unfinished-friend answers"),
        ("👀 Peek at a Friend's Picks" in app and "_render_friend_pick_peek(active_group, board)" in app, "friend picks live in a separate optional section below personal results"),
        ("You made different" not in app and "biggest miss was Q" not in app, "side-by-side comparison analytics are removed"),
        ("See {friend_name}'s 10 picks" in app and "Q{q}" in app, "friend peek shows a simple ten-pick list"),
        ("_cached_group_player_daily_review" in app, "friend picks still use the spoiler-safe immutable review path"),
    ]
    for ok, message in checks:
        require(ok, message)

    # Behavior test: detailed answers are inaccessible until both group members finish.
    store = InMemoryDailyStore()
    alice = store.create_player("Alice", "1234")
    bob = store.create_player("Bob", "5678")
    outsider = store.create_player("Outsider", "9012")
    group = store.create_group(alice.player_id, "Testers")
    store.join_group(bob.player_id, group.join_code)
    store.ensure_challenge("c1", "2026-08-16", "test", [f"p{i}" for i in range(1, 11)])

    try:
        store.group_player_daily_review(group.group_id, "c1", alice.player_id, bob.player_id)
        require(False, "viewer cannot review before finishing")
    except DailyStoreError:
        require(True, "viewer cannot review before finishing")

    complete(store, alice.player_id, "c1")
    try:
        store.group_player_daily_review(group.group_id, "c1", alice.player_id, bob.player_id)
        require(False, "unfinished friend remains private")
    except DailyStoreError:
        require(True, "unfinished friend remains private")

    complete(store, bob.player_id, "c1", [0, .2, 0, 1.1, 0, 0, .4, 0, 0, .1])
    review = store.group_player_daily_review(group.group_id, "c1", alice.player_id, bob.player_id)
    require(review["display_name"] == "Bob", "finished friend identity returned")
    require(len(review["answers"]) == 10, "all ten immutable friend answers returned")
    require(abs(review["summary"]["total_ev_loss"] - 1.8) < 1e-9, "friend summary matches saved losses")

    try:
        store.group_player_daily_review(group.group_id, "c1", alice.player_id, outsider.player_id)
        require(False, "non-group player cannot be reviewed")
    except GroupNotFound:
        require(True, "non-group player cannot be reviewed")

    print("Phase 2K.7 scorecard + friend review checks passed")


if __name__ == "__main__":
    run()
