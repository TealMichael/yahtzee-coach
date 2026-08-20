from __future__ import annotations

"""Fast exact-policy lookup and personalized coach-report generation for Yahtzee Coach v42.5.

The heavy dynamic-programming solve is performed offline. The live app only
loads a compact policy table and performs indexed lookups. Player-facing Daily
and Practice coaching require the exact policy; the legacy fallback helpers at
the bottom of this module remain only for historical compatibility/tests.
"""

from dataclasses import dataclass
import hashlib
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

# Known-good v43B exact-policy artifact. Any intentional policy regeneration
# must update this fingerprint explicitly after the math audit passes.
EXPECTED_EXACT_POLICY_SHA256 = "cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b"


def exact_policy_sha256(path: str | Path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_exact_policy_fingerprint(
    path: str | Path,
    expected: str = EXPECTED_EXACT_POLICY_SHA256,
) -> str:
    """Fail closed if the packaged exact policy is not the audited artifact."""
    actual = exact_policy_sha256(path)
    if actual.lower() != str(expected).lower():
        raise RuntimeError(
            "Exact policy integrity check failed. "
            f"Expected {expected}, got {actual}."
        )
    return actual


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


def _scorecard_context_notes(scorecard: Mapping[str, int | None]) -> list[str]:
    """Explain advanced scorecard conditions without changing the exact ranking."""
    bonus = _upper_bonus_context(scorecard)
    open_categories = [CATEGORY_LABELS[c] for c in CATEGORIES if scorecard.get(c) is None]
    notes: list[str] = []

    if len(open_categories) <= 2:
        labels = " and ".join(open_categories) if open_categories else "no categories"
        notes.append(
            f"True endgame: only {labels} remain open. Generic opening rules matter much less now; the exact hold is optimizing those specific destinations."
        )

    if scorecard.get("yahtzee") == 50:
        notes.append(
            "Yahtzee is already scored for 50, so another Yahtzee can carry the 100-point bonus and the forced-upper/Joker rules can materially change the value of matching dice."
        )

    if bonus["earned"]:
        notes.append(
            "The 35-point upper bonus is already secured. Upper-section dice no longer need extra protection just to defend the 63-point threshold."
        )
    elif not bonus["alive"]:
        notes.append(
            "The 35-point upper bonus is mathematically out of reach. The exact solver is no longer paying for bonus pressure that cannot be recovered."
        )

    if scorecard.get("chance") is None and len(open_categories) <= 3:
        notes.append(
            "Chance is one of very few remaining escape valves, so raw die total can matter more than it would on an open scorecard."
        )

    # Two notes are enough to teach the context without turning the report into a wall of text.
    return notes[:2]


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
        guaranteed = "25 points" if made == "Full House" else "guaranteed value"
        return (
            "Protect a made hand",
            f"The exact hold keeps the complete {made}. Banking {guaranteed} is worth more here than reopening dice for another reroll.",
            "When a scoring hand is already made, compare its guaranteed score with what the remaining scorecard can gain by reopening dice.",
        )

    if scorecard.get("yahtzee") == 50 and max_count >= 3:
        face = max(counts, key=counts.get)
        return (
            "Exploit the extra-Yahtzee window",
            f"The exact hold protects the {face}s because Yahtzee is already scored for 50. Another Yahtzee can add the 100-point bonus, and Joker/forced-upper rules make this matching core more valuable than it looks in an ordinary turn.",
            "After a 50-point Yahtzee, matching dice deserve a fresh evaluation: the extra-Yahtzee bonus and Joker rules can dramatically raise their future value.",
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
            if bonus["earned"]:
                context = "; the upper bonus is already secured, so the pair is being judged on the value of the open box and future scoring paths"
            elif bonus["alive"]:
                context = " and the 35-point upper bonus is still reachable"
            else:
                context = "; the upper bonus is no longer reachable, so the pair has to justify itself without that 35-point incentive"
            if bonus["earned"]:
                takeaway = "The upper bonus is already safe. Keep upper dice only when their open box or the remaining matching boxes still make them valuable."
            elif bonus["alive"]:
                takeaway = "When the upper bonus is still reachable, a pair that matches an open upper box can do two jobs: build that box and support matching hands."
            else:
                takeaway = "A dead upper bonus does not make upper dice worthless; it only removes the 35-point incentive. Keep them only when the boxes that remain still reward that number."
            return (
                f"Build the {CATEGORY_LABELS[upper]} box",
                f"The exact hold protects a pair of {face}s while the {CATEGORY_LABELS[upper]} box is open{context}.",
                takeaway,
            )
        return (
            "Keep the best matching base",
            f"The exact hold protects a pair of {face}s and rerolls the loose dice, preserving a clearer path to a stronger matching hand.",
            "If the matching upper box is closed, judge a pair by the lower-section boxes it can still reach—not just by the fact that two dice match.",
        )

    if len(hold) == 1:
        face = hold[0]
        upper = UPPER_BY_FACE[face]
        if _is_open(scorecard, upper):
            if bonus["earned"]:
                upper_context = "the upper bonus is already banked, so this is about the value of the remaining box rather than protecting 63"
            elif bonus["alive"]:
                upper_context = "the upper bonus is still reachable"
            else:
                upper_context = "the upper bonus is out of reach, so this die must earn its keep from the remaining scorecard alone"
            if bonus["earned"]:
                takeaway = "Once the upper bonus is secured, an upper die has to earn its place through the boxes that remain. Read the open boxes, not just the dice."
            elif bonus["alive"]:
                takeaway = "When the upper bonus is still reachable, one useful upper die can be worth protecting if it also keeps enough fresh dice for the rest of the board. Read the open boxes, not just the dice."
            else:
                takeaway = "When the upper bonus is dead, do not keep an upper die for 63. Keep it only if that die still helps the remaining boxes. Read the open boxes, not just the dice."
            return (
                "Let the scorecard choose the die",
                f"The exact solver keeps the {face} because {CATEGORY_LABELS[upper]} is still open and {upper_context}; the other dice are worth more as fresh rerolls in this scorecard state.",
                takeaway,
            )
        return (
            "Keep flexibility",
            f"The exact solver keeps only the {face}, which means the rest of this roll is worth more as fresh dice than as a partial pattern in the current scorecard.",
            "A lone die can be correct when keeping extra dice would lock you into a weak route. More fresh dice means more chances to find the boxes the scorecard still needs.",
        )

    if not hold:
        return (
            "Reset a weak structure",
            "The exact solver rerolls all five dice. In this scorecard state, none of the current fragments is valuable enough to justify reducing the number of fresh dice.",
            "Rerolling everything is not giving up; sometimes maximum flexibility has the highest long-run value.",
        )

    return (
        "Match the hold to the open boxes",
        "The exact hold keeps the dice that connect to the remaining scoring boxes and rerolls the pieces that do not add enough value.",
        "When no obvious pair, triple, or straight decides the play, compare which open boxes each hold can actually reach and how many fresh dice it leaves you.",
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
            if _is_open(scorecard, "full_house"):
                lines.append("You protected two pairs, giving you a direct Full House idea while keeping two matching bases.")
            else:
                lines.append("You protected two pairs, but Full House is already filled, so the hold has to earn its value through the matching boxes that remain.")
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



def _hold_intent(
    hold: Sequence[int],
    scorecard: Mapping[str, int | None],
) -> str:
    """Translate a hold into a cautious, player-facing description of its likely plan.

    We describe what the hold *does* rather than claiming to know what the player
    was thinking.  That keeps the teaching language personalized without
    pretending the app can read intent.
    """
    hold = canonical(hold)
    bonus = _upper_bonus_context(scorecard)

    if not hold:
        return "Your hold resets the roll and maximizes the number of fresh dice."

    made = _made_hand_name(hold, scorecard)
    if made:
        return f"Your hold locks in a made {made} instead of risking that completed structure."

    counts = {face: hold.count(face) for face in range(1, 7)}
    max_count = max(counts.values(), default=0)

    if max_count >= 4:
        face = max(counts, key=counts.get)
        return f"Your hold builds around four {face}s, a one-die-away matching core with major upside."

    if max_count == 3:
        face = max(counts, key=counts.get)
        return f"Your hold builds around three {face}s and uses the remaining reroll(s) to improve that matching core."

    pair_faces = [face for face, count in counts.items() if count == 2]
    if len(pair_faces) >= 2:
        if _is_open(scorecard, "full_house"):
            return f"Your hold protects two pairs ({pair_faces[0]}s and {pair_faces[1]}s), keeping a direct Full House path alive."
        return f"Your hold protects two pairs ({pair_faces[0]}s and {pair_faces[1]}s), preserving two matching-number directions."

    straight_name, straight_core = _straight_core(hold, scorecard)
    if straight_name and straight_core >= 4 and len(set(hold)) >= 4:
        return f"Your hold protects a four-number {straight_name} core and rerolls around the missing connection."
    if straight_name and straight_core == 3 and len(set(hold)) >= 3:
        return f"Your hold is a {straight_name} chase: it keeps three useful distinct numbers from a live straight pattern."

    if max_count == 2:
        face = max(counts, key=counts.get)
        upper = UPPER_BY_FACE[face]
        if _is_open(scorecard, upper):
            if bonus["earned"]:
                return f"Your hold targets the pair of {face}s and the open {CATEGORY_LABELS[upper]} box; the upper bonus is already secured."
            if bonus["alive"]:
                return f"Your hold targets the pair of {face}s, supporting the open {CATEGORY_LABELS[upper]} box while the upper bonus is still reachable."
            return f"Your hold targets the pair of {face}s and the open {CATEGORY_LABELS[upper]} box even though the upper bonus is no longer reachable."
        return f"Your hold uses the pair of {face}s as a matching-number base and rerolls the loose dice."

    if len(hold) == 1:
        face = hold[0]
        upper = UPPER_BY_FACE[face]
        if _is_open(scorecard, upper):
            return f"Your hold keeps the {face} as a clean target for the open {CATEGORY_LABELS[upper]} box while rerolling everything else."
        return f"Your hold keeps only the {face}, choosing flexibility over committing to a larger partial pattern."

    return "Your hold protects a mixed partial structure while leaving the remaining dice available to improve it."


def _personalized_adjustment(
    user_hold: Sequence[int],
    optimal_hold: Sequence[int],
    *,
    points_lost: float,
    is_optimal: bool,
) -> str:
    user = list(canonical(user_hold))
    optimal = list(canonical(optimal_hold))
    if is_optimal:
        return "No adjustment needed: your plan is already an exact best play in this position."

    add = optimal.copy()
    release = user.copy()
    for value in canonical(user_hold):
        if value in add:
            add.remove(value)
            release.remove(value)

    if points_lost <= 0.25:
        lead = "Tiny refinement"
    elif points_lost <= 0.75:
        lead = "Small refinement"
    elif points_lost <= 2.50:
        lead = "Upgrade the plan"
    elif points_lost <= 6.00:
        lead = "Clear adjustment"
    else:
        lead = "Major correction"

    if add and not release:
        return f"{lead}: keep your current idea, but also protect {_format_faces(add)}."
    if release and not add:
        return f"{lead}: keep the useful core, but release {_format_faces(release)} back into the reroll."
    if add and release:
        return f"{lead}: protect {_format_faces(add)} and release {_format_faces(release)}."
    return f"{lead}: use the exact hold instead of the current selection."


def _personalized_comparison(
    scorecard: Mapping[str, int | None],
    user_hold: Sequence[int],
    optimal_hold: Sequence[int],
    *,
    visible_reason: str,
    points_lost: float,
    is_optimal: bool,
) -> tuple[str, str, str]:
    """Return player-plan, best-plan, and adjustment sentences for v39."""
    user_idea = _hold_intent(user_hold, scorecard)
    if is_optimal:
        best_idea = "The exact solver agrees with that plan. " + visible_reason
    else:
        best_idea = f"The exact plan is {hold_text(optimal_hold)}. {visible_reason}"
    adjustment = _personalized_adjustment(
        user_hold, optimal_hold, points_lost=points_lost, is_optimal=is_optimal
    )
    return user_idea, best_idea, adjustment

def _open_category_keys(scorecard: Mapping[str, int | None]) -> list[str]:
    return [category for category in CATEGORIES if _is_open(scorecard, category)]


def _fresh_dice_text(count: int) -> str:
    count = int(count)
    return "1 fresh die" if count == 1 else f"{count} fresh dice"


def _rerolls_text(count: int) -> str:
    count = int(count)
    return "1 reroll" if count == 1 else f"{count} rerolls"


def _live_paths_for_hold(
    hold: Sequence[int],
    scorecard: Mapping[str, int | None],
    *,
    limit: int = 4,
) -> list[str]:
    """Name visible scoring destinations supported by a hold.

    This is teaching language only.  The exact DP table still determines value.
    We deliberately name only paths a player can see from the current dice and
    scorecard so explanations stay concrete instead of sounding like solver jargon.
    """
    held = canonical(hold)
    if not held:
        return []

    counts = {face: held.count(face) for face in range(1, 7)}
    max_count = max(counts.values(), default=0)
    paths: list[str] = []

    # Open upper boxes directly supported by held faces.
    for face in sorted(set(held), reverse=True):
        upper = UPPER_BY_FACE[face]
        if _is_open(scorecard, upper):
            paths.append(CATEGORY_LABELS[upper])

    # Matching-number destinations become meaningfully supported once a hold has
    # at least a pair.  A triple/four-of-kind makes these paths even more obvious.
    if max_count >= 2:
        for category in ("three_of_a_kind", "four_of_a_kind", "yahtzee"):
            if _is_open(scorecard, category):
                paths.append(CATEGORY_LABELS[category])
        pair_count = sum(1 for count in counts.values() if count >= 2)
        if _is_open(scorecard, "full_house") and (pair_count >= 2 or max_count >= 3):
            paths.append("Full House")

    straight_name, straight_core = _straight_core(held, scorecard)
    if straight_name and straight_core >= 3 and len(set(held)) >= 3:
        paths.append(straight_name)

    # Chance is most useful to name when the held dice are already a meaningful
    # raw-total base rather than a low singleton.
    if _is_open(scorecard, "chance") and (sum(held) >= 10 or max(held) >= 5 and len(held) >= 2):
        paths.append("Chance")

    # Preserve order while removing duplicates.
    unique: list[str] = []
    for item in paths:
        if item not in unique:
            unique.append(item)
    return unique[:limit]


def _simple_why_with_family(
    scorecard: Mapping[str, int | None],
    user_hold: Sequence[int],
    optimal_hold: Sequence[int],
    *,
    roll_number: int,
    is_optimal: bool,
    visible_reason: str,
    points_lost: float | None = None,
) -> tuple[str, str]:
    """Return (family, explanation) for concise player-facing coaching.

    Every explanation follows the same teaching idea:
      1) acknowledge the visible plan,
      2) connect the exact hold to the boxes that are actually live,
      3) explain the reroll/flexibility tradeoff in plain language.

    The family tag is diagnostic/test metadata only; it never changes the exact
    strategy ranking.
    """
    user = canonical(user_hold)
    optimal = canonical(optimal_hold)
    bonus = _upper_bonus_context(scorecard)
    open_keys = _open_category_keys(scorecard)
    open_labels = [CATEGORY_LABELS[c] for c in open_keys]
    rerolls = 3 - roll_number
    fresh = 5 - len(optimal)

    user_counts = {face: user.count(face) for face in range(1, 7)}
    optimal_counts = {face: optimal.count(face) for face in range(1, 7)}
    user_pair_faces = [face for face, count in user_counts.items() if count >= 2]
    optimal_pair_faces = [face for face, count in optimal_counts.items() if count >= 2]
    optimal_distinct = sorted(set(optimal))
    optimal_max_count = max(optimal_counts.values(), default=0)

    if is_optimal:
        return "optimal", f"You found the exact best hold. {visible_reason}"

    # Special Yahtzee/Joker state: ordinary matching-dice rules change after a
    # 50-point Yahtzee because another Yahtzee is worth a 100-point bonus.
    if scorecard.get("yahtzee") == 50 and optimal_max_count >= 3:
        face = max(optimal_counts, key=optimal_counts.get)
        return (
            "extra_yahtzee_joker",
            f"Yahtzee is already scored for 50, so another Yahtzee can add a 100-point bonus and can activate the forced-upper/Joker scoring rules. "
            f"Keeping the {face}s protects that special upside, which makes this matching core worth more than it would in a normal turn.",
        )

    user_made = _made_hand_name(user, scorecard)
    optimal_made = _made_hand_name(optimal, scorecard)
    if optimal_made:
        bank_value = "25-point" if optimal_made == "Full House" else "made"
        return (
            "protect_made_hand",
            f"You already have a {bank_value} {optimal_made}. Keeping all five banks that guaranteed score; "
            "the exact math says the open boxes do not pay enough to justify breaking it here.",
        )
    if user_made and len(user) == 5:
        paths = _live_paths_for_hold(optimal, scorecard, limit=3)
        path_text = _join_paths(paths) if paths else "the remaining open boxes"
        bank_text = "Banking the guaranteed 25" if user_made == "Full House" else f"Keeping the made {user_made}"
        return (
            "break_made_hand",
            f"{bank_text} is a reasonable safety play, but made does not automatically mean keep. "
            f"With {rerolls} reroll{'s' if rerolls != 1 else ''} left, the exact hold reopens {_fresh_dice_text(fresh)} because {path_text} offer more full-game value from this scorecard.",
        )

    # True endgame: name the only destinations left before discussing generic
    # pattern rules.  This is where players most need the scorecard connection.
    if len(open_keys) <= 2:
        target_text = _join_paths(open_labels) if open_labels else "no remaining boxes"
        paths = _live_paths_for_hold(optimal, scorecard, limit=2)
        path_text = _join_paths(paths) if paths else target_text
        return (
            "true_endgame",
            f"Only {target_text} remain open, so normal opening rules matter much less. "
            f"The exact hold is built specifically for {path_text}; dice that do not help those last boxes are better rerolled.",
        )

    # Dead-bonus late-game trap: a lower pair can look like the natural 3K/4K
    # chase, but a higher open upper die can serve every remaining matching box.
    if len(optimal) == 1 and any(user_counts[face] == 2 for face in user_pair_faces) and not bonus["earned"] and not bonus["alive"]:
        face = optimal[0]
        upper = UPPER_BY_FACE[face]
        pair_face = max(face for face in user_pair_faces if user_counts[face] == 2)
        matching_paths = [
            CATEGORY_LABELS[c]
            for c in ("three_of_a_kind", "four_of_a_kind", "yahtzee")
            if _is_open(scorecard, c)
        ]
        if _is_open(scorecard, upper) and face > pair_face and matching_paths:
            path_text = _join_paths([CATEGORY_LABELS[upper], *matching_paths])
            return (
                "bonus_dead_high_die",
                f"The 35-point upper bonus is already out of reach, so keeping the {face} is not a bonus chase. "
                f"{path_text} are still live, and the {face} can help all of them while giving the matching-number boxes a higher scoring base than the pair of {pair_face}s. "
                f"With {_rerolls_text(rerolls)} left, keeping one {face} and rolling {_fresh_dice_text(fresh)} is worth more than committing early to the lower pair.",
            )

    # Two-pair player hold: recognize the Full House idea before generic matching-dice language.
    # This prevents a 5,5,6,6 hold from being described as a 3K/4K/Yahtzee chase.
    user_exact_pair_faces = [face for face, count in user_counts.items() if count == 2]
    if len(user_exact_pair_faces) >= 2 and _is_open(scorecard, "full_house"):
        pair_text = _join_paths([f"{face}s" for face in sorted(user_exact_pair_faces)[:2]])
        best_paths = _live_paths_for_hold(optimal, scorecard, limit=4)
        best_text = _join_paths(best_paths) if best_paths else "the remaining open boxes"
        if len(user) == 4:
            return (
                "two_pair_full_house_tradeoff",
                f"Keeping both pairs ({pair_text}) is a natural Full House chase: one fresh die can finish it. "
                f"But it locks four dice. The exact hold, {hold_text(optimal)}, leaves {_fresh_dice_text(fresh)} and keeps {best_text} available. "
                "On this scorecard, those extra fresh dice are worth more.",
            )
        if len(user) == 5:
            return (
                "two_pair_no_reroll",
                f"Your hold contains two pairs, but keeping all five dice leaves no fresh die to complete the Full House. "
                f"The exact hold, {hold_text(optimal)}, reopens {_fresh_dice_text(fresh)} so the remaining scorecard can still improve.",
            )

    # Common human trap: keep a closed-number pair even though the remaining
    # board strongly rewards distinct straight anchors.
    if (
        roll_number == 2
        and len(user_pair_faces) == 1
        and len(optimal) >= 2
        and len(optimal_distinct) == len(optimal)
        and (_is_open(scorecard, "small_straight") or _is_open(scorecard, "large_straight"))
    ):
        face = user_pair_faces[0]
        upper = UPPER_BY_FACE[face]
        pair_support_open = [
            category for category in (upper, "three_of_a_kind", "full_house")
            if _is_open(scorecard, category)
        ]
        straight_names = [
            CATEGORY_LABELS[category]
            for category in ("small_straight", "large_straight")
            if _is_open(scorecard, category)
        ]
        matching_upside = [
            CATEGORY_LABELS[category]
            for category in ("four_of_a_kind", "yahtzee")
            if _is_open(scorecard, category)
        ]
        if not pair_support_open and straight_names:
            closed_bits = [CATEGORY_LABELS[upper], "Three of a Kind", "Full House"]
            if not _is_open(scorecard, "chance"):
                closed_bits.append("Chance")
            closed_text = ", ".join(closed_bits[:-1]) + f", and {closed_bits[-1]}" if len(closed_bits) > 1 else closed_bits[0]
            matching_text = _join_paths(matching_upside) if matching_upside else "a narrow matching-dice payoff"
            straight_text = _join_paths(straight_names)
            straight_core = max(
                (_straight_core(optimal, scorecard)[1],),
                default=0,
            )
            if straight_core >= 3:
                exact_reason = (
                    f"Keeping {_format_faces(optimal_distinct)} instead preserves a {straight_core}-number straight core for {straight_text} "
                    f"with {_fresh_dice_text(fresh)}."
                )
            else:
                exact_reason = (
                    f"Keeping {_format_faces(optimal_distinct)} instead gives you useful anchors for {straight_text} "
                    f"with {_fresh_dice_text(fresh)}."
                )
            return (
                "pair_vs_straight",
                f"Your pair of {face}s looks strong, but {closed_text} are already filled, so that pair mostly chases {matching_text}. "
                f"{exact_reason}",
            )

    # If the exact answer is a visible straight core, say exactly what the
    # connected dice are doing instead of using generic "flexibility" language.
    straight_name, straight_core = _straight_core(optimal, scorecard)
    if straight_name and straight_core >= 3 and len(set(optimal)) >= 3:
        if user_pair_faces:
            return (
                "straight_over_matching",
                f"Your hold builds around matching dice, but the open {straight_name} box needs distinct connected numbers. "
                f"The exact hold keeps {straight_core} useful straight numbers and rerolls the pieces that do less for that path.",
            )
        return (
            "straight_structure",
            f"The exact hold keeps {straight_core} distinct numbers that already fit the open {straight_name} path. "
            f"That leaves {_fresh_dice_text(fresh)} to find the missing connection instead of restarting the straight from scratch.",
        )

    # Two pairs with Full House open are easy to teach concretely: both matching
    # directions matter, not just the higher-looking pair.
    if len(optimal_pair_faces) >= 2 and _is_open(scorecard, "full_house"):
        faces = sorted(optimal_pair_faces)[:2]
        return (
            "two_pair_full_house",
            f"Both pairs matter because Full House is still open. Keeping the {faces[0]}s and {faces[1]}s preserves two different ways for the last die to complete the hand instead of throwing away half of that structure.",
        )

    # Four matching dice are a premium matching core. Mention Yahtzee only when
    # Yahtzee (or the extra-Yahtzee bonus state) is actually relevant.
    if optimal_max_count >= 4:
        face = max(optimal_counts, key=optimal_counts.get)
        paths = _live_paths_for_hold(optimal, scorecard, limit=4)
        path_text = _join_paths(paths) if paths else "the live matching boxes"
        if _is_open(scorecard, "yahtzee"):
            lead = f"Four {face}s are one matching die from Yahtzee"
        elif scorecard.get("yahtzee") == 50:
            lead = f"Four {face}s are one matching die from another Yahtzee and its 100-point bonus"
        else:
            lead = f"Four {face}s are already a powerful matching core"
        return (
            "four_matching",
            f"{lead} and also support {path_text}. "
            f"Breaking that four-die core would give up a much stronger structure than the loose dice can replace.",
        )

    # Triples deserve a similarly concrete explanation.
    if optimal_max_count == 3:
        face = max(optimal_counts, key=optimal_counts.get)
        paths = _live_paths_for_hold(optimal, scorecard, limit=4)
        path_text = _join_paths(paths) if paths else "the live matching boxes"
        return (
            "triple_matching",
            f"Three {face}s already give you a strong matching base for {path_text}. "
            f"Keeping the triple leaves {_fresh_dice_text(fresh)} to improve it instead of rebuilding that structure from the beginning.",
        )

    # A pair tied directly to an open upper box should explain the upper-bonus
    # status explicitly so players know whether 63 is actually part of the value.
    if len(optimal_pair_faces) == 1:
        face = optimal_pair_faces[0]
        upper = UPPER_BY_FACE[face]
        if _is_open(scorecard, upper):
            extra_paths = [
                CATEGORY_LABELS[c]
                for c in ("three_of_a_kind", "four_of_a_kind", "yahtzee")
                if _is_open(scorecard, c)
            ]
            path_text = _join_paths([CATEGORY_LABELS[upper], *extra_paths[:2]])
            if bonus["earned"]:
                bonus_line = "The 35-point upper bonus is already secured, so this is not about protecting 63."
                family = "bonus_secured_pair"
            elif bonus["alive"]:
                bonus_line = f"The 35-point upper bonus is still in play; you need {bonus['needed']} more points from the remaining upper boxes."
                family = "bonus_alive_pair"
            else:
                bonus_line = "The 35-point upper bonus is out of reach, so the pair has to be valuable without any bonus help."
                family = "bonus_dead_pair"
            return (
                family,
                f"{bonus_line} The pair of {face}s still supports {path_text}, which is why it beats the looser alternatives on this scorecard.",
            )

    # Chance timing: when the scorecard is cramped and Chance is one of very few
    # escape valves, high dice can be worth holding for their raw point value.
    if _is_open(scorecard, "chance") and len(open_keys) <= 4 and optimal and sum(optimal) >= 10:
        paths = _live_paths_for_hold(optimal, scorecard, limit=3)
        path_text = _join_paths(paths) if paths else "Chance"
        return (
            "chance_timing",
            f"Chance is one of only {len(open_keys)} boxes left, so raw die total matters more than it does on an open board. "
            f"Keeping {_format_faces(optimal)} starts with {sum(optimal)} points of useful dice while still supporting {path_text}.",
        )

    # A singleton exact hold is often a scorecard/bonus-state lesson.
    if len(optimal) == 1:
        face = optimal[0]
        upper = UPPER_BY_FACE[face]
        if _is_open(scorecard, upper):
            paths = _live_paths_for_hold(optimal, scorecard, limit=3)
            path_text = _join_paths(paths) if paths else CATEGORY_LABELS[upper]
            if bonus["earned"]:
                context = "The upper bonus is already secured, so this die is being kept for the boxes it can still score—not to protect 63."
                family = "bonus_secured_singleton"
            elif bonus["alive"]:
                context = f"The upper bonus is still in play, and you need {bonus['needed']} more points from the remaining upper boxes, so {CATEGORY_LABELS[upper]} still matters."
                family = "bonus_alive_singleton"
            else:
                context = "The upper bonus is already out of reach, so this die must justify itself through the boxes that remain."
                family = "bonus_dead_singleton"
            return (
                family,
                f"{context} Keeping the {face} supports {path_text} while giving you {_fresh_dice_text(fresh)} to search for a stronger finish.",
            )

    # Early/open-board flexibility: explain why *not* locking weak fragments is
    # valuable when many categories are still available.
    if len(open_keys) >= 8 and len(optimal) <= 1:
        keep_text = hold_text(optimal)
        return (
            "open_board_flexibility",
            f"The board is still wide open, so a weak partial pattern is not worth locking in yet. "
            f"The exact play is {keep_text}, leaving {_fresh_dice_text(fresh)} and more ways to grow into the many categories that are still available.",
        )

    if not optimal:
        return (
            "reroll_all",
            f"None of the current dice creates enough value for the boxes that remain. Rerolling all five gives you the maximum number of fresh dice instead of spending a reroll protecting a weak fragment.",
        )

    # Generic fallback: still name the player's visible route and the exact hold's
    # visible destinations.  Near-ties need especially careful wording: when the
    # solver edge is only a few hundredths, describe the small scorecard tradeoff
    # instead of making a strong human hold sound strategically wrong.
    user_paths = _live_paths_for_hold(user, scorecard, limit=3)
    best_paths = _live_paths_for_hold(optimal, scorecard, limit=3)
    user_text = _join_paths(user_paths) if user_paths else "a narrower partial pattern"
    best_text = _join_paths(best_paths) if best_paths else "more of the boxes that are still open"

    if points_lost is not None and 0.0 < float(points_lost) <= 0.25:
        added = list(optimal)
        released = list(user)
        for value in user:
            if value in added:
                added.remove(value)
                released.remove(value)

        # Chance is often technically supported but is rarely the clearest reason
        # to protect one extra low/mid die. Prefer the concrete scorecard boxes
        # first, and name Chance only when it is truly the only visible route.
        concrete_paths = [path for path in best_paths if path != "Chance"] or best_paths
        path_text = _join_paths(concrete_paths[:2]) if concrete_paths else "remaining scorecard"
        box_word = "box" if len(concrete_paths[:2]) == 1 else "boxes"

        if added and not released:
            extra_fresh = len(optimal) - len(user)
            tradeoff = (
                f"That tiny scorecard edge is just barely worth giving up {extra_fresh} fresh reroll "
                f"{'die' if extra_fresh == 1 else 'dice'}."
            ) if extra_fresh > 0 else "That tiny scorecard edge is just enough to separate the two holds."
            return (
                "scorecard_fit_close",
                f"Your hold was already a strong idea. The exact hold, {hold_text(optimal)}, also adds {_format_faces(added)} because the open {path_text} {box_word} still {'has' if box_word == 'box' else 'have'} scoring value. "
                f"{tradeoff} Your hold is only {float(points_lost):.2f} Points Lost.",
            )

        return (
            "scorecard_fit_close",
            f"Your hold was already a strong idea. The exact hold, {hold_text(optimal)}, fits the open {path_text} {box_word} just a little better while keeping a similar reroll plan. "
            f"This is a fine scorecard distinction—only {float(points_lost):.2f} Points Lost.",
        )

    return (
        "scorecard_fit",
        f"Your hold is mainly aiming at {user_text}. The exact hold, {hold_text(optimal)}, supports {best_text} while leaving {_fresh_dice_text(fresh)} to reroll. "
        "On this scorecard, those remaining routes are worth more than the pattern you chose.",
    )


def _simple_why(
    scorecard: Mapping[str, int | None],
    user_hold: Sequence[int],
    optimal_hold: Sequence[int],
    *,
    roll_number: int,
    is_optimal: bool,
    visible_reason: str,
) -> str:
    """Give one short, concrete explanation of why the exact hold fits this board."""
    _, explanation = _simple_why_with_family(
        scorecard,
        user_hold,
        optimal_hold,
        roll_number=roll_number,
        is_optimal=is_optimal,
        visible_reason=visible_reason,
    )
    return explanation

def _clear_takeaway_for_family(family: str, fallback: str) -> str:
    """Keep the reusable 'Remember' line short, concrete, and consistent."""
    lessons = {
        "extra_yahtzee_joker": "After a 50-point Yahtzee, matching dice get extra value because another Yahtzee can add 100 points and may activate forced-upper/Joker scoring rules.",
        "protect_made_hand": "A made hand gives guaranteed value. Protect it unless the remaining scorecard gives a clear reason to gamble for more.",
        "break_made_hand": "Made does not always mean keep. With rerolls left, compare guaranteed points with the upside in the boxes that are still open.",
        "true_endgame": "Near the end, forget generic opening rules and optimize the boxes that are actually left.",
        "bonus_dead_high_die": "When the upper bonus is dead, stop paying for 63—but an upper die can still be right if it also helps the remaining boxes. Read the open boxes, not just the dice.",
        "bonus_dead_pair": "When the upper bonus is dead, a pair must earn its value from the boxes that remain; the lost 35-point bonus should not influence the hold.",
        "bonus_dead_singleton": "When the upper bonus is dead, do not keep an upper die for 63. Keep it only if that die still helps the remaining boxes. Read the open boxes, not just the dice.",
        "bonus_alive_pair": "When the upper bonus is still in play, a pair that matches an open upper box can do two jobs: build the bonus and support matching hands.",
        "bonus_alive_singleton": "When the upper bonus is still in play, one useful upper die can matter—but only if keeping it still leaves enough reroll flexibility. Read the open boxes, not just the dice.",
        "bonus_secured_pair": "Once the upper bonus is secured, judge an upper pair only by the boxes that remain; there is no extra need to protect 63.",
        "bonus_secured_singleton": "Once the upper bonus is secured, an upper die has to earn its place through the boxes that remain. Read the open boxes, not just the dice.",
        "pair_vs_straight": "Straights need distinct connected numbers. A pair is only worth protecting when the remaining matching boxes reward it more.",
        "straight_over_matching": "When a straight box is live, distinct connected numbers can be worth more than a pair or triple that looks stronger at first glance.",
        "straight_structure": "A connected straight core is a premium structure. Protect it and reroll the dice that do not help complete it.",
        "two_pair_full_house": "With Full House open, two pairs create a direct one-die finish. Do not throw away one pair without a strong scorecard reason.",
        "two_pair_full_house_tradeoff": "Two pairs are a strong Full House start, but four locked dice leave only one fresh die. Compare that direct finish with the value of reopening more dice for the rest of the scorecard.",
        "two_pair_no_reroll": "Two pairs only chase a Full House if you leave a die to reroll. Keeping all five freezes the hand instead of giving the pairs a chance to connect.",
        "four_matching": "Four matching dice are a premium matching core. Protect them unless the remaining scorecard gives a very strong reason to break the structure.",
        "triple_matching": "A triple already has scoring strength and still has room to grow. Keep it when the remaining matching boxes reward that number.",
        "chance_timing": "When Chance is one of only a few boxes left, raw die total matters more than it does on an open scorecard.",
        "open_board_flexibility": "Early on, do not lock weak fragments just because they look like a pattern. Fresh dice keep more scoring routes alive.",
        "reroll_all": "Rerolling everything is correct when none of the current dice earns its place on the remaining scorecard.",
        "scorecard_fit": "When no obvious pattern decides the play, compare which open boxes each hold actually supports and how many fresh dice it leaves.",
        "scorecard_fit_close": "When two holds are this close, use the open scorecard boxes to find the small edge.",
    }
    return lessons.get(family, fallback)

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
    context_notes = _scorecard_context_notes(scorecard)
    difference = _hold_difference(user_hold, display_optimal)
    closeness = _closeness_line(points_lost, is_optimal)
    user_idea, best_idea, adjustment = _personalized_comparison(
        scorecard,
        user_hold,
        display_optimal,
        visible_reason=visible_reason,
        points_lost=points_lost,
        is_optimal=is_optimal,
    )
    coaching_family, simple_why = _simple_why_with_family(
        scorecard,
        user_hold,
        display_optimal,
        roll_number=roll_number,
        is_optimal=is_optimal,
        visible_reason=visible_reason,
        points_lost=points_lost,
    )
    takeaway = _clear_takeaway_for_family(coaching_family, takeaway)

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
        "Your idea vs. best idea:",
        f"- Your idea: {user_idea}",
        f"- Best idea: {best_idea}",
        f"- Adjustment: {adjustment}",
        "",
        "Simple why:",
        f"- {simple_why}",
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

    for note in context_notes:
        report.append(f"- Scorecard context: {note}")

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
        "teaching_takeaway": takeaway,
        "context_notes": " | ".join(context_notes),
        "user_idea": user_idea,
        "best_idea": best_idea,
        "adjustment": adjustment,
        "simple_why": simple_why,
        "coaching_family": coaching_family,
        "lookup_ms": (perf_counter() - started) * 1000.0,
    }
    return "\n".join(report), metadata


def build_exact_live_report(
    policy: ExactPolicyTable,
    *,
    dice: Sequence[int],
    scorecard: Mapping[str, int | None],
    user_hold: Sequence[int],
    roll_number: int,
) -> tuple[str, dict]:
    """Exact-only player-facing report router. Never substitutes heuristic advice."""
    try:
        return build_exact_report(
            policy,
            dice=dice,
            scorecard=scorecard,
            user_hold=user_hold,
            roll_number=roll_number,
        )
    except Exception as exc:
        return "", {
            "source": "exact_unavailable",
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_exact_live_report_from_loader(
    policy_loader,
    *,
    dice: Sequence[int],
    scorecard: Mapping[str, int | None],
    user_hold: Sequence[int],
    roll_number: int,
) -> tuple[str, dict]:
    """Exact-only router that fails closed if the policy cannot load."""
    try:
        policy = policy_loader()
    except Exception as exc:
        return "", {
            "source": "exact_unavailable",
            "available": False,
            "error": f"policy_load_error: {type(exc).__name__}: {exc}",
        }
    return build_exact_live_report(
        policy,
        dice=dice,
        scorecard=scorecard,
        user_hold=user_hold,
        roll_number=roll_number,
    )


def build_live_report_with_fallback(
    policy: ExactPolicyTable,
    *,
    dice: Sequence[int],
    scorecard: Mapping[str, int | None],
    user_hold: Sequence[int],
    roll_number: int,
    legacy_report_factory,
) -> tuple[str, dict]:
    """Legacy compatibility router. The player-facing app does not call this.

    Kept only so older regression tooling can compare historic behavior.
    New Daily/Practice code must use build_exact_live_report instead.
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
    """Legacy compatibility loader. The player-facing app does not call this."""
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
