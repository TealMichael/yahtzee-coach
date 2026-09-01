"""Optional, read-only learning after the official Daily Ten.

No database, scoring, selection, random-state, or persistence side effects.
Counterfactuals use only states supported by the unchanged exact policy.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import math

from exact_mode import (
    CATEGORIES, TIE_TOLERANCE, canonical, hold_text, scorecard_state_key,
    build_exact_report, _instructive_optimal_alternative,
)

LABELS = {key: key.replace('_', ' ').title() for key in CATEGORIES}
LABELS.update(three_of_a_kind="Three of a Kind", four_of_a_kind="Four of a Kind")
SPECIAL_FAMILIES = {
    "true_endgame_straight_flexibility", "two_pair_full_house_tradeoff",
    "pair_vs_straight", "protect_made_hand", "break_made_hand",
    "bonus_dead_high_die", "extra_yahtzee_joker",
}


def select_spotlight(answers, *, completed=False, policy=None, seed=""):
    """Pick one meaningful personal review, without running additional solves.

    A practical tie alone is not a lesson. Strong, specific optimal-answer
    comparisons are eligible and receive a small preference over corrections.
    """
    if not completed or len(answers) != 10:
        return None
    if [a.get("challenge", {}).get("daily_number") for a in answers] != list(range(1, 11)):
        return None
    dates = {a.get("challenge", {}).get("daily_date") for a in answers}
    if len(dates) != 1 or not next(iter(dates)):
        return None
    candidates = []
    for index, answer in enumerate(answers):
        record = answer.get("solver_record", {})
        if record.get("source") != "exact":
            return None
        loss = float(record.get("points_lost", 0) or 0)
        why = str(record.get("simple_why", "")).strip()
        kind = str(record.get("instructive_alternative_kind", ""))
        family = str(record.get("coaching_family", ""))
        exact = loss <= TIE_TOLERANCE
        gap = float(record.get("instructive_alternative_gap") or 0) if exact else loss
        if not math.isfinite(gap) or not math.isfinite(loss) or gap <= .10 or not why:
            continue
        specific = kind in {"two_pair_full_house", "made_full_house"} or family in SPECIAL_FAMILIES
        # Generic lookahead prose alone doesn't justify a featured lesson.
        if not specific and "%" not in why:
            continue
        if "No single visible" in why or "no single practical" in why.lower():
            continue
        score = (4 if specific else 1) + (1 if exact else 0) + (1 if .25 <= gap <= 4 else 0)
        if loss > 6:
            score -= 2  # Do not simply pick the largest miss.
        challenge = answer["challenge"]
        counts = sorted(Counter(challenge["dice"]).values(), reverse=True)
        if counts == [3, 2] and challenge["scorecard"].get("full_house") is None:
            title = "Bank the Full House—or break it?"
        elif counts == [2, 2, 1] and challenge["scorecard"].get("full_house") is None:
            title = "Are both pairs worth keeping?"
        elif "straight" in family or challenge.get("skill_tag") == "Straight Structure":
            title = "Which dice really help the straight?"
        elif "bonus" in family:
            title = "How much is the upper bonus worth here?"
        elif "joker" in family:
            title = "When another Yahtzee changes the plan"
        else:
            title = "Two good-looking plans. One scorecard."
        candidates.append((score, -index, {
            "index": index, "number": index + 1, "title": title,
            "status": "You found the best hold. Here's the interesting tradeoff." if exact
                      else "A decision worth another look—not just your biggest miss.",
        }))
    if not candidates:
        return None
    ranked = sorted(candidates, key=lambda item: item[:2], reverse=True)
    if policy is not None:
        # Preflight only tiny table lookups, once after completion. Don't trade
        # a strong lesson for a generic one just to force a follow-up.
        for score, _, candidate in ranked:
            if score < ranked[0][0] - 2:
                break
            variation = build_what_if(policy, answers[candidate["index"]]["challenge"], seed=seed)
            if variation is not None:
                return {**candidate, "variant": variation}
    return {**ranked[0][2], "variant": None}


def _single_box_cards(scorecard):
    """Legal one-box edits. Never alter Yahtzee/Joker eligibility.

    An upper-score adjustment preserves the category's filled status. Opening
    or scratching a category is explicitly a hypothetical scorecard, not a
    suggestion to rewrite a real completed score. Avoid forced-Yahtzee upper
    scores while that category remains open, matching the app's realism rule.
    """
    original_key = scorecard_state_key(scorecard)
    seen = set()
    for i, category in enumerate(CATEGORIES):
        if category == "yahtzee":
            continue
        old = scorecard[category]
        if old is None:
            values = [0]
        else:
            values = [None]
            if i < 6:
                max_count = 4 if scorecard.get("yahtzee") is None else 5
                values += [n * (i + 1) for n in range(max_count + 1)]
        for new in values:
            if new == old:
                continue
            card = dict(scorecard)
            card[category] = new
            if not any(value is None for value in card.values()):
                continue
            key = scorecard_state_key(card)
            if key == original_key or key in seen:
                continue
            seen.add(key)
            yield category, old, new, card


def _by_hold(results):
    return {canonical(row["hold"]): float(row["strategy_value"]) for row in results}


def build_what_if(policy, challenge, *, seed=""):
    """Return at most one mathematically verified variation, or no lesson.

    The same dice and roll are kept. A changed winner must beat the original
    best by >= .25 and have been > .10 behind originally. An unchanged winner
    must have a useful alternative whose margin changes by >= .25. A stable
    hash mixes those outcomes when both exist; the player isn't told which.
    No fabricated EV decomposition or across-scorecard absolute comparison.
    """
    dice = canonical(challenge["dice"])
    card = challenge["scorecard"]
    roll = int(challenge["roll_number"])
    original = policy.analyze(card, dice, roll)
    original_values = _by_hold(original)
    reference = canonical(original[0]["hold"])
    original_best = original_values[reference]
    alternative, _ = _instructive_optimal_alternative(dice, card, reference, original)
    stable_alternative = canonical(alternative["hold"]) if alternative else None
    preferred_changed = int(sha256(str(seed).encode()).hexdigest()[:8], 16) % 2 == 0
    candidates = []
    for category, old, new, variant_card in _single_box_cards(card):
        if policy.state_index(variant_card) is None:
            continue
        rows = policy.analyze(variant_card, dice, roll)
        values = _by_hold(rows)
        new_best = float(rows[0]["strategy_value"])
        reference_loss = max(0., new_best - values[reference])
        if reference_loss > TIE_TOLERANCE:
            comparison = canonical(rows[0]["hold"])
            before_margin = original_best - original_values[comparison]
            after_margin = values[reference] - values[comparison]
            if reference_loss < .25 or before_margin <= .10:
                continue
            changed = True
        else:
            comparison = stable_alternative
            if comparison is None:
                continue
            before_margin = original_best - original_values[comparison]
            after_margin = values[reference] - values[comparison]
            if not .10 < before_margin <= 5 or after_margin <= .10:
                continue
            if abs(after_margin - before_margin) < .25:
                continue
            changed = False
        # Prefer an instructive margin, not extreme changes or microscopic ties.
        merit = (3 if changed == preferred_changed else 0)
        merit += 2 if .25 <= abs(after_margin) <= 4 else 0
        merit += 1 if old is not None and new is not None else 0
        merit += min(abs(after_margin - before_margin), 3) / 10
        identity = f"{scorecard_state_key(card)}|{dice}|{roll}|{category}|{old}|{new}"
        variant = {
            "id": sha256(identity.encode()).hexdigest()[:16],
            "dice": list(dice), "roll_number": roll, "scorecard": variant_card,
            "original_scorecard": dict(card),
            "category": category, "old": old, "new": new,
            "change": f"{LABELS[category]}: {'open' if old is None else old} → {'open' if new is None else new}",
            "reference_hold": list(reference), "comparison_hold": list(comparison),
            "before_margin": before_margin, "after_margin": after_margin,
            "answer_changes": changed,
        }
        candidates.append((merit, variant))
    if not candidates:
        return None
    return deepcopy(max(candidates, key=lambda item: item[0])[1])


def evaluate_what_if(policy, variant, user_hold):
    """Unscored feedback; never construct or save an official Daily record."""
    _, meta = build_exact_report(
        policy, dice=variant["dice"], scorecard=variant["scorecard"],
        user_hold=user_hold, roll_number=variant["roll_number"],
    )
    # Recompute both sides at reveal time; do not trust cached presentation data.
    before = _by_hold(policy.analyze(variant["original_scorecard"], variant["dice"], variant["roll_number"]))
    after = _by_hold(policy.analyze(variant["scorecard"], variant["dice"], variant["roll_number"]))
    ref, alt = canonical(variant["reference_hold"]), canonical(variant["comparison_hold"])
    before_margin, after_margin = before[ref] - before[alt], after[ref] - after[alt]
    best_value = max(after.values())
    changed = best_value - after[ref] > TIE_TOLERANCE
    comparison_rows = []
    for label, margin in (("Original scorecard", before_margin), ("Changed scorecard", after_margin)):
        leader, other = (ref, alt) if margin >= 0 else (alt, ref)
        comparison_rows.append({
            "Scorecard": label, "Between these two holds": hold_text(leader),
            "Expected-point edge": f"{abs(margin):.2f}",
        })
    category = variant["category"]
    if variant["old"] is not None and variant["new"] is not None:
        old_total = sum(variant["original_scorecard"][c] or 0 for c in CATEGORIES[:6])
        new_total = sum(variant["scorecard"][c] or 0 for c in CATEGORIES[:6])
        context = (f"{LABELS[category]} stays filled. Changing that earlier score changes the upper-bonus position; "
                   f"the upper subtotal moves from {old_total} to {new_total}. The open boxes are identical.")
    else:
        action = "available" if variant["new"] is None else "unavailable"
        context = (f"{LABELS[category]} is now {action}. That changes both the scoring options "
                   "and how many turns remain—not the probabilities on a given reroll.")
    leader, other = (ref, alt) if after_margin >= 0 else (alt, ref)
    lesson = (f"Originally, {hold_text(ref)} led {hold_text(alt)} by {before_margin:.2f} expected points. "
              f"On the changed card, {hold_text(leader)} leads {hold_text(other)} by {abs(after_margin):.2f}.")
    return {
        "heading": "The best hold changes." if changed else "The original best hold still works.",
        "choice_feedback": "You found a best hold." if meta["points_lost"] <= TIE_TOLERANCE
            else "Your choice is essentially tied." if meta["points_lost"] <= .10
            else f"The model prefers {meta['optimal_hold']} on this scorecard.",
        "why": meta["simple_why"], "rank_context": meta.get("rank_context", ""),
        "comparison_card": meta.get("comparison_card"),
        "context": context, "lesson": lesson,
        "comparison_rows": comparison_rows,
        "comparison_label": f"{hold_text(ref)} versus {hold_text(alt)}",
        "note": "Edges compare these two holds within each scorecard. They are expected remaining-game points, not hand-completion probabilities or guaranteed gains.",
        "points_lost": float(meta["points_lost"]), "optimal_hold": meta["optimal_hold"],
    }


def variety_snapshot(challenges):
    """Offline audit, not a new quota or a mutation of the shared Daily."""
    return {
        "families": dict(Counter(c["skill_tag"] for c in challenges)),
        "rolls": dict(Counter(c["roll_number"] for c in challenges)),
        "stages": dict(Counter(c["stage"] for c in challenges)),
        "bank_break": [c.get("bank_break_outcome") for c in challenges if c.get("bank_break_outcome")],
        "unique_ids": len({c["challenge_id"] for c in challenges}),
    }
