from __future__ import annotations

"""Fast exact-policy lookup and coach-report generation for Yahtzee Coach v37.

The heavy dynamic-programming solve is performed offline.  The live app only
loads a compact policy table and performs indexed lookups.  If a scorecard is
not present in the packaged policy, the Streamlit app falls back to the legacy
heuristic coach rather than failing.
"""

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

import numpy as np

CATEGORIES: tuple[str, ...] = (
    "ones", "twos", "threes", "fours", "fives", "sixes",
    "three_of_a_kind", "four_of_a_kind", "full_house",
    "small_straight", "large_straight", "yahtzee", "chance",
)

TIE_TOLERANCE = 1e-5


def canonical(values: Sequence[int]) -> tuple[int, ...]:
    return tuple(sorted(int(value) for value in values))


def encode_hold(hold: Sequence[int]) -> int:
    code = 0
    held = canonical(hold)
    for face in range(1, 7):
        code |= held.count(face) << ((face - 1) * 3)
    return code


def decode_hold(code: int) -> tuple[int, ...]:
    values: list[int] = []
    for face in range(1, 7):
        count = (int(code) >> ((face - 1) * 3)) & 0b111
        values.extend([face] * count)
    return tuple(values)


def hold_text(hold: Sequence[int]) -> str:
    held = canonical(hold)
    return "reroll everything" if not held else "keep " + ", ".join(map(str, held))


def scorecard_state_key(scorecard: Mapping[str, int | None]) -> int:
    """Encode the exact solver state used by the packaged policy table."""
    open_mask = 0
    upper_total = 0
    for category_id, category in enumerate(CATEGORIES):
        value = scorecard.get(category)
        if value is None:
            open_mask |= 1 << category_id
        elif category_id < 6:
            upper_total += int(value)

    # Once the upper section has reached 63, higher subtotals are equivalent
    # for future-value purposes because the 35-point bonus is already secured.
    upper_total = min(63, upper_total)
    yahtzee_bonus_live = scorecard.get("yahtzee") == 50
    return open_mask | (upper_total << 13) | (int(yahtzee_bonus_live) << 19)


def _is_legal_hold(dice: Sequence[int], hold: Sequence[int]) -> bool:
    dice = canonical(dice)
    hold = canonical(hold)
    return all(hold.count(face) <= dice.count(face) for face in range(1, 7))


@dataclass
class ExactPolicyTable:
    path: Path

    def __post_init__(self) -> None:
        data = np.load(self.path, allow_pickle=False)
        version = int(data["format_version"][0])
        if version != 2:
            raise ValueError(f"Unsupported exact policy format: {version}")

        self.state_keys = data["state_keys"]
        self.rolls = data["rolls"]
        self.hold_codes = data["hold_codes"]
        self.roll1_values = data["roll1_hold_values"]
        self.roll2_values = data["roll2_hold_values"]
        self.roll1_best = data["roll1_best_hold_ids"]
        self.roll2_best = data["roll2_best_hold_ids"]

        self.roll_to_id = {
            tuple(int(value) for value in roll): index
            for index, roll in enumerate(self.rolls)
        }
        self.hold_id_by_code: list[dict[int, int]] = []
        for row in self.hold_codes:
            self.hold_id_by_code.append({
                int(code): hold_id
                for hold_id, code in enumerate(row)
                if int(code) >= 0
            })

    def state_index(self, scorecard: Mapping[str, int | None]) -> int | None:
        key = scorecard_state_key(scorecard)
        index = int(np.searchsorted(self.state_keys, key))
        if index >= len(self.state_keys) or int(self.state_keys[index]) != key:
            return None
        return index

    def _indices(
        self,
        scorecard: Mapping[str, int | None],
        dice: Sequence[int],
    ) -> tuple[int, int] | None:
        state_index = self.state_index(scorecard)
        if state_index is None:
            return None
        roll_id = self.roll_to_id.get(canonical(dice))
        if roll_id is None:
            return None
        return state_index, roll_id

    def analyze(
        self,
        scorecard: Mapping[str, int | None],
        dice: Sequence[int],
        roll_number: int,
    ) -> list[dict]:
        """Return every legal hold ranked by exact full-game expected value."""
        indices = self._indices(scorecard, dice)
        if indices is None:
            raise KeyError("scorecard/dice state is not present in the exact policy table")
        state_index, roll_id = indices

        if roll_number == 1:
            values = self.roll1_values[state_index, roll_id]
        elif roll_number == 2:
            values = self.roll2_values[state_index, roll_id]
        else:
            raise ValueError("Exact mode supports Roll 1 and Roll 2 only")

        results: list[dict] = []
        for hold_id, code in enumerate(self.hold_codes[roll_id]):
            code = int(code)
            if code < 0:
                continue
            value = float(values[hold_id])
            if not np.isfinite(value):
                continue
            hold = decode_hold(code)
            results.append({
                "hold": list(hold),
                "strategy_value": value,
                "exact_expected_game_value": value,
                "hold_id": int(hold_id),
                "roll_number": int(roll_number),
                "rolls_remaining": 3 - int(roll_number),
            })

        results.sort(key=lambda item: (-item["strategy_value"], item["hold_id"]))
        if not results:
            raise RuntimeError("exact policy returned no legal holds")
        return results

    def best_hold(
        self,
        scorecard: Mapping[str, int | None],
        dice: Sequence[int],
        roll_number: int,
    ) -> tuple[tuple[int, ...], float]:
        results = self.analyze(scorecard, dice, roll_number)
        return tuple(results[0]["hold"]), float(results[0]["strategy_value"])

    def hold_value(
        self,
        scorecard: Mapping[str, int | None],
        dice: Sequence[int],
        roll_number: int,
        hold: Sequence[int],
    ) -> float | None:
        indices = self._indices(scorecard, dice)
        if indices is None:
            return None
        state_index, roll_id = indices
        hold_id = self.hold_id_by_code[roll_id].get(encode_hold(hold))
        if hold_id is None:
            return None
        values = self.roll1_values if roll_number == 1 else self.roll2_values if roll_number == 2 else None
        if values is None:
            raise ValueError("Exact mode supports Roll 1 and Roll 2 only")
        value = values[state_index, roll_id, hold_id]
        return None if not np.isfinite(value) else float(value)


