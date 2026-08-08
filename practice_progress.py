from __future__ import annotations

"""Lightweight session gamification for Yahtzee Coach v42.

This module is presentation/learning only. It never changes the exact policy,
grades, or strategy recommendations. All progress is intentionally session-only.
"""

from collections import defaultdict
from typing import Iterable, Mapping

from session_learning import SKILL_DESCRIPTIONS, lesson_to_skill

OPTIMAL_TOLERANCE = 1e-5
STRONG_TOLERANCE = 0.75

BADGE_DEFINITIONS = {
    "bullseye": {
        "icon": "🎯",
        "name": "Bullseye",
        "description": "Hit an exact best hold.",
    },
    "three_straight": {
        "icon": "🔥",
        "name": "Three in a Row",
        "description": "Hit three exact best holds in a row.",
    },
    "locked_in": {
        "icon": "⚡",
        "name": "Locked In",
        "description": "Hit five exact best holds in a row.",
    },
    "sharp_session": {
        "icon": "🧠",
        "name": "Sharp Session",
        "description": "Average 0.75 or fewer expected points lost through 10+ rounds.",
    },
    "session_mastery": {
        "icon": "🏅",
        "name": "Strategy Mastery",
        "description": "Reach Session Mastery in a strategy skill.",
    },
}


def _exact_records(records: Iterable[Mapping]) -> list[dict]:
    exact: list[dict] = []
    for record in records:
        if record.get("source") != "exact":
            continue
        try:
            loss = max(0.0, float(record.get("points_lost", 0.0) or 0.0))
        except (TypeError, ValueError):
            loss = 0.0
        exact.append({
            **dict(record),
            "points_lost": loss,
            "skill": lesson_to_skill(record.get("lesson_title")),
        })
    return exact


def _streak(values: list[bool]) -> int:
    count = 0
    for value in reversed(values):
        if not value:
            break
        count += 1
    return count


def _best_streak(values: list[bool]) -> int:
    best = current = 0
    for value in values:
        if value:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _mastery(records: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[record["skill"]].append(record)

    rows: list[dict] = []
    for skill, items in groups.items():
        attempts = len(items)
        losses = [item["points_lost"] for item in items]
        strong_count = sum(loss <= STRONG_TOLERANCE for loss in losses)
        exact_count = sum(loss <= OPTIMAL_TOLERANCE for loss in losses)
        strong_rate = strong_count / attempts
        avg_loss = sum(losses) / attempts

        # "Session Mastery" is deliberately conservative: five examples,
        # at least 80% strong decisions, and low average exact-value loss.
        if attempts >= 5 and strong_rate >= 0.80 and avg_loss <= 0.50:
            level = "Session Mastery"
            level_rank = 4
        elif attempts >= 3 and strong_rate >= 2 / 3 and avg_loss <= 1.00:
            level = "Strong"
            level_rank = 3
        elif attempts >= 2:
            level = "Building"
            level_rank = 2
        else:
            level = "Seen"
            level_rank = 1

        rows.append({
            "skill": skill,
            "description": SKILL_DESCRIPTIONS.get(skill, skill.lower()),
            "attempts": attempts,
            "strong_count": strong_count,
            "exact_count": exact_count,
            "strong_rate": strong_rate,
            "avg_loss": avg_loss,
            "level": level,
            "level_rank": level_rank,
        })

    rows.sort(key=lambda row: (-row["level_rank"], -row["attempts"], row["avg_loss"], row["skill"]))
    return rows


def build_practice_progress(records: Iterable[Mapping]) -> dict:
    exact = _exact_records(records)
    losses = [record["points_lost"] for record in exact]
    optimal_flags = [loss <= OPTIMAL_TOLERANCE for loss in losses]
    strong_flags = [loss <= STRONG_TOLERANCE for loss in losses]

    rounds = len(exact)
    optimal_count = sum(optimal_flags)
    avg_loss = sum(losses) / rounds if rounds else None
    mastery = _mastery(exact)

    current_exact_streak = _streak(optimal_flags)
    best_exact_streak = _best_streak(optimal_flags)
    current_strong_streak = _streak(strong_flags)

    badge_ids: list[str] = []
    if optimal_count >= 1:
        badge_ids.append("bullseye")
    if best_exact_streak >= 3:
        badge_ids.append("three_straight")
    if best_exact_streak >= 5:
        badge_ids.append("locked_in")
    if rounds >= 10 and avg_loss is not None and avg_loss <= 0.75:
        badge_ids.append("sharp_session")
    if any(row["level"] == "Session Mastery" for row in mastery):
        badge_ids.append("session_mastery")

    badges = [{"id": badge_id, **BADGE_DEFINITIONS[badge_id]} for badge_id in badge_ids]

    return {
        "rounds": rounds,
        "optimal_count": optimal_count,
        "optimal_rate": (optimal_count / rounds) if rounds else 0.0,
        "avg_points_lost": avg_loss,
        "current_exact_streak": current_exact_streak,
        "best_exact_streak": best_exact_streak,
        "current_strong_streak": current_strong_streak,
        "mastery": mastery,
        "badges": badges,
        "badge_ids": badge_ids,
    }


def newly_unlocked_badges(before_records: Iterable[Mapping], after_records: Iterable[Mapping]) -> list[dict]:
    before = set(build_practice_progress(before_records)["badge_ids"])
    after_progress = build_practice_progress(after_records)
    return [badge for badge in after_progress["badges"] if badge["id"] not in before]
