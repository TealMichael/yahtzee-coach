from __future__ import annotations

"""Session-level teaching summary for Yahtzee Coach v40.

This module does not change Yahtzee strategy. It summarizes the exact solver's
per-round teaching metadata into cautious, session-only coaching patterns.
"""

from collections import defaultdict
from typing import Iterable, Mapping

OPTIMAL_TOLERANCE = 1e-5
MIN_ROUNDS_FOR_SUMMARY = 5


SKILL_DESCRIPTIONS = {
    "Protecting made hands": "recognizing when guaranteed scoring value is worth protecting",
    "Matching-dice structures": "protecting pairs, triples, two-pair structures, and four-of-a-kind cores",
    "Straight structure": "preserving connected dice and useful straight fragments",
    "Upper-section targeting": "using open upper boxes and bonus pressure to choose a number target",
    "Scorecard-aware flexibility": "letting the remaining scorecard decide which single die or small structure matters",
    "Flexible rerolls": "knowing when fewer held dice create more useful future paths",
    "Scorecard fit": "matching the hold to the open boxes instead of judging the dice in isolation",
}


def lesson_to_skill(lesson_title: str | None) -> str:
    title = (lesson_title or "").strip()
    if not title:
        return "Scorecard fit"
    if title == "Protect a made hand":
        return "Protecting made hands"
    if title in {"Protect four matching dice", "Build from the triple", "Keep both pairs alive", "Keep the best matching base"}:
        return "Matching-dice structures"
    if title.startswith("Build the ") and title.endswith(" box"):
        return "Upper-section targeting"
    if title in {"Protect the straight core", "Preserve the useful straight fragment"}:
        return "Straight structure"
    if title == "Let the scorecard choose the die":
        return "Scorecard-aware flexibility"
    if title in {"Keep flexibility", "Reset a weak structure"}:
        return "Flexible rerolls"
    if title == "Keep the most useful flexibility":
        return "Scorecard fit"
    return title


def _exact_records(records: Iterable[Mapping]) -> list[dict]:
    cleaned: list[dict] = []
    for record in records:
        if record.get("source") != "exact":
            continue
        try:
            points_lost = max(0.0, float(record.get("points_lost", 0.0)))
        except (TypeError, ValueError):
            points_lost = 0.0
        cleaned.append({
            **dict(record),
            "points_lost": points_lost,
            "skill": lesson_to_skill(record.get("lesson_title")),
        })
    return cleaned


def _skill_stats(records: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[record["skill"]].append(record)

    stats: list[dict] = []
    for skill, items in groups.items():
        losses = [item["points_lost"] for item in items]
        strong = [loss <= 0.75 for loss in losses]
        exact = [loss <= OPTIMAL_TOLERANCE for loss in losses]
        stats.append({
            "skill": skill,
            "description": SKILL_DESCRIPTIONS.get(skill, skill.lower()),
            "attempts": len(items),
            "strong_count": sum(strong),
            "optimal_count": sum(exact),
            "strong_rate": sum(strong) / len(items),
            "optimal_rate": sum(exact) / len(items),
            "avg_loss": sum(losses) / len(losses),
            "total_loss": sum(losses),
            "max_loss": max(losses),
            "latest_lesson": items[-1].get("lesson_title", skill),
        })
    return stats


def build_session_learning_summary(records: Iterable[Mapping], min_rounds: int = MIN_ROUNDS_FOR_SUMMARY) -> dict:
    exact = _exact_records(records)
    rounds = len(exact)
    summary = {
        "ready": rounds >= min_rounds,
        "rounds": rounds,
        "rounds_needed": max(0, min_rounds - rounds),
        "optimal_count": 0,
        "optimal_rate": 0.0,
        "avg_points_lost": 0.0,
        "strengths": [],
        "focus_areas": [],
        "biggest_lesson": "",
        "trend": "",
    }
    if not exact:
        return summary

    losses = [record["points_lost"] for record in exact]
    optimal_count = sum(loss <= OPTIMAL_TOLERANCE for loss in losses)
    summary["optimal_count"] = optimal_count
    summary["optimal_rate"] = optimal_count / rounds
    summary["avg_points_lost"] = sum(losses) / rounds

    stats = _skill_stats(exact)

    # Strengths require repeated evidence. A skill qualifies when the player has
    # seen it at least twice and 75%+ of those decisions were within 0.75 points
    # of optimal, with low average loss overall.
    strengths = [
        stat for stat in stats
        if stat["attempts"] >= 2 and stat["strong_rate"] >= 0.75 and stat["avg_loss"] <= 0.75
    ]
    strengths.sort(key=lambda s: (-s["attempts"], s["avg_loss"], s["skill"]))
    summary["strengths"] = strengths[:2]

    # Focus areas are driven by actual exact-value cost. One large miss is worth
    # surfacing; smaller misses need repeated evidence before we call it a pattern.
    focus = [
        stat for stat in stats
        if stat["max_loss"] >= 2.5 or (stat["attempts"] >= 2 and stat["avg_loss"] >= 1.0)
    ]
    focus.sort(key=lambda s: (-s["total_loss"], -s["avg_loss"], s["skill"]))
    summary["focus_areas"] = focus[:2]

    if focus:
        top = focus[0]
        if top["attempts"] == 1:
            summary["biggest_lesson"] = (
                f"{top['skill']}: one decision cost {top['max_loss']:.2f} expected game points. "
                f"Focus on {top['description']}."
            )
        else:
            summary["biggest_lesson"] = (
                f"{top['skill']}: {top['attempts']} decisions averaged {top['avg_loss']:.2f} expected points lost. "
                f"Focus on {top['description']}."
            )
    elif summary["strengths"]:
        top = summary["strengths"][0]
        summary["biggest_lesson"] = (
            f"Keep leaning on {top['skill'].lower()}: {top['strong_count']} of {top['attempts']} decisions "
            "were exact or very close to exact."
        )
    else:
        summary["biggest_lesson"] = (
            "Keep building the sample. Your exact decisions are being tracked by strategy type, "
            "but there is not enough repeated evidence yet to label a specific pattern."
        )

    # Trend is intentionally conservative and appears only after 6 exact rounds.
    if rounds >= 6:
        split = rounds // 2
        early = losses[:split]
        recent = losses[-split:]
        early_avg = sum(early) / len(early)
        recent_avg = sum(recent) / len(recent)
        delta = recent_avg - early_avg
        if delta <= -0.5:
            summary["trend"] = f"Trending better: recent decisions are giving up {abs(delta):.2f} fewer expected points per round than the early part of the session."
        elif delta >= 0.5:
            summary["trend"] = f"Recent rounds have been tougher: they are giving up {delta:.2f} more expected points per round than the early part of the session."
        else:
            summary["trend"] = "Steady session: recent decision quality is close to the early-session level."

    return summary
