from __future__ import annotations

"""Daily Challenge gameplay helpers for Yahtzee Coach v43A.

v43A intentionally keeps persistence local to the active Streamlit session.
The shared database/player/group layer arrives in v43B.  The functions in this
module are UI-independent so challenge scoring, deterministic demo leaderboards,
and end-of-run summaries can be tested exhaustively before a database is added.
"""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import math
import random
from typing import Mapping, Sequence
from zoneinfo import ZoneInfo

from puzzle_bank import generate_daily_challenge_set

DAILY_CHALLENGE_VERSION = "43A-bank42.6"
DAILY_TIMEZONE = "America/New_York"
TIE_TOLERANCE = 1e-9

MOCK_FRIENDS = (
    ("Alex", 0.18),
    ("Casey", 0.08),
    ("Jordan", 0.25),
    ("Morgan", -0.02),
    ("Riley", 0.14),
    ("Sam", -0.10),
    ("Taylor", 0.04),
)

DIFFICULTY_EXACT_RATE = {
    "Clear": 0.70,
    "Medium": 0.56,
    "Hard": 0.43,
    "Punishing": 0.29,
    "Knife-edge": 0.24,
}

DIFFICULTY_LOSS_SCALE = {
    "Clear": 0.75,
    "Medium": 1.10,
    "Hard": 1.45,
    "Punishing": 2.10,
    "Knife-edge": 0.55,
}


def current_daily_date_key(now: datetime | None = None, timezone_name: str = DAILY_TIMEZONE) -> str:
    """Return the challenge date in the single shared Daily Challenge timezone."""
    tz = ZoneInfo(timezone_name)
    if now is None:
        now = datetime.now(tz)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)
    return now.date().isoformat()


def daily_challenges(date_key: str) -> list[dict]:
    """Return the deterministic Daily 10, decorated with a stable version id."""
    challenges = generate_daily_challenge_set(str(date_key), count=10)
    for number, challenge in enumerate(challenges, start=1):
        challenge["daily_number"] = number
        challenge["daily_version"] = DAILY_CHALLENGE_VERSION
        challenge["daily_date"] = str(date_key)
    return challenges


def challenge_set_id(date_key: str, challenges: Sequence[Mapping]) -> str:
    material = "|".join(str(item.get("challenge_id", "")) for item in challenges)
    digest = sha256(f"{DAILY_CHALLENGE_VERSION}|{date_key}|{material}".encode("utf-8")).hexdigest()
    return f"{date_key}-{digest[:10]}"


def is_exact_record(record: Mapping) -> bool:
    return float(record.get("points_lost", 0.0) or 0.0) <= TIE_TOLERANCE


def best_exact_streak(records: Sequence[Mapping]) -> int:
    best = 0
    current = 0
    for record in records:
        if is_exact_record(record):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def summarize_attempt(records: Sequence[Mapping]) -> dict:
    """Create leaderboard-ready scoring from exact-solver records."""
    losses = [max(0.0, float(item.get("points_lost", 0.0) or 0.0)) for item in records]
    exact_count = sum(is_exact_record(item) for item in records)
    total = float(sum(losses))
    worst = float(max(losses)) if losses else 0.0
    return {
        "questions": len(records),
        "total_ev_loss": total,
        "avg_ev_loss": total / len(losses) if losses else 0.0,
        "exact_count": int(exact_count),
        "best_exact_streak": int(best_exact_streak(records)),
        "worst_miss": worst,
        "perfect": bool(records) and exact_count == len(records),
    }


