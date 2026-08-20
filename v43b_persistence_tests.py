from __future__ import annotations

"""Focused regression tests for Yahtzee Coach v43B persistence behavior.

Run:
    python v43b_persistence_tests.py

These tests deliberately use InMemoryDailyStore so they require no network,
Supabase account, Streamlit session, exact-policy file, or puzzle-bank file.
"""

from datetime import datetime, timezone

from daily_store import (
    AttemptAlreadyComplete,
    ChallengeMismatch,
    DuplicateAnswer,
    InMemoryDailyStore,
    InvalidOfficialAnswer,
    OutOfOrderAnswer,
    PlayerNameTaken,
)


class Clock:
    def __init__(self):
        self.tick = 0

    def __call__(self):
        self.tick += 1
        return datetime(2026, 8, 9, 16, 0, self.tick % 60, tzinfo=timezone.utc)


def add_challenge(store, date_key="2026-08-09", version="43A-bank42.6", suffix="a"):
    puzzle_ids = [f"{date_key}-{suffix}-p{i}" for i in range(1, 11)]
    challenge_id = f"{date_key}-{version}-{suffix}"
    return store.ensure_challenge(challenge_id, date_key, version, puzzle_ids)


def finish_attempt(store, player_id, challenge, losses):
    attempt, _ = store.get_or_create_attempt(player_id, challenge.challenge_id)
    for number, loss in enumerate(losses, start=1):
        store.save_answer(
            attempt.attempt_id,
            question_number=number,
            puzzle_id=challenge.puzzle_ids[number - 1],
            chosen_hold=[number % 6 + 1],
            optimal_hold=[6],
            points_lost=loss,
            solver_source="exact",
        )
    return store.complete_attempt(attempt.attempt_id)


