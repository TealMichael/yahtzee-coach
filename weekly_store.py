from __future__ import annotations

"""Trusted-server Weekly persistence, using the existing custom-PIN sessions.

SupabaseWeeklyStore is scoped to one authenticated actor, never globally cached.
The backend client is the app's existing service-key client. Only the RPC may
access weekly tables. Neither private schedules nor credentials leave this layer.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping
from uuid import UUID, uuid4

from daily_store import hash_device_token_secret, split_device_token
from weekly_game import (
    DiceSchedule, GameComplete, GameExpired, GameState, InvalidAction, StaleState,
    UnsupportedVersion, WeeklyGameError, apply_action, generate_schedule, week_bounds,
)


class WeeklyStoreError(RuntimeError):
    pass


class WeeklyAuthRequired(WeeklyStoreError):
    pass


class WeeklyAccessDenied(WeeklyStoreError):
    pass


class WeeklyGameNotFound(WeeklyStoreError):
    pass


class WeeklyReplayLocked(WeeklyStoreError):
    pass


def _uuid(value: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidAction("Invalid Weekly request identifier.") from exc


def _timestamp(value) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise WeeklyStoreError("The Weekly server returned an invalid timestamp.")
    return result


@dataclass(frozen=True, repr=False)
class WeeklyActor:
    player_id: str
    session_id: str
    token_hash: str

    @classmethod
    def from_token(cls, player_id: str, token: str) -> "WeeklyActor":
        session_id, secret = split_device_token(token)
        if not session_id or not secret:
            raise WeeklyAuthRequired("Sign in again to open your Weekly game.")
        try:
            return cls(_uuid(player_id), _uuid(session_id), hash_device_token_secret(secret))
        except InvalidAction as exc:
            raise WeeklyAuthRequired("Sign in again to open your Weekly game.") from exc

    def __repr__(self) -> str:
        return "WeeklyActor(<private session>)"


ERRORS = {
    "WEEKLY_AUTH_REQUIRED": (WeeklyAuthRequired, "Your sign-in expired. Sign in again to continue your saved game."),
    "WEEKLY_ACCESS_DENIED": (WeeklyAccessDenied, "You do not have access to that friend group."),
    "WEEKLY_GAME_NOT_FOUND": (WeeklyGameNotFound, "That Weekly game is no longer available. Reload your saved game."),
    "WEEKLY_REPLAY_LOCKED": (WeeklyReplayLocked, "Finish your official game before replaying this week's dice."),
    "WEEKLY_EXPIRED": (GameExpired, "This week's official game is closed. Your saved progress is retained."),
    "WEEKLY_STALE_STATE": (StaleState, "Your game changed in another tab. Reload the saved game."),
    "WEEKLY_GAME_LOCKED": (GameComplete, "Your completed game is locked."),
    "WEEKLY_REQUEST_REUSED": (InvalidAction, "That request was already used for a different action. Reload your saved game."),
    "WEEKLY_UNSUPPORTED_VERSION": (UnsupportedVersion, "This Weekly game needs a different app version."),
    "WEEKLY_INVALID_STATE": (WeeklyStoreError, "The Weekly game could not be saved. Reload the saved game."),
    "WEEKLY_INVALID_SCHEDULE": (WeeklyStoreError, "This week's dice are not available. Please try again."),
    "WEEKLY_INVALID_REQUEST": (InvalidAction, "That Weekly action is not valid. Reload your saved game."),
    "WEEKLY_INVALID_WEEK": (InvalidAction, "Choose a valid challenge week."),
}


class SupabaseWeeklyStore:
    def __init__(self, client, actor: WeeklyActor, *, schedule_factory: Callable[[str], DiceSchedule] = generate_schedule):
        self._client = client
        self._actor = actor
        self._schedule_factory = schedule_factory

    def _rpc(self, operation: str, payload: Mapping) -> dict:
        try:
            result = self._client.rpc("yc_weekly_rpc", {
                "p_session_id": self._actor.session_id,
                "p_token_hash": self._actor.token_hash,
                "p_player_id": self._actor.player_id,
                "p_operation": operation,
                "p_payload": dict(payload),
            }).execute()
        except Exception as exc:
            # Never forward raw database errors: they can contain arguments,
            # state or a private schedule. Only known fixed messages are public.
            details = " ".join(str(getattr(exc, k, "")) for k in ("message", "details", "code")) + " " + str(exc)
            for key, (error_type, message) in ERRORS.items():
                if key in details:
                    raise error_type(message) from None
            raise WeeklyStoreError("Weekly couldn't reach the saved game. Please try again.") from None
        data = result.data
        if not isinstance(data, dict):
            raise WeeklyStoreError("Weekly returned an unexpected response. Please try again.")
        return data

    @staticmethod
    def _public_game(data: Mapping) -> dict:
        fields = {"game_id", "week_id", "mode", "state", "revision", "total_score", "started_at", "updated_at", "completed_at"}
        if set(data) != fields:
            raise WeeklyStoreError("Weekly returned an invalid saved game.")
        return dict(data)

    def dashboard(self, week_id: str) -> dict:
        week_bounds(week_id)
        return self._rpc("dashboard", {"week_id": week_id})

    def standings(self, week_id: str, group_id: str) -> dict:
        week_bounds(week_id)
        return self._rpc("standings", {"week_id": week_id, "group_id": _uuid(group_id)})

    def history(self, *, before_week: str | None = None, limit: int = 52) -> list[dict]:
        if before_week is not None:
            week_bounds(before_week)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise InvalidAction("Invalid Weekly history page size.")
        return self._rpc("history", {"before_week": before_week, "limit": limit})["weeks"]

    def start_official(self, week_id: str, *, request_id: str | None = None) -> dict:
        week_bounds(week_id)
        schedule = self._schedule_factory(week_id)
        if schedule.week_id != week_id:
            raise WeeklyStoreError("Weekly generated dice for the wrong week.")
        result = self._rpc("start", {"week_id": week_id, "request_id": _uuid(request_id or str(uuid4())),
            "schedule": schedule.to_private_dict(), "commitment": schedule.commitment})
        return self._public_game(result)

    def start_replay(self, week_id: str, *, expected_replay_id: str | None, request_id: str | None = None) -> dict:
        week_bounds(week_id)
        return self._public_game(self._rpc("replay", {
            "week_id": week_id, "request_id": _uuid(request_id or str(uuid4())),
            "expected_replay_id": _uuid(expected_replay_id) if expected_replay_id is not None else None,
        }))

    def act(self, game_id: str, *, expected_revision: int, request_id: str, action: Mapping) -> dict:
        """Validate against authoritative state, then compare-and-swap in Postgres.

        Keep the same request ID, revision and action when retrying a timeout.
        The latest identical retry returns saved state. An older retry is stale
        and cannot execute again. A new request needs a new UUID.
        """
        game_id, request_id = _uuid(game_id), _uuid(request_id)
        if type(expected_revision) is not int or expected_revision < 0 or not isinstance(action, Mapping):
            raise InvalidAction("Invalid Weekly action.")
        action = dict(action)
        if action.get("kind") == "hold" and isinstance(action.get("held"), (list, tuple)):
            if any(type(face) is not int for face in action["held"]):
                raise InvalidAction("Dice must be whole-number faces.")
            action["held"] = sorted(action["held"])
        context = self._rpc("context", {"game_id": game_id})
        game = self._public_game(context["game"])
        receipt = {"action": dict(action), "revision": expected_revision}
        if context["last_request_id"] == request_id:
            if context["last_request"] != receipt:
                raise InvalidAction("That request was already used for a different action. Reload your saved game.")
            return game
        schedule = DiceSchedule.from_private_dict(context["schedule"])
        state = GameState.from_dict(game["state"], schedule)
        if (state.mode, state.week_id, state.revision) != (game["mode"], game["week_id"], game["revision"]):
            raise WeeklyStoreError("The saved Weekly identity is inconsistent.")
        next_state = apply_action(state, schedule, action,
            expected_revision=expected_revision, now=_timestamp(context["server_now"]))
        return self._public_game(self._rpc("commit", {
            "game_id": game_id, "request_id": request_id, "expected_revision": expected_revision,
            "action": dict(action), "next_state": next_state.to_dict(),
        }))
