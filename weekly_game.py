from __future__ import annotations

"""Versioned, UI-independent rules for a Weekly Yahtzee game.

Only trusted server code may hold DiceSchedule objects. Browser responses must
come from GameState.to_dict(), which contains observed dice only. Persistence,
identity, one-official-attempt enforcement and replay eligibility belong to the
store; this module validates rules, deadlines and optimistic state revisions.

Rules reference: https://www.hasbro.com/common/instruct/yahtzee.pdf
"""

from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from hashlib import sha256
import hmac
import json
import secrets
from typing import Mapping, Sequence
from zoneinfo import ZoneInfo


CATEGORIES = (
    "ones", "twos", "threes", "fours", "fives", "sixes",
    "three_of_a_kind", "four_of_a_kind", "full_house",
    "small_straight", "large_straight", "yahtzee", "chance",
)
CATEGORY_LABELS = {
    "ones": "Ones", "twos": "Twos", "threes": "Threes", "fours": "Fours",
    "fives": "Fives", "sixes": "Sixes", "three_of_a_kind": "Three of a Kind",
    "four_of_a_kind": "Four of a Kind", "full_house": "Full House",
    "small_straight": "Small Straight", "large_straight": "Large Straight",
    "yahtzee": "Yahtzee", "chance": "Chance",
}
UPPER = CATEGORIES[:6]
LOWER = CATEGORIES[6:]
RULES_VERSION = "classic-yahtzee-v1"
DICE_VERSION = "hmac-sha256-pools-v1"
STATE_VERSION = 1
WEEK_TIMEZONE = "America/New_York"


class WeeklyGameError(ValueError):
    """A safe rule-validation failure; no state has changed."""


class InvalidAction(WeeklyGameError):
    pass


class StaleState(WeeklyGameError):
    pass


class GameExpired(WeeklyGameError):
    pass


class GameComplete(WeeklyGameError):
    pass


class UnsupportedVersion(WeeklyGameError):
    pass


def _integer(value, minimum: int, maximum: int, label: str) -> int:
    # bool is an int subclass, but is not a valid die/score/revision.
    if type(value) is not int or not minimum <= value <= maximum:
        raise WeeklyGameError(f"Invalid {label}.")
    return value


def _dice(values: Sequence[int], *, count: int | None = 5) -> tuple[int, ...]:
    if not isinstance(values, (tuple, list)):
        raise WeeklyGameError("Dice must be a list of whole-number faces.")
    result = tuple(_integer(v, 1, 6, "die face") for v in values)
    if (count is not None and len(result) != count) or len(result) > 5:
        raise WeeklyGameError("Invalid number of dice.")
    return result


def _held(dice: Sequence[int], held: Sequence[int]) -> tuple[int, ...]:
    values = tuple(sorted(_dice(held, count=None)))
    if Counter(values) - Counter(dice):
        raise InvalidAction("You can hold only dice in your current hand.")
    return values


def _now(now: datetime | None) -> datetime:
    now = now or datetime.now(ZoneInfo(WEEK_TIMEZONE))
    if now.tzinfo is None or now.utcoffset() is None:
        raise WeeklyGameError("A timezone-aware server time is required.")
    return now.astimezone(ZoneInfo(WEEK_TIMEZONE))


def current_week_id(now: datetime | None = None) -> str:
    day = _now(now).date()
    return (day - timedelta(days=day.weekday())).isoformat()


def week_bounds(week_id: str) -> tuple[datetime, datetime]:
    try:
        monday = date.fromisoformat(week_id)
    except (TypeError, ValueError) as exc:
        raise WeeklyGameError("Invalid week ID.") from exc
    if monday.weekday() != 0 or monday.isoformat() != week_id:
        raise WeeklyGameError("A week ID must be an ISO Monday date.")
    tz = ZoneInfo(WEEK_TIMEZONE)
    # Construct local midnights independently: DST weeks are not 168 UTC hours.
    return (datetime.combine(monday, time(), tz),
            datetime.combine(monday + timedelta(days=7), time(), tz))


def _require_open_week(week_id: str, now: datetime | None) -> None:
    start, end = week_bounds(week_id)
    if not start <= _now(now) < end:
        raise GameExpired("This week's official game is closed.")


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _pool(secret: bytes, week_id: str, round_number: int, roll_number: int) -> tuple[int, ...]:
    values: list[int] = []
    counter = 0
    while len(values) < 5:
        message = f"{DICE_VERSION}|{week_id}|{round_number}|{roll_number}|{counter}".encode()
        block = hmac.new(secret, message, sha256).digest()
        # Reject 252..255: 252 is divisible by six, so modulo introduces no bias.
        values.extend(1 + byte % 6 for byte in block if byte < 252)
        counter += 1
    return tuple(values[:5])


