from __future__ import annotations

"""Realistic puzzle-bank runtime for Yahtzee Coach v42.6.

The exact solver remains the source of truth.  This module supplies a much
broader, tagged universe of scorecard contexts and dice outcomes for Unlimited
Practice. In v42.6, 85% of scorecard contexts come from turn-by-turn simulated
games and 15% remain deliberately curated edge cases. It also includes the
deterministic Daily-10 selector that v43 can use
when shared leaderboards are added.
"""

from datetime import date, timedelta
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import random
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parent
BANK_PATH = ROOT / "puzzle_bank.npz"
CATALOG_PATH = ROOT / "challenge_catalog.npz"

CATEGORIES = (
    "ones", "twos", "threes", "fours", "fives", "sixes",
    "three_of_a_kind", "four_of_a_kind", "full_house",
    "small_straight", "large_straight", "yahtzee", "chance",
)

SCENARIO_PRESENTATION = {
    "Joker / Extra Yahtzee": (
        "Joker Doorway",
        "You already scored a Yahtzee. Extra-Yahtzee and Joker rules can make matching dice much more valuable than usual.",
    ),
    "Full House": (
        "Full House Puzzle",
        "You have matching dice that could build a Full House. Decide whether that path is better than using more fresh dice.",
    ),
    "Straight Structure": (
        "Straight Structure",
        "Some of these dice can build a straight. Decide which connected numbers are worth keeping.",
    ),
    "Matching Dice": (
        "Matching Dice Pressure",
        "You have matching dice. Use the scorecard to decide how many of them are worth keeping.",
    ),
    "Upper Bonus": (
        "Upper Bonus Pressure",
        "The 35-point upper bonus is still possible. Decide whether an upper number is worth keeping or another open box is stronger.",
    ),
    "Bonus Secured": (
        "Bonus Banked",
        "You already earned the upper bonus. Choose the hold that helps the open boxes most; you no longer need to protect 63.",
    ),
    "Bonus Is Gone": (
        "Bonus Is Gone",
        "The upper bonus is no longer possible. Focus only on the boxes you can still score.",
    ),
    "Chance Timing": (
        "Chance Crossroads",
        "Chance is still available as a backup. Decide whether high dice are worth keeping or another pattern has more value.",
    ),
    "Flexible Board": (
        "Open Board Fun",
        "There is no obvious pattern to chase. Let the open boxes on the scorecard decide which dice are most useful.",
    ),
}

TRUE_ENDGAME_TITLE = "True Endgame"
TRUE_ENDGAME_DESCRIPTION = (
    "Only one or two boxes remain. Ignore general rules and keep the dice that give those last boxes the best chance to score."
)


@lru_cache(maxsize=1)
def _data() -> dict:
    bank = np.load(BANK_PATH, allow_pickle=False)
    catalog = np.load(CATALOG_PATH, allow_pickle=False)
    return {
        "state_keys": bank["state_keys"],
        "scorecards": bank["scorecards"],
        "stage": bank["stage"],
        "bonus_status": bank["bonus_status"],
        "yahtzee_status": bank["yahtzee_status"],
        "open_count": bank["open_count"],
        "origin": bank["origin"],
        "player_profile": bank["player_profile"],
        "turns_played": bank["turns_played"],
        "rows": catalog["rows"],
        "rolls": catalog["rolls"],
        "skill_names": tuple(str(x) for x in catalog["skill_names"]),
        "difficulty_names": tuple(str(x) for x in catalog["difficulty_names"]),
    }


def scorecard_for_state_index(state_index: int) -> dict[str, int | None]:
    data = _data()
    row = data["scorecards"][int(state_index)]
    return {
        category: (None if int(row[index]) < 0 else int(row[index]))
        for index, category in enumerate(CATEGORIES)
    }


def _scenario_for(state_index: int, skill: str) -> tuple[str, str]:
    data = _data()
    stage = str(data["stage"][state_index])
    if stage == "True Endgame":
        return TRUE_ENDGAME_TITLE, TRUE_ENDGAME_DESCRIPTION
    return SCENARIO_PRESENTATION[skill]


