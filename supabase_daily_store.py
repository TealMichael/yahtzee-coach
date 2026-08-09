from __future__ import annotations

"""Supabase persistence backend for Yahtzee Coach v43B Daily Challenge.

This module implements the persistence contract defined in ``daily_store.py``.
It intentionally contains no Streamlit UI code and no Yahtzee solver imports.
The exact strategy engine remains local to the app; Supabase stores only player,
group, challenge, attempt, and compact answer/result data.

Expected server-side secrets:
    SUPABASE_URL
    SUPABASE_SECRET_KEY

The secret key must only be used from the trusted Streamlit server.
"""

from datetime import date, datetime, timedelta, timezone
import re
from typing import Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from supabase import Client, create_client

from daily_store import (
    TIE_TOLERANCE,
    AnswerRecord,
    AttemptAlreadyComplete,
    AttemptRecord,
    ChallengeMismatch,
    ChallengeRecord,
    DailyStoreError,
    DuplicateAnswer,
    GroupNotFound,
    GroupRecord,
    InvalidOfficialAnswer,
    OutOfOrderAnswer,
    PlayerNameTaken,
    PlayerNotFound,
    PublicPlayer,
    ResumeState,
    generate_join_code,
    hash_pin,
    normalize_display_name,
    utc_now,
    verify_pin,
)



def _normalize_supabase_url(value: str) -> tuple[str, bool]:
    """Return the base Supabase project URL expected by create_client().

    The dashboard can surface REST/Data API endpoints such as
    https://<project>.supabase.co/rest/v1.  supabase-py expects the project base
    URL instead and appends product routes itself.  Normalizing known API paths
    here makes the deployment tolerant of either form without exposing secrets.
    """
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        return raw, False

    try:
        parts = urlsplit(raw)
    except Exception:
        return raw, False

    path = (parts.path or "").rstrip("/")
    known_api_paths = (
        "/rest/v1",
        "/auth/v1",
        "/storage/v1",
        "/realtime/v1",
        "/functions/v1",
        "/graphql/v1",
    )
    if path in known_api_paths:
        normalized = urlunsplit((parts.scheme, parts.netloc, "", "", "")).rstrip("/")
        return normalized, normalized != raw

    return raw, False

def _as_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        result = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        result = datetime.fromisoformat(text)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result


def _row_list(response) -> list[dict]:
    data = getattr(response, "data", None)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def _first_row(response) -> dict | None:
    rows = _row_list(response)
    return rows[0] if rows else None


def _error_text(exc: Exception) -> str:
    parts = [str(exc)]
    for attr in ("message", "details", "hint", "code"):
        value = getattr(exc, attr, None)
        if value:
            parts.append(str(value))
    return " | ".join(parts).lower()


def _is_unique_violation(exc: Exception) -> bool:
    text = _error_text(exc)
    return "23505" in text or "duplicate key" in text or "unique constraint" in text


def _player_from_row(row: Mapping) -> PublicPlayer:
    return PublicPlayer(
        player_id=str(row["player_id"]),
        display_name=str(row["display_name"]),
        created_at=_as_datetime(row["created_at"]) or utc_now(),
    )


def _group_from_row(row: Mapping) -> GroupRecord:
    return GroupRecord(
        group_id=str(row["group_id"]),
        group_name=str(row["group_name"]),
        join_code=str(row["join_code"]),
        created_by_player_id=str(row["created_by_player_id"]),
        created_at=_as_datetime(row["created_at"]) or utc_now(),
    )


def _challenge_from_row(row: Mapping) -> ChallengeRecord:
    return ChallengeRecord(
        challenge_id=str(row["challenge_id"]),
        challenge_date=str(row["challenge_date"]),
        challenge_version=str(row["challenge_version"]),
        puzzle_ids=tuple(str(value) for value in (row.get("puzzle_ids") or [])),
        created_at=_as_datetime(row["created_at"]) or utc_now(),
    )