def exact_grade(points_lost: float, is_optimal: bool) -> tuple[str, str]:
    """Pedagogical letter grade based on exact expected points surrendered.

    The recommendation itself is mathematically exact.  The letter-grade bands
    are intentionally a coaching rubric rather than a claim from the solver.
    """
    if is_optimal:
        return "A+", "Excellent move. This is an exact optimal hold."
    if points_lost <= 0.25:
        return "A", "Excellent alternative. It gives up almost no exact value."
    if points_lost <= 0.75:
        return "A-", "Very strong move. The exact difference is small."
    if points_lost <= 1.50:
        return "B+", "Good move, but the exact solver finds a stronger hold."
    if points_lost <= 2.50:
        return "B", "Reasonable move with a noticeable exact-value tradeoff."
    if points_lost <= 4.00:
        return "B-", "Playable, but it gives up meaningful expected value."
    if points_lost <= 6.00:
        return "C", "This has some logic, but a stronger plan is available."
    if points_lost <= 10.00:
        return "D", "This is a weak hold in this scorecard position."
    return "F", "This hold gives up a large amount of exact expected value."


def _hold_rank(results: Sequence[dict], user_value: float) -> int:
    return 1 + sum(
        1 for result in results
        if float(result["strategy_value"]) > user_value + TIE_TOLERANCE
    )


def _pattern_lines(dice: Sequence[int], hold: Sequence[int]) -> list[str]:
    hold = canonical(hold)
    if not hold:
        return ["Rerolling everything keeps all five dice available for a completely new pattern."]

    counts = {face: hold.count(face) for face in range(1, 7)}
    max_count = max(counts.values(), default=0)
    unique = sorted(set(hold))
    lines: list[str] = []

    if max_count >= 4:
        face = max(counts, key=counts.get)
        lines.append(f"You protected {max_count} matching {face}s, keeping the strongest matching-dice path intact.")
    elif max_count == 3:
        face = max(counts, key=counts.get)
        lines.append(f"You protected a triple of {face}s, preserving strong upper-section, 3K/4K, and Yahtzee potential where those boxes remain open.")
    elif max_count == 2:
        pair_faces = [face for face, count in counts.items() if count == 2]
        if len(pair_faces) >= 2:
            lines.append("You protected two pairs, which keeps Full House and matching-number improvement paths available.")
        else:
            lines.append(f"You protected a pair of {pair_faces[0]}s, giving the hand a clear matching-number path.")

    longest_run = 1
    current = 1
    for left, right in zip(unique, unique[1:]):
        if right == left + 1:
            current += 1
            longest_run = max(longest_run, current)
        else:
            current = 1
    if longest_run >= 3:
        lines.append("You kept a connected run of numbers, preserving straight potential.")

    if len(hold) == 5:
        lines.append("You chose to keep the complete roll, so the solver is treating the current made hand as more valuable than another reroll.")
    elif not lines:
        lines.append("Your hold preserves some flexibility for the remaining reroll(s).")

    return lines[:2]