@dataclass(frozen=True, repr=False)
class DiceSchedule:
    """Private 13 x 3 x 5 pools; serialize only into server-protected storage."""

    week_id: str
    pools: tuple[tuple[tuple[int, ...], ...], ...]
    rules_version: str = RULES_VERSION
    dice_version: str = DICE_VERSION

    def __post_init__(self) -> None:
        week_bounds(self.week_id)
        if self.rules_version != RULES_VERSION or self.dice_version != DICE_VERSION:
            raise UnsupportedVersion("Unsupported weekly rules or dice version.")
        if not isinstance(self.pools, tuple) or len(self.pools) != 13:
            raise WeeklyGameError("A weekly dice schedule needs thirteen rounds.")
        for rounds in self.pools:
            if not isinstance(rounds, tuple) or len(rounds) != 3:
                raise WeeklyGameError("Each round needs three dice pools.")
            for pool in rounds:
                if not isinstance(pool, tuple):
                    raise WeeklyGameError("Dice schedule pools must be immutable.")
                _dice(pool)

    def __repr__(self) -> str:
        # Logs and exception diagnostics must not accidentally print future dice.
        return f"DiceSchedule(week_id={self.week_id!r}, dice_version={self.dice_version!r}, pools=<private>)"

    def to_private_dict(self) -> dict:
        return {
            "week_id": self.week_id,
            "rules_version": self.rules_version,
            "dice_version": self.dice_version,
            "pools": [[list(pool) for pool in rounds] for rounds in self.pools],
        }

    @classmethod
    def from_private_dict(cls, value: Mapping) -> "DiceSchedule":
        if not isinstance(value, Mapping) or set(value) != {"week_id", "rules_version", "dice_version", "pools"}:
            raise WeeklyGameError("Invalid private schedule format.")
        try:
            pools = tuple(tuple(_dice(pool) for pool in rounds) for rounds in value["pools"])
        except (TypeError, KeyError) as exc:
            raise WeeklyGameError("Invalid private dice pools.") from exc
        return cls(value["week_id"], pools, value["rules_version"], value["dice_version"])

    @property
    def commitment(self) -> str:
        # This hash can be recorded before play without disclosing the pools.
        return sha256(_json(self.to_private_dict()).encode()).hexdigest()

    def pool(self, round_number: int, roll_number: int) -> tuple[int, ...]:
        _integer(round_number, 1, 13, "round number")
        _integer(roll_number, 1, 3, "roll number")
        return self.pools[round_number - 1][roll_number - 1]


def generate_schedule(week_id: str, *, secret: bytes | None = None) -> DiceSchedule:
    """Generate once per week on the server, then persist the private pools.

    Inject a 256-bit secret only for reproducibility/audit tests. Production uses
    OS entropy. The date is a domain separator, never a publicly guessable seed.
    """
    week_bounds(week_id)
    secret = secrets.token_bytes(32) if secret is None else secret
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise WeeklyGameError("Weekly dice require at least 256 bits of secret key material.")
    return DiceSchedule(week_id, tuple(
        tuple(_pool(secret, week_id, r, roll) for roll in range(1, 4))
        for r in range(1, 14)
    ))


def _scorecard(scores: Mapping[str, int | None]) -> dict[str, int | None]:
    if not isinstance(scores, Mapping) or set(scores) != set(CATEGORIES):
        raise WeeklyGameError("The scorecard must contain exactly thirteen categories.")
    result = {}
    for i, category in enumerate(CATEGORIES):
        value = scores[category]
        if value is not None:
            _integer(value, 0, 50, "category score")
            if i < 6 and (value > 5 * (i + 1) or value % (i + 1)):
                raise WeeklyGameError("Invalid upper-section score.")
            legal = {"full_house": (0, 25), "small_straight": (0, 30),
                     "large_straight": (0, 40), "yahtzee": (0, 50)}
            if category in legal and value not in legal[category]:
                raise WeeklyGameError("Invalid fixed-category score.")
            if category in ("three_of_a_kind", "four_of_a_kind", "chance") and not (value == 0 or 5 <= value <= 30):
                raise WeeklyGameError("Invalid sum-category score.")
        result[category] = value
    return result


