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
import hmac
import re
import secrets
from typing import Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

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
    FeedbackRecord,
    InvalidOfficialAnswer,
    OutOfOrderAnswer,
    PlayerNameTaken,
    PlayerNotFound,
    PublicPlayer,
    ResumeState,
    generate_join_code,
    hash_device_token_secret,
    hash_pin,
    normalize_display_name,
    rank_leaderboard_rows,
    split_device_token,
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

    def create_device_session(self, player_id: str, days: int = 30) -> str:
        """Create a revocable 30-day browser credential without storing the player's PIN."""
        self._require_player_row(player_id)
        ttl_days = max(1, min(int(days), 90))
        secret = secrets.token_urlsafe(32)
        now = utc_now()
        payload = {
            "player_id": str(player_id),
            "token_hash": hash_device_token_secret(secret),
            "expires_at": (now + timedelta(days=ttl_days)).isoformat(),
            "last_used_at": now.isoformat(),
        }
        response = (
            self.client.table("player_sessions")
            .insert(payload)
            .select("session_id")
            .execute()
        )
        row = _first_row(response)
        if row is None:
            raise DailyStoreError("Supabase did not return the remembered-device session.")
        return f"{row['session_id']}.{secret}"

    def authenticate_device_session(self, token: str) -> PublicPlayer | None:
        """Restore a player from a high-entropy browser token if it is live and unrevoked."""
        session_id, secret = split_device_token(token)
        if not session_id or not secret:
            return None
        response = (
            self.client.table("player_sessions")
            .select("session_id,player_id,token_hash,expires_at,revoked_at")
            .eq("session_id", str(session_id))
            .limit(1)
            .execute()
        )
        row = _first_row(response)
        if row is None or row.get("revoked_at") is not None:
            return None
        expires_at = _as_datetime(row.get("expires_at"))
        if expires_at is None or expires_at <= utc_now():
            return None
        actual_hash = hash_device_token_secret(secret)
        if not hmac.compare_digest(actual_hash, str(row.get("token_hash") or "")):
            return None
        player_row = self._require_player_row(str(row["player_id"]))
        return _player_from_row(player_row)

    def revoke_device_session(self, token: str) -> None:
        """Revoke the current browser credential; malformed/unknown tokens are harmless."""
        session_id, secret = split_device_token(token)
        if not session_id or not secret:
            return
        token_hash = hash_device_token_secret(secret)
        (
            self.client.table("player_sessions")
            .update({"revoked_at": utc_now().isoformat()})
            .eq("session_id", str(session_id))
            .eq("token_hash", token_hash)
            .execute()
        )

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
        group_ids = [str(row["group_id"]) for row in memberships]
        if not group_ids:
            return []
        rows = _row_list(
            self.client.table("friend_groups")
            .select("group_id,group_name,join_code,created_by_player_id,created_at")
            .in_("group_id", group_ids)
            .execute()
        )
        groups = [_group_from_row(row) for row in rows]
        return sorted(groups, key=lambda group: (group.group_name.casefold(), group.group_id))

    def list_group_members(self, group_id: str) -> list[dict]:
        self._require_group_row(group_id)
        memberships = _row_list(
            self.client.table("group_members")
            .select("player_id")
            .eq("group_id", str(group_id))
            .execute()
        )
        player_ids = [str(row["player_id"]) for row in memberships]
        if not player_ids:
            return []
        player_rows = _row_list(
            self.client.table("players")
            .select("player_id,display_name,created_at")
            .in_("player_id", player_ids)
            .execute()
        )
        rows = [{
            "player_id": str(row["player_id"]),
            "display_name": str(row["display_name"]),
        } for row in player_rows]
        return sorted(rows, key=lambda row: (row["display_name"].casefold(), row["player_id"]))

    def get_player_profile(self, player_id: str) -> dict:
        row = _first_row(
            self.client.table("players")
            .select("player_id,display_name,avatar_config,avatar_setup_complete")
            .eq("player_id", str(player_id))
            .limit(1)
            .execute()
        )
        if row is None:
            raise PlayerNotFound(str(player_id))
        return {
            "player_id": str(row["player_id"]),
            "display_name": str(row["display_name"]),
            "avatar_config": dict(row.get("avatar_config") or {}),
            "avatar_setup_complete": bool(row.get("avatar_setup_complete")),
        }

    def save_player_avatar(self, player_id: str, avatar_config: Mapping) -> dict:
        self._require_player_row(player_id)
        payload = {
            "avatar_config": {str(key): str(value) for key, value in dict(avatar_config or {}).items()},
            "avatar_setup_complete": True,
        }
        row = _first_row(
            self.client.table("players")
            .update(payload)
            .eq("player_id", str(player_id))
            .select("player_id,display_name,avatar_config,avatar_setup_complete")
            .execute()
        )
        if row is None:
            raise DailyStoreError("Player avatar could not be saved.")
        return {
            "player_id": str(row["player_id"]),
            "display_name": str(row["display_name"]),
            "avatar_config": dict(row.get("avatar_config") or {}),
            "avatar_setup_complete": bool(row.get("avatar_setup_complete")),
        }

    def player_medal_totals(self, player_id: str, group_id: str, through_date: str) -> dict:
        """Derive finalized social medals from stored Daily attempts using leaderboard tie rules."""
        self._require_player_row(player_id)
        player_id = str(player_id)
        group_id = str(group_id)
        self._require_group_row(group_id)
        cutoff = date.fromisoformat(str(through_date))

        membership_rows = _row_list(
            self.client.table("group_members")
            .select("player_id,joined_at")
            .eq("group_id", group_id)
            .execute()
        )
        memberships = {
            str(row["player_id"]): (_as_datetime(row.get("joined_at")) or utc_now())
            for row in membership_rows
        }
        if player_id not in memberships:
            raise GroupNotFound("Player must belong to this friend group.")
        player_ids = list(memberships)
        if len(player_ids) < 2:
            return {"gold": 0, "silver": 0, "bronze": 0, "total": 0}

        attempt_rows = _row_list(
            self.client.table("daily_attempts")
            .select("player_id,challenge_id,completed_at,total_ev_loss")
            .in_("player_id", player_ids)
            .execute()
        )
        completed_rows = [row for row in attempt_rows if row.get("completed_at") is not None]
        challenge_ids = sorted({str(row["challenge_id"]) for row in completed_rows})
        if not challenge_ids:
            return {"gold": 0, "silver": 0, "bronze": 0, "total": 0}

        challenge_rows = _row_list(
            self.client.table("daily_challenges")
            .select("challenge_id,challenge_date")
            .in_("challenge_id", challenge_ids)
            .execute()
        )
        challenge_dates = {
            str(row["challenge_id"]): date.fromisoformat(str(row["challenge_date"]))
            for row in challenge_rows
        }
        player_rows = _row_list(
            self.client.table("players")
            .select("player_id,display_name")
            .in_("player_id", player_ids)
            .execute()
        )
        names = {str(row["player_id"]): str(row["display_name"]) for row in player_rows}

        # Choose at most one official challenge id per calendar day for this player.
        # This protects medal history if an old deployment boundary ever registered two
        # challenge versions for the same date; the first completed attempt wins.
        selected_by_day: dict[date, tuple[datetime, str]] = {}
        for row in completed_rows:
            if str(row["player_id"]) != player_id:
                continue
            challenge_id = str(row["challenge_id"])
            challenge_day = challenge_dates.get(challenge_id)
            completed_at = _as_datetime(row.get("completed_at"))
            if challenge_day is None or completed_at is None or challenge_day > cutoff:
                continue
            joined_at = memberships[player_id]
            if joined_at.astimezone(ZoneInfo("America/New_York")).date() > challenge_day:
                continue
            prior = selected_by_day.get(challenge_day)
            if prior is None or completed_at < prior[0]:
                selected_by_day[challenge_day] = (completed_at, challenge_id)
        selected_ids = {challenge_id for _, challenge_id in selected_by_day.values()}
        if not selected_ids:
            return {"gold": 0, "silver": 0, "bronze": 0, "total": 0}

        by_challenge: dict[str, list[dict]] = {}
        for row in completed_rows:
            challenge_id = str(row["challenge_id"])
            if challenge_id not in selected_ids:
                continue
            challenge_day = challenge_dates.get(challenge_id)
            if challenge_day is None:
                continue
            member_id = str(row["player_id"])
            joined_at = memberships.get(member_id)
            if joined_at is None or joined_at.astimezone(ZoneInfo("America/New_York")).date() > challenge_day:
                continue
            by_challenge.setdefault(challenge_id, []).append(row)

        totals = {"gold": 0, "silver": 0, "bronze": 0, "total": 0}
        for challenge_day in sorted(selected_by_day):
            challenge_id = selected_by_day[challenge_day][1]
            rows = by_challenge.get(challenge_id, [])
            eligible_member_ids = {
                member_id for member_id, joined_at in memberships.items()
                if joined_at.astimezone(ZoneInfo("America/New_York")).date() <= challenge_day
            }
            if player_id not in eligible_member_ids or len(eligible_member_ids) < 2:
                continue
            board = []
            for row in rows:
                member_id = str(row["player_id"])
                if member_id not in eligible_member_ids or member_id not in names:
                    continue
                board.append({
                    "player_id": member_id,
                    "display_name": names[member_id],
                    "total_ev_loss": float(row.get("total_ev_loss") or 0.0),
                })
            if not board:
                continue
            rank_leaderboard_rows(board)
            mine = next((item for item in board if item["player_id"] == player_id), None)
            if mine is None:
                continue
            rank = int(mine.get("rank") or 0)
            if rank == 1:
                totals["gold"] += 1
            elif rank == 2:
                totals["silver"] += 1
            elif rank == 3:
                totals["bronze"] += 1
        totals["total"] = totals["gold"] + totals["silver"] + totals["bronze"]
        return totals

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
        """Save one Daily answer with a single network write.

        Postgres trigger ``guard_daily_answer_insert`` is the authoritative
        guard for attempt state, order, puzzle identity, exact scoring, and the
        exact flag. Keeping those checks in the transaction removes several
        redundant read-before-write round trips from every Save & Next.
        """
        if str(solver_source) != "exact":
            raise InvalidOfficialAnswer("Official Daily answers must be scored by the exact solver.")
        question_number = int(question_number)
        if not 1 <= question_number <= 10:
            raise ValueError("question_number must be 1-10.")
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
                raise DuplicateAnswer("That Daily answer is already saved.") from exc
            if "already complete" in text or "completed daily" in text:
                raise AttemptAlreadyComplete("Completed Daily attempts are immutable.") from exc
            if "expected daily question" in text:
                raise OutOfOrderAnswer("Daily answers must be saved in order.") from exc
            if "puzzle id does not match" in text:
                raise ChallengeMismatch(
                    "Answer puzzle_id does not match the registered Daily Challenge slot."
                ) from exc
            if "exact scoring" in text or "exact flag" in text:
                raise InvalidOfficialAnswer("Official Daily answer failed exact-score validation.") from exc
            raise
        row = _first_row(response)
        if row is None:
            raise DailyStoreError("Supabase did not return the saved answer.")
        return _answer_from_row(row)

    def revise_answer(
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
        """Revise a saved draft with one update request.

        The Phase 2E database trigger is the final guard that blocks completed
        attempts and validates answer identity/exact scoring.
        """
        if str(solver_source) != "exact":
            raise InvalidOfficialAnswer("Official Daily answers must be scored by the exact solver.")
        question_number = int(question_number)
        if not 1 <= question_number <= 10:
            raise ValueError("question_number must be 1-10.")
        loss = float(points_lost)
        if loss < -TIE_TOLERANCE:
            raise ValueError("points_lost cannot be negative.")
        loss = max(0.0, loss)
        payload = {
            "chosen_hold": [int(value) for value in chosen_hold],
            "optimal_hold": [int(value) for value in optimal_hold],
            "points_lost": loss,
            "exact": loss <= TIE_TOLERANCE,
            "solver_source": "exact",
            "submitted_at": utc_now().isoformat(),
        }
        try:
            response = (
                self.client.table("daily_answers")
                .update(payload)
                .eq("attempt_id", str(attempt_id))
                .eq("question_number", question_number)
                .eq("puzzle_id", str(puzzle_id))
                .select("*")
                .execute()
            )
        except Exception as exc:
            text = _error_text(exc)
            if "already complete" in text or "completed daily" in text:
                raise AttemptAlreadyComplete("Completed Daily attempts are immutable.") from exc
            if "puzzle id" in text:
                raise ChallengeMismatch(
                    "Answer puzzle_id does not match the registered Daily Challenge slot."
                ) from exc
            if "exact scoring" in text or "exact flag" in text:
                raise InvalidOfficialAnswer("Official Daily answer failed exact-score validation.") from exc
            raise
        row = _first_row(response)
        if row is None:
            raise DailyStoreError("That Daily answer could not be revised.")
        return _answer_from_row(row)

    def complete_attempt(self, attempt_id: str) -> AttemptRecord:
        attempt = _attempt_from_row(self._require_attempt_row(attempt_id))
        if attempt.complete:
            return attempt

        answers = self._answers_for_attempt(attempt_id)
        if len(answers) != 10 or [a.question_number for a in answers] != list(range(1, 11)):
            raise DailyStoreError("A Daily attempt cannot complete until all 10 answers are saved.")

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

    def group_daily_snapshot(self, group_id: str, challenge_id: str) -> dict:
        """Return group members, standings, and question stats with batched reads.

        The active group has already been resolved by ``list_groups`` in the
        app, so this path avoids repeating group/membership/attempt queries for
        each separate result widget. A completed group Daily needs four reads:
        memberships, players, attempts, and answers.
        """
        memberships = _row_list(
            self.client.table("group_members")
            .select("player_id")
            .eq("group_id", str(group_id))
            .execute()
        )
        player_ids = [str(row["player_id"]) for row in memberships]
        if not player_ids:
            return {"members": [], "leaderboard": [], "question_stats": []}

        player_rows = _row_list(
            self.client.table("players")
            .select("player_id,display_name,created_at")
            .in_("player_id", player_ids)
            .execute()
        )
        names = {str(row["player_id"]): str(row["display_name"]) for row in player_rows}
        members = sorted(
            [
                {"player_id": player_id, "display_name": names[player_id]}
                for player_id in player_ids
                if player_id in names
            ],
            key=lambda row: (row["display_name"].casefold(), row["player_id"]),
        )

        attempt_rows = _row_list(
            self.client.table("daily_attempts")
            .select("*")
            .in_("player_id", player_ids)
            .eq("challenge_id", str(challenge_id))
            .execute()
        )
        completed = [_attempt_from_row(row) for row in attempt_rows if row.get("completed_at") is not None]
        board: list[dict] = []
        for attempt in completed:
            display_name = names.get(attempt.player_id)
            if not display_name:
                continue
            board.append({
                "player_id": attempt.player_id,
                "display_name": display_name,
                "total_ev_loss": float(attempt.total_ev_loss or 0.0),
                "exact_count": int(attempt.exact_count or 0),
                "worst_miss": float(attempt.worst_miss or 0.0),
                "best_exact_streak": int(attempt.best_exact_streak or 0),
                "completed_at": attempt.completed_at,
            })
        rank_leaderboard_rows(board)

        attempt_ids = [attempt.attempt_id for attempt in completed]
        stats: list[dict] = []
        if attempt_ids:
            answer_rows = _row_list(
                self.client.table("daily_answers")
                .select("question_number,points_lost,exact")
                .in_("attempt_id", attempt_ids)
                .execute()
            )
            by_question: dict[int, list[dict]] = {}
            for row in answer_rows:
                by_question.setdefault(int(row["question_number"]), []).append(row)
            for question_number in range(1, 11):
                answers = by_question.get(question_number, [])
                if not answers:
                    continue
                exact_count = sum(bool(row.get("exact")) for row in answers)
                stats.append({
                    "question_number": question_number,
                    "players": len(answers),
                    "exact_count": exact_count,
                    "exact_rate": exact_count / len(answers),
                    "avg_loss": sum(float(row.get("points_lost") or 0.0) for row in answers) / len(answers),
                })

        return {"members": members, "leaderboard": board, "question_stats": stats}

    def leaderboard(self, group_id: str, challenge_id: str) -> list[dict]:
        self._require_group_row(group_id)
        memberships = _row_list(
            self.client.table("group_members")
            .select("player_id")
            .eq("group_id", str(group_id))
            .execute()
        )
        player_ids = [str(row["player_id"]) for row in memberships]
        if not player_ids:
            return []

        attempt_rows = _row_list(
            self.client.table("daily_attempts")
            .select("*")
            .in_("player_id", player_ids)
            .eq("challenge_id", str(challenge_id))
            .execute()
        )
        completed = [_attempt_from_row(row) for row in attempt_rows if row.get("completed_at") is not None]
        if not completed:
            return []

        completed_player_ids = [attempt.player_id for attempt in completed]
        player_rows = _row_list(
            self.client.table("players")
            .select("player_id,display_name,created_at")
            .in_("player_id", completed_player_ids)
            .execute()
        )
        names = {str(row["player_id"]): str(row["display_name"]) for row in player_rows}
        rows: list[dict] = []
        for attempt in completed:
            display_name = names.get(attempt.player_id)
            if not display_name:
                continue
            rows.append({
                "player_id": attempt.player_id,
                "display_name": display_name,
                "total_ev_loss": float(attempt.total_ev_loss or 0.0),
                "exact_count": int(attempt.exact_count or 0),
                "worst_miss": float(attempt.worst_miss or 0.0),
                "best_exact_streak": int(attempt.best_exact_streak or 0),
                "completed_at": attempt.completed_at,
            })

        return rank_leaderboard_rows(rows)

    def group_question_stats(self, group_id: str, challenge_id: str) -> list[dict]:
        self._require_group_row(group_id)
        memberships = _row_list(
            self.client.table("group_members")
            .select("player_id")
            .eq("group_id", str(group_id))
            .execute()
        )
        player_ids = [str(row["player_id"]) for row in memberships]
        if not player_ids:
            return []

        attempt_rows = _row_list(
            self.client.table("daily_attempts")
            .select("attempt_id,player_id,completed_at")
            .in_("player_id", player_ids)
            .eq("challenge_id", str(challenge_id))
            .execute()
        )
        attempt_ids = [str(row["attempt_id"]) for row in attempt_rows if row.get("completed_at") is not None]
        if not attempt_ids:
            return []

        answer_rows = _row_list(
            self.client.table("daily_answers")
            .select("*")
            .in_("attempt_id", attempt_ids)
            .execute()
        )
        by_question: dict[int, list[AnswerRecord]] = {}
        for row in answer_rows:
            answer = _answer_from_row(row)
            by_question.setdefault(answer.question_number, []).append(answer)

        stats: list[dict] = []
        for question_number in range(1, 11):
            answers = by_question.get(question_number, [])
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

    def group_player_daily_review(self, group_id: str, challenge_id: str,
                                  viewer_player_id: str, target_player_id: str) -> dict:
        """Return one completed friend's immutable Daily choices after viewer completion.

        This is intentionally separate from ``group_daily_snapshot`` so detailed
        answers are never fetched during the pre-Daily completion-count view.
        """
        self._require_group_row(group_id)
        viewer_player_id = str(viewer_player_id)
        target_player_id = str(target_player_id)
        membership_rows = _row_list(
            self.client.table("group_members")
            .select("player_id")
            .eq("group_id", str(group_id))
            .in_("player_id", [viewer_player_id, target_player_id])
            .execute()
        )
        member_ids = {str(row["player_id"]) for row in membership_rows}
        if viewer_player_id not in member_ids or target_player_id not in member_ids:
            raise GroupNotFound("Both players must belong to this friend group.")

        attempt_rows = _row_list(
            self.client.table("daily_attempts")
            .select("*")
            .in_("player_id", [viewer_player_id, target_player_id])
            .eq("challenge_id", str(challenge_id))
            .execute()
        )
        attempts = {}
        for row in attempt_rows:
            attempt = _attempt_from_row(row)
            attempts[attempt.player_id] = attempt
        viewer_attempt = attempts.get(viewer_player_id)
        target_attempt = attempts.get(target_player_id)
        if viewer_attempt is None or not viewer_attempt.complete:
            raise DailyStoreError("Finish your own Daily before reviewing a friend's choices.")
        if target_attempt is None or not target_attempt.complete:
            raise DailyStoreError("That player has not finished this Daily yet.")

        player_row = _first_row(
            self.client.table("players")
            .select("player_id,display_name")
            .eq("player_id", target_player_id)
            .limit(1)
            .execute()
        )
        if player_row is None:
            raise PlayerNotFound(target_player_id)

        answer_rows = _row_list(
            self.client.table("daily_answers")
            .select("question_number,puzzle_id,chosen_hold,optimal_hold,points_lost,exact,solver_source")
            .eq("attempt_id", str(target_attempt.attempt_id))
            .order("question_number")
            .execute()
        )
        if len(answer_rows) != 10:
            raise DailyStoreError("That completed Daily does not have all 10 answers.")
        answers = []
        for row in answer_rows:
            answers.append({
                "question_number": int(row["question_number"]),
                "puzzle_id": str(row["puzzle_id"]),
                "chosen_hold": [int(value) for value in (row.get("chosen_hold") or [])],
                "optimal_hold": [int(value) for value in (row.get("optimal_hold") or [])],
                "points_lost": float(row.get("points_lost") or 0.0),
                "exact": bool(row.get("exact")),
                "solver_source": str(row.get("solver_source") or ""),
            })
        return {
            "player_id": target_player_id,
            "display_name": str(player_row["display_name"]),
            "summary": {
                "total_ev_loss": float(target_attempt.total_ev_loss or 0.0),
                "exact_count": int(target_attempt.exact_count or 0),
                "worst_miss": float(target_attempt.worst_miss or 0.0),
                "best_exact_streak": int(target_attempt.best_exact_streak or 0),
            },
            "answers": answers,
        }

    def current_participation_streak(self, player_id: str, current_date: str) -> int:
        self._require_player_row(player_id)
        today = date.fromisoformat(str(current_date))
        attempt_rows = _row_list(
            self.client.table("daily_attempts")
            .select("challenge_id,completed_at")
            .eq("player_id", str(player_id))
            .execute()
        )
        challenge_ids = sorted({
            str(row["challenge_id"])
            for row in attempt_rows
            if row.get("completed_at") is not None
        })
        if not challenge_ids:
            return 0
        challenge_rows = _row_list(
            self.client.table("daily_challenges")
            .select("challenge_id,challenge_date")
            .in_("challenge_id", challenge_ids)
            .execute()
        )
        completed_dates = {date.fromisoformat(str(row["challenge_date"])) for row in challenge_rows}

        cursor = today if today in completed_dates else today - timedelta(days=1)
        streak = 0
        while cursor in completed_dates:
            streak += 1
            cursor -= timedelta(days=1)
        return streak


    def submit_feedback(self, *, player_id: str | None, feedback_type: str, message: str,
                        app_version: str, page_mode: str) -> FeedbackRecord:
        if player_id is not None:
            self._require_player_row(str(player_id))
        kind = re.sub(r"\s+", " ", str(feedback_type or "").strip())[:40]
        text = str(message or "").strip()
        version = re.sub(r"\s+", " ", str(app_version or "").strip())[:80]
        mode = re.sub(r"\s+", " ", str(page_mode or "").strip())[:80]
        if not kind:
            raise ValueError("Choose a feedback type.")
        if not (3 <= len(text) <= 1200):
            raise ValueError("Feedback must be 3-1200 characters.")
        payload = {
            "player_id": (None if player_id is None else str(player_id)),
            "feedback_type": kind,
            "message": text,
            "app_version": version,
            "page_mode": mode,
        }
        row = _first_row(self.client.table("beta_feedback").insert(payload).execute())
        if row is None:
            raise DailyStoreError("Feedback could not be saved.")
        return FeedbackRecord(
            feedback_id=str(row["feedback_id"]),
            player_id=(None if row.get("player_id") is None else str(row["player_id"])),
            feedback_type=str(row["feedback_type"]),
            message=str(row["message"]),
            app_version=str(row.get("app_version") or ""),
            page_mode=str(row.get("page_mode") or ""),
            created_at=_as_datetime(row.get("created_at")) or utc_now(),
        )