def _attempt_from_row(row: Mapping) -> AttemptRecord:
    return AttemptRecord(
        attempt_id=str(row["attempt_id"]),
        player_id=str(row["player_id"]),
        challenge_id=str(row["challenge_id"]),
        started_at=_as_datetime(row["started_at"]) or utc_now(),
        completed_at=_as_datetime(row.get("completed_at")),
        total_ev_loss=(None if row.get("total_ev_loss") is None else float(row["total_ev_loss"])),
        exact_count=(None if row.get("exact_count") is None else int(row["exact_count"])),
        worst_miss=(None if row.get("worst_miss") is None else float(row["worst_miss"])),
        best_exact_streak=(
            None if row.get("best_exact_streak") is None else int(row["best_exact_streak"])
        ),
    )


def _answer_from_row(row: Mapping) -> AnswerRecord:
    return AnswerRecord(
        attempt_id=str(row["attempt_id"]),
        question_number=int(row["question_number"]),
        puzzle_id=str(row["puzzle_id"]),
        chosen_hold=tuple(int(value) for value in (row.get("chosen_hold") or [])),
        optimal_hold=tuple(int(value) for value in (row.get("optimal_hold") or [])),
        points_lost=float(row["points_lost"]),
        exact=bool(row["exact"]),
        solver_source=str(row.get("solver_source") or "exact"),
        submitted_at=_as_datetime(row["submitted_at"]) or utc_now(),
    )


