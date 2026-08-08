from __future__ import annotations

"""Fast exact-policy lookup and coach-report generation for Yahtzee Coach v38.

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


CATEGORY_LABELS = {
    "ones": "Ones", "twos": "Twos", "threes": "Threes",
    "fours": "Fours", "fives": "Fives", "sixes": "Sixes",
    "three_of_a_kind": "Three of a Kind", "four_of_a_kind": "Four of a Kind",
    "full_house": "Full House", "small_straight": "Small Straight",
    "large_straight": "Large Straight", "yahtzee": "Yahtzee", "chance": "Chance",
}
UPPER_BY_FACE = {1: "ones", 2: "twos", 3: "threes", 4: "fours", 5: "fives", 6: "sixes"}
SMALL_STRAIGHTS = ({1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6})
LARGE_STRAIGHTS = ({1, 2, 3, 4, 5}, {2, 3, 4, 5, 6})


def _is_open(scorecard: Mapping[str, int | None], category: str) -> bool:
    return scorecard.get(category) is None


def _upper_bonus_context(scorecard: Mapping[str, int | None]) -> dict:
    scored_total = 0
    max_remaining = 0
    open_upper: list[str] = []
    for face, category in UPPER_BY_FACE.items():
        value = scorecard.get(category)
        if value is None:
            open_upper.append(category)
            max_remaining += face * 5
        else:
            scored_total += int(value)
    earned = scored_total >= 63
    alive = (not earned) and scored_total + max_remaining >= 63
    return {
        "total": scored_total,
        "needed": max(0, 63 - scored_total),
        "earned": earned,
        "alive": alive,
        "open_upper": open_upper,
    }


def _straight_core(hold: Sequence[int], scorecard: Mapping[str, int | None]) -> tuple[str | None, int]:
    unique = set(canonical(hold))
    candidates: list[tuple[str, int]] = []
    if _is_open(scorecard, "large_straight"):
        candidates.append(("Large Straight", max((len(unique & target) for target in LARGE_STRAIGHTS), default=0)))
    if _is_open(scorecard, "small_straight"):
        candidates.append(("Small Straight", max((len(unique & target) for target in SMALL_STRAIGHTS), default=0)))
    if not candidates:
        return None, 0
    candidates.sort(key=lambda item: (item[1], item[0] == "Large Straight"), reverse=True)
    return candidates[0]


def _made_hand_name(hold: Sequence[int], scorecard: Mapping[str, int | None]) -> str | None:
    held = canonical(hold)
    if len(held) != 5:
        return None
    counts = sorted((held.count(face) for face in range(1, 7) if held.count(face)), reverse=True)
    unique = set(held)
    if counts == [5] and (_is_open(scorecard, "yahtzee") or scorecard.get("yahtzee") == 50):
        return "Yahtzee"
    if unique in LARGE_STRAIGHTS and _is_open(scorecard, "large_straight"):
        return "Large Straight"
    if counts == [3, 2] and _is_open(scorecard, "full_house"):
        return "Full House"
    if counts and counts[0] >= 4 and _is_open(scorecard, "four_of_a_kind"):
        return "Four of a Kind"
    if any(target.issubset(unique) for target in SMALL_STRAIGHTS) and _is_open(scorecard, "small_straight"):
        return "Small Straight"
    return None


def _format_faces(values: Sequence[int]) -> str:
    values = canonical(values)
    if not values:
        return "nothing"
    return ", ".join(map(str, values))


def _hold_difference(user_hold: Sequence[int], optimal_hold: Sequence[int]) -> str | None:
    user = list(canonical(user_hold))
    optimal = list(canonical(optimal_hold))
    add = optimal.copy()
    release = user.copy()
    for value in canonical(user_hold):
        if value in add:
            add.remove(value)
            release.remove(value)
    if not add and not release:
        return None
    if add and release:
        return f"Compared with your hold, the exact play adds {_format_faces(add)} and sends {_format_faces(release)} back into the reroll."
    if add:
        return f"Compared with your hold, the exact play also protects {_format_faces(add)} instead of rerolling those dice."
    return f"Compared with your hold, the exact play releases {_format_faces(release)} so those dice can be rerolled."


def _join_paths(paths: Sequence[str]) -> str:
    paths = list(paths)
    if not paths:
        return "your strongest matching-dice paths"
    if len(paths) == 1:
        return paths[0]
    if len(paths) == 2:
        return f"{paths[0]} and {paths[1]}"
    return ", ".join(paths[:-1]) + f", and {paths[-1]}"


def _visible_strategy_reason(
    scorecard: Mapping[str, int | None],
    optimal_hold: Sequence[int],
    roll_number: int,
) -> tuple[str, str, str]:
    """Return (lesson title, visible reason, reusable takeaway).

    This does not pretend a single heuristic *proves* the optimal hold. The DP
    table proves the ranking; this function translates the most useful visible
    feature of that exact answer into coaching language.
    """
    hold = canonical(optimal_hold)
    counts = {face: hold.count(face) for face in range(1, 7)}
    max_count = max(counts.values(), default=0)
    bonus = _upper_bonus_context(scorecard)
    made = _made_hand_name(hold, scorecard)

    if made:
        return (
            "Protect a made hand",
            f"The exact hold keeps the complete {made}. The current made value is worth more than opening up another reroll.",
            "When a scoring hand is already made, compare the value of improving it with the risk of breaking guaranteed value.",
        )

    if max_count >= 4:
        face = max(counts, key=counts.get)
        paths: list[str] = []
        upper = UPPER_BY_FACE[face]
        if _is_open(scorecard, upper):
            paths.append(CATEGORY_LABELS[upper])
        if _is_open(scorecard, "four_of_a_kind"):
            paths.append("Four of a Kind")
        if _is_open(scorecard, "yahtzee"):
            paths.append("Yahtzee")
        elif scorecard.get("yahtzee") == 50:
            paths.append("an extra Yahtzee/Joker")
        path_text = _join_paths(paths[:3])
        return (
            "Protect four matching dice",
            f"Keeping all four {face}s preserves a one-die improvement path while protecting {path_text}.",
            "Four matching dice are usually a structure to protect; breaking them should require a very strong scorecard reason.",
        )

    if max_count == 3:
        face = max(counts, key=counts.get)
        paths: list[str] = []
        upper = UPPER_BY_FACE[face]
        if _is_open(scorecard, upper):
            paths.append(CATEGORY_LABELS[upper])
        for category in ("three_of_a_kind", "four_of_a_kind", "yahtzee"):
            if _is_open(scorecard, category):
                paths.append(CATEGORY_LABELS[category])
        path_text = _join_paths(paths[:3]) if paths else "matching-dice scoring"
        return (
            "Build from the triple",
            f"The exact hold protects three {face}s, giving the remaining dice room to improve while keeping {path_text} available.",
            "A triple is valuable because it already has scoring strength and still has room to grow into stronger matching hands.",
        )

    pair_faces = [face for face, count in counts.items() if count == 2]
    if len(pair_faces) >= 2 and _is_open(scorecard, "full_house"):
        return (
            "Keep both pairs alive",
            "The exact hold protects two pairs. That keeps a strong Full House path while preserving two different matching numbers that can improve.",
            "With Full House open, two pairs can be more valuable together than choosing only the prettier or higher pair.",
        )

    straight_name, straight_core = _straight_core(hold, scorecard)
    if straight_name and straight_core >= 4:
        if straight_name == "Small Straight" and len(set(hold)) >= 4:
            reason = "The exact hold preserves four distinct numbers from a straight pattern, so the straight structure survives the reroll."
        else:
            reason = f"The exact hold preserves a four-number core for {straight_name}, leaving the rerolled dice to find the missing connection."
        return (
            "Protect the straight core",
            reason,
            "Four connected straight numbers are a premium structure. Avoid breaking the core just to keep an unrelated pair or high die.",
        )

    if straight_name and straight_core == 3 and len(set(hold)) >= 3:
        return (
            "Preserve the useful straight fragment",
            f"The exact hold keeps three distinct numbers that fit a live {straight_name} pattern while rerolling the dice that do less for that path.",
            "For straight chases, coverage of a live straight pattern matters more than simply keeping the highest-looking dice.",
        )

    if max_count == 2:
        face = max(counts, key=counts.get)
        upper = UPPER_BY_FACE[face]
        if _is_open(scorecard, upper):
            bonus_text = " and the 35-point upper bonus is still reachable" if bonus["alive"] else ""
            return (
                f"Build the {CATEGORY_LABELS[upper]} box",
                f"The exact hold protects a pair of {face}s while the {CATEGORY_LABELS[upper]} box is open{bonus_text}.",
                "Pairs are worth more when they line up with an open upper box and the rest of the scorecard still rewards that number.",
            )
        return (
            "Keep the best matching base",
            f"The exact hold protects a pair of {face}s and rerolls the loose dice, preserving a clearer path to a stronger matching hand.",
            "A clean pair often gives future rolls a better target than several unrelated single dice.",
        )

    if len(hold) == 1:
        face = hold[0]
        upper = UPPER_BY_FACE[face]
        if _is_open(scorecard, upper) and bonus["alive"]:
            return (
                "Let the scorecard choose the die",
                f"The exact solver keeps the {face} because {CATEGORY_LABELS[upper]} is still open and the upper bonus is still reachable; the other dice are worth more as fresh rerolls in this scorecard state.",
                "Late or constrained scorecards can make one useful upper die better than a visually nicer pattern. Read the open boxes, not just the dice.",
            )
        return (
            "Keep flexibility",
            f"The exact solver keeps only the {face}, which means the rest of this roll is worth more as fresh dice than as a partial pattern in the current scorecard.",
            "When no partial pattern is strong enough, keeping fewer dice can create more ways to improve.",
        )

    if not hold:
        return (
            "Reset a weak structure",
            "The exact solver rerolls all five dice. In this scorecard state, none of the current fragments is valuable enough to justify reducing the number of fresh dice.",
            "Rerolling everything is not giving up; sometimes maximum flexibility has the highest long-run value.",
        )

    return (
        "Keep the most useful flexibility",
        "The exact hold keeps the dice that fit the remaining scorecard best while releasing the weaker pieces for another chance to improve.",
        "The best hold is about the interaction between the dice and the open boxes, not just the prettiest pattern on the table.",
    )


def _pattern_lines(
    dice: Sequence[int],
    hold: Sequence[int],
    scorecard: Mapping[str, int | None],
) -> list[str]:
    hold = canonical(hold)
    if not hold:
        return ["You chose maximum flexibility by rerolling all five dice."]

    counts = {face: hold.count(face) for face in range(1, 7)}
    max_count = max(counts.values(), default=0)
    lines: list[str] = []
    bonus = _upper_bonus_context(scorecard)

    if max_count >= 4:
        face = max(counts, key=counts.get)
        lines.append(f"You recognized the value of a four-of-a-kind core with the {face}s.")
    elif max_count == 3:
        face = max(counts, key=counts.get)
        lines.append(f"You protected a triple of {face}s, a strong base that can still improve.")
    elif max_count == 2:
        pair_faces = [face for face, count in counts.items() if count == 2]
        if len(pair_faces) >= 2:
            lines.append("You protected two pairs, so your hold has a clear Full House/matching-dice idea.")
        else:
            face = pair_faces[0]
            upper = UPPER_BY_FACE[face]
            if _is_open(scorecard, upper):
                bonus_note = " with the upper bonus still reachable" if bonus["alive"] else ""
                lines.append(f"You protected a pair of {face}s while {CATEGORY_LABELS[upper]} is open{bonus_note}.")
            else:
                lines.append(f"You protected a pair of {face}s, giving the hand a clear matching-number target.")

    straight_name, core = _straight_core(hold, scorecard)
    if straight_name and core >= 3 and len(set(hold)) >= 3:
        lines.append(f"You also preserved {core} useful distinct numbers for a live {straight_name} path.")

    if len(hold) == 5:
        made = _made_hand_name(hold, scorecard)
        if made:
            lines.append(f"You recognized that you already had a made {made}.")
        elif not lines:
            lines.append("You chose to lock the complete roll rather than use another reroll.")
    elif not lines:
        lines.append("Your hold keeps some flexibility for the remaining reroll(s).")

    return lines[:2]


def _closeness_line(points_lost: float, is_optimal: bool) -> str:
    if is_optimal:
        return "Exact best play: no legal hold has a higher full-game expected score."
    if points_lost <= 0.25:
        return f"Near tie: your hold is only {points_lost:.2f} expected game points behind. This is a fine distinction, not a bad strategy choice."
    if points_lost <= 0.75:
        return f"Small edge: the exact play is {points_lost:.2f} expected game points better. Your idea is still very strong."
    if points_lost <= 2.50:
        return f"Meaningful edge: the exact play gains about {points_lost:.2f} expected game points over your hold."
    if points_lost <= 6.00:
        return f"Clear edge: the exact play gains about {points_lost:.2f} expected game points, enough to make the structural difference worth learning."
    return f"Large edge: the exact play gains about {points_lost:.2f} expected game points. This is a pattern worth correcting, not just a tiny solver preference."


def _top_hold_lines(results: Sequence[dict], user_hold: Sequence[int], user_value: float) -> list[str]:
    best = float(results[0]["strategy_value"])
    lines: list[str] = []
    for index, result in enumerate(results[:3], start=1):
        gap = max(0.0, best - float(result["strategy_value"]))
        suffix = "best" if gap <= TIE_TOLERANCE else f"-{gap:.2f} expected pts"
        lines.append(f"#{index}: {hold_text(result['hold'])} ({suffix})")
    rank = _hold_rank(results, user_value)
    if rank > 3:
        lines.append(f"Your hold: #{rank} ({max(0.0, best - user_value):.2f} expected pts behind)")
    return lines


def build_exact_report(
    policy: ExactPolicyTable,
    *,
    dice: Sequence[int],
    scorecard: Mapping[str, int | None],
    user_hold: Sequence[int],
    roll_number: int,
) -> tuple[str, dict]:
    """Create a teaching-first player report grounded in the exact policy table."""
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
    if is_optimal:
        display_optimal = user_hold
    else:
        display_optimal = tuple(optimal_results[0]["hold"])

    rank = _hold_rank(results, user_value)
    grade, rating = exact_grade(points_lost, is_optimal)
    lesson_title, visible_reason, takeaway = _visible_strategy_reason(
        scorecard, display_optimal, roll_number
    )
    difference = _hold_difference(user_hold, display_optimal)
    closeness = _closeness_line(points_lost, is_optimal)

    if is_optimal:
        recommendation = f"Yes — {hold_text(display_optimal)}. {visible_reason}"
    elif points_lost <= 0.25:
        recommendation = (
            f"Exact edge: {hold_text(display_optimal)}. Your idea was almost tied, so focus on the small structural advantage rather than treating this as a major mistake."
        )
    elif points_lost <= 0.75:
        recommendation = f"Best play: {hold_text(display_optimal)}. {visible_reason}"
    else:
        recommendation = f"Best play: {hold_text(display_optimal)}. {visible_reason}"

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
        f"Expected game points lost: {points_lost:.2f}",
        "",
        "How close was it?",
        f"- {closeness}",
        "- Expected game points means the average final-game score over all possible future rolls and optimal future decisions from this scorecard state.",
        "",
        "What was good about your move?",
    ]

    for line in _pattern_lines(dice, user_hold, scorecard):
        report.append(f"- {line}")
    if is_optimal:
        report.append("- Most importantly, your hold is tied for the highest exact full-game expected value in this position.")
    elif points_lost <= 0.75:
        report.append("- The exact cost is small, so keep the good idea and refine only the part that separates it from the best hold.")

    report.extend(["", "Why was the optimal move better?"])
    if is_optimal:
        if len(optimal_results) > 1:
            report.append(f"- Your move is one of {len(optimal_results)} holds tied for the exact best value.")
        else:
            report.append("- Your move was the exact optimal hold.")
        report.append(f"- {visible_reason}")
    else:
        if difference:
            report.append(f"- {difference}")
        report.append(f"- {visible_reason}")
        report.append(
            f"- That exact choice finishes about {points_lost:.2f} expected game point(s) higher from this scorecard state."
        )

    report.extend(["", "Teaching takeaway:"])
    report.append(f"- {lesson_title}: {takeaway}")

    report.extend(["", "Top exact holds:"])
    for line in _top_hold_lines(results, user_hold, user_value):
        report.append(f"- {line}")

    report.extend(["", "Coach recommendation:"])
    report.append(recommendation)

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
        "lesson_title": lesson_title,
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