def build_exact_report(
    policy: ExactPolicyTable,
    *,
    dice: Sequence[int],
    scorecard: Mapping[str, int | None],
    user_hold: Sequence[int],
    roll_number: int,
) -> tuple[str, dict]:
    """Create the player-facing report using only exact policy values."""
    started = perf_counter()
    dice = canonical(dice)
    user_hold = canonical(user_hold)
    if not _is_legal_hold(dice, user_hold):
        raise ValueError("That hold is not possible with the current dice.")

    results = policy.analyze(scorecard, dice, roll_number)
    best_value = float(results[0]["strategy_value"])
    user_result = next((r for r in results if tuple(r["hold"]) == user_hold), None)
    if user_result is None:
        raise ValueError("That hold is not present in the exact policy table.")
    user_value = float(user_result["strategy_value"])
    points_lost = max(0.0, best_value - user_value)
    is_optimal = points_lost <= TIE_TOLERANCE

    optimal_results = [
        result for result in results
        if best_value - float(result["strategy_value"]) <= TIE_TOLERANCE
    ]
    # When the player's hold is tied for best, display it as the optimal choice
    # so a mathematically equivalent move is never presented as wrong.
    if is_optimal:
        display_optimal = user_hold
    else:
        display_optimal = tuple(optimal_results[0]["hold"])

    rank = _hold_rank(results, user_value)
    grade, rating = exact_grade(points_lost, is_optimal)

    report: list[str] = [
        "YAHTZEE COACH REPORT",
        "=" * 40,
        f"Roll Number: {roll_number} of 3",
        f"Rolls Remaining: {3 - roll_number}",
        f"Current dice: {list(dice)}",
        f"Your choice: {hold_text(user_hold)}",
        f"Optimal choice: {hold_text(display_optimal)}",
        "",
        f"Grade: {grade}",
        f"Coach rating: {rating}",
        f"Hold rank: #{rank} of {len(results)} legal holds",
        f"Your exact expected game value: {user_value:.2f}",
        f"Optimal exact expected game value: {best_value:.2f}",
        f"Strategy value lost: {points_lost:.2f}",
        "",
        "What was good about your move?",
    ]

    for line in _pattern_lines(dice, user_hold):
        report.append(f"- {line}")
    if is_optimal:
        report.append("- Most importantly, this hold ties for the highest exact full-game expected value in this position.")
    elif points_lost <= 0.75:
        report.append("- This is close to the exact best play, so the strategic cost of the difference is small.")

    report.extend(["", "Why was the optimal move better?"])
    if is_optimal:
        if len(optimal_results) > 1:
            report.append(f"- Your move is one of {len(optimal_results)} holds tied for the exact best value.")
        else:
            report.append("- Your move was the exact optimal hold.")
        report.append("- The solver found no legal hold with a higher full-game expected score.")
    else:
        report.append(
            f"- {hold_text(display_optimal).capitalize()} finishes about {points_lost:.2f} expected game point(s) higher from this exact scorecard state."
        )
        report.append(
            f"- The solver compared every legal hold across the remaining {3 - roll_number} reroll(s) and all future scorecard decisions."
        )
        report.append("- Upper-bonus status, Yahtzee/Joker rules, and future open-category value are included in that comparison.")

    report.extend(["", "Coach recommendation:"])
    if is_optimal:
        report.append("Stay with this thinking. You found an exact optimal hold for this position.")
    elif points_lost <= 0.75:
        report.append(
            f"Your idea was strong, but the exact edge goes to {hold_text(display_optimal)}."
        )
    else:
        report.append(
            f"The stronger play is to {hold_text(display_optimal)}. That is the exact full-game recommendation for this position."
        )

    metadata = {
        "source": "exact",
        "available": True,
        "state_key": scorecard_state_key(scorecard),
        "roll_number": int(roll_number),
        "dice": " ".join(map(str, dice)),
        "user_hold": hold_text(user_hold),
        "optimal_hold": hold_text(display_optimal),
        "optimal_tie_count": len(optimal_results),
        "hold_rank": int(rank),
        "legal_hold_count": len(results),
        "points_lost": float(points_lost),
        "lookup_ms": (perf_counter() - started) * 1000.0,
    }
    return "\n".join(report), metadata


def build_live_report_with_fallback(
    policy: ExactPolicyTable,
    *,
    dice: Sequence[int],
    scorecard: Mapping[str, int | None],
    user_hold: Sequence[int],
    roll_number: int,
    legacy_report_factory,
) -> tuple[str, dict]:
    """Exact-first report router with a safe legacy fallback.

    Kept outside Streamlit so the exact/fallback integration can be tested
    exhaustively without launching the web app.
    """
    try:
        return build_exact_report(
            policy,
            dice=dice,
            scorecard=scorecard,
            user_hold=user_hold,
            roll_number=roll_number,
        )
    except Exception as exc:
        report = legacy_report_factory(dice, scorecard, user_hold, roll_number)
        return report, {
            "source": "legacy_fallback",
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_live_report_from_loader(
    policy_loader,
    *,
    dice: Sequence[int],
    scorecard: Mapping[str, int | None],
    user_hold: Sequence[int],
    roll_number: int,
    legacy_report_factory,
) -> tuple[str, dict]:
    """Exact-first router that also survives policy-file load failures."""
    try:
        policy = policy_loader()
    except Exception as exc:
        report = legacy_report_factory(dice, scorecard, user_hold, roll_number)
        return report, {
            "source": "legacy_fallback",
            "available": False,
            "error": f"policy_load_error: {type(exc).__name__}: {exc}",
        }

    return build_live_report_with_fallback(
        policy,
        dice=dice,
        scorecard=scorecard,
        user_hold=user_hold,
        roll_number=roll_number,
        legacy_report_factory=legacy_report_factory,
    )
