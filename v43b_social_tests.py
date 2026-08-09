from __future__ import annotations

"""Focused v43B Phase 2D friend-group + real leaderboard regression checks."""

from pathlib import Path

from daily_store import InMemoryDailyStore


def _challenge(store):
    return store.ensure_challenge(
        "2026-08-09-social",
        "2026-08-09",
        "43A-bank42.6",
        [f"social-p{i}" for i in range(1, 11)],
    )


def _finish(store, player_id, challenge, losses):
    attempt, _ = store.get_or_create_attempt(player_id, challenge.challenge_id)
    for number, loss in enumerate(losses, start=1):
        store.save_answer(
            attempt.attempt_id,
            question_number=number,
            puzzle_id=challenge.puzzle_ids[number - 1],
            chosen_hold=[6],
            optimal_hold=[6],
            points_lost=loss,
            solver_source="exact",
        )
    return store.complete_attempt(attempt.attempt_id)


def run():
    checks = []
    codes = iter(["FRIEND", "SECOND"])
    store = InMemoryDailyStore(join_code_factory=lambda: next(codes))
    alice = store.create_player("Alice", "1234")
    bob = store.create_player("Bob", "2345")
    cara = store.create_player("Cara", "3456")

    group = store.create_group(alice.player_id, "Sunday Rollers")
    checks.append(("group creator is visible in public member directory", [m["display_name"] for m in store.list_group_members(group.group_id)] == ["Alice"]))
    store.join_group(bob.player_id, group.join_code.lower())
    store.join_group(cara.player_id, group.join_code)
    checks.append(("invite code joins real players case-insensitively", [m["display_name"] for m in store.list_group_members(group.group_id)] == ["Alice", "Bob", "Cara"]))

    challenge = _challenge(store)
    # Cara starts but does not finish; she must not leak partial competitive results.
    store.get_or_create_attempt(cara.player_id, challenge.challenge_id)
    _finish(store, alice.player_id, challenge, [0.0] * 9 + [0.40])
    _finish(store, bob.player_id, challenge, [0.0] * 8 + [0.10, 0.20])
    board = store.leaderboard(group.group_id, challenge.challenge_id)
    checks.append(("leaderboard contains only completed official attempts", [row["display_name"] for row in board] == ["Bob", "Alice"]))
    checks.append(("real leaderboard ranks by locked EV result", [row["rank"] for row in board] == [1, 2]))
    checks.append(("unfinished member remains a group member without a leaderboard score", len(store.list_group_members(group.group_id)) == 3 and all(row["display_name"] != "Cara" for row in board)))

    stats = store.group_question_stats(group.group_id, challenge.challenge_id)
    checks.append(("group question story uses completed real answers", len(stats) == 10 and all(row["players"] == 2 for row in stats)))

    source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    backend = Path(__file__).with_name("supabase_daily_store.py").read_text(encoding="utf-8")
    checks.append(("Daily UI can create friend groups", 'create_friend_group_form' in source and '.create_group(' in source))
    checks.append(("Daily UI can join groups by invite code", 'join_friend_group_form' in source and '.join_group(' in source))
    checks.append(("players can select among multiple groups", 'friend_group_selector' in source and 'active_group_id' in source))
    checks.append(("live Daily results call the real database leaderboard", 'store.leaderboard(active.group.group_id' not in source and 'store.leaderboard(active.group_id' in source))
    checks.append(("live Daily results refresh real group question stats", 'store.group_question_stats(active.group_id' in source))
    checks.append(("simulated friend board is no longer imported by the live app", 'build_leaderboard' not in source and 'group_story' not in source and 'user_rank' not in source))
    checks.append(("Supabase backend exposes real member directory", 'def list_group_members(self, group_id: str)' in backend))
    checks.append(("results explain that only completed attempts appear", 'Only completed official attempts appear' in source))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