@dataclass(frozen=True)
class ScoreOption:
    category: str
    points: int
    yahtzee_bonus: int = 0


def scoring_options(dice: Sequence[int], scores: Mapping[str, int | None]) -> tuple[ScoreOption, ...]:
    """Return legal immediate scores, with forced Joker placement applied."""
    dice = _dice(dice)
    scores = _scorecard(scores)
    counts = Counter(dice)
    is_yahtzee = len(counts) == 1
    repeated = is_yahtzee and scores["yahtzee"] is not None
    bonus = 100 if is_yahtzee and scores["yahtzee"] == 50 else 0
    available = [c for c in CATEGORIES if scores[c] is None]
    if repeated:
        matching_upper = UPPER[dice[0] - 1]
        if matching_upper in available:
            available = [matching_upper]
        else:
            lower = [c for c in LOWER if c in available]
            available = lower or available
    values = {c: dice.count(i + 1) * (i + 1) for i, c in enumerate(UPPER)}
    faces = set(dice)
    values.update({
        "three_of_a_kind": sum(dice) if max(counts.values()) >= 3 else 0,
        "four_of_a_kind": sum(dice) if max(counts.values()) >= 4 else 0,
        "full_house": 25 if repeated or sorted(counts.values()) == [2, 3] else 0,
        "small_straight": 30 if repeated or any(set(range(i, i + 4)) <= faces for i in range(1, 4)) else 0,
        "large_straight": 40 if repeated or faces in ({1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}) else 0,
        "yahtzee": 50 if is_yahtzee else 0,
        "chance": sum(dice),
    })
    return tuple(ScoreOption(c, values[c], bonus) for c in available)


def score_totals(scores: Mapping[str, int | None], yahtzee_bonus_count: int = 0) -> dict[str, int]:
    scores = _scorecard(scores)
    _integer(yahtzee_bonus_count, 0, 12, "Yahtzee bonus count")
    if yahtzee_bonus_count and scores["yahtzee"] != 50:
        raise WeeklyGameError("Yahtzee bonuses require a fifty-point Yahtzee box.")
    upper = sum(scores[c] or 0 for c in UPPER)
    lower = sum(scores[c] or 0 for c in LOWER)
    upper_bonus = 35 if upper >= 63 else 0
    extra = 100 * yahtzee_bonus_count
    return {"upper": upper, "lower": lower, "upper_bonus": upper_bonus,
            "yahtzee_bonus": extra, "total": upper + lower + upper_bonus + extra}


@dataclass(frozen=True)
class RollRecord:
    dice: tuple[int, ...]
    held_before: tuple[int, ...] = ()

    def to_dict(self) -> dict:
        return {"dice": list(self.dice), "held_before": list(self.held_before)}

    @classmethod
    def from_dict(cls, value: Mapping) -> "RollRecord":
        if not isinstance(value, Mapping) or set(value) != {"dice", "held_before"}:
            raise WeeklyGameError("Invalid saved roll.")
        return cls(_dice(value["dice"]), _dice(value["held_before"], count=None))


@dataclass(frozen=True)
class RoundRecord:
    category: str
    points: int
    yahtzee_bonus: int
    rolls: tuple[RollRecord, ...]

    def to_dict(self) -> dict:
        return {"category": self.category, "points": self.points,
                "yahtzee_bonus": self.yahtzee_bonus, "rolls": [r.to_dict() for r in self.rolls]}

    @classmethod
    def from_dict(cls, value: Mapping) -> "RoundRecord":
        if not isinstance(value, Mapping) or set(value) != {"category", "points", "yahtzee_bonus", "rolls"}:
            raise WeeklyGameError("Invalid saved round.")
        return cls(value["category"], _integer(value["points"], 0, 50, "score"),
                   _integer(value["yahtzee_bonus"], 0, 100, "bonus"),
                   tuple(RollRecord.from_dict(r) for r in value["rolls"]))


