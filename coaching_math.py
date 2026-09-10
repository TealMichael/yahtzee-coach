"""Explanatory calculations only. Never supplies rankings or gameplay values."""
from collections import Counter
from functools import lru_cache


@lru_cache(maxsize=2048)
def immediate_points(hold, open_categories):
    """One final reroll; choose the highest raw score in an open box.

    Excludes upper/extra-Yahtzee bonuses and future value. Callers must not use
    this ordinary-rules illustration for a live extra-Yahtzee scorecard.
    """
    from exact_mode import _evidence_reroll_outcomes, _evidence_category_result
    return sum(
        count * max(_evidence_category_result(dice, category)[1] for category in open_categories)
        for dice, count in _evidence_reroll_outcomes(hold)
    ) / 6 ** (5 - len(hold))


def bonus_explanation(scorecard):
    from exact_mode import CATEGORIES
    upper = [scorecard.get(k) for k in CATEGORIES[:6]]
    subtotal = sum(v for v in upper if v is not None)
    remaining = [i + 1 for i, v in enumerate(upper) if v is None]
    maximum = subtotal + 5 * sum(remaining)
    if subtotal >= 63:
        return 'The upper bonus is already earned; extra upper points still score normally.'
    if maximum < 63:
        return f'The bonus is unreachable: {subtotal} + at most {maximum-subtotal} = {maximum}, below 63.'
    benchmark = subtotal + 3 * sum(remaining)
    if benchmark == 63:
        pace = 'exactly 63'
    elif benchmark < 63:
        pace = f'{benchmark}, still {63-benchmark} short of 63'
    else:
        pace = f'{benchmark}, {benchmark-63} above 63'
    return (f'Upper subtotal: {subtotal}. Three of each remaining face would finish at {pace}. '
            'Three-of-a-face odds describe this turn, not the chance of earning the bonus.')


def explain_full_house(scorecard, left, right, roll_number, winner_side, edge):
    """Compare chasing/banking a house with a matching-dice alternative."""
    from exact_mode import _turn_plan_stats, _one_reroll_plan_stats, CATEGORY_LABELS, UPPER_BY_FACE, hold_text
    if scorecard.get('full_house') is not None or scorecard.get('yahtzee') == 50:
        return None  # Preserve specialized Joker guidance.
    shapes = [sorted(Counter(h).values()) for h in (left, right)]
    house_indices = [i for i, shape in enumerate(shapes) if shape in ([2,2], [2,3])]
    if len(house_indices) != 1:
        return None
    hi = house_indices[0]
    holds = (left, right)
    house, match = holds[hi], holds[1-hi]
    matching_plan = bool(match) and len(set(match)) == 1
    bank = shapes[hi] == [2,3]
    horizon = 'on the final roll' if roll_number == 2 else 'by Roll 3'
    hp = _turn_plan_stats(house, 'full_house', roll_number)[0]
    mp = _turn_plan_stats(match, 'full_house', roll_number)[0]
    intro = ('Keeping all five protects a made Full House worth 25. ' if bank else 'Keeping both pairs chases a Full House. ')
    alternative = f'keeping only the {match[0]}s' if matching_plan else ('rerolling everything' if not match else 'keeping ' + ', '.join(map(str,match)))
    summary = intro + f'Full House odds {horizon}: {hp:.1%} versus {mp:.1%} {alternative}. '
    details = []
    for hold in (house, match):
        fresh = 5-len(hold)
        total = 6**fresh
        rate = _one_reroll_plan_stats(hold,'full_house')[0]
        hits = round(rate*total)
        details.append('Keeping all five guarantees the made Full House: 25 points, no reroll needed.' if len(hold)==5 else f'{hold_text(hold).capitalize()}: {hits}/{total} equally likely next-roll outcomes make a Full House ({rate:.1%}).')
    if roll_number == 1:
        details.append('The by-Roll-3 odds allow a new hold after Roll 2, chosen specifically to maximize Full House completion.')
    face = match[0] if matching_plan else None
    category = UPPER_BY_FACE[face] if face else None
    if category and scorecard.get(category) is None:
        hs = _turn_plan_stats(house, category, roll_number)
        ms = _turn_plan_stats(match, category, roll_number)
        summary += f'{CATEGORY_LABELS[category]} at {3*face}+: {hs[2]:.1%} versus {ms[2]:.1%}. '
        summary += bonus_explanation(scorecard).split('Three-of-a-face odds')[0].replace('Upper subtotal: ', 'Upper total: ')
        details.append(f'Expected {CATEGORY_LABELS[category]} if used in that box: {hs[1]:.2f} versus {ms[1]:.2f}. ' + bonus_explanation(scorecard))
    elif category:
        details.append(f'{CATEGORY_LABELS[category]} is closed, so those matching dice cannot earn an upper score there.')
    winner = left if winner_side == 'left' else right
    if roll_number == 2:
        open_categories = tuple(k for k in CATEGORY_LABELS if scorecard.get(k) is None)
        immediate = [immediate_points(h,open_categories) for h in holds]
        wi = 0 if winner_side == 'left' else 1
        if immediate[1-wi] - immediate[wi] >= .005:
            summary += 'The immediate-points leader reverses across the remaining game. '
        details.append(f'Best immediate raw score, choosing one open box after each final roll: {hold_text(left)} {immediate[0]:.2f}; {hold_text(right)} {immediate[1]:.2f}. This excludes bonuses and the value of the boxes left for future turns.')
    summary += f'{hold_text(winner).capitalize()} leads by {edge:.2f} expected remaining-game points.'
    if edge <= .10:
        summary += ' These choices are effectively tied.'
    details.append('A Full House-only expected score is 25 times its completion probability, with zero for every miss. A miss can still score elsewhere. Do not add the scoring-path rows: only one box is filled per turn.')
    details.append('The remaining-game margin includes later turns and the scorecard left behind. These separate statistics do not isolate how much of that margin comes from the bonus.')
    takeaway = ('Compare the guaranteed 25 with the opportunity you reopen by breaking the house.' if bank else 'Two pairs improve the Full House chase; releasing a pair can improve the scorecard you carry into later turns.')
    return summary, takeaway if edge > .10 else '', ' '.join(details)


def supporting_math(scorecard, rows, roll_number):
    """Explain common units and horizons without altering evidence or ranking."""
    labels = {row['label'] for row in rows}
    bits = []
    if any(label in labels for label in ('Expected upper box','Three-of-a-face chance','Ones','Twos','Threes','Fours','Fives','Sixes')):
        bits.append(bonus_explanation(scorecard))
    if labels & {'Three of a Kind','Four of a Kind'}:
        bits.append('Three/Four of a Kind points average the dice total on qualifying hands and zero on misses. Completion chance alone does not measure the value of the hand.')
    if 'Straight payoff' in labels:
        bits.append('Straight payoff uses 40 for a Large Straight, 30 for Small-only, and zero otherwise; a Large Straight is not counted twice.')
    if bits:
        if roll_number == 1:
            bits.append('Each scoring path assumes its own best final hold after Roll 2; they are alternative plans, not simultaneous promises.')
        bits.append('Only one box can be scored each turn, so these rows cannot be added to obtain the full-game margin.')
    return ' '.join(bits)