def _challenge_from_row(row) -> dict:
    data = _data()
    state_index = int(row["state_index"])
    roll_id = int(row["roll_id"])
    roll_number = int(row["roll_number"])
    skill = data["skill_names"][int(row["skill_code"])]
    difficulty = data["difficulty_names"][int(row["difficulty_code"])]
    scenario_name, description = _scenario_for(state_index, skill)
    scorecard = scorecard_for_state_index(state_index)
    return {
        "mode": "Unlimited Practice",
        "scenario_name": scenario_name,
        "scenario_description": description,
        "roll_number": roll_number,
        "rolls_remaining": 3 - roll_number,
        "dice": [int(x) for x in data["rolls"][roll_id]],
        "scorecard": scorecard,
        "bank_version": "42.6",
        "bank_state_index": state_index,
        "bank_state_key": int(data["state_keys"][state_index]),
        "skill_tag": skill,
        "difficulty": difficulty,
        "top_gap": float(row["top_gap"]),
        "optimal_tie_count": int(row["tie_count"]),
        "stage": str(data["stage"][state_index]),
        "bonus_status": str(data["bonus_status"][state_index]),
        "yahtzee_status": str(data["yahtzee_status"][state_index]),
        "scorecard_origin": str(data["origin"][state_index]),
        "simulated_player_profile": str(data["player_profile"][state_index]),
    }


def challenge_signature(challenge: dict) -> tuple:
    scorecard = challenge.get("scorecard", {}) or {}
    filled = tuple(
        (category, scorecard.get(category))
        for category in CATEGORIES
        if scorecard.get(category) is not None
    )
    return (
        challenge.get("scenario_name"),
        challenge.get("roll_number"),
        tuple(sorted(challenge.get("dice", []))),
        filled,
    )


@lru_cache(maxsize=None)
def _eligible_indices(*, roll_number: int | None = None, stage: str | None = None,
                      skill_code: int | None = None, origin: str | None = None, daily: bool = False) -> np.ndarray:
    data = _data()
    rows = data["rows"]
    mask = rows["daily_eligible"].astype(bool) if daily else rows["practice_eligible"].astype(bool)
    if roll_number is not None:
        mask &= rows["roll_number"] == int(roll_number)
    if skill_code is not None:
        mask &= rows["skill_code"] == int(skill_code)
    if stage is not None:
        state_stages = data["stage"][rows["state_index"]]
        mask &= state_stages == stage
    if origin is not None:
        state_origins = data["origin"][rows["state_index"]]
        mask &= state_origins == origin
    return np.flatnonzero(mask)