@dataclass(frozen=True)
class GameState:
    week_id: str
    schedule_commitment: str
    mode: str
    scores: tuple[int | None, ...]
    rolls: tuple[RollRecord, ...]
    rounds: tuple[RoundRecord, ...] = ()
    held: tuple[int, ...] = ()
    revision: int = 0
    rules_version: str = RULES_VERSION
    dice_version: str = DICE_VERSION

    @property
    def complete(self) -> bool:
        return len(self.rounds) == 13

    @property
    def round_number(self) -> int:
        return min(13, len(self.rounds) + 1)

    @property
    def roll_number(self) -> int:
        return len(self.rolls)

    @property
    def dice(self) -> tuple[int, ...]:
        return self.rolls[-1].dice

    @property
    def scorecard(self) -> dict[str, int | None]:
        return dict(zip(CATEGORIES, self.scores))

    @property
    def yahtzee_bonus_count(self) -> int:
        return sum(r.yahtzee_bonus for r in self.rounds) // 100

    @property
    def totals(self) -> dict[str, int]:
        return score_totals(self.scorecard, self.yahtzee_bonus_count)

    def to_dict(self) -> dict:
        """A player's own observed game. No secret, pools or future dice."""
        return {
            "state_version": STATE_VERSION, "week_id": self.week_id,
            "rules_version": self.rules_version, "dice_version": self.dice_version,
            "schedule_commitment": self.schedule_commitment, "mode": self.mode,
            "scores": list(self.scores), "held": list(self.held), "revision": self.revision,
            "rolls": [r.to_dict() for r in self.rolls],
            "rounds": [r.to_dict() for r in self.rounds],
        }

    @classmethod
    def from_dict(cls, value: Mapping, schedule: DiceSchedule) -> "GameState":
        expected = {"state_version", "week_id", "rules_version", "dice_version", "schedule_commitment",
                    "mode", "scores", "held", "revision", "rolls", "rounds"}
        if not isinstance(value, Mapping) or set(value) != expected:
            raise WeeklyGameError("Invalid saved weekly game format.")
        if type(value["state_version"]) is not int or value["state_version"] != STATE_VERSION:
            raise UnsupportedVersion("Unsupported saved weekly game version.")
        try:
            state = cls(
                week_id=value["week_id"], rules_version=value["rules_version"],
                dice_version=value["dice_version"], schedule_commitment=value["schedule_commitment"],
                mode=value["mode"], scores=tuple(value["scores"]), held=_dice(value["held"], count=None),
                revision=_integer(value["revision"], 0, 2**63 - 1, "revision"),
                rolls=tuple(RollRecord.from_dict(r) for r in value["rolls"]),
                rounds=tuple(RoundRecord.from_dict(r) for r in value["rounds"]),
            )
        except (TypeError, KeyError) as exc:
            raise WeeklyGameError("Invalid saved weekly game.") from exc
        validate_state(state, schedule)
        return state


def _validate_rolls(rolls: tuple[RollRecord, ...], schedule: DiceSchedule, round_number: int) -> None:
    if not isinstance(rolls, tuple) or not 1 <= len(rolls) <= 3:
        raise WeeklyGameError("Invalid saved roll count.")
    previous: tuple[int, ...] = ()
    for number, roll in enumerate(rolls, 1):
        _dice(roll.dice)
        held = _held(previous, roll.held_before) if number > 1 else ()
        if roll.held_before != held or (number > 1 and len(held) == 5):
            raise WeeklyGameError("Invalid saved hold.")
        expected = tuple(sorted(held + schedule.pool(round_number, number)[:5 - len(held)]))
        if expected != roll.dice:
            raise WeeklyGameError("Saved dice do not match this week's schedule.")
        previous = roll.dice


