from __future__ import annotations

"""Persistence contract for Yahtzee Coach v43B Daily Challenge.

This module deliberately has no Streamlit, Supabase, exact-solver, or puzzle-bank
imports.  It defines the persistence behavior independently so it can be tested
without touching the locked strategy engine or the v42.6/v43A challenge bank.

The first production backend will implement the same API against Supabase.  The
in-memory backend below is the reference implementation used by v43B tests.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import base64
import hashlib
import hmac
import os
import re
import secrets
from typing import Callable, Iterable, Mapping, Protocol, Sequence
from uuid import uuid4

TIE_TOLERANCE = 1e-9
JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class DailyStoreError(RuntimeError):
    """Base class for persistence-contract errors."""


class PlayerNameTaken(DailyStoreError):
    pass


class InvalidPin(DailyStoreError):
    pass


class PlayerNotFound(DailyStoreError):
    pass


class GroupNotFound(DailyStoreError):
    pass


class ChallengeMismatch(DailyStoreError):
    pass


class AttemptAlreadyComplete(DailyStoreError):
    pass


class DuplicateAnswer(DailyStoreError):
    pass


class OutOfOrderAnswer(DailyStoreError):
    pass


class InvalidOfficialAnswer(DailyStoreError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_display_name(display_name: str) -> tuple[str, str]:
    cleaned = re.sub(r"\s+", " ", str(display_name or "").strip())
    if not (2 <= len(cleaned) <= 24):
        raise ValueError("Display name must be 2-24 characters.")
    return cleaned, cleaned.casefold()


def validate_pin(pin: str) -> str:
    value = str(pin or "").strip()
    if not value.isdigit() or not (4 <= len(value) <= 12):
        raise InvalidPin("PIN must contain 4-12 digits.")
    return value


def hash_pin(pin: str, *, salt: bytes | None = None) -> str:
    """Hash a private PIN using stdlib scrypt with a random per-player salt."""
    pin = validate_pin(pin)
    salt = salt or os.urandom(16)
    n, r, p, dklen = 2**14, 8, 1, 32
    digest = hashlib.scrypt(pin.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen)
    enc_salt = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    enc_digest = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"scrypt${n}${r}${p}${dklen}${enc_salt}${enc_digest}"


def _decode_b64url(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


def verify_pin(pin: str, encoded_hash: str) -> bool:
    try:
        pin = validate_pin(pin)
        algorithm, n, r, p, dklen, enc_salt, enc_digest = str(encoded_hash).split("$", 6)
        if algorithm != "scrypt":
            return False
        expected = _decode_b64url(enc_digest)
        actual = hashlib.scrypt(
            pin.encode("utf-8"),
            salt=_decode_b64url(enc_salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=int(dklen),
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def generate_join_code(length: int = 6) -> str:
    return "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(length))


@dataclass(frozen=True)
class PublicPlayer:
    player_id: str
    display_name: str
    created_at: datetime


@dataclass
class _StoredPlayer:
    player_id: str
    display_name: str
    display_name_key: str
    pin_hash: str
    created_at: datetime

    def public(self) -> PublicPlayer:
        return PublicPlayer(self.player_id, self.display_name, self.created_at)


@dataclass(frozen=True)
class GroupRecord:
    group_id: str
    group_name: str
    join_code: str
    created_by_player_id: str
    created_at: datetime


@dataclass(frozen=True)
class ChallengeRecord:
    challenge_id: str
    challenge_date: str
    challenge_version: str
    puzzle_ids: tuple[str, ...]
    created_at: datetime


@dataclass
class AttemptRecord:
    attempt_id: str
    player_id: str
    challenge_id: str
    started_at: datetime
    completed_at: datetime | None = None
    total_ev_loss: float | None = None
    exact_count: int | None = None
    worst_miss: float | None = None
    best_exact_streak: int | None = None

    @property
    def complete(self) -> bool:
        return self.completed_at is not None


@dataclass(frozen=True)
class AnswerRecord:
    attempt_id: str
    question_number: int
    puzzle_id: str
    chosen_hold: tuple[int, ...]
    optimal_hold: tuple[int, ...]
    points_lost: float
    exact: bool
    solver_source: str
    submitted_at: datetime


@dataclass(frozen=True)
class ResumeState:
    attempt: AttemptRecord
    answers: tuple[AnswerRecord, ...]
    next_question_number: int | None


class DailyStore(Protocol):
    """Behavior required by the v43B Streamlit integration."""

    def create_player(self, display_name: str, pin: str) -> PublicPlayer: ...
    def authenticate_player(self, display_name: str, pin: str) -> PublicPlayer | None: ...
    def create_group(self, player_id: str, group_name: str) -> GroupRecord: ...
    def join_group(self, player_id: str, join_code: str) -> GroupRecord: ...
    def list_groups(self, player_id: str) -> list[GroupRecord]: ...
    def list_group_members(self, group_id: str) -> list[dict]: ...
    def ensure_challenge(self, challenge_id: str, challenge_date: str,
                         challenge_version: str, puzzle_ids: Sequence[str]) -> ChallengeRecord: ...
    def get_or_create_attempt(self, player_id: str, challenge_id: str) -> tuple[AttemptRecord, bool]: ...
    def get_resume_state(self, player_id: str, challenge_id: str) -> ResumeState | None: ...
    def save_answer(self, attempt_id: str, *, question_number: int, puzzle_id: str,
                    chosen_hold: Sequence[int], optimal_hold: Sequence[int], points_lost: float,
                    solver_source: str = "exact") -> AnswerRecord: ...
    def complete_attempt(self, attempt_id: str) -> AttemptRecord: ...
    def leaderboard(self, group_id: str, challenge_id: str) -> list[dict]: ...
    def group_question_stats(self, group_id: str, challenge_id: str) -> list[dict]: ...
    def current_participation_streak(self, player_id: str, current_date: str) -> int: ...


class InMemoryDailyStore:
    """Reference backend used by v43B automated tests."""

    def __init__(self, *, now_factory: Callable[[], datetime] = utc_now,
                 join_code_factory: Callable[[], str] = generate_join_code):
        self._now = now_factory
        self._join_code_factory = join_code_factory
        self.players: dict[str, _StoredPlayer] = {}
        self.player_id_by_name_key: dict[str, str] = {}
        self.groups: dict[str, GroupRecord] = {}
        self.group_id_by_join_code: dict[str, str] = {}
        self.group_members: set[tuple[str, str]] = set()
        self.challenges: dict[str, ChallengeRecord] = {}
        self.attempts: dict[str, AttemptRecord] = {}
        self.attempt_id_by_player_challenge: dict[tuple[str, str], str] = {}
        self.answers: dict[tuple[str, int], AnswerRecord] = {}

    def _require_player(self, player_id: str) -> _StoredPlayer:
        player = self.players.get(str(player_id))
        if player is None:
            raise PlayerNotFound(f"Unknown player_id: {player_id}")
        return player

    def _require_attempt(self, attempt_id: str) -> AttemptRecord:
        attempt = self.attempts.get(str(attempt_id))
        if attempt is None:
            raise DailyStoreError(f"Unknown attempt_id: {attempt_id}")
        return attempt

    def create_player(self, display_name: str, pin: str) -> PublicPlayer:
        display_name, name_key = normalize_display_name(display_name)
        if name_key in self.player_id_by_name_key:
            raise PlayerNameTaken("That display name is already in use.")
        player = _StoredPlayer(
            player_id=str(uuid4()),
            display_name=display_name,
            display_name_key=name_key,
            pin_hash=hash_pin(pin),
            created_at=self._now(),
        )
        self.players[player.player_id] = player
        self.player_id_by_name_key[name_key] = player.player_id
        return player.public()

    def authenticate_player(self, display_name: str, pin: str) -> PublicPlayer | None:
        try:
            _, name_key = normalize_display_name(display_name)
        except ValueError:
            return None
        player_id = self.player_id_by_name_key.get(name_key)
        if player_id is None:
            return None
        player = self.players[player_id]
        return player.public() if verify_pin(pin, player.pin_hash) else None

    def create_group(self, player_id: str, group_name: str) -> GroupRecord:
        self._require_player(player_id)
        group_name = re.sub(r"\s+", " ", str(group_name or "").strip())
        if not (2 <= len(group_name) <= 40):
            raise ValueError("Group name must be 2-40 characters.")
        join_code = ""
        for _ in range(20):
            candidate = str(self._join_code_factory()).strip().upper()
            if candidate and candidate not in self.group_id_by_join_code:
                join_code = candidate
                break
        if not join_code:
            raise DailyStoreError("Could not generate a unique join code.")
        group = GroupRecord(
            group_id=str(uuid4()),
            group_name=group_name,
            join_code=join_code,
            created_by_player_id=player_id,
            created_at=self._now(),
        )
        self.groups[group.group_id] = group
        self.group_id_by_join_code[group.join_code] = group.group_id
        self.group_members.add((group.group_id, player_id))
        return group

    def join_group(self, player_id: str, join_code: str) -> GroupRecord:
        self._require_player(player_id)
        code = re.sub(r"\s+", "", str(join_code or "")).upper()
        group_id = self.group_id_by_join_code.get(code)
        if group_id is None:
            raise GroupNotFound("No group found for that join code.")
        self.group_members.add((group_id, player_id))
        return self.groups[group_id]

    def list_groups(self, player_id: str) -> list[GroupRecord]:
        self._require_player(player_id)
        groups = [self.groups[group_id] for group_id, member_id in self.group_members if member_id == player_id]
        return sorted(groups, key=lambda group: (group.group_name.casefold(), group.group_id))

    def list_group_members(self, group_id: str) -> list[dict]:
        if str(group_id) not in self.groups:
            raise GroupNotFound(f"Unknown group_id: {group_id}")
        rows = []
        for member_group_id, player_id in self.group_members:
            if member_group_id != str(group_id):
                continue
            player = self._require_player(player_id).public()
            rows.append({
                "player_id": player.player_id,
                "display_name": player.display_name,
            })
        return sorted(rows, key=lambda row: (row["display_name"].casefold(), row["player_id"]))

    def ensure_challenge(self, challenge_id: str, challenge_date: str,
                         challenge_version: str, puzzle_ids: Sequence[str]) -> ChallengeRecord:
        challenge_id = str(challenge_id).strip()
        challenge_version = str(challenge_version).strip()
        parsed_date = date.fromisoformat(str(challenge_date)).isoformat()
        puzzle_ids = tuple(str(value) for value in puzzle_ids)
        if len(puzzle_ids) != 10 or len(set(puzzle_ids)) != 10:
            raise ValueError("An official Daily Challenge must contain exactly 10 unique puzzle IDs.")
        existing = self.challenges.get(challenge_id)
        if existing:
            if (existing.challenge_date != parsed_date or
                    existing.challenge_version != challenge_version or
                    existing.puzzle_ids != puzzle_ids):
                raise ChallengeMismatch("Existing challenge_id does not match date/version/puzzle IDs.")
            return existing
        # One challenge set per exact (date, version) contract.
        for other in self.challenges.values():
            if other.challenge_date == parsed_date and other.challenge_version == challenge_version:
                raise ChallengeMismatch("That date/version is already registered under another challenge_id.")
        record = ChallengeRecord(
            challenge_id=challenge_id,
            challenge_date=parsed_date,
            challenge_version=challenge_version,
            puzzle_ids=puzzle_ids,
            created_at=self._now(),
        )
        self.challenges[challenge_id] = record
        return record

    def get_or_create_attempt(self, player_id: str, challenge_id: str) -> tuple[AttemptRecord, bool]:
        self._require_player(player_id)
        if challenge_id not in self.challenges:
            raise DailyStoreError(f"Unknown challenge_id: {challenge_id}")
        key = (player_id, challenge_id)
        attempt_id = self.attempt_id_by_player_challenge.get(key)
        if attempt_id:
            return self.attempts[attempt_id], False
        attempt = AttemptRecord(
            attempt_id=str(uuid4()),
            player_id=player_id,
            challenge_id=challenge_id,
            started_at=self._now(),
        )
        self.attempts[attempt.attempt_id] = attempt
        self.attempt_id_by_player_challenge[key] = attempt.attempt_id
        return attempt, True

    def _answers_for_attempt(self, attempt_id: str) -> list[AnswerRecord]:
        rows = [answer for (row_attempt_id, _), answer in self.answers.items() if row_attempt_id == attempt_id]
        return sorted(rows, key=lambda answer: answer.question_number)

    def get_resume_state(self, player_id: str, challenge_id: str) -> ResumeState | None:
        attempt_id = self.attempt_id_by_player_challenge.get((player_id, challenge_id))
        if not attempt_id:
            return None
        attempt = self.attempts[attempt_id]
        answers = tuple(self._answers_for_attempt(attempt_id))
        next_question = None if attempt.complete else len(answers) + 1
        return ResumeState(attempt=attempt, answers=answers, next_question_number=next_question)

    def save_answer(self, attempt_id: str, *, question_number: int, puzzle_id: str,
                    chosen_hold: Sequence[int], optimal_hold: Sequence[int], points_lost: float,
                    solver_source: str = "exact") -> AnswerRecord:
        attempt = self._require_attempt(attempt_id)
        if attempt.complete:
            raise AttemptAlreadyComplete("Completed Daily attempts are immutable.")
        if str(solver_source) != "exact":
            raise InvalidOfficialAnswer("Official Daily answers must be scored by the exact solver.")
        question_number = int(question_number)
        if not 1 <= question_number <= 10:
            raise ValueError("question_number must be 1-10.")
        key = (attempt_id, question_number)
        if key in self.answers:
            raise DuplicateAnswer("That Daily answer is already locked.")
        existing = self._answers_for_attempt(attempt_id)
        expected_question = len(existing) + 1
        if question_number != expected_question:
            raise OutOfOrderAnswer(f"Expected question {expected_question}, got {question_number}.")
        challenge = self.challenges[attempt.challenge_id]
        expected_puzzle_id = challenge.puzzle_ids[question_number - 1]
        if str(puzzle_id) != expected_puzzle_id:
            raise ChallengeMismatch("Answer puzzle_id does not match the registered Daily Challenge slot.")
        loss = float(points_lost)
        if loss < -TIE_TOLERANCE:
            raise ValueError("points_lost cannot be negative.")
        loss = max(0.0, loss)
        record = AnswerRecord(
            attempt_id=attempt_id,
            question_number=question_number,
            puzzle_id=str(puzzle_id),
            chosen_hold=tuple(int(value) for value in chosen_hold),
            optimal_hold=tuple(int(value) for value in optimal_hold),
            points_lost=loss,
            exact=loss <= TIE_TOLERANCE,
            solver_source="exact",
            submitted_at=self._now(),
        )
        self.answers[key] = record
        return record

    def complete_attempt(self, attempt_id: str) -> AttemptRecord:
        attempt = self._require_attempt(attempt_id)
        if attempt.complete:
            return attempt
        answers = self._answers_for_attempt(attempt_id)
        if len(answers) != 10 or [answer.question_number for answer in answers] != list(range(1, 11)):
            raise DailyStoreError("A Daily attempt cannot complete until all 10 answers are locked.")
        losses = [answer.points_lost for answer in answers]
        best_streak = 0
        current = 0
        for answer in answers:
            if answer.exact:
                current += 1
                best_streak = max(best_streak, current)
            else:
                current = 0
        attempt.total_ev_loss = float(sum(losses))
        attempt.exact_count = sum(answer.exact for answer in answers)
        attempt.worst_miss = max(losses) if losses else 0.0
        attempt.best_exact_streak = best_streak
        attempt.completed_at = self._now()
        return attempt

    def leaderboard(self, group_id: str, challenge_id: str) -> list[dict]:
        if group_id not in self.groups:
            raise GroupNotFound(group_id)
        member_ids = {player_id for row_group_id, player_id in self.group_members if row_group_id == group_id}
        rows = []
        for player_id in member_ids:
            attempt_id = self.attempt_id_by_player_challenge.get((player_id, challenge_id))
            if not attempt_id:
                continue
            attempt = self.attempts[attempt_id]
            if not attempt.complete:
                continue
            player = self.players[player_id]
            rows.append({
                "player_id": player_id,
                "display_name": player.display_name,
                "total_ev_loss": float(attempt.total_ev_loss or 0.0),
                "exact_count": int(attempt.exact_count or 0),
                "worst_miss": float(attempt.worst_miss or 0.0),
                "best_exact_streak": int(attempt.best_exact_streak or 0),
                "completed_at": attempt.completed_at,
            })
        rows.sort(key=lambda item: (
            round(item["total_ev_loss"], 12),
            -item["exact_count"],
            round(item["worst_miss"], 12),
            item["display_name"].casefold(),
            item["player_id"],
        ))
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
        return rows

    def group_question_stats(self, group_id: str, challenge_id: str) -> list[dict]:
        if group_id not in self.groups:
            raise GroupNotFound(group_id)
        completed_player_ids = {row["player_id"] for row in self.leaderboard(group_id, challenge_id)}
        rows: list[dict] = []
        for question_number in range(1, 11):
            answers: list[AnswerRecord] = []
            for player_id in completed_player_ids:
                attempt_id = self.attempt_id_by_player_challenge[(player_id, challenge_id)]
                answer = self.answers.get((attempt_id, question_number))
                if answer:
                    answers.append(answer)
            if not answers:
                continue
            exact_count = sum(answer.exact for answer in answers)
            rows.append({
                "question_number": question_number,
                "players": len(answers),
                "exact_count": exact_count,
                "exact_rate": exact_count / len(answers),
                "avg_loss": sum(answer.points_lost for answer in answers) / len(answers),
            })
        return rows

    def current_participation_streak(self, player_id: str, current_date: str) -> int:
        self._require_player(player_id)
        today = date.fromisoformat(str(current_date))
        completed_dates: set[date] = set()
        for attempt in self.attempts.values():
            if attempt.player_id != player_id or not attempt.complete:
                continue
            challenge = self.challenges[attempt.challenge_id]
            completed_dates.add(date.fromisoformat(challenge.challenge_date))
        # Before today's challenge is complete, yesterday's streak is still alive.
        cursor = today if today in completed_dates else today - timedelta(days=1)
        streak = 0
        while cursor in completed_dates:
            streak += 1
            cursor -= timedelta(days=1)
        return streak