def generate_practice_challenge(
    avoid_recent_scenarios: Iterable[str] | None = None,
    avoid_recent_signatures: Iterable[tuple] | None = None,
    max_attempts: int = 80,
) -> dict:
    """Draw broadly from the expanded exact-policy universe.

    Roll 1 and Roll 2 are sampled 50/50.  Stage and strategy family are chosen
    before the exact candidate, which prevents the enormous matching-dice pool
    from drowning out rarer skills such as Chance timing or bonus-dead play.
    """
    data = _data()
    avoid_titles = set(avoid_recent_scenarios or [])
    avoid_signatures = set(avoid_recent_signatures or [])
    bank_break = _try_practice_bank_break(avoid_titles, avoid_signatures)
    if bank_break is not None:
        return bank_break
    stages = ["Opening", "Midgame", "Late Game", "True Endgame"]
    stage_weights = [0.20, 0.30, 0.30, 0.20]
    origin_weights = [("Simulated Game", 0.85), ("Curated Edge Case", 0.15)]
    # Rare strategic families stay available, but ordinary practice should feel
    # like a real game more often than a parade of Joker/bonus edge cases.
    skill_weights = {
        "Matching Dice": 1.35,
        "Straight Structure": 1.25,
        "Full House": 0.95,
        "Upper Bonus": 1.20,
        "Bonus Secured": 0.55,
        "Bonus Is Gone": 0.80,
        "Chance Timing": 0.85,
        "Joker / Extra Yahtzee": 0.45,
        "Flexible Board": 1.20,
    }

    fallback = None
    for _ in range(max_attempts):
        roll_number = random.choice((1, 2))
        stage = random.choices(stages, weights=stage_weights, k=1)[0]
        origin = random.choices([x[0] for x in origin_weights], weights=[x[1] for x in origin_weights], k=1)[0]

        # Choose among strategy families that actually exist for this stage/roll/origin,
        # then sample a candidate from that family.  This deliberately broadens
        # practice rather than matching natural dice-frequency distribution.
        available_skills = []
        for skill_code in range(len(data["skill_names"])):
            idx = _eligible_indices(roll_number=roll_number, stage=stage, skill_code=skill_code, origin=origin)
            if len(idx):
                available_skills.append((skill_code, idx, skill_weights.get(data["skill_names"][skill_code], 1.0)))
        if not available_skills:
            # A rare stage/skill combination may not exist in the 15% curated
            # slice. Relax only the origin preference, not the exact-policy or
            # stage/roll requirements.
            other_origin = "Curated Edge Case" if origin == "Simulated Game" else "Simulated Game"
            for skill_code in range(len(data["skill_names"])):
                idx = _eligible_indices(roll_number=roll_number, stage=stage, skill_code=skill_code, origin=other_origin)
                if len(idx):
                    available_skills.append((skill_code, idx, skill_weights.get(data["skill_names"][skill_code], 1.0)))
        if not available_skills:
            continue
        chosen_skill = random.choices(available_skills, weights=[item[2] for item in available_skills], k=1)[0]
        skill_code, indices, _ = chosen_skill
        index_list = indices.tolist()
        # Within a strategy family, use cheap rejection sampling to make rare
        # scorecard conditions genuinely occasional. This avoids scanning every
        # candidate on each Streamlit round.
        skill_name = data["skill_names"][skill_code]
        chosen_index = None
        for _candidate_try in range(16):
            idx = int(random.choice(index_list))
            state_index = int(data["rows"][idx]["state_index"])
            accept = 1.0
            if str(data["yahtzee_status"][state_index]) == "Live 50" and skill_name != "Joker / Extra Yahtzee":
                accept *= 0.30
            if str(data["bonus_status"][state_index]) == "Earned" and skill_name != "Bonus Secured":
                accept *= 0.45
            if random.random() <= accept:
                chosen_index = idx
                break
        if chosen_index is None:
            chosen_index = int(random.choice(index_list))
        row = data["rows"][chosen_index]
        challenge = _challenge_from_row(row)
        sig = challenge_signature(challenge)
        if fallback is None:
            fallback = challenge
        if sig in avoid_signatures:
            continue
        if challenge["scenario_name"] in avoid_titles:
            continue
        return challenge

    return fallback if fallback is not None else _challenge_from_row(data["rows"][0])


DAILY_2K9_EFFECTIVE_DATE = date(2026, 8, 19)
BANK_BREAK_THEME = "Bank It or Break It?"


def _hold_size_from_code(code: int) -> int:
    return sum((int(code) >> ((face - 1) * 3)) & 0b111 for face in range(1, 7))


def _dice_pattern(values: Iterable[int]) -> str:
    dice = tuple(int(value) for value in values)
    counts = sorted((dice.count(face) for face in range(1, 7) if dice.count(face)), reverse=True)
    if counts == [5]:
        return "Yahtzee"
    if counts == [4, 1]:
        return "Four"
    if counts == [3, 2]:
        return "Full House"
    if counts == [3, 1, 1]:
        return "Triple"
    if counts == [2, 2, 1]:
        return "Two pair"
    if counts == [2, 1, 1, 1]:
        return "Pair"
    return "All different"


def _bank_break_kind(row) -> str | None:
    """Classify exact-supported made-Full-House decisions without changing policy data."""
    data = _data()
    state_index = int(row["state_index"])
    roll_id = int(row["roll_id"])
    if int(data["scorecards"][state_index][8]) >= 0:  # Full House is already filled.
        return None
    if _dice_pattern(data["rolls"][roll_id]) != "Full House":
        return None
    return "BANK" if _hold_size_from_code(int(row["best_hold_code"])) == 5 else "BREAK"