def validate_state(state: GameState, schedule: DiceSchedule) -> None:
    """Check persisted state against its private schedule and complete own history."""
    if state.rules_version != schedule.rules_version or state.dice_version != schedule.dice_version:
        raise UnsupportedVersion("Game and schedule versions do not match.")
    if state.week_id != schedule.week_id or state.schedule_commitment != schedule.commitment:
        raise WeeklyGameError("Game and weekly dice schedule do not match.")
    if state.mode not in ("official", "practice"):
        raise WeeklyGameError("Invalid weekly game mode.")
    _integer(state.revision, 0, 2**63 - 1, "revision")
    if not isinstance(state.scores, tuple) or len(state.scores) != 13:
        raise WeeklyGameError("Invalid saved scorecard length.")
    _scorecard(state.scorecard)
    if not isinstance(state.rounds, tuple) or len(state.rounds) > 13:
        raise WeeklyGameError("Invalid saved round count.")
    scores: dict[str, int | None] = dict.fromkeys(CATEGORIES)
    minimum_revision = 0
    for number, round_record in enumerate(state.rounds, 1):
        _validate_rolls(round_record.rolls, schedule, number)
        option = next((o for o in scoring_options(round_record.rolls[-1].dice, scores)
                       if o.category == round_record.category), None)
        if option is None or (round_record.points, round_record.yahtzee_bonus) != (option.points, option.yahtzee_bonus):
            raise WeeklyGameError("Saved round contains an invalid score.")
        scores[round_record.category] = round_record.points
        minimum_revision += len(round_record.rolls)  # rerolls plus scoring action
    if scores != state.scorecard:
        raise WeeklyGameError("Saved scorecard does not match completed rounds.")
    _validate_rolls(state.rolls, schedule, state.round_number)
    if state.complete:
        if state.rolls != state.rounds[-1].rolls or state.held:
            raise WeeklyGameError("Invalid completed game state.")
    else:
        minimum_revision += len(state.rolls) - 1
        if _held(state.dice, state.held) != state.held:
            raise WeeklyGameError("Saved hold is not canonical.")
        if len(state.rolls) == 3 and state.held:
            raise WeeklyGameError("The final roll cannot have a pending hold.")
    if state.revision < minimum_revision:
        raise WeeklyGameError("Saved revision predates the recorded actions.")


def new_game(schedule: DiceSchedule, *, mode: str = "official", now: datetime | None = None) -> GameState:
    if mode not in ("official", "practice"):
        raise InvalidAction("Invalid weekly game mode.")
    if mode == "official":
        _require_open_week(schedule.week_id, now)
    return GameState(schedule.week_id, schedule.commitment, mode, (None,) * 13,
                     (RollRecord(tuple(sorted(schedule.pool(1, 1)))),))


def apply_action(state: GameState, schedule: DiceSchedule, action: Mapping,
                 *, expected_revision: int, now: datetime | None = None) -> GameState:
    """Validate and return an immutable next state; never accept supplied dice.

    The store must compare and commit the expected revision atomically. An
    action UUID/receipt in that transaction handles network retries. This pure
    function also refuses stale revisions, but is not itself a database lock.
    """
    validate_state(state, schedule)
    _integer(expected_revision, 0, 2**63 - 1, "expected revision")
    if expected_revision != state.revision:
        raise StaleState("Your game changed in another tab. Reload the saved game.")
    if state.complete:
        raise GameComplete("This completed game is locked.")
    if state.mode == "official":
        _require_open_week(state.week_id, now)
    if not isinstance(action, Mapping):
        raise InvalidAction("Invalid weekly action.")
    kind = action.get("kind")
    allowed = {"hold": {"kind", "held"}, "reroll": {"kind"}, "score": {"kind", "category"}}
    if not isinstance(kind, str) or kind not in allowed or set(action) != allowed[kind]:
        raise InvalidAction("Invalid weekly action fields.")
    revision = state.revision + 1
    if kind == "hold":
        if state.roll_number >= 3:
            raise InvalidAction("Choose a scoring category after your third roll.")
        return replace(state, held=_held(state.dice, action["held"]), revision=revision)
    if kind == "reroll":
        if state.roll_number >= 3:
            raise InvalidAction("There are no rerolls left in this round.")
        if len(state.held) == 5:
            raise InvalidAction("Release at least one die or score this hand.")
        pool = schedule.pool(state.round_number, state.roll_number + 1)
        dice = tuple(sorted(state.held + pool[:5 - len(state.held)]))
        rolls = state.rolls + (RollRecord(dice, state.held),)
        # Keep the selected multiset after Roll 2; users may change it. Roll 3
        # has no next hold. All equivalent duplicate-die selections are equal.
        held = state.held if len(rolls) < 3 else ()
        return replace(state, rolls=rolls, held=held, revision=revision)
    option = next((o for o in scoring_options(state.dice, state.scorecard)
                   if o.category == action["category"]), None)
    if option is None:
        raise InvalidAction("That category is filled or unavailable under the Joker rule.")
    scores = dict(state.scorecard)
    scores[option.category] = option.points
    rounds = state.rounds + (RoundRecord(option.category, option.points, option.yahtzee_bonus, state.rolls),)
    rolls = state.rolls if len(rounds) == 13 else (RollRecord(tuple(sorted(schedule.pool(len(rounds) + 1, 1)))),)
    return replace(state, scores=tuple(scores[c] for c in CATEGORIES), rounds=rounds,
                   rolls=rolls, held=(), revision=revision)