def run():
    checks = []
    clock = Clock()
    codes = iter(["TEAL01", "TEAL02", "TEAL03"])
    store = InMemoryDailyStore(now_factory=clock, join_code_factory=lambda: next(codes))

    alice = store.create_player("Alice", "2468")
    bob = store.create_player("Bob", "1357")
    cara = store.create_player("Cara", "9876")
    checks.append(("PIN auth accepts correct PIN", store.authenticate_player("alice", "2468").player_id == alice.player_id))
    checks.append(("PIN auth rejects wrong PIN", store.authenticate_player("Alice", "0000") is None))
    checks.append(("PIN hash is not plaintext", store.players[alice.player_id].pin_hash != "2468" and store.players[alice.player_id].pin_hash.startswith("scrypt$")))
    try:
        store.create_player("ALICE", "1111")
        duplicate_name_ok = False
    except PlayerNameTaken:
        duplicate_name_ok = True
    checks.append(("return-by-name flow has case-insensitive unique display names", duplicate_name_ok))

    group = store.create_group(alice.player_id, "Dice Friends")
    joined = store.join_group(bob.player_id, group.join_code.lower())
    store.join_group(cara.player_id, group.join_code)
    checks.append(("group join code is case-insensitive", joined.group_id == group.group_id))
    checks.append(("group creator is automatically a member", group.group_id in {g.group_id for g in store.list_groups(alice.player_id)}))
    checks.append(("group membership stores multiple players", len([1 for gid, _ in store.group_members if gid == group.group_id]) == 3))
    members = store.list_group_members(group.group_id)
    checks.append(("group member directory exposes public player names", [row["display_name"] for row in members] == ["Alice", "Bob", "Cara"]))

    challenge = add_challenge(store)
    same = store.ensure_challenge(challenge.challenge_id, challenge.challenge_date, challenge.challenge_version, challenge.puzzle_ids)
    checks.append(("deterministic challenge registration is idempotent", same == challenge))
    try:
        store.ensure_challenge(challenge.challenge_id, challenge.challenge_date, "DIFFERENT", challenge.puzzle_ids)
        mismatch_ok = False
    except ChallengeMismatch:
        mismatch_ok = True
    checks.append(("challenge ID/version mismatch is rejected", mismatch_ok))

    attempt1, created1 = store.get_or_create_attempt(alice.player_id, challenge.challenge_id)
    attempt2, created2 = store.get_or_create_attempt(alice.player_id, challenge.challenge_id)
    checks.append(("one-attempt uniqueness returns same attempt", created1 and not created2 and attempt1.attempt_id == attempt2.attempt_id))

    store.save_answer(
        attempt1.attempt_id,
        question_number=1,
        puzzle_id=challenge.puzzle_ids[0],
        chosen_hold=[6, 6],
        optimal_hold=[6, 6],
        points_lost=0.0,
    )
    store.save_answer(
        attempt1.attempt_id,
        question_number=2,
        puzzle_id=challenge.puzzle_ids[1],
        chosen_hold=[5, 6],
        optimal_hold=[6, 6],
        points_lost=0.42,
    )
    resume = store.get_resume_state(alice.player_id, challenge.challenge_id)
    checks.append(("resume returns saved answers", len(resume.answers) == 2 and resume.next_question_number == 3))

    try:
        store.save_answer(
            attempt1.attempt_id,
            question_number=2,
            puzzle_id=challenge.puzzle_ids[1],
            chosen_hold=[1], optimal_hold=[2], points_lost=1.0,
        )
        duplicate_answer_ok = False
    except DuplicateAnswer:
        duplicate_answer_ok = True
    checks.append(("duplicate first-save answer is rejected", duplicate_answer_ok))

    revised = store.revise_answer(
        attempt1.attempt_id,
        question_number=2,
        puzzle_id=challenge.puzzle_ids[1],
        chosen_hold=[4, 6],
        optimal_hold=[6, 6],
        points_lost=0.42,
    )
    checks.append(("saved answer can be revised before completion", revised.chosen_hold == (4, 6) and revised.points_lost == 0.42))
    checks.append(("revising an earlier answer preserves resume position", store.get_resume_state(alice.player_id, challenge.challenge_id).next_question_number == 3))

    try:
        store.save_answer(
            attempt1.attempt_id,
            question_number=4,
            puzzle_id=challenge.puzzle_ids[3],
            chosen_hold=[1], optimal_hold=[2], points_lost=1.0,
        )
        out_of_order_ok = False
    except OutOfOrderAnswer:
        out_of_order_ok = True
    checks.append(("skipping ahead is rejected", out_of_order_ok))

    try:
        store.save_answer(
            attempt1.attempt_id,
            question_number=3,
            puzzle_id=challenge.puzzle_ids[2],
            chosen_hold=[1], optimal_hold=[2], points_lost=1.0,
            solver_source="legacy_fallback",
        )
        fallback_ok = False
    except InvalidOfficialAnswer:
        fallback_ok = True
    checks.append(("official Daily answer rejects heuristic fallback", fallback_ok))

    # Complete Alice's already-started attempt.
    for number in range(3, 11):
        store.save_answer(
            attempt1.attempt_id,
            question_number=number,
            puzzle_id=challenge.puzzle_ids[number - 1],
            chosen_hold=[6], optimal_hold=[6],
            points_lost=0.0 if number not in (5, 8) else 0.10,
        )
    alice_done = store.complete_attempt(attempt1.attempt_id)
    checks.append(("completion summary is calculated from final saved answers", abs(alice_done.total_ev_loss - 0.62) < 1e-12 and alice_done.exact_count == 7 and abs(alice_done.worst_miss - 0.42) < 1e-12))
    checks.append(("completed attempt resumes as complete", store.get_resume_state(alice.player_id, challenge.challenge_id).next_question_number is None))
    try:
        store.save_answer(
            attempt1.attempt_id,
            question_number=10,
            puzzle_id=challenge.puzzle_ids[9],
            chosen_hold=[], optimal_hold=[], points_lost=0,
        )
        completed_mutation_ok = False
    except AttemptAlreadyComplete:
        completed_mutation_ok = True
    checks.append(("completed attempt rejects new saves", completed_mutation_ok))
    try:
        store.revise_answer(
            attempt1.attempt_id,
            question_number=2,
            puzzle_id=challenge.puzzle_ids[1],
            chosen_hold=[6, 6], optimal_hold=[6, 6], points_lost=0.0,
        )
        completed_revision_ok = False
    except AttemptAlreadyComplete:
        completed_revision_ok = True
    checks.append(("completed attempt rejects revisions", completed_revision_ok))

    # Leaderboard tie contract: displayed Points Lost is the official competition score.
    # Bob and Alice both display 0.62, so exact-count differences do not break the tie.
    bob_losses = [0, 0, 0, 0, 0, 0, 0, 0, 0.31, 0.31]
    finish_attempt(store, bob.player_id, challenge, bob_losses)
    # Cara is lower at 0.50 and remains first.
    cara_losses = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0.50]
    finish_attempt(store, cara.player_id, challenge, cara_losses)
    board = store.leaderboard(group.group_id, challenge.challenge_id)
    checks.append(("leaderboard primary sort is lowest displayed Points Lost", [row["display_name"] for row in board][0] == "Cara"))
    alice_rank = next(row["rank"] for row in board if row["display_name"] == "Alice")
    bob_rank = next(row["rank"] for row in board if row["display_name"] == "Bob")
    checks.append(("same displayed Points Lost is a real tie despite different best-hold counts", alice_rank == bob_rank == 2))

    # Dave and Erin also tie at 1.00 even though their biggest misses differ.
    dave = store.create_player("Dave", "1234")
    erin = store.create_player("Erin", "5678")
    store.join_group(dave.player_id, group.join_code)
    store.join_group(erin.player_id, group.join_code)
    finish_attempt(store, dave.player_id, challenge, [0]*8 + [0.50, 0.50])
    finish_attempt(store, erin.player_id, challenge, [0]*8 + [0.75, 0.25])
    board2 = store.leaderboard(group.group_id, challenge.challenge_id)
    dave_rank = next(row["rank"] for row in board2 if row["display_name"] == "Dave")
    erin_rank = next(row["rank"] for row in board2 if row["display_name"] == "Erin")
    checks.append(("biggest miss no longer breaks a displayed-score tie", dave_rank == erin_rank == 4))

    stats = store.group_question_stats(group.group_id, challenge.challenge_id)
    q10 = next(row for row in stats if row["question_number"] == 10)
    checks.append(("group question analytics use completed real attempts", q10["players"] == 5 and q10["exact_count"] == 1 and q10["avg_loss"] > 0))

    # Streak calculations across challenge dates. Use a separate player to keep it simple.
    streaker = store.create_player("Streaker", "4321")
    for day in ("2026-08-06", "2026-08-07", "2026-08-08"):
        c = add_challenge(store, day, suffix=day[-2:])
        finish_attempt(store, streaker.player_id, c, [0.0] * 10)
    checks.append(("streak remains alive before today's completion", store.current_participation_streak(streaker.player_id, "2026-08-09") == 3))
    today_c = add_challenge(store, "2026-08-09", version="43B-test", suffix="today")
    finish_attempt(store, streaker.player_id, today_c, [0.0] * 10)
    checks.append(("streak increments on today's completion", store.current_participation_streak(streaker.player_id, "2026-08-09") == 4))
    gap_c = add_challenge(store, "2026-08-11", suffix="11")
    finish_attempt(store, streaker.player_id, gap_c, [0.0] * 10)
    checks.append(("streak resets after a missed calendar day", store.current_participation_streak(streaker.player_id, "2026-08-11") == 1))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print(f"{len(checks)} PASS / 0 FAIL")


if __name__ == "__main__":
    run()