class SupabaseDailyStore:
    """Production v43B DailyStore implementation backed by Supabase/Postgres."""

    def __init__(self, supabase_url: str, supabase_secret_key: str, *, client: Client | None = None):
        raw_url = str(supabase_url or "").strip()
        url, was_normalized = _normalize_supabase_url(raw_url)
        key = str(supabase_secret_key or "").strip()
        if not url:
            raise ValueError("SUPABASE_URL is missing.")
        if not key:
            raise ValueError("SUPABASE_SECRET_KEY is missing.")
        self.supabase_url = url
        self.url_was_normalized = was_normalized
        self.client: Client = client or create_client(url, key)

    @classmethod
    def from_secrets(cls, secrets: Mapping[str, str]) -> "SupabaseDailyStore":
        """Build from a mapping such as Streamlit's ``st.secrets`` object."""
        return cls(
            str(secrets["SUPABASE_URL"]),
            str(secrets["SUPABASE_SECRET_KEY"]),
        )

    # ---------- Small DB helpers ----------

    def health_check(self) -> bool:
        """Make a harmless server-side query to verify credentials/table access."""
        self.client.table("players").select("player_id").limit(1).execute()
        return True

    def _require_player_row(self, player_id: str) -> dict:
        response = (
            self.client.table("players")
            .select("player_id,display_name,display_name_key,pin_hash,created_at")
            .eq("player_id", str(player_id))
            .limit(1)
            .execute()
        )
        row = _first_row(response)
        if row is None:
            raise PlayerNotFound(f"Unknown player_id: {player_id}")
        return row

    def _require_group_row(self, group_id: str) -> dict:
        response = (
            self.client.table("friend_groups")
            .select("group_id,group_name,join_code,created_by_player_id,created_at")
            .eq("group_id", str(group_id))
            .limit(1)
            .execute()
        )
        row = _first_row(response)
        if row is None:
            raise GroupNotFound(str(group_id))
        return row

    def _require_attempt_row(self, attempt_id: str) -> dict:
        response = (
            self.client.table("daily_attempts")
            .select("*")
            .eq("attempt_id", str(attempt_id))
            .limit(1)
            .execute()
        )
        row = _first_row(response)
        if row is None:
            raise DailyStoreError(f"Unknown attempt_id: {attempt_id}")
        return row

    def _answers_for_attempt(self, attempt_id: str) -> list[AnswerRecord]:
        response = (
            self.client.table("daily_answers")
            .select("*")
            .eq("attempt_id", str(attempt_id))
            .order("question_number")
            .execute()
        )
        return [_answer_from_row(row) for row in _row_list(response)]

    # ---------- Player identity ----------

    def create_player(self, display_name: str, pin: str) -> PublicPlayer:
        display_name, name_key = normalize_display_name(display_name)
        payload = {
            "display_name": display_name,
            "display_name_key": name_key,
            "pin_hash": hash_pin(pin),
        }
        try:
            response = (
                self.client.table("players")
                .insert(payload)
                .select("player_id,display_name,created_at")
                .execute()
            )
        except Exception as exc:
            if _is_unique_violation(exc):
                raise PlayerNameTaken("That display name is already in use.") from exc
            raise
        row = _first_row(response)
        if row is None:
            raise DailyStoreError("Supabase did not return the created player.")
        return _player_from_row(row)

    def authenticate_player(self, display_name: str, pin: str) -> PublicPlayer | None:
        try:
            _, name_key = normalize_display_name(display_name)
        except ValueError:
            return None
        response = (
            self.client.table("players")
            .select("player_id,display_name,pin_hash,created_at")
            .eq("display_name_key", name_key)
            .limit(1)
            .execute()
        )
        row = _first_row(response)
        if row is None:
            return None
        if not verify_pin(pin, str(row["pin_hash"])):
            return None
        return _player_from_row(row)

    # ---------- Friend groups ----------

    def create_group(self, player_id: str, group_name: str) -> GroupRecord:
        self._require_player_row(player_id)
        cleaned_name = re.sub(r"\s+", " ", str(group_name or "").strip())
        if not (2 <= len(cleaned_name) <= 40):
            raise ValueError("Group name must be 2-40 characters.")

        last_exc: Exception | None = None
        for _ in range(20):
            join_code = generate_join_code()
            try:
                response = (
                    self.client.table("friend_groups")
                    .insert({
                        "group_name": cleaned_name,
                        "join_code": join_code,
                        "created_by_player_id": str(player_id),
                    })
                    .select("group_id,group_name,join_code,created_by_player_id,created_at")
                    .execute()
                )
                row = _first_row(response)
                if row is None:
                    raise DailyStoreError("Supabase did not return the created group.")
                group = _group_from_row(row)
                try:
                    self.client.table("group_members").insert({
                        "group_id": group.group_id,
                        "player_id": str(player_id),
                    }).execute()
                except Exception:
                    # Avoid leaving an orphan group if creator membership fails.
                    self.client.table("friend_groups").delete().eq(
                        "group_id", group.group_id
                    ).execute()
                    raise
                return group
            except Exception as exc:
                last_exc = exc
                if _is_unique_violation(exc):
                    continue
                raise
        raise DailyStoreError("Could not generate a unique group join code.") from last_exc

    def join_group(self, player_id: str, join_code: str) -> GroupRecord:
        self._require_player_row(player_id)
        code = re.sub(r"\s+", "", str(join_code or "")).upper()
        response = (
            self.client.table("friend_groups")
            .select("group_id,group_name,join_code,created_by_player_id,created_at")
            .eq("join_code", code)
            .limit(1)
            .execute()
        )
        row = _first_row(response)
        if row is None:
            raise GroupNotFound("No group found for that join code.")
        group = _group_from_row(row)
        try:
            self.client.table("group_members").insert({
                "group_id": group.group_id,
                "player_id": str(player_id),
            }).execute()
        except Exception as exc:
            # Already belonging to a group is idempotent/successful.
            if not _is_unique_violation(exc):
                raise
        return group

    def list_groups(self, player_id: str) -> list[GroupRecord]:
        self._require_player_row(player_id)
        memberships = _row_list(
            self.client.table("group_members")
            .select("group_id")
            .eq("player_id", str(player_id))
            .execute()
        )
        groups: list[GroupRecord] = []
        for membership in memberships:
            response = (
                self.client.table("friend_groups")
                .select("group_id,group_name,join_code,created_by_player_id,created_at")
                .eq("group_id", str(membership["group_id"]))
                .limit(1)
                .execute()
            )
            row = _first_row(response)
            if row is not None:
                groups.append(_group_from_row(row))
        return sorted(groups, key=lambda group: (group.group_name.casefold(), group.group_id))

    # ---------- Challenge registration ----------

    def ensure_challenge(
        self,
        challenge_id: str,
        challenge_date: str,
        challenge_version: str,
        puzzle_ids: Sequence[str],
    ) -> ChallengeRecord:
        challenge_id = str(challenge_id).strip()
        parsed_date = date.fromisoformat(str(challenge_date)).isoformat()
        challenge_version = str(challenge_version).strip()
        puzzle_tuple = tuple(str(value) for value in puzzle_ids)
        if len(puzzle_tuple) != 10 or len(set(puzzle_tuple)) != 10:
            raise ValueError("An official Daily Challenge must contain exactly 10 unique puzzle IDs.")

        existing_response = (
            self.client.table("daily_challenges")
            .select("*")
            .eq("challenge_id", challenge_id)
            .limit(1)
            .execute()
        )
        existing_row = _first_row(existing_response)
        if existing_row is not None:
            existing = _challenge_from_row(existing_row)
            if (
                existing.challenge_date != parsed_date
                or existing.challenge_version != challenge_version
                or existing.puzzle_ids != puzzle_tuple
            ):
                raise ChallengeMismatch(
                    "Existing challenge_id does not match date/version/puzzle IDs."
                )
            return existing

        date_version_response = (
            self.client.table("daily_challenges")
            .select("*")
            .eq("challenge_date", parsed_date)
            .eq("challenge_version", challenge_version)
            .limit(1)
            .execute()
        )
        other_row = _first_row(date_version_response)
        if other_row is not None:
            other = _challenge_from_row(other_row)
            if other.challenge_id != challenge_id:
                raise ChallengeMismatch(
                    "That date/version is already registered under another challenge_id."
                )
            return other

        payload = {
            "challenge_id": challenge_id,
            "challenge_date": parsed_date,
            "challenge_version": challenge_version,
            "puzzle_ids": list(puzzle_tuple),
        }
        try:
            response = self.client.table("daily_challenges").insert(payload).select("*").execute()
        except Exception as exc:
            if not _is_unique_violation(exc):
                raise
            # A simultaneous request may have registered it first. Re-read and verify.
            response = (
                self.client.table("daily_challenges")
                .select("*")
                .eq("challenge_id", challenge_id)
                .limit(1)
                .execute()
            )
        row = _first_row(response)
        if row is None:
            raise DailyStoreError("Could not register the Daily Challenge.")
        record = _challenge_from_row(row)
        if (
            record.challenge_date != parsed_date
            or record.challenge_version != challenge_version
            or record.puzzle_ids != puzzle_tuple
        ):
            raise ChallengeMismatch("Registered Daily Challenge does not match the local challenge.")
        return record

    # ---------- Attempts / answer locking ----------

    def get_or_create_attempt(self, player_id: str, challenge_id: str) -> tuple[AttemptRecord, bool]:
        self._require_player_row(player_id)
        challenge_exists = _first_row(
            self.client.table("daily_challenges")
            .select("challenge_id")
            .eq("challenge_id", str(challenge_id))
            .limit(1)
            .execute()
        )
        if challenge_exists is None:
            raise DailyStoreError(f"Unknown challenge_id: {challenge_id}")

        existing_response = (
            self.client.table("daily_attempts")
            .select("*")
            .eq("player_id", str(player_id))
            .eq("challenge_id", str(challenge_id))
            .limit(1)
            .execute()
        )
        row = _first_row(existing_response)
        if row is not None:
            return _attempt_from_row(row), False

        try:
            response = (
                self.client.table("daily_attempts")
                .insert({"player_id": str(player_id), "challenge_id": str(challenge_id)})
                .select("*")
                .execute()
            )
            row = _first_row(response)
            if row is None:
                raise DailyStoreError("Supabase did not return the created attempt.")
            return _attempt_from_row(row), True
        except Exception as exc:
            if not _is_unique_violation(exc):
                raise
            # The DB uniqueness constraint is the final one-attempt guard.
            response = (
                self.client.table("daily_attempts")
                .select("*")
                .eq("player_id", str(player_id))
                .eq("challenge_id", str(challenge_id))
                .limit(1)
                .execute()
            )
            row = _first_row(response)
            if row is None:
                raise
            return _attempt_from_row(row), False

    def get_resume_state(self, player_id: str, challenge_id: str) -> ResumeState | None:
        response = (
            self.client.table("daily_attempts")
            .select("*")
            .eq("player_id", str(player_id))
            .eq("challenge_id", str(challenge_id))
            .limit(1)
            .execute()
        )
        row = _first_row(response)
        if row is None:
            return None
        attempt = _attempt_from_row(row)
        answers = tuple(self._answers_for_attempt(attempt.attempt_id))
        next_question = None if attempt.complete else len(answers) + 1
        return ResumeState(
            attempt=attempt,
            answers=answers,
            next_question_number=next_question,
        )

    def save_answer(
        self,
        attempt_id: str,
        *,
        question_number: int,
        puzzle_id: str,
        chosen_hold: Sequence[int],
        optimal_hold: Sequence[int],
        points_lost: float,
        solver_source: str = "exact",
    ) -> AnswerRecord:
        attempt = _attempt_from_row(self._require_attempt_row(attempt_id))
        if attempt.complete:
            raise AttemptAlreadyComplete("Completed Daily attempts are immutable.")
        if str(solver_source) != "exact":
            raise InvalidOfficialAnswer("Official Daily answers must be scored by the exact solver.")

        question_number = int(question_number)
        if not 1 <= question_number <= 10:
            raise ValueError("question_number must be 1-10.")

        existing = self._answers_for_attempt(attempt_id)
        if any(answer.question_number == question_number for answer in existing):
            raise DuplicateAnswer("That Daily answer is already locked.")
        expected_question = len(existing) + 1
        if question_number != expected_question:
            raise OutOfOrderAnswer(f"Expected question {expected_question}, got {question_number}.")

        challenge_response = (
            self.client.table("daily_challenges")
            .select("*")
            .eq("challenge_id", attempt.challenge_id)
            .limit(1)
            .execute()
        )
        challenge_row = _first_row(challenge_response)
        if challenge_row is None:
            raise DailyStoreError(f"Unknown challenge_id: {attempt.challenge_id}")
        challenge = _challenge_from_row(challenge_row)
        expected_puzzle_id = challenge.puzzle_ids[question_number - 1]
        if str(puzzle_id) != expected_puzzle_id:
            raise ChallengeMismatch(
                "Answer puzzle_id does not match the registered Daily Challenge slot."
            )

        loss = float(points_lost)
        if loss < -TIE_TOLERANCE:
            raise ValueError("points_lost cannot be negative.")
        loss = max(0.0, loss)
        payload = {
            "attempt_id": str(attempt_id),
            "question_number": question_number,
            "puzzle_id": str(puzzle_id),
            "chosen_hold": [int(value) for value in chosen_hold],
            "optimal_hold": [int(value) for value in optimal_hold],
            "points_lost": loss,
            "exact": loss <= TIE_TOLERANCE,
            "solver_source": "exact",
        }
        try:
            response = self.client.table("daily_answers").insert(payload).select("*").execute()
        except Exception as exc:
            text = _error_text(exc)
            if _is_unique_violation(exc):
                raise DuplicateAnswer("That Daily answer is already locked.") from exc
            if "already complete" in text:
                raise AttemptAlreadyComplete("Completed Daily attempts are immutable.") from exc
            if "expected daily question" in text:
                raise OutOfOrderAnswer("Daily answers must be locked in order.") from exc
            if "puzzle id does not match" in text:
                raise ChallengeMismatch(
                    "Answer puzzle_id does not match the registered Daily Challenge slot."
                ) from exc
            if "exact scoring" in text or "exact flag" in text:
                raise InvalidOfficialAnswer("Official Daily answer failed exact-score validation.") from exc
            raise
        row = _first_row(response)
        if row is None:
            raise DailyStoreError("Supabase did not return the locked answer.")
        return _answer_from_row(row)

    def complete_attempt(self, attempt_id: str) -> AttemptRecord:
        attempt = _attempt_from_row(self._require_attempt_row(attempt_id))
        if attempt.complete:
            return attempt

        answers = self._answers_for_attempt(attempt_id)
        if len(answers) != 10 or [a.question_number for a in answers] != list(range(1, 11)):
            raise DailyStoreError("A Daily attempt cannot complete until all 10 answers are locked.")

        losses = [answer.points_lost for answer in answers]
        best_streak = 0
        current_streak = 0
        for answer in answers:
            if answer.exact:
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = 0

        payload = {
            "completed_at": utc_now().isoformat(),
            "total_ev_loss": float(sum(losses)),
            "exact_count": int(sum(answer.exact for answer in answers)),
            "worst_miss": float(max(losses) if losses else 0.0),
            "best_exact_streak": int(best_streak),
        }
        response = (
            self.client.table("daily_attempts")
            .update(payload)
            .eq("attempt_id", str(attempt_id))
            .select("*")
            .execute()
        )
        row = _first_row(response)
        if row is None:
            raise DailyStoreError("Supabase did not return the completed attempt.")
        return _attempt_from_row(row)

    # ---------- Social results ----------

    def leaderboard(self, group_id: str, challenge_id: str) -> list[dict]:
        self._require_group_row(group_id)
        memberships = _row_list(
            self.client.table("group_members")
            .select("player_id")
            .eq("group_id", str(group_id))
            .execute()
        )
        rows: list[dict] = []
        for membership in memberships:
            player_id = str(membership["player_id"])
            attempt_response = (
                self.client.table("daily_attempts")
                .select("*")
                .eq("player_id", player_id)
                .eq("challenge_id", str(challenge_id))
                .limit(1)
                .execute()
            )
            attempt_row = _first_row(attempt_response)
            if attempt_row is None:
                continue
            attempt = _attempt_from_row(attempt_row)
            if not attempt.complete:
                continue
            player = _player_from_row(self._require_player_row(player_id))
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
        completed_player_ids = {row["player_id"] for row in self.leaderboard(group_id, challenge_id)}
        stats: list[dict] = []
        for question_number in range(1, 11):
            answers: list[AnswerRecord] = []
            for player_id in completed_player_ids:
                attempt_response = (
                    self.client.table("daily_attempts")
                    .select("attempt_id")
                    .eq("player_id", player_id)
                    .eq("challenge_id", str(challenge_id))
                    .limit(1)
                    .execute()
                )
                attempt_row = _first_row(attempt_response)
                if attempt_row is None:
                    continue
                answer_response = (
                    self.client.table("daily_answers")
                    .select("*")
                    .eq("attempt_id", str(attempt_row["attempt_id"]))
                    .eq("question_number", question_number)
                    .limit(1)
                    .execute()
                )
                answer_row = _first_row(answer_response)
                if answer_row is not None:
                    answers.append(_answer_from_row(answer_row))
            if not answers:
                continue
            exact_count = sum(answer.exact for answer in answers)
            stats.append({
                "question_number": question_number,
                "players": len(answers),
                "exact_count": exact_count,
                "exact_rate": exact_count / len(answers),
                "avg_loss": sum(answer.points_lost for answer in answers) / len(answers),
            })
        return stats

    def current_participation_streak(self, player_id: str, current_date: str) -> int:
        self._require_player_row(player_id)
        today = date.fromisoformat(str(current_date))
        completed_attempts = _row_list(
            self.client.table("daily_attempts")
            .select("challenge_id")
            .eq("player_id", str(player_id))
            .execute()
        )
        completed_dates: set[date] = set()
        for row in completed_attempts:
            attempt_response = (
                self.client.table("daily_attempts")
                .select("challenge_id,completed_at")
                .eq("player_id", str(player_id))
                .eq("challenge_id", str(row["challenge_id"]))
                .limit(1)
                .execute()
            )
            attempt_row = _first_row(attempt_response)
            if attempt_row is None or attempt_row.get("completed_at") is None:
                continue
            challenge_response = (
                self.client.table("daily_challenges")
                .select("challenge_date")
                .eq("challenge_id", str(attempt_row["challenge_id"]))
                .limit(1)
                .execute()
            )
            challenge_row = _first_row(challenge_response)
            if challenge_row is not None:
                completed_dates.add(date.fromisoformat(str(challenge_row["challenge_date"])))

        cursor = today if today in completed_dates else today - timedelta(days=1)
        streak = 0
        while cursor in completed_dates:
            streak += 1
            cursor -= timedelta(days=1)
        return streak
