"""Weekly rules, deterministic dice and saved-state regression tests.

Run directly with Python; no database, secrets, network or pytest is required.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from itertools import product
import json
import random
import unittest
from zoneinfo import ZoneInfo

from weekly_game import (
    CATEGORIES, DICE_VERSION, RULES_VERSION, DiceSchedule, GameComplete,
    GameExpired, GameState, InvalidAction, RollRecord, StaleState,
    UnsupportedVersion, WeeklyGameError, apply_action, current_week_id,
    generate_schedule, new_game, score_totals, scoring_options, validate_state,
    week_bounds,
)

WEEK = "2026-11-09"
NOW = datetime(2026, 11, 11, 18, 0, tzinfo=ZoneInfo("America/New_York"))
SECRET = bytes(range(32))


def blank():
    return dict.fromkeys(CATEGORIES)


def options(dice, scorecard=None):
    return {o.category: o for o in scoring_options(dice, blank() if scorecard is None else scorecard)}


def advance(state, schedule, kind, **fields):
    return apply_action(state, schedule, {"kind": kind, **fields},
                        expected_revision=state.revision, now=NOW)


def fixed_schedule(dice=(6, 6, 6, 6, 6)):
    return DiceSchedule(WEEK, tuple((tuple(dice),) * 3 for _ in range(13)))


class ScoringTests(unittest.TestCase):
    def test_every_ordinary_hand_against_independent_reference(self):
        # Covers all 7,776 ordered hands and all thirteen categories. The
        # reference predates Weekly and is not used by the implementation.
        from yahtzee_engine import calculate_all_scores
        for dice in product(range(1, 7), repeat=5):
            result = options(dice)
            self.assertEqual({c: o.points for c, o in result.items()}, calculate_all_scores(list(dice)))
            self.assertTrue(all(o.yahtzee_bonus == 0 for o in result.values()))

    def test_each_upper_category_counts_only_its_face(self):
        for face, category in enumerate(CATEGORIES[:6], 1):
            dice = [face] * 3 + [face % 6 + 1] * 2
            self.assertEqual(options(dice)[category].points, 3 * face)

    def test_three_and_four_kind_require_their_counts(self):
        for dice, three, four in [([2, 2, 2, 1, 6], 13, 0), ([3, 3, 3, 3, 2], 14, 14),
                                  ([1, 1, 2, 2, 5], 0, 0)]:
            self.assertEqual(options(dice)["three_of_a_kind"].points, three)
            self.assertEqual(options(dice)["four_of_a_kind"].points, four)

    def test_full_house_needs_three_plus_two_without_joker(self):
        self.assertEqual(options([2, 2, 2, 5, 5])["full_house"].points, 25)
        self.assertEqual(options([5] * 5)["full_house"].points, 0)
        self.assertEqual(options([2, 2, 2, 5, 6])["full_house"].points, 0)

    def test_straights_allow_duplicates_only_for_small(self):
        self.assertEqual(options([1, 2, 3, 4, 4])["small_straight"].points, 30)
        self.assertEqual(options([1, 2, 3, 4, 4])["large_straight"].points, 0)
        self.assertEqual(options([2, 3, 4, 5, 6])["large_straight"].points, 40)
        self.assertEqual(options([1, 2, 3, 5, 6])["small_straight"].points, 0)

    def test_first_yahtzee_does_not_force_yahtzee_box(self):
        result = options([3] * 5)
        self.assertEqual(len(result), 13)
        self.assertEqual(result["yahtzee"].points, 50)
        self.assertEqual(result["threes"].points, 15)
        self.assertEqual(result["large_straight"].points, 0)

    def test_repeat_forces_matching_upper_for_fifty_and_zero(self):
        for previous in (0, 50):
            for face in range(1, 7):
                card = blank()
                card["yahtzee"] = previous
                result = options([face] * 5, card)
                category = CATEGORIES[face - 1]
                self.assertEqual(list(result), [category])
                self.assertEqual(result[category].points, 5 * face)
                self.assertEqual(result[category].yahtzee_bonus, 100 if previous == 50 else 0)

    def test_joker_lower_scores_when_matching_upper_used(self):
        for previous in (0, 50):
            card = blank()
            card["yahtzee"] = previous
            card["fours"] = 0  # Filled with zero counts as filled.
            result = options([4] * 5, card)
            self.assertEqual({c: o.points for c, o in result.items()}, {
                "three_of_a_kind": 20, "four_of_a_kind": 20, "full_house": 25,
                "small_straight": 30, "large_straight": 40, "chance": 20,
            })
            self.assertTrue(all(o.yahtzee_bonus == (100 if previous == 50 else 0) for o in result.values()))

    def test_joker_uses_upper_zero_only_after_all_lower_filled(self):
        for previous in (0, 50):
            card = blank()
            for c in CATEGORIES[6:]:
                card[c] = 0
            card["yahtzee"] = previous
            card["sixes"] = 30
            result = options([6] * 5, card)
            self.assertEqual(set(result), set(CATEGORIES[:5]))
            self.assertTrue(all(o.points == 0 for o in result.values()))
            self.assertTrue(all(o.yahtzee_bonus == (100 if previous == 50 else 0) for o in result.values()))

    def test_repeat_bonus_is_not_awarded_for_an_ordinary_hand(self):
        card = blank()
        card["yahtzee"] = 50
        self.assertTrue(all(o.yahtzee_bonus == 0 for o in options([1, 2, 3, 4, 5], card).values()))

    def test_filled_categories_never_appear(self):
        for category in CATEGORIES:
            card = blank()
            card[category] = 0
            self.assertNotIn(category, options([1, 2, 3, 4, 5], card))

    def test_upper_bonus_exact_boundary(self):
        card = blank()
        card.update(dict(zip(CATEGORIES[:6], (2, 6, 9, 12, 15, 18))))
        self.assertEqual(score_totals(card)["upper_bonus"], 0)
        card["ones"] = 3
        self.assertEqual(score_totals(card)["upper_bonus"], 35)
        self.assertEqual(score_totals(card)["total"], 98)
        card["ones"] = 5
        self.assertEqual(score_totals(card)["upper_bonus"], 35)

    def test_all_total_components_include_each_bonus_once(self):
        card = dict(zip(CATEGORIES, (3, 6, 9, 12, 15, 18, 24, 26, 25, 30, 40, 50, 22)))
        total = score_totals(card, 2)
        self.assertEqual(total, {"upper": 63, "lower": 217, "upper_bonus": 35,
                                 "yahtzee_bonus": 200, "total": 515})

    def test_reject_malformed_dice(self):
        for dice in ([1, 2], [1, 2, 3, 4, 7], [True, 2, 3, 4, 5], [1.0, 2, 3, 4, 5], "12345"):
            with self.assertRaises(WeeklyGameError):
                scoring_options(dice, blank())

    def test_reject_malformed_scorecard_and_bonus(self):
        for card in ({}, {**blank(), "unknown": None}, {**blank(), "yahtzee": 25},
                     {**blank(), "ones": -1}, {**blank(), "threes": 14}, {**blank(), "ones": True}):
            with self.assertRaises(WeeklyGameError):
                scoring_options([1, 2, 3, 4, 5], card)
        for count in (1, -1, 13, True):
            with self.assertRaises(WeeklyGameError):
                score_totals(blank(), count)


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.schedule = generate_schedule(WEEK, secret=SECRET)

    def test_generator_version_vector_and_commitment(self):
        self.assertEqual(self.schedule.pools[0], ((5, 5, 4, 2, 6), (5, 2, 6, 3, 3), (5, 2, 4, 4, 3)))
        self.assertEqual(self.schedule.pools[-1], ((2, 4, 5, 4, 1), (3, 5, 4, 3, 6), (5, 4, 4, 4, 3)))
        self.assertEqual(self.schedule.commitment, "7fed3d88926242276abb5b9f2883b029c06d74dcc210996546136819fd67776a")

    def test_determinism_and_week_domain_separation(self):
        self.assertEqual(self.schedule, generate_schedule(WEEK, secret=SECRET))
        self.assertNotEqual(self.schedule.pools, generate_schedule("2026-11-16", secret=SECRET).pools)
        self.assertNotEqual(self.schedule.pools, generate_schedule(WEEK, secret=b"z" * 32).pools)

    def test_secret_required_and_default_not_date_seeded(self):
        for key in (b"", b"a" * 31, "a" * 32):
            with self.assertRaises(WeeklyGameError):
                generate_schedule(WEEK, secret=key)
        self.assertNotEqual(generate_schedule(WEEK).pools, generate_schedule(WEEK).pools)

    def test_schedule_shape_and_versions_are_strict(self):
        for data in (self.schedule.pools[:12], (self.schedule.pools[0][:2],) * 13):
            with self.assertRaises(WeeklyGameError):
                DiceSchedule(WEEK, data)
        with self.assertRaises(UnsupportedVersion):
            replace(self.schedule, dice_version="unrecognized")
        with self.assertRaises(UnsupportedVersion):
            replace(self.schedule, rules_version="unrecognized")
        with self.assertRaises(WeeklyGameError):
            self.schedule.pool(0, 1)

    def test_private_roundtrip_preserves_schedule(self):
        saved = json.loads(json.dumps(self.schedule.to_private_dict()))
        self.assertEqual(DiceSchedule.from_private_dict(saved), self.schedule)

    def test_repr_never_prints_pools(self):
        text = repr(self.schedule)
        self.assertIn("<private>", text)
        self.assertNotIn(str(self.schedule.pools[0]), text)

    def test_rejection_mapping_is_exactly_uniform(self):
        # Each accepted byte maps to a face exactly 42 times; rejected bytes
        # are not mapped at all. No statistical claim relies on a flaky test.
        counts = Counter(1 + byte % 6 for byte in range(256) if byte < 252)
        self.assertEqual(counts, {face: 42 for face in range(1, 7)})

    def test_large_deterministic_sample_has_no_obvious_distribution_error(self):
        # A generous deterministic smoke check, not proof of randomness.
        counts = Counter()
        for seed in range(256):
            schedule = generate_schedule(WEEK, secret=seed.to_bytes(32, "big"))
            for rounds in schedule.pools:
                for pool in rounds:
                    counts.update(pool)
        self.assertEqual(sum(counts.values()), 256 * 13 * 3 * 5)
        expected = sum(counts.values()) / 6
        self.assertTrue(all(abs(counts[face] - expected) < 0.05 * expected for face in range(1, 7)))


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.schedule = generate_schedule(WEEK, secret=SECRET)
        self.state = new_game(self.schedule, now=NOW)

    def test_new_game_reveals_only_first_observed_roll(self):
        self.assertEqual(self.state.dice, (2, 4, 5, 5, 6))
        self.assertEqual(self.state.round_number, 1)
        self.assertEqual(self.state.roll_number, 1)
        payload = self.state.to_dict()
        self.assertEqual(payload["rounds"], [])
        self.assertEqual(payload["rolls"], [{"dice": [2, 4, 5, 5, 6], "held_before": []}])
        self.assertFalse(set(payload) & {"secret", "seed", "pools", "schedule"})

    def test_equivalent_duplicate_holds_give_identical_hands(self):
        first = advance(self.state, self.schedule, "hold", held=[5, 4, 5])
        second = advance(self.state, self.schedule, "hold", held=[4, 5, 5])
        first = advance(first, self.schedule, "reroll")
        second = advance(second, self.schedule, "reroll")
        self.assertEqual(first, second)
        self.assertEqual(first.dice, (2, 4, 5, 5, 5))

    def test_different_holds_can_give_different_hands(self):
        held = advance(self.state, self.schedule, "hold", held=[6])
        first = advance(held, self.schedule, "reroll")
        second = advance(self.state, self.schedule, "reroll")
        self.assertNotEqual(first.dice, second.dice)

    def test_prefix_pool_is_used_for_each_reroll_count(self):
        for number_held in range(5):
            held = self.state.dice[:number_held]
            state = advance(self.state, self.schedule, "hold", held=list(held))
            result = advance(state, self.schedule, "reroll")
            expected = tuple(sorted(held + self.schedule.pool(1, 2)[:5 - number_held]))
            self.assertEqual(result.dice, expected)

    def test_can_release_previously_held_dice(self):
        state = advance(self.state, self.schedule, "hold", held=[5, 5])
        state = advance(state, self.schedule, "reroll")
        self.assertEqual(state.held, (5, 5))
        state = advance(state, self.schedule, "hold", held=[])
        state = advance(state, self.schedule, "reroll")
        self.assertEqual(state.dice, tuple(sorted(self.schedule.pool(1, 3))))
        self.assertEqual(state.held, ())

    def test_cannot_hold_nonexistent_dice_or_reroll_all_held(self):
        for held in ([1], [5, 5, 5], [True], [5] * 6):
            with self.assertRaises(WeeklyGameError):
                advance(self.state, self.schedule, "hold", held=held)
        state = advance(self.state, self.schedule, "hold", held=list(self.state.dice))
        with self.assertRaises(InvalidAction):
            advance(state, self.schedule, "reroll")
        self.assertEqual(advance(state, self.schedule, "score", category="chance").round_number, 2)

    def test_maximum_three_rolls_then_must_score(self):
        state = advance(self.state, self.schedule, "reroll")
        state = advance(state, self.schedule, "reroll")
        self.assertEqual(state.roll_number, 3)
        for kind, fields in (("reroll", {}), ("hold", {"held": []})):
            with self.assertRaises(InvalidAction):
                advance(state, self.schedule, kind, **fields)

    def test_score_after_any_roll(self):
        for rolls in (1, 2, 3):
            state = self.state
            for _ in range(rolls - 1):
                state = advance(state, self.schedule, "reroll")
            total = sum(state.dice)
            result = advance(state, self.schedule, "score", category="chance")
            self.assertEqual(result.scorecard["chance"], total)
            self.assertEqual(len(result.rounds[0].rolls), rolls)
            self.assertEqual(result.roll_number, 1)
            self.assertEqual(result.held, ())

    def test_stopping_early_does_not_shift_next_round(self):
        early = advance(self.state, self.schedule, "score", category="chance")
        late = advance(self.state, self.schedule, "reroll")
        late = advance(late, self.schedule, "reroll")
        late = advance(late, self.schedule, "score", category="chance")
        self.assertEqual(early.dice, late.dice)
        self.assertEqual(early.dice, tuple(sorted(self.schedule.pool(2, 1))))

    def test_zero_scores_are_valid_and_category_cannot_repeat(self):
        state = advance(self.state, self.schedule, "score", category="ones")
        self.assertEqual(state.scorecard["ones"], 0)
        with self.assertRaises(InvalidAction):
            advance(state, self.schedule, "score", category="ones")

    def test_cannot_bypass_forced_joker_category(self):
        schedule = fixed_schedule()
        state = new_game(schedule, now=NOW)
        state = advance(state, schedule, "score", category="yahtzee")
        with self.assertRaises(InvalidAction):
            advance(state, schedule, "score", category="chance")
        state = advance(state, schedule, "score", category="sixes")
        self.assertEqual(state.yahtzee_bonus_count, 1)
        state = advance(state, schedule, "score", category="large_straight")
        self.assertEqual(state.scorecard["large_straight"], 40)
        self.assertEqual(state.yahtzee_bonus_count, 2)

    def test_full_game_finalizes_on_thirteenth_score(self):
        state = self.state
        while not state.complete:
            category = scoring_options(state.dice, state.scorecard)[0].category
            state = advance(state, self.schedule, "score", category=category)
            validate_state(state, self.schedule)
        self.assertEqual(len(state.rounds), 13)
        self.assertEqual(state.round_number, 13)
        self.assertTrue(all(v is not None for v in state.scores))
        self.assertEqual(state.totals["total"], sum(state.scores) + state.totals["upper_bonus"])
        for action in ({"kind": "reroll"}, {"kind": "hold", "held": []}, {"kind": "score", "category": "chance"}):
            with self.assertRaises(GameComplete):
                apply_action(state, self.schedule, action, expected_revision=state.revision, now=NOW)

    def test_twelve_extra_yahtzees_are_counted_once_each(self):
        schedule = fixed_schedule()
        state = new_game(schedule, now=NOW)
        state = advance(state, schedule, "score", category="yahtzee")
        while not state.complete:
            option = scoring_options(state.dice, state.scorecard)[0]
            state = advance(state, schedule, "score", category=option.category)
        self.assertEqual(state.yahtzee_bonus_count, 12)
        self.assertEqual(state.totals["yahtzee_bonus"], 1200)
        self.assertEqual(state.totals["total"], 1465)
        validate_state(state, schedule)

    def test_old_revision_rejected_without_mutating_original(self):
        before = self.state.to_dict()
        result = advance(self.state, self.schedule, "reroll")
        with self.assertRaises(StaleState):
            apply_action(result, self.schedule, {"kind": "reroll"}, expected_revision=0, now=NOW)
        self.assertEqual(self.state.to_dict(), before)

    def test_no_client_dice_or_mode_changes(self):
        for action in ({"kind": "reroll", "dice": [6] * 5}, {"kind": "restart"},
                       {"kind": "score", "category": "chance", "points": 100},
                       {"kind": "hold", "held": [], "mode": "practice"}, {"kind": []}):
            with self.assertRaises(InvalidAction):
                apply_action(self.state, self.schedule, action, expected_revision=0, now=NOW)

    def test_randomized_full_games_resume_after_every_action(self):
        rng = random.Random(4343)
        for trial in range(60):
            schedule = generate_schedule(WEEK, secret=trial.to_bytes(32, "big"))
            state = new_game(schedule, now=NOW)
            while not state.complete:
                if state.roll_number < 3 and rng.random() < 0.65:
                    held = [d for d in state.dice if rng.random() < 0.5]
                    state = advance(state, schedule, "hold", held=held)
                    state = GameState.from_dict(json.loads(json.dumps(state.to_dict())), schedule)
                    if len(held) < 5:
                        state = advance(state, schedule, "reroll")
                else:
                    category = rng.choice(scoring_options(state.dice, state.scorecard)).category
                    state = advance(state, schedule, "score", category=category)
                state = GameState.from_dict(json.loads(json.dumps(state.to_dict())), schedule)
            validate_state(state, schedule)


class SaveAndTimeTests(unittest.TestCase):
    def setUp(self):
        self.schedule = generate_schedule(WEEK, secret=SECRET)
        self.state = new_game(self.schedule, now=NOW)

    def test_roundtrip_from_json_at_each_step(self):
        state = self.state
        for kind, fields in (("hold", {"held": [5]}), ("reroll", {}),
                             ("hold", {"held": []}), ("reroll", {}),
                             ("score", {"category": "chance"})):
            state = advance(state, self.schedule, kind, **fields)
            self.assertEqual(GameState.from_dict(json.loads(json.dumps(state.to_dict())), self.schedule), state)

    def test_tampered_dice_scores_history_or_version_rejected(self):
        state = advance(self.state, self.schedule, "score", category="chance")
        original = state.to_dict()
        mutations = []
        for field, value in (("revision", -1), ("state_version", 99), ("state_version", True),
                             ("rules_version", "other"), ("week_id", "2026-11-16"),
                             ("schedule_commitment", "0" * 64), ("mode", "other")):
            data = deepcopy(original)
            data[field] = value
            mutations.append(data)
        data = deepcopy(original)
        data["rolls"][0]["dice"] = [6] * 5
        mutations.append(data)
        data = deepcopy(original)
        data["scores"][-1] = 30
        mutations.append(data)
        data = deepcopy(original)
        data["rounds"][0]["points"] = 30
        mutations.append(data)
        data = deepcopy(original)
        data["rounds"][0]["yahtzee_bonus"] = 100
        mutations.append(data)
        data = deepcopy(original)
        data["secret"] = "unexpected field"
        mutations.append(data)
        for data in mutations:
            with self.assertRaises(WeeklyGameError):
                GameState.from_dict(data, self.schedule)

    def test_reject_different_private_schedule(self):
        other = generate_schedule(WEEK, secret=b"x" * 32)
        with self.assertRaises(WeeklyGameError):
            GameState.from_dict(self.state.to_dict(), other)

    def test_week_boundary_uses_eastern_not_utc(self):
        before = datetime(2026, 11, 16, 4, 59, 59, tzinfo=timezone.utc)
        after = before + timedelta(seconds=1)
        self.assertEqual(current_week_id(before), WEEK)
        self.assertEqual(current_week_id(after), "2026-11-16")
        self.assertEqual(current_week_id(NOW), WEEK)

    def test_official_start_and_actions_expire_at_exact_cutoff(self):
        start, end = week_bounds(WEEK)
        new_game(self.schedule, now=start)
        new_game(self.schedule, now=end - timedelta(microseconds=1))
        for now in (start - timedelta(microseconds=1), end):
            with self.assertRaises(GameExpired):
                new_game(self.schedule, now=now)
            with self.assertRaises(GameExpired):
                apply_action(self.state, self.schedule, {"kind": "reroll"}, expected_revision=0, now=now)

    def test_historical_state_can_be_read_after_cutoff(self):
        # Loading/auditing does not submit any score or extend the deadline.
        self.assertEqual(GameState.from_dict(self.state.to_dict(), self.schedule), self.state)

    def test_practice_uses_same_dice_and_can_run_after_cutoff(self):
        # The store, not the pure engine, must prove official completion first.
        state = new_game(self.schedule, mode="practice", now=NOW + timedelta(days=30))
        self.assertEqual(state.dice, self.state.dice)
        result = apply_action(state, self.schedule, {"kind": "reroll"},
                              expected_revision=0, now=NOW + timedelta(days=30))
        self.assertEqual(result.dice, advance(self.state, self.schedule, "reroll").dice)
        self.assertEqual(result.mode, "practice")

    def test_dst_weeks_close_at_local_midnight(self):
        for week, hours in (("2026-03-02", 167), ("2026-10-26", 169), (WEEK, 168)):
            start, end = week_bounds(week)
            self.assertEqual((end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds(), hours * 3600)
            self.assertEqual((start.hour, end.hour), (0, 0))

    def test_reject_naive_server_time_and_non_monday_ids(self):
        with self.assertRaises(WeeklyGameError):
            current_week_id(datetime(2026, 11, 11, 20, 0))
        for week in ("2026-11-10", "not a date", "20261109", None):
            with self.assertRaises(WeeklyGameError):
                week_bounds(week)


if __name__ == "__main__":
    unittest.main(verbosity=2)