def _stable_seed(*parts: object) -> int:
    text = "|".join(str(part) for part in parts)
    digest = sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _mock_question_result(rng: random.Random, challenge: Mapping, skill_adjustment: float) -> dict:
    difficulty = str(challenge.get("difficulty", "Medium"))
    base_rate = DIFFICULTY_EXACT_RATE.get(difficulty, 0.50)
    exact_probability = min(0.90, max(0.08, base_rate + skill_adjustment))
    exact = rng.random() < exact_probability
    if exact:
        loss = 0.0
    else:
        top_gap = max(0.03, float(challenge.get("top_gap", 0.4) or 0.4))
        scale = DIFFICULTY_LOSS_SCALE.get(difficulty, 1.0)
        # A miss should at least clear the best-vs-second gap, while allowing
        # ordinary and occasionally ugly human mistakes.  Knife-edge puzzles
        # naturally remain low-loss even when many players miss the exact hold.
        multiplier = 1.0 + abs(rng.gauss(0.75, 0.65))
        tail = rng.random() ** 3 * scale * 2.2
        loss = min(18.0, top_gap * multiplier + tail)
        loss = max(0.03, loss)
    return {"exact": exact, "points_lost": float(loss)}


def build_mock_friend_results(date_key: str, challenges: Sequence[Mapping]) -> list[dict]:
    """Create deterministic v43A friend results for UI testing only.

    The mock group lets the complete social experience be tested before v43B
    connects real players.  It is deterministic by date and challenge version,
    so reloading the same Daily Challenge yields the same demo competition.
    """
    players: list[dict] = []
    for name, skill_adjustment in MOCK_FRIENDS:
        rng = random.Random(_stable_seed("mock-group", DAILY_CHALLENGE_VERSION, date_key, name))
        question_results = [
            _mock_question_result(rng, challenge, skill_adjustment)
            for challenge in challenges
        ]
        summary = summarize_attempt(question_results)
        players.append({
            "display_name": name,
            "is_user": False,
            "question_results": question_results,
            **summary,
        })
    return players


def build_leaderboard(date_key: str, challenges: Sequence[Mapping], user_records: Sequence[Mapping] | None = None,
                      user_name: str = "You") -> list[dict]:
    """Return deterministic demo friends plus the user's completed score, ranked."""
    entries = build_mock_friend_results(date_key, challenges)
    if user_records is not None:
        summary = summarize_attempt(user_records)
        entries.append({
            "display_name": user_name,
            "is_user": True,
            "question_results": [
                {"exact": is_exact_record(item), "points_lost": float(item.get("points_lost", 0.0) or 0.0)}
                for item in user_records
            ],
            **summary,
        })

    entries.sort(key=lambda item: (
        round(float(item["total_ev_loss"]), 12),
        -int(item["exact_count"]),
        round(float(item["worst_miss"]), 12),
        item["display_name"].lower(),
    ))
    for rank, entry in enumerate(entries, start=1):
        entry["rank"] = rank
    return entries


def question_group_stats(leaderboard: Sequence[Mapping], question_count: int = 10) -> list[dict]:
    """Aggregate exact rate and EV loss by question for the prototype group."""
    stats: list[dict] = []
    for index in range(question_count):
        rows = []
        for entry in leaderboard:
            results = entry.get("question_results", [])
            if index < len(results):
                rows.append(results[index])
        if not rows:
            continue
        exact_count = sum(bool(row.get("exact")) for row in rows)
        avg_loss = sum(float(row.get("points_lost", 0.0) or 0.0) for row in rows) / len(rows)
        stats.append({
            "question_number": index + 1,
            "players": len(rows),
            "exact_count": exact_count,
            "exact_rate": exact_count / len(rows),
            "avg_loss": avg_loss,
        })
    return stats


def group_story(leaderboard: Sequence[Mapping], challenges: Sequence[Mapping]) -> dict:
    """Pick useful social callouts for the end-of-challenge results screen."""
    stats = question_group_stats(leaderboard, question_count=len(challenges))
    if not stats:
        return {"toughest": None, "easiest": None, "unanimous": None}
    toughest = min(stats, key=lambda row: (row["exact_rate"], -row["avg_loss"], row["question_number"]))
    easiest = max(stats, key=lambda row: (row["exact_rate"], -row["avg_loss"], -row["question_number"]))
    unanimous = next((row for row in stats if row["exact_count"] == row["players"]), None)
    return {"toughest": toughest, "easiest": easiest, "unanimous": unanimous}


def user_rank(leaderboard: Sequence[Mapping]) -> int | None:
    for entry in leaderboard:
        if entry.get("is_user"):
            return int(entry.get("rank", 0)) or None
    return None