def _decorate_bank_break(challenge: dict, outcome: str) -> dict:
    challenge = dict(challenge)
    challenge["scenario_name"] = BANK_BREAK_THEME
    challenge["scenario_description"] = (
        "You already have a 25-point Full House. Read the scorecard: is the guaranteed 25 worth banking, "
        "or is this one of the spots where reopening dice is worth more?"
    )
    challenge["puzzle_theme"] = "Bank It or Break It"
    challenge["bank_break_outcome"] = str(outcome)
    return challenge


def _stable_daily_random(tag: str, day: date) -> random.Random:
    digest = sha256(f"yahtzee-coach-2k9|{tag}|{day.isoformat()}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


@lru_cache(maxsize=None)
def _bank_break_day_plan(date_key: str) -> str | None:
    """Return BANK/BREAK/None with a cooldown and a gentle drought correction.

    The plan is deterministic from the date, averages about one appearance on
    one-third of days, strongly discourages back-to-back appearances, and keeps
    BANK/BREAK outcomes balanced over time.
    """
    day = date.fromisoformat(str(date_key))
    if day < DAILY_2K9_EFFECTIVE_DATE:
        return None

    history: list[str | None] = []
    for offset in range(1, 5):
        previous = day - timedelta(days=offset)
        if previous >= DAILY_2K9_EFFECTIVE_DATE:
            history.append(_bank_break_day_plan(previous.isoformat()))

    chance = 0.38
    if history and history[0] is not None:
        chance = 0.08
    elif len(history) >= 4 and all(item is None for item in history[:4]):
        chance = 0.78
    elif len(history) >= 3 and all(item is None for item in history[:3]):
        chance = 0.58

    if _stable_daily_random("bank-break-presence", day).random() >= chance:
        return None

    recent = {"BANK": 0, "BREAK": 0}
    for offset in range(1, 15):
        previous = day - timedelta(days=offset)
        if previous < DAILY_2K9_EFFECTIVE_DATE:
            break
        outcome = _bank_break_day_plan(previous.isoformat())
        if outcome in recent:
            recent[outcome] += 1
    if recent["BANK"] < recent["BREAK"]:
        return "BANK"
    if recent["BREAK"] < recent["BANK"]:
        return "BREAK"
    return "BANK" if _stable_daily_random("bank-break-outcome", day).random() < 0.5 else "BREAK"


def _weekly_family_targets(date_key: str) -> set[str]:
    """Build a deterministic soft family plan for the week, not a daily checklist."""
    day = date.fromisoformat(str(date_key))
    monday = day - timedelta(days=day.weekday())
    rng = _stable_daily_random("weekly-family-plan", monday)

    normal_families = [
        "Matching Dice", "Straight Structure", "Full House", "Upper Bonus",
        "Bonus Secured", "Bonus Is Gone", "Chance Timing", "Flexible Board",
    ]
    family_weights = {
        "Matching Dice": 1.20,
        "Straight Structure": 1.15,
        "Full House": 0.95,
        "Upper Bonus": 1.05,
        "Bonus Secured": 0.60,
        "Bonus Is Gone": 0.80,
        "Chance Timing": 0.80,
        "Flexible Board": 1.10,
    }

    # Joker is intentionally rare: one or two Daily appearances per week.
    joker_count = rng.choice((1, 2, 2))
    joker_days: list[int] = []
    day_order = list(range(7))
    rng.shuffle(day_order)
    for candidate in day_order:
        if any(abs(candidate - chosen) == 1 for chosen in joker_days):
            continue
        joker_days.append(candidate)
        if len(joker_days) >= joker_count:
            break
    if len(joker_days) < joker_count:
        for candidate in day_order:
            if candidate not in joker_days:
                joker_days.append(candidate)
                if len(joker_days) >= joker_count:
                    break

    coverage = {family: 0 for family in normal_families}
    week_targets: list[set[str]] = []
    for weekday in range(7):
        target_count = rng.choice((5, 6, 6, 6, 7))
        target: set[str] = set()
        # Start from the least-used families so coverage is a weekly goal rather
        # than forcing every lesson into every Daily 10.
        least_used = sorted(normal_families, key=lambda family: (coverage[family], rng.random()))
        target.update(least_used[:2])
        while len(target) < target_count:
            available = [family for family in normal_families if family not in target]
            if not available:
                break
            weights = [family_weights[family] / (1.0 + 0.35 * coverage[family]) for family in available]
            picked = rng.choices(available, weights=weights, k=1)[0]
            target.add(picked)
        if weekday in joker_days:
            target.add("Joker / Extra Yahtzee")
        for family in target:
            if family in coverage:
                coverage[family] += 1
        week_targets.append(target)
    return week_targets[day.weekday()]


@lru_cache(maxsize=8)
def _bank_break_indices(outcome: str, roll_number: int = 2) -> tuple[int, ...]:
    data = _data()
    rows = data["rows"]
    matches: list[int] = []
    for idx in _eligible_indices(roll_number=roll_number, daily=False).tolist():
        row = rows[idx]
        if _bank_break_kind(row) == outcome:
            matches.append(idx)
    return tuple(matches)


def _try_practice_bank_break(avoid_titles: set[str], avoid_signatures: set[tuple]) -> dict | None:
    # Practice may teach this family deliberately, but the existing five-scenario
    # avoidance keeps it from becoming a repetitive drill.
    if BANK_BREAK_THEME in avoid_titles or random.random() >= 0.34:
        return None
    data = _data()
    preferred_roll = 2 if random.random() < 0.60 else 1
    for outcome in random.sample(["BANK", "BREAK"], k=2):
        indices = list(_bank_break_indices(outcome, preferred_roll))
        if not indices:
            continue
        for _ in range(24):
            row = data["rows"][random.choice(indices)]
            challenge = _decorate_bank_break(_challenge_from_row(row), outcome)
            gap = float(row["top_gap"])
            # Favor teachable decisions, but do not throw away the full exact
            # range if rejection sampling happens to miss one.
            if not (0.10 <= gap <= 6.0) and random.random() < 0.80:
                continue
            if challenge_signature(challenge) in avoid_signatures:
                continue
            return challenge
    return None


def _special_bank_break_candidates(*, stage: str, roll_number: int, origin: str, difficulty: str,
                                   outcome: str) -> list[int]:
    data = _data()
    rows = data["rows"]
    candidate_idx = _eligible_indices(roll_number=roll_number, stage=stage, origin=origin, daily=False)
    matches: list[int] = []
    for idx in candidate_idx.tolist():
        row = rows[idx]
        if data["difficulty_names"][int(row["difficulty_code"])] != difficulty:
            continue
        if data["skill_names"][int(row["skill_code"])] == "Joker / Extra Yahtzee":
            continue
        if _bank_break_kind(row) != outcome:
            continue
        matches.append(idx)
    return matches

def _daily_seed(date_key: str) -> int:
    digest = sha256(f"yahtzee-coach-daily-v42.6|{date_key}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _generate_legacy_daily_challenge_set(date_key: str, count: int = 10) -> list[dict]:
    """Deterministically produce the same balanced Daily 10 for a date key.

    This is intentionally database-free.  v43 can store player submissions and
    leaderboard results while recreating the puzzle set from the date + bank
    version, keeping challenge content identical for every player.
    """
    if count != 10:
        raise ValueError("The Daily Challenge format is currently designed for exactly 10 situations.")

    data = _data()
    rows = data["rows"]
    rng = random.Random(_daily_seed(str(date_key)))

    stage_plan = ["Opening", "Opening", "Midgame", "Midgame", "Midgame",
                  "Late Game", "Late Game", "Late Game", "True Endgame", "True Endgame"]
    roll_plan = [1] * 5 + [2] * 5
    difficulty_plan = ["Hard", "Medium", "Clear", "Medium", "Punishing",
                       "Hard", "Clear", "Medium", "Punishing", "Knife-edge"]
    # Nine realistic game-history cards plus one intentionally curated edge case
    # keeps the Daily 10 believable while still teaching rare situations.
    origin_plan = ["Simulated Game"] * 9 + ["Curated Edge Case"]
    rng.shuffle(stage_plan)
    rng.shuffle(roll_plan)
    rng.shuffle(difficulty_plan)
    rng.shuffle(origin_plan)

    used_states: set[int] = set()
    used_rows: set[int] = set()
    skill_counts: dict[int, int] = {}
    chosen: list[dict] = []

    for stage, roll_number, target_difficulty, origin in zip(stage_plan, roll_plan, difficulty_plan, origin_plan):
        candidate_idx = _eligible_indices(roll_number=roll_number, stage=stage, origin=origin, daily=True)
        candidate_list = candidate_idx.tolist()
        if not candidate_list:
            candidate_idx = _eligible_indices(roll_number=roll_number, stage=stage, daily=True)
            candidate_list = candidate_idx.tolist()
        rng.shuffle(candidate_list)

        # Prefer the requested difficulty and a skill not yet seen.  Relax those
        # preferences only if necessary; never relax same-date determinism,
        # uniqueness, stage balance, or the 5/5 Roll-1/Roll-2 split.
        best_index = None
        best_score = -10**9
        for idx in candidate_list[:12000]:
            row = rows[idx]
            state_index = int(row["state_index"])
            if idx in used_rows or state_index in used_states:
                continue
            skill_code = int(row["skill_code"])
            diff = data["difficulty_names"][int(row["difficulty_code"])]
            score = 0
            if diff == target_difficulty:
                score += 12
            score += 8 if skill_counts.get(skill_code, 0) == 0 else -4 * skill_counts.get(skill_code, 0)
            chosen_live_yahtzees = sum(1 for item in chosen if item.get("yahtzee_status") == "Live 50")
            chosen_earned_bonus = sum(1 for item in chosen if item.get("bonus_status") == "Earned")
            state_ytz = str(data["yahtzee_status"][state_index])
            state_bonus = str(data["bonus_status"][state_index])
            if state_ytz == "Live 50":
                score += 2 if chosen_live_yahtzees == 0 else -12 * chosen_live_yahtzees
            if state_bonus == "Earned":
                score += 1 if chosen_earned_bonus == 0 else -6 * chosen_earned_bonus
            # Avoid filling a competitive set with exact ties unless the planned
            # slot is the knife-edge puzzle.
            tie_count = int(row["tie_count"])
            if tie_count > 1 and target_difficulty != "Knife-edge":
                score -= 5
            # Moderate exact gaps make good competitive decisions; huge obvious
            # gaps and microscopic gaps are still allowed in their planned slots.
            gap = float(row["top_gap"])
            if 0.15 <= gap <= 4.0:
                score += 3
            score += rng.random() * 0.01
            if score > best_score:
                best_score = score
                best_index = idx

        if best_index is None:
            raise RuntimeError("Daily challenge selector could not satisfy its balance constraints.")
        row = rows[best_index]
        used_rows.add(best_index)
        used_states.add(int(row["state_index"]))
        skill_code = int(row["skill_code"])
        skill_counts[skill_code] = skill_counts.get(skill_code, 0) + 1
        challenge = _challenge_from_row(row)
        challenge["mode"] = "Daily Challenge"
        challenge["daily_date"] = str(date_key)
        challenge["daily_number"] = len(chosen) + 1
        raw_id = f"42.6|{date_key}|{challenge['bank_state_key']}|{challenge['dice']}|{challenge['roll_number']}"
        challenge["challenge_id"] = sha256(raw_id.encode("utf-8")).hexdigest()[:16]
        chosen.append(challenge)

    return chosen



def _generate_phase2k9_daily_challenge_set(date_key: str, count: int = 10) -> list[dict]:
    if count != 10:
        raise ValueError("The Daily Challenge format is currently designed for exactly 10 situations.")

    data = _data()
    rows = data["rows"]
    rng = random.Random(_daily_seed(str(date_key)))

    stage_plan = ["Opening", "Opening", "Midgame", "Midgame", "Midgame",
                  "Late Game", "Late Game", "Late Game", "True Endgame", "True Endgame"]
    roll_plan = [1] * 5 + [2] * 5
    difficulty_plan = ["Hard", "Medium", "Clear", "Medium", "Punishing",
                       "Hard", "Clear", "Medium", "Punishing", "Knife-edge"]
    origin_plan = ["Simulated Game"] * 9 + ["Curated Edge Case"]
    rng.shuffle(stage_plan)
    rng.shuffle(roll_plan)
    rng.shuffle(difficulty_plan)
    rng.shuffle(origin_plan)

    target_bank_break = _bank_break_day_plan(str(date_key))
    target_families = _weekly_family_targets(str(date_key))
    messy_roll_target = _stable_daily_random(
        "messy-roll-presence", date.fromisoformat(str(date_key))
    ).random() < 0.60

    # Reserve one compatible slot for Bank It or Break It when today's soft
    # schedule calls for it. Roll 2 is preferred because it mirrors real play:
    # one reroll remains and the 25-point decision is immediate.
    special_slot: int | None = None
    special_candidates: list[int] = []
    if target_bank_break:
        slot_order = list(range(10))
        rng.shuffle(slot_order)
        slot_order.sort(key=lambda slot: (roll_plan[slot] != 2, difficulty_plan[slot] in {"Punishing", "Knife-edge"}))
        for slot in slot_order:
            found = _special_bank_break_candidates(
                stage=stage_plan[slot],
                roll_number=roll_plan[slot],
                origin=origin_plan[slot],
                difficulty=difficulty_plan[slot],
                outcome=target_bank_break,
            )
            if found:
                special_slot = slot
                special_candidates = found
                break

    special_index: int | None = None
    reserved_special_state: int | None = None
    if special_slot is not None and special_candidates:
        ranked_special = list(special_candidates)
        rng.shuffle(ranked_special)
        special_index = max(
            ranked_special,
            key=lambda idx: (
                1 if 0.15 <= float(rows[idx]["top_gap"]) <= 4.0 else 0,
                1 if int(rows[idx]["tie_count"]) == 1 else 0,
                rng.random(),
            ),
        )
        reserved_special_state = int(rows[special_index]["state_index"])

    used_states: set[int] = set()
    used_rows: set[int] = set()
    skill_counts: dict[int, int] = {}
    chosen: list[dict] = []

    for slot, (stage, roll_number, target_difficulty, origin) in enumerate(
        zip(stage_plan, roll_plan, difficulty_plan, origin_plan)
    ):
        if slot == special_slot:
            candidate_list = [special_index] if special_index is not None else []
        else:
            candidate_idx = _eligible_indices(roll_number=roll_number, stage=stage, origin=origin, daily=True)
            candidate_list = candidate_idx.tolist()
            if not candidate_list:
                candidate_idx = _eligible_indices(roll_number=roll_number, stage=stage, daily=True)
                candidate_list = candidate_idx.tolist()
            rng.shuffle(candidate_list)

        best_index = None
        best_score = -10**9
        for idx in candidate_list[:30000]:
            row = rows[idx]
            state_index = int(row["state_index"])
            if idx in used_rows or state_index in used_states:
                continue
            if slot != special_slot and reserved_special_state is not None and state_index == reserved_special_state:
                continue
            diff = data["difficulty_names"][int(row["difficulty_code"])]
            if diff != target_difficulty:
                continue  # preserve the approved fixed 2/3/2/2/1 difficulty mix

            bank_break_kind = _bank_break_kind(row)
            if slot != special_slot and bank_break_kind is not None:
                # Prevent accidental all-BREAK made-Full-House puzzles from
                # sneaking around the deliberate 30-40% family schedule.
                continue
            if slot == special_slot and bank_break_kind != target_bank_break:
                continue

            skill_code = int(row["skill_code"])
            skill_name = data["skill_names"][skill_code]
            if slot != special_slot and skill_name == "Joker / Extra Yahtzee" and skill_name not in target_families:
                continue

            score = 0.0
            if skill_name in target_families:
                score += 4.0
                if skill_name == "Joker / Extra Yahtzee":
                    score += 6.0
            else:
                score -= 0.75

            seen = skill_counts.get(skill_code, 0)
            if seen == 0:
                score += 2.5
                if len(skill_counts) >= 7:
                    score -= 8.0
            elif seen == 1:
                score += 0.15
            else:
                score -= 3.0 * (seen - 1)

            chosen_live_yahtzees = sum(1 for item in chosen if item.get("yahtzee_status") == "Live 50")
            chosen_earned_bonus = sum(1 for item in chosen if item.get("bonus_status") == "Earned")
            state_ytz = str(data["yahtzee_status"][state_index])
            state_bonus = str(data["bonus_status"][state_index])
            if state_ytz == "Live 50":
                score += 1.0 if chosen_live_yahtzees == 0 else -10.0 * chosen_live_yahtzees
            if state_bonus == "Earned":
                score += 0.5 if chosen_earned_bonus == 0 else -5.0 * chosen_earned_bonus

            tie_count = int(row["tie_count"])
            if tie_count > 1 and target_difficulty != "Knife-edge":
                score -= 5.0
            gap = float(row["top_gap"])
            if 0.15 <= gap <= 4.0:
                score += 3.0

            # Messier rolls are a soft preference, not a quota. The old selector
            # made 97% of Daily dice show a pair/triple/etc.; this gives straight
            # fragments and open-board rerolls a fairer chance to appear.
            pattern = _dice_pattern(data["rolls"][int(row["roll_id"])])
            if pattern == "All different":
                chosen_messy = sum(
                    1 for item in chosen if _dice_pattern(item.get("dice", [])) == "All different"
                )
                if messy_roll_target and chosen_messy == 0:
                    score += 0.45
                else:
                    score -= 0.10
            elif pattern == "Pair":
                score += 0.20

            if slot == special_slot:
                # Prefer close/meaningful bank-vs-break decisions over the most
                # obvious made-hand cases when the planned difficulty allows it.
                if 0.15 <= gap <= 4.0:
                    score += 5.0
                if roll_number == 2:
                    score += 2.0

            score += rng.random() * 0.01
            if score > best_score:
                best_score = score
                best_index = idx

        if best_index is None:
            raise RuntimeError("Daily challenge selector could not satisfy its Phase 2K.9 balance constraints.")

        row = rows[best_index]
        used_rows.add(best_index)
        used_states.add(int(row["state_index"]))
        skill_code = int(row["skill_code"])
        skill_counts[skill_code] = skill_counts.get(skill_code, 0) + 1
        challenge = _challenge_from_row(row)
        if slot == special_slot and target_bank_break:
            challenge = _decorate_bank_break(challenge, target_bank_break)
        challenge["mode"] = "Daily Challenge"
        challenge["daily_date"] = str(date_key)
        challenge["daily_number"] = len(chosen) + 1
        raw_id = f"42.6-2K9|{date_key}|{challenge['bank_state_key']}|{challenge['dice']}|{challenge['roll_number']}"
        challenge["challenge_id"] = sha256(raw_id.encode("utf-8")).hexdigest()[:16]
        chosen.append(challenge)

    return chosen


def generate_daily_challenge_set(date_key: str, count: int = 10) -> list[dict]:
    """Return the legacy Daily before 2K.9, and the balanced selector afterward.

    Historical determinism is intentionally preserved so yesterday recaps and
    saved friend results keep resolving to the exact challenge that was played.
    """
    day = date.fromisoformat(str(date_key))
    if day < DAILY_2K9_EFFECTIVE_DATE:
        return _generate_legacy_daily_challenge_set(str(date_key), count=count)
    return _generate_phase2k9_daily_challenge_set(str(date_key), count=count)

def bank_summary() -> dict:
    data = _data()
    rows = data["rows"]
    return {
        "bank_version": "42.6",
        "scorecard_contexts": int(len(data["state_keys"])),
        "canonical_dice_rolls": int(len(data["rolls"])),
        "roll_stages": [1, 2],
        "state_roll_situations": int(len(rows)),
        "daily_eligible_situations": int(np.sum(rows["daily_eligible"])),
        "skills": list(data["skill_names"]),
        "difficulties": list(data["difficulty_names"]),
        "simulated_scorecard_contexts": int(np.sum(data["origin"] == "Simulated Game")),
        "curated_scorecard_contexts": int(np.sum(data["origin"] == "Curated Edge Case")),
    }
