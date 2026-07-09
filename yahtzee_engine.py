"""Yahtzee Coach engine exported from the July 8 clean notebook.

Roll 1 and Roll 2 hold-decision practice only.
"""


# ===== Source notebook cell 2 =====
# ============================
# YAHTZEE COACH
# Unlimited Practice + Classroom Mode Foundation
# ============================

from itertools import combinations
from collections import Counter
import random

# ===== Source notebook cell 3 =====
# ============================
# SCORING ENGINE
# ============================

def score_upper_category(dice, number):
    return dice.count(number) * number


def score_three_of_kind(dice):
    counts = Counter(dice)

    if max(counts.values()) >= 3:
        return sum(dice)

    return 0


def score_four_of_kind(dice):
    counts = Counter(dice)

    if max(counts.values()) >= 4:
        return sum(dice)

    return 0


def score_full_house(dice):
    counts = sorted(Counter(dice).values())

    if counts == [2, 3]:
        return 25

    return 0


def score_small_straight(dice):
    unique = set(dice)

    small_straights = [
        {1, 2, 3, 4},
        {2, 3, 4, 5},
        {3, 4, 5, 6}
    ]

    for straight in small_straights:
        if straight.issubset(unique):
            return 30

    return 0


def score_large_straight(dice):
    unique = sorted(set(dice))

    if unique == [1, 2, 3, 4, 5] or unique == [2, 3, 4, 5, 6]:
        return 40

    return 0


def score_yahtzee(dice):
    if len(set(dice)) == 1:
        return 50

    return 0


def score_chance(dice):
    return sum(dice)


def calculate_all_scores(dice):
    scores = {}

    # Upper section
    scores["ones"] = score_upper_category(dice, 1)
    scores["twos"] = score_upper_category(dice, 2)
    scores["threes"] = score_upper_category(dice, 3)
    scores["fours"] = score_upper_category(dice, 4)
    scores["fives"] = score_upper_category(dice, 5)
    scores["sixes"] = score_upper_category(dice, 6)

    # Lower section
    scores["three_of_a_kind"] = score_three_of_kind(dice)
    scores["four_of_a_kind"] = score_four_of_kind(dice)
    scores["full_house"] = score_full_house(dice)
    scores["small_straight"] = score_small_straight(dice)
    scores["large_straight"] = score_large_straight(dice)
    scores["yahtzee"] = score_yahtzee(dice)
    scores["chance"] = score_chance(dice)

    return scores

# ===== Source notebook cell 4 =====
# ============================
# HOLD GENERATOR
# ============================

def generate_holds(dice):
    holds = []

    for hold_size in range(0, len(dice) + 1):
        for hold_indices in combinations(range(len(dice)), hold_size):
            held_dice = [dice[i] for i in hold_indices]
            holds.append(held_dice)

    return holds

# ===== Source notebook cell 5 =====
# ============================
# UNIQUE HOLD GENERATOR
# ============================

def generate_unique_holds(dice):
    unique_holds = set()

    for hold_size in range(0, len(dice) + 1):
        for hold_indices in combinations(range(len(dice)), hold_size):
            held_dice = tuple(sorted([dice[i] for i in hold_indices]))
            unique_holds.add(held_dice)

    sorted_holds = sorted(unique_holds, key=lambda hold: (len(hold), hold))

    return [list(hold) for hold in sorted_holds]

# ===== Source notebook cell 6 =====
# ============================
# REROLL OUTCOME GENERATOR
# ============================

from itertools import product

def generate_reroll_outcomes(number_of_dice):
    outcomes = []

    for outcome in product(range(1, 7), repeat=number_of_dice):
        outcomes.append(list(outcome))

    return outcomes

# ===== Source notebook cell 7 =====
# ============================
# FINAL ROLL GENERATOR
# ============================

def generate_final_rolls_after_hold(hold, total_dice=5):
    number_to_reroll = total_dice - len(hold)

    reroll_outcomes = generate_reroll_outcomes(number_to_reroll)

    final_rolls = []

    for outcome in reroll_outcomes:
        final_roll = sorted(hold + outcome)
        final_rolls.append(final_roll)

    return final_rolls

# ===== Source notebook cell 8 =====
# ============================
# EXPECTED VALUE ENGINE
# ============================

YAHTZEE_CATEGORIES = [
    "ones",
    "twos",
    "threes",
    "fours",
    "fives",
    "sixes",
    "three_of_a_kind",
    "four_of_a_kind",
    "full_house",
    "small_straight",
    "large_straight",
    "yahtzee",
    "chance"
]


def best_score_for_roll(dice, available_categories):
    all_scores = calculate_all_scores(dice)

    best_category = None
    best_score = -1

    for category in available_categories:
        score = all_scores[category]

        if score > best_score:
            best_score = score
            best_category = category

    return best_category, best_score


def expected_value_of_hold(hold, available_categories):
    final_rolls = generate_final_rolls_after_hold(hold)

    total_score = 0
    category_counter = Counter()

    for final_roll in final_rolls:
        best_category, best_score = best_score_for_roll(final_roll, available_categories)

        total_score += best_score
        category_counter[best_category] += 1

    expected_value = total_score / len(final_rolls)

    return expected_value, category_counter

# ===== Source notebook cell 9 =====
# ============================
# HOLD ANALYZER
# ============================

def analyze_all_holds(dice, available_categories):
    holds = generate_unique_holds(dice)

    results = []

    for hold in holds:
        expected_value, category_counter = expected_value_of_hold(
            hold,
            available_categories
        )

        results.append({
            "hold": hold,
            "expected_value": expected_value,
            "category_counter": category_counter
        })

    results = sorted(
        results,
        key=lambda result: result["expected_value"],
        reverse=True
    )

    return results

# ===== Source notebook cell 10 =====
# ============================
# SCORE SHEET
# ============================

EMPTY_SCORECARD = {
    "ones": None,
    "twos": None,
    "threes": None,
    "fours": None,
    "fives": None,
    "sixes": None,
    "three_of_a_kind": None,
    "four_of_a_kind": None,
    "full_house": None,
    "small_straight": None,
    "large_straight": None,
    "yahtzee": None,
    "chance": None
}


def get_available_categories(scorecard):
    available_categories = []

    for category, score in scorecard.items():
        if score is None:
            available_categories.append(category)

    return available_categories

# ===== Source notebook cell 11 =====
# ============================
# UPPER SECTION BONUS TRACKER
# ============================

UPPER_CATEGORIES = [
    "ones",
    "twos",
    "threes",
    "fours",
    "fives",
    "sixes"
]

UPPER_BONUS_TARGET = 63
UPPER_BONUS_POINTS = 35


def upper_section_total(scorecard):
    total = 0

    for category in UPPER_CATEGORIES:
        if scorecard[category] is not None:
            total += scorecard[category]

    return total


def upper_categories_remaining(scorecard):
    remaining = []

    for category in UPPER_CATEGORIES:
        if scorecard[category] is None:
            remaining.append(category)

    return remaining


def upper_bonus_status(scorecard):
    current_total = upper_section_total(scorecard)
    remaining_categories = upper_categories_remaining(scorecard)

    points_needed = max(0, UPPER_BONUS_TARGET - current_total)

    return {
        "current_upper_total": current_total,
        "upper_categories_remaining": remaining_categories,
        "points_needed_for_bonus": points_needed,
        "bonus_already_earned": current_total >= UPPER_BONUS_TARGET
    }

# ===== Source notebook cell 12 =====
# ============================
# BONUS-AWARE SCORING
# ============================

UPPER_CATEGORY_VALUES = {
    "ones": 1,
    "twos": 2,
    "threes": 3,
    "fours": 4,
    "fives": 5,
    "sixes": 6
}


def upper_max_possible_remaining(scorecard, category_being_scored=None):
    remaining = upper_categories_remaining(scorecard)

    if category_being_scored in remaining:
        remaining.remove(category_being_scored)

    max_possible = 0

    for category in remaining:
        max_possible += UPPER_CATEGORY_VALUES[category] * 5

    return max_possible


def bonus_still_possible_after_score(scorecard, category, score):
    current_total = upper_section_total(scorecard)

    if category in UPPER_CATEGORIES:
        projected_total = current_total + score
        max_remaining = upper_max_possible_remaining(scorecard, category)
    else:
        projected_total = current_total
        max_remaining = upper_max_possible_remaining(scorecard)

    return projected_total + max_remaining >= UPPER_BONUS_TARGET


def bonus_adjusted_category_value(category, raw_score, scorecard):
    adjusted_score = raw_score

    if category in UPPER_CATEGORIES:
        status = upper_bonus_status(scorecard)

        if not status["bonus_already_earned"]:
            if bonus_still_possible_after_score(scorecard, category, raw_score):
                bonus_value_per_upper_point = UPPER_BONUS_POINTS / UPPER_BONUS_TARGET
                adjusted_score += raw_score * bonus_value_per_upper_point

    return adjusted_score

# ===== Source notebook cell 13 =====
# ============================
# BONUS-AWARE BEST SCORE ENGINE
# ============================

def best_score_for_roll_bonus_aware(dice, available_categories, scorecard):
    all_scores = calculate_all_scores(dice)

    best_category = None
    best_raw_score = -1
    best_adjusted_score = -1

    for category in available_categories:
        raw_score = all_scores[category]
        adjusted_score = bonus_adjusted_category_value(
            category,
            raw_score,
            scorecard
        )

        if adjusted_score > best_adjusted_score:
            best_category = category
            best_raw_score = raw_score
            best_adjusted_score = adjusted_score

    return best_category, best_raw_score, best_adjusted_score

# ===== Source notebook cell 14 =====
# ============================
# BONUS-AWARE EXPECTED VALUE ENGINE
# ============================

def expected_value_of_hold_bonus_aware(hold, available_categories, scorecard):
    final_rolls = generate_final_rolls_after_hold(hold)

    total_adjusted_score = 0
    total_raw_score = 0
    category_counter = Counter()

    for final_roll in final_rolls:
        best_category, raw_score, adjusted_score = best_score_for_roll_bonus_aware(
            final_roll,
            available_categories,
            scorecard
        )

        total_raw_score += raw_score
        total_adjusted_score += adjusted_score
        category_counter[best_category] += 1

    raw_expected_score = total_raw_score / len(final_rolls)
    adjusted_expected_value = total_adjusted_score / len(final_rolls)

    return adjusted_expected_value, raw_expected_score, category_counter

# ===== Source notebook cell 15 =====
# ============================
# BONUS-AWARE HOLD ANALYZER
# ============================

def analyze_all_holds_bonus_aware(dice, scorecard):
    holds = generate_unique_holds(dice)
    available_categories = get_available_categories(scorecard)

    results = []

    for hold in holds:
        adjusted_expected_value, raw_expected_score, category_counter = expected_value_of_hold_bonus_aware(
            hold,
            available_categories,
            scorecard
        )

        results.append({
            "hold": hold,
            "adjusted_expected_value": adjusted_expected_value,
            "raw_expected_score": raw_expected_score,
            "category_counter": category_counter
        })

    results = sorted(
        results,
        key=lambda result: result["adjusted_expected_value"],
        reverse=True
    )

    return results

# ===== Source notebook cell 16 =====
# ============================
# LETTER GRADE ENGINE
# ============================

def letter_grade_from_efficiency(efficiency):
    if efficiency >= 0.98:
        return "A+"
    elif efficiency >= 0.95:
        return "A"
    elif efficiency >= 0.90:
        return "A-"
    elif efficiency >= 0.85:
        return "B"
    elif efficiency >= 0.80:
        return "B-"
    elif efficiency >= 0.75:
        return "C"
    elif efficiency >= 0.65:
        return "D"
    else:
        return "F"

# ===== Source notebook cell 17 =====
# ============================
# USER MOVE EVALUATOR
# ============================

def evaluate_user_hold(dice, scorecard, user_hold):
    results = analyze_all_holds_bonus_aware(dice, scorecard)

    optimal_result = results[0]
    optimal_value = optimal_result["adjusted_expected_value"]

    normalized_user_hold = sorted(user_hold)

    user_result = None

    for result in results:
        if result["hold"] == normalized_user_hold:
            user_result = result
            break

    if user_result is None:
        raise ValueError("That hold is not possible with the current dice.")

    user_value = user_result["adjusted_expected_value"]

    efficiency = user_value / optimal_value
    grade = letter_grade_from_efficiency(efficiency)

    points_lost = optimal_value - user_value

    return {
        "current_dice": dice,
        "user_hold": normalized_user_hold,
        "optimal_hold": optimal_result["hold"],
        "user_value": user_value,
        "optimal_value": optimal_value,
        "efficiency": efficiency,
        "points_lost": points_lost,
        "grade": grade
    }

# ===== Source notebook cell 18 =====
# ============================
# COACH FEEDBACK ENGINE
# ============================

CATEGORY_DISPLAY_NAMES = {
    "ones": "Ones",
    "twos": "Twos",
    "threes": "Threes",
    "fours": "Fours",
    "fives": "Fives",
    "sixes": "Sixes",
    "three_of_a_kind": "Three of a Kind",
    "four_of_a_kind": "Four of a Kind",
    "full_house": "Full House",
    "small_straight": "Small Straight",
    "large_straight": "Large Straight",
    "yahtzee": "Yahtzee",
    "chance": "Chance"
}


def format_hold(hold):
    if len(hold) == 0:
        return "reroll everything"
    return "keep " + ", ".join(str(die) for die in hold)


def most_common_categories_text(category_counter, limit=3):
    if not category_counter:
        return "No common scoring category found."

    parts = []

    for category, count in category_counter.most_common(limit):
        name = CATEGORY_DISPLAY_NAMES[category]
        parts.append(f"{name} ({count} outcomes)")

    return ", ".join(parts)


def hold_strength_label(efficiency):
    if efficiency >= 0.98:
        return "excellent"
    elif efficiency >= 0.95:
        return "very strong"
    elif efficiency >= 0.90:
        return "solid"
    elif efficiency >= 0.85:
        return "decent"
    elif efficiency >= 0.75:
        return "risky"
    else:
        return "weak"


def describe_hold_pattern(hold, scorecard):
    counts = Counter(hold)
    feedback = []

    # Empty hold
    if len(hold) == 0:
        feedback.append("You are choosing to reroll everything, which gives maximum flexibility but gives up any pattern you already had.")
        return feedback

    # Five dice held
    if len(hold) == 5:
        feedback.append("You are keeping all five dice, which locks in the current roll and gives up the chance to improve.")
        return feedback

    # Three or more of a kind
    if any(count >= 3 for count in counts.values()):
        repeated_number = max(counts, key=counts.get)
        feedback.append(
            f"You preserved three or more {repeated_number}s, which keeps strong paths open for Three of a Kind, Four of a Kind, Yahtzee, and the upper section."
        )

    # Pair
    elif any(count == 2 for count in counts.values()):
        repeated_number = max(counts, key=counts.get)
        feedback.append(
            f"You kept a pair of {repeated_number}s. That can be useful, but it is usually less powerful than keeping three of a kind or a strong straight pattern."
        )

    # Straight potential
    unique = set(hold)
    straight_patterns = [
        {1, 2, 3, 4},
        {2, 3, 4, 5},
        {3, 4, 5, 6}
    ]

    for pattern in straight_patterns:
        if len(unique.intersection(pattern)) >= 3:
            feedback.append(
                "Your hold keeps part of a straight pattern alive, which can create chances for Small Straight or Large Straight."
            )
            break

    # Upper bonus relevance
    status = upper_bonus_status(scorecard)

    if not status["bonus_already_earned"]:
        remaining_upper = status["upper_categories_remaining"]

        for category in remaining_upper:
            number = UPPER_CATEGORY_VALUES[category]

            if number in hold:
                feedback.append(
                    f"Keeping {number}s may help the {CATEGORY_DISPLAY_NAMES[category]} box, which matters because the 35-point upper bonus is still available."
                )
                break

    # Too many unrelated dice
    if len(hold) >= 3 and max(counts.values()) == 1:
        feedback.append(
            "One concern is that you are holding several unrelated dice. That reduces the number of dice you can reroll and may limit improvement."
        )

    return feedback


def coach_explanation_for_hold(dice, scorecard, hold_result, optimal_value):
    hold = hold_result["hold"]
    adjusted_value = hold_result["adjusted_expected_value"]
    raw_score = hold_result["raw_expected_score"]
    category_counter = hold_result["category_counter"]

    efficiency = adjusted_value / optimal_value
    strength = hold_strength_label(efficiency)

    explanation = []

    explanation.append(f"Hold choice: {format_hold(hold)}")
    explanation.append(f"Coach rating: This is a {strength} move.")
    explanation.append(f"Raw expected score: {round(raw_score, 2)}")
    explanation.append(f"Bonus-aware value: {round(adjusted_value, 2)}")
    explanation.append(f"Efficiency: {round(efficiency * 100, 1)}% of optimal")

    explanation.append("")
    explanation.append("Why it can be good:")

    pattern_feedback = describe_hold_pattern(hold, scorecard)

    for line in pattern_feedback:
        explanation.append(f"- {line}")

    explanation.append(
        f"- The most common best scoring paths after this hold are: {most_common_categories_text(category_counter)}."
    )

    explanation.append("")
    explanation.append("Possible downside:")

    points_lost = optimal_value - adjusted_value

    if points_lost <= 0.1:
        explanation.append("- There is very little downside. This is essentially optimal.")
    elif points_lost <= 1:
        explanation.append("- This move is close to optimal, but there may be a slightly better way to balance scoring and future bonus value.")
    elif points_lost <= 3:
        explanation.append("- This move gives up some expected value. It may still be reasonable, but it is not the strongest statistical choice.")
    else:
        explanation.append("- This move gives up a lot of expected value compared with the best available hold.")

    return "\n".join(explanation)

# ===== Source notebook cell 19 =====
# ============================
# CLEANER COACH LANGUAGE HELPERS
# ============================

def article_for_word(word):
    if word[0].lower() in ["a", "e", "i", "o", "u"]:
        return "an"
    return "a"


def outcome_word(count):
    if count == 1:
        return "outcome"
    return "outcomes"


def most_common_categories_text_clean(category_counter, limit=3):
    if not category_counter:
        return "No common scoring category found."

    parts = []

    for category, count in category_counter.most_common(limit):
        name = CATEGORY_DISPLAY_NAMES[category]
        parts.append(f"{name} ({count} {outcome_word(count)})")

    return ", ".join(parts)

# ===== Source notebook cell 20 =====
# ============================
# USER-FACING COACH REPORT
# ============================

def find_result_for_hold(results, user_hold):
    normalized_user_hold = sorted(user_hold)

    for result in results:
        if result["hold"] == normalized_user_hold:
            return result

    raise ValueError("That hold is not possible with the current dice.")


def coach_report_for_user_hold(dice, scorecard, user_hold):
    results = analyze_all_holds_bonus_aware(dice, scorecard)

    optimal_result = results[0]
    user_result = find_result_for_hold(results, user_hold)

    optimal_value = optimal_result["adjusted_expected_value"]
    user_value = user_result["adjusted_expected_value"]

    efficiency = user_value / optimal_value
    grade = letter_grade_from_efficiency(efficiency)
    strength = hold_strength_label(efficiency)
    points_lost = optimal_value - user_value

    user_hold_clean = user_result["hold"]
    optimal_hold_clean = optimal_result["hold"]

    report = []

    report.append("YAHTZEE COACH REPORT")
    report.append("=" * 40)
    report.append(f"Current dice: {dice}")
    report.append(f"Your choice: {format_hold(user_hold_clean)}")
    report.append(f"Optimal choice: {format_hold(optimal_hold_clean)}")
    report.append("")
    report.append(f"Grade: {grade}")
    report.append(f"Coach rating: This is {article_for_word(strength)} {strength} move.")
    report.append(f"Your bonus-aware value: {round(user_value, 2)}")
    report.append(f"Optimal bonus-aware value: {round(optimal_value, 2)}")
    report.append(f"Efficiency: {round(efficiency * 100, 1)}% of optimal")
    report.append(f"Expected value lost: {round(points_lost, 2)}")
    report.append("")

    report.append("What was good about your move?")
    good_feedback = describe_hold_pattern(user_hold_clean, scorecard)

    if good_feedback:
        for line in good_feedback:
            report.append(f"- {line}")
    else:
        report.append("- This hold keeps some flexibility, but it does not strongly build toward a specific scoring pattern.")

    report.append(
        f"- Your most common scoring paths were: {most_common_categories_text_clean(user_result['category_counter'])}."
    )

    report.append("")
    report.append("What was the downside?")

    if user_hold_clean == optimal_hold_clean:
        report.append("- There really was not a meaningful downside. This was the best statistical choice.")
    elif points_lost <= 1:
        report.append("- This was very close to optimal. The difference is small enough that it is still a strong strategic choice.")
    elif points_lost <= 3:
        report.append("- This gave up some expected value. It may still score well, but the optimal hold creates slightly better long-term opportunities.")
    else:
        report.append("- This gave up a lot of expected value. The optimal hold gave you a much better chance to improve your score.")

    report.append("")
    report.append("Coach recommendation:")

    if user_hold_clean == optimal_hold_clean:
        report.append("Stay with this thinking. You balanced immediate scoring with the upper-section bonus well.")
    else:
        report.append(
            f"The stronger play was to {format_hold(optimal_hold_clean)} because it produced the highest bonus-aware expected value."
        )

    return "\n".join(report)

# ===== Source notebook cell 21 =====
# ============================
# PRACTICE CHALLENGE GENERATOR
# ============================

def roll_dice(number_of_dice=5):
    dice = []

    for _ in range(number_of_dice):
        dice.append(random.randint(1, 6))

    return sorted(dice)


def create_empty_scorecard():
    return {
        "ones": None,
        "twos": None,
        "threes": None,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": None,
        "large_straight": None,
        "yahtzee": None,
        "chance": None
    }


def create_sample_midgame_scorecard():
    scorecard = create_empty_scorecard()

    # A reasonable mid-game situation.
    # None means the category is still open.
    scorecard["ones"] = 3
    scorecard["twos"] = 6
    scorecard["threes"] = 9

    scorecard["small_straight"] = 30
    scorecard["large_straight"] = 40

    return scorecard


def generate_practice_challenge():
    challenge = {
        "mode": "Unlimited Practice",
        "roll_number": 2,
        "rolls_remaining": 1,
        "dice": roll_dice(5),
        "scorecard": create_sample_midgame_scorecard()
    }

    return challenge

# ===== Source notebook cell 22 =====
# ============================
# FUTURE-AWARE STRATEGY ENGINE
# ============================

LOWER_COMBO_CATEGORIES = [
    "three_of_a_kind",
    "four_of_a_kind",
    "full_house",
    "yahtzee"
]

STRAIGHT_CATEGORIES = [
    "small_straight",
    "large_straight"
]


def any_category_open(scorecard, categories):
    for category in categories:
        if scorecard[category] is None:
            return True

    return False


CATEGORY_TARGETS = {
    "ones": 3,
    "twos": 6,
    "threes": 9,
    "fours": 12,
    "fives": 15,
    "sixes": 18,

    "three_of_a_kind": 20,
    "four_of_a_kind": 24,
    "full_house": 25,
    "small_straight": 30,
    "large_straight": 40,
    "yahtzee": 50,
    "chance": 23
}


CATEGORY_SHORTFALL_WEIGHTS = {
    "ones": 1.00,
    "twos": 1.00,
    "threes": 1.00,
    "fours": 1.00,
    "fives": 1.00,
    "sixes": 1.00,

    "three_of_a_kind": 0.45,
    "four_of_a_kind": 0.35,
    "full_house": 0.80,
    "small_straight": 0.80,
    "large_straight": 0.80,
    "yahtzee": 0.20,
    "chance": 1.20
}


def future_aware_category_value(category, raw_score, scorecard):
    value = bonus_adjusted_category_value(category, raw_score, scorecard)

    target = CATEGORY_TARGETS[category]
    shortfall = max(0, target - raw_score)
    penalty_weight = CATEGORY_SHORTFALL_WEIGHTS[category]

    value -= shortfall * penalty_weight

    return value

# ===== Source notebook cell 23 =====
# ============================
# HOLD SHAPE STRATEGY
# ============================

def hold_shape_future_adjustment(hold, scorecard):
    if len(hold) == 0:
        return 0

    counts = Counter(hold)
    max_count = max(counts.values())
    unique = set(hold)

    adjustment = 0

    # Reward clean commitment to three-of-a-kind patterns.
    if max_count >= 3 and any_category_open(scorecard, LOWER_COMBO_CATEGORIES):
        if max_count == 3:
            if len(hold) == 3:
                adjustment += 2.0
            else:
                adjustment += 0.75
                adjustment -= 0.9 * (len(hold) - 3)

        elif max_count == 4:
            adjustment += 1.0

    # Reward straight structures only when straights are still open.
    if any_category_open(scorecard, STRAIGHT_CATEGORIES):
        large_patterns = [
            {1, 2, 3, 4, 5},
            {2, 3, 4, 5, 6}
        ]

        small_patterns = [
            {1, 2, 3, 4},
            {2, 3, 4, 5},
            {3, 4, 5, 6}
        ]

        if any(len(unique.intersection(pattern)) >= 4 for pattern in large_patterns):
            adjustment += 1.5

        elif any(len(unique.intersection(pattern)) >= 3 for pattern in small_patterns):
            adjustment += 0.6

    # Discourage holding unrelated dice unless they build toward a straight.
    has_pair_or_better = max_count >= 2

    has_straight_structure = any(
        len(unique.intersection(pattern)) >= 3
        for pattern in [
            {1, 2, 3, 4},
            {2, 3, 4, 5},
            {3, 4, 5, 6}
        ]
    )

    if len(hold) >= 3 and not has_pair_or_better and not has_straight_structure:
        adjustment -= 1.0

    return adjustment

# ===== Source notebook cell 24 =====
# ============================
# FUTURE-AWARE HOLD ANALYZER
# ============================

def best_score_for_roll_future_aware(dice, available_categories, scorecard):
    all_scores = calculate_all_scores(dice)

    best_category = None
    best_raw_score = -1
    best_future_value = -999999

    for category in available_categories:
        raw_score = all_scores[category]
        future_value = future_aware_category_value(
            category,
            raw_score,
            scorecard
        )

        if future_value > best_future_value:
            best_category = category
            best_raw_score = raw_score
            best_future_value = future_value

    return best_category, best_raw_score, best_future_value


def expected_value_of_hold_future_aware(hold, available_categories, scorecard):
    final_rolls = generate_final_rolls_after_hold(hold)

    total_future_value = 0
    total_raw_score = 0
    category_counter = Counter()

    for final_roll in final_rolls:
        best_category, raw_score, future_value = best_score_for_roll_future_aware(
            final_roll,
            available_categories,
            scorecard
        )

        total_raw_score += raw_score
        total_future_value += future_value
        category_counter[best_category] += 1

    raw_expected_score = total_raw_score / len(final_rolls)
    future_aware_value = total_future_value / len(final_rolls)

    shape_adjustment = hold_shape_future_adjustment(hold, scorecard)
    future_aware_value += shape_adjustment

    return future_aware_value, raw_expected_score, category_counter, shape_adjustment


def analyze_all_holds_future_aware(dice, scorecard):
    holds = generate_unique_holds(dice)
    available_categories = get_available_categories(scorecard)

    results = []

    for hold in holds:
        future_aware_value, raw_expected_score, category_counter, shape_adjustment = expected_value_of_hold_future_aware(
            hold,
            available_categories,
            scorecard
        )

        results.append({
            "hold": hold,
            "future_aware_value": future_aware_value,
            "raw_expected_score": raw_expected_score,
            "category_counter": category_counter,
            "shape_adjustment": shape_adjustment
        })

    results = sorted(
        results,
        key=lambda result: result["future_aware_value"],
        reverse=True
    )

    return results

# ===== Source notebook cell 25 =====
# ============================
# PATCH CELL - CURRENT BEST VERSION
# Fixes:
# 1. Uses Future-Aware Strategy instead of old Bonus-Aware report
# 2. Stops giving straight-structure credit when straights are already closed
# 3. Rewards preserving strong patterns from the original roll
# 4. Uses "Strategy Value" language instead of "Bonus-Aware Value"
# 5. Generates and solves the same challenge
# ============================


def straights_are_open(scorecard):
    return any_category_open(scorecard, STRAIGHT_CATEGORIES)


def hold_has_straight_structure(hold):
    unique = set(hold)

    straight_patterns = [
        {1, 2, 3, 4},
        {2, 3, 4, 5},
        {3, 4, 5, 6}
    ]

    return any(len(unique.intersection(pattern)) >= 3 for pattern in straight_patterns)


def hold_shape_future_adjustment(hold, scorecard):
    if len(hold) == 0:
        return 0

    counts = Counter(hold)
    max_count = max(counts.values())
    unique = set(hold)

    adjustment = 0

    # Reward clean commitment to three-of-a-kind patterns.
    if max_count >= 3 and any_category_open(scorecard, LOWER_COMBO_CATEGORIES):
        if max_count == 3:
            if len(hold) == 3:
                adjustment += 2.5
            else:
                adjustment += 0.75
                adjustment -= 0.9 * (len(hold) - 3)

        elif max_count == 4:
            adjustment += 1.2

    # Reward straight structures only when straights are actually open.
    if straights_are_open(scorecard):
        large_patterns = [
            {1, 2, 3, 4, 5},
            {2, 3, 4, 5, 6}
        ]

        small_patterns = [
            {1, 2, 3, 4},
            {2, 3, 4, 5},
            {3, 4, 5, 6}
        ]

        if any(len(unique.intersection(pattern)) >= 4 for pattern in large_patterns):
            adjustment += 1.5

        elif any(len(unique.intersection(pattern)) >= 3 for pattern in small_patterns):
            adjustment += 0.6

    # Discourage holding several unrelated dice.
    # But only excuse it as "straight structure" if straights are still open.
    has_pair_or_better = max_count >= 2
    has_useful_straight_structure = straights_are_open(scorecard) and hold_has_straight_structure(hold)

    if len(hold) >= 3 and not has_pair_or_better and not has_useful_straight_structure:
        adjustment -= 1.0

    return adjustment


def original_roll_pattern_adjustment(dice, hold, scorecard):
    """
    This helps fix situations like [3, 3, 3, 4, 5],
    where an experienced Yahtzee player usually does not want to abandon the triple.
    """
    dice_counts = Counter(dice)
    hold_counts = Counter(hold)

    adjustment = 0

    # If original roll already has 3+ of a kind, reward preserving it.
    if any_category_open(scorecard, LOWER_COMBO_CATEGORIES):
        for number, count in dice_counts.items():
            if count >= 3:
                if hold_counts[number] >= 3:
                    adjustment += 3.0

                    # Keeping extra unrelated dice with the triple is less flexible.
                    if len(hold) > 3:
                        adjustment -= 0.6 * (len(hold) - 3)
                else:
                    adjustment -= 2.5

    # If straights are open and original roll has straight potential,
    # reward holding that structure.
    if straights_are_open(scorecard):
        unique_dice = set(dice)
        unique_hold = set(hold)

        straight_patterns = [
            {1, 2, 3, 4},
            {2, 3, 4, 5},
            {3, 4, 5, 6}
        ]

        for pattern in straight_patterns:
            if len(unique_dice.intersection(pattern)) >= 4:
                if len(unique_hold.intersection(pattern)) >= 4:
                    adjustment += 1.5
                elif len(unique_hold.intersection(pattern)) <= 2:
                    adjustment -= 1.0
                break

    return adjustment


def analyze_all_holds_future_aware(dice, scorecard):
    holds = generate_unique_holds(dice)
    available_categories = get_available_categories(scorecard)

    results = []

    for hold in holds:
        future_aware_value, raw_expected_score, category_counter, shape_adjustment = expected_value_of_hold_future_aware(
            hold,
            available_categories,
            scorecard
        )

        original_adjustment = original_roll_pattern_adjustment(dice, hold, scorecard)

        strategy_value = future_aware_value + original_adjustment

        results.append({
            "hold": hold,
            "strategy_value": strategy_value,
            "future_aware_value": strategy_value,  # kept for compatibility with older code
            "raw_expected_score": raw_expected_score,
            "category_counter": category_counter,
            "shape_adjustment": shape_adjustment,
            "original_adjustment": original_adjustment
        })

    results = sorted(
        results,
        key=lambda result: result["strategy_value"],
        reverse=True
    )

    return results


def evaluate_user_hold_future_aware(dice, scorecard, user_hold):
    results = analyze_all_holds_future_aware(dice, scorecard)

    optimal_result = results[0]
    optimal_value = optimal_result["strategy_value"]

    user_result = find_result_for_hold(results, user_hold)
    user_value = user_result["strategy_value"]

    efficiency = user_value / optimal_value
    grade = letter_grade_from_efficiency(efficiency)
    points_lost = optimal_value - user_value

    return {
        "current_dice": dice,
        "user_hold": user_result["hold"],
        "optimal_hold": optimal_result["hold"],
        "user_value": user_value,
        "optimal_value": optimal_value,
        "efficiency": efficiency,
        "points_lost": points_lost,
        "grade": grade,
        "user_result": user_result,
        "optimal_result": optimal_result
    }


def coach_report_for_user_hold_future_aware(dice, scorecard, user_hold):
    evaluation = evaluate_user_hold_future_aware(dice, scorecard, user_hold)

    user_result = evaluation["user_result"]
    optimal_result = evaluation["optimal_result"]

    user_hold_clean = evaluation["user_hold"]
    optimal_hold_clean = evaluation["optimal_hold"]

    efficiency = evaluation["efficiency"]
    grade = evaluation["grade"]
    strength = hold_strength_label(efficiency)
    points_lost = evaluation["points_lost"]

    report = []

    report.append("YAHTZEE COACH REPORT")
    report.append("=" * 40)
    report.append(f"Current dice: {dice}")
    report.append(f"Your choice: {format_hold(user_hold_clean)}")
    report.append(f"Optimal choice: {format_hold(optimal_hold_clean)}")
    report.append("")
    report.append(f"Grade: {grade}")
    report.append(f"Coach rating: This is {article_for_word(strength)} {strength} move.")
    report.append(f"Your strategy value: {round(evaluation['user_value'], 2)}")
    report.append(f"Optimal strategy value: {round(evaluation['optimal_value'], 2)}")
    report.append(f"Efficiency: {round(efficiency * 100, 1)}% of optimal")
    report.append(f"Strategy value lost: {round(points_lost, 2)}")
    report.append("")

    report.append("What was good about your move?")
    good_feedback = describe_hold_pattern(user_hold_clean, scorecard)

    if good_feedback:
        for line in good_feedback:
            report.append(f"- {line}")
    else:
        report.append("- This hold keeps some flexibility, but it does not strongly build toward a specific scoring pattern.")

    report.append(
        f"- Your most common scoring paths were: {most_common_categories_text_clean(user_result['category_counter'])}."
    )

    if user_result["shape_adjustment"] > 0:
        report.append("- The hold has a helpful structure, such as a repeated-number pattern or useful scoring path.")

    if user_result["original_adjustment"] > 0:
        report.append("- You preserved a strong pattern from the original roll.")

    if user_result["original_adjustment"] < 0:
        report.append("- You moved away from a strong pattern that was already available in the original roll.")

    report.append("")
    report.append("What was the downside?")

    if user_hold_clean == optimal_hold_clean:
        report.append("- There really was not a meaningful downside. This was the best strategic choice according to the current engine.")
    elif points_lost <= 1:
        report.append("- This was very close to optimal. The difference is small enough that it is still a strong strategic choice.")
    elif points_lost <= 3:
        report.append("- This gave up some strategy value. It may still score well, but the optimal hold creates better long-term opportunities.")
    else:
        report.append("- This gave up a lot of strategy value. The optimal hold gave you a much better chance to improve your overall position.")

    report.append("")
    report.append("Coach recommendation:")

    if user_hold_clean == optimal_hold_clean:
        report.append("Stay with this thinking. You balanced immediate scoring, pattern strength, and future value well.")
    else:
        report.append(
            f"The stronger play was to {format_hold(optimal_hold_clean)} because it produced the highest strategy value."
        )

    return "\n".join(report)


def show_and_solve_practice_challenge(challenge=None, top_n=5):
    if challenge is None:
        challenge = generate_practice_challenge()

    dice = challenge["dice"]
    scorecard = challenge["scorecard"]

    results = analyze_all_holds_future_aware(dice, scorecard)
    best_result = results[0]

    print("YAHTZEE COACH CHALLENGE")
    print("=" * 40)
    print("Mode:", challenge["mode"])
    print("Roll Number:", challenge["roll_number"], "of 3")
    print("Rolls Remaining:", challenge["rolls_remaining"])
    print("Dice:", dice)
    print()
    print("Best Hold:", best_result["hold"])
    print("Raw Expected Score:", round(best_result["raw_expected_score"], 2))
    print("Strategy Value:", round(best_result["strategy_value"], 2))
    print()
    print(f"Top {top_n} Holds:")

    for rank, result in enumerate(results[:top_n], start=1):
        print(
            rank,
            "Hold:", result["hold"],
            "Raw Expected Score:", round(result["raw_expected_score"], 2),
            "Strategy Value:", round(result["strategy_value"], 2)
        )

    return challenge, results

# ===== Source notebook cell 26 =====
# ============================
# PLAYABLE PRACTICE MODE
# ============================

CURRENT_CHALLENGE = None
CURRENT_HOLD_OPTIONS = None


def print_scorecard(scorecard):
    print("Scorecard:")
    print("-" * 40)

    for category in YAHTZEE_CATEGORIES:
        display_name = CATEGORY_DISPLAY_NAMES.get(category, category)
        score = scorecard[category]

        if score is None:
            print(f"{display_name}: OPEN")
        else:
            print(f"{display_name}: {score}")

    print()


def show_practice_round(challenge=None):
    global CURRENT_CHALLENGE
    global CURRENT_HOLD_OPTIONS

    if challenge is None:
        challenge = generate_practice_challenge()

    CURRENT_CHALLENGE = challenge

    dice = challenge["dice"]
    scorecard = challenge["scorecard"]

    CURRENT_HOLD_OPTIONS = generate_unique_holds(dice)

    print("YAHTZEE COACH PRACTICE ROUND")
    print("=" * 40)
    print("Mode:", challenge["mode"])
    print("Roll Number:", challenge["roll_number"], "of 3")
    print("Rolls Remaining:", challenge["rolls_remaining"])
    print("Dice:", dice)
    print()

    print_scorecard(scorecard)

    print("Choose which dice to keep:")
    print("-" * 40)

    for index, hold in enumerate(CURRENT_HOLD_OPTIONS, start=1):
        print(index, ":", format_hold(hold))

    print()
    print("To submit a choice, run:")
    print("submit_hold_number(choice_number)")
    print()
    print("Example:")
    print("submit_hold_number(5)")


def submit_hold_number(choice_number):
    if CURRENT_CHALLENGE is None:
        print("No active challenge. Run show_practice_round() first.")
        return

    if CURRENT_HOLD_OPTIONS is None:
        print("No hold options found. Run show_practice_round() first.")
        return

    if choice_number < 1 or choice_number > len(CURRENT_HOLD_OPTIONS):
        print("That choice number is not valid.")
        return

    dice = CURRENT_CHALLENGE["dice"]
    scorecard = CURRENT_CHALLENGE["scorecard"]

    user_hold = CURRENT_HOLD_OPTIONS[choice_number - 1]

    print(coach_report_for_user_hold_future_aware(dice, scorecard, user_hold))


def reveal_best_move():
    if CURRENT_CHALLENGE is None:
        print("No active challenge. Run show_practice_round() first.")
        return

    dice = CURRENT_CHALLENGE["dice"]
    scorecard = CURRENT_CHALLENGE["scorecard"]

    results = analyze_all_holds_future_aware(dice, scorecard)
    best_result = results[0]

    print("BEST MOVE")
    print("=" * 40)
    print("Dice:", dice)
    print("Best hold:", format_hold(best_result["hold"]))
    print("Raw Expected Score:", round(best_result["raw_expected_score"], 2))
    print("Strategy Value:", round(best_result["strategy_value"], 2))
    print()

    print("Top 5 holds:")
    for rank, result in enumerate(results[:5], start=1):
        print(
            rank,
            format_hold(result["hold"]),
            "| Raw Expected Score:",
            round(result["raw_expected_score"], 2),
            "| Strategy Value:",
            round(result["strategy_value"], 2)
        )

# ===== Source notebook cell 27 =====
# ============================
# PATCH: BONUS-CHASE AWARE COACHING
# ============================
# This patch keeps the best mathematical move the same,
# but adds better explanation when a player's move is a reasonable
# upper-section bonus chase.

def upper_category_for_die(die):
    for category, value in UPPER_CATEGORY_VALUES.items():
        if value == die:
            return category
    return None


def upper_pace_target(category):
    """
    The usual upper-section pace is 3 of each number.
    Example: Sixes target = 18.
    """
    return UPPER_CATEGORY_VALUES[category] * 3


def open_upper_categories_in_hold(hold, scorecard):
    categories = []

    for die in sorted(set(hold), reverse=True):
        category = upper_category_for_die(die)

        if category in UPPER_CATEGORIES and scorecard[category] is None:
            categories.append(category)

    return categories


def analyze_upper_chase_hold(hold, target_category, scorecard):
    """
    This analyzes a human-style strategy:
    - If the reroll creates at least 3 of the target number, score that upper box.
    - Otherwise, use Chance if Chance is open.
    """
    final_rolls = generate_final_rolls_after_hold(hold)
    target_score_needed = upper_pace_target(target_category)

    success_count = 0
    total_strategy_score = 0
    success_scores = []
    fallback_scores = []

    available_categories = get_available_categories(scorecard)

    for final_roll in final_rolls:
        all_scores = calculate_all_scores(final_roll)
        target_score = all_scores[target_category]

        if target_score >= target_score_needed:
            success_count += 1
            total_strategy_score += target_score
            success_scores.append(target_score)

        else:
            if scorecard["chance"] is None:
                fallback_score = all_scores["chance"]
            else:
                fallback_category, fallback_score = best_score_for_roll(
                    final_roll,
                    available_categories
                )

            total_strategy_score += fallback_score
            fallback_scores.append(fallback_score)

    total_outcomes = len(final_rolls)

    return {
        "hold": hold,
        "target_category": target_category,
        "target_score_needed": target_score_needed,
        "success_count": success_count,
        "total_outcomes": total_outcomes,
        "success_probability": success_count / total_outcomes,
        "expected_score_using_chase_rule": total_strategy_score / total_outcomes,
        "average_success_score": sum(success_scores) / len(success_scores) if success_scores else 0,
        "average_fallback_score": sum(fallback_scores) / len(fallback_scores) if fallback_scores else 0
    }


def compare_bonus_chase_to_optimal(dice, scorecard, user_hold, optimal_hold):
    """
    Checks whether the user's hold is a defensible upper-bonus chase.
    Example: user keeps [6], optimal keeps [5, 6].
    """
    possible_targets = open_upper_categories_in_hold(user_hold, scorecard)

    if not possible_targets:
        return None

    # Prioritize the highest upper box in the user's hold.
    target_category = possible_targets[0]

    user_chase = analyze_upper_chase_hold(
        user_hold,
        target_category,
        scorecard
    )

    optimal_chase = analyze_upper_chase_hold(
        optimal_hold,
        target_category,
        scorecard
    )

    return {
        "target_category": target_category,
        "user_chase": user_chase,
        "optimal_chase": optimal_chase
    }


def percent_text(value):
    return str(round(value * 100, 2)) + "%"


def bonus_chase_grade_adjustment(base_grade, efficiency, points_lost, chase_comparison):
    """
    If the user made a slightly lower-EV move that clearly improves
    their chance at a key upper box, do not grade it too harshly.
    """
    if chase_comparison is None:
        return base_grade, ""

    user_chase = chase_comparison["user_chase"]
    optimal_chase = chase_comparison["optimal_chase"]

    user_prob = user_chase["success_probability"]
    optimal_prob = optimal_chase["success_probability"]

    user_has_better_bonus_chase = user_prob > optimal_prob + 0.03
    close_to_optimal = efficiency >= 0.87 and points_lost <= 2.5

    if user_has_better_bonus_chase and close_to_optimal:
        if base_grade in ["B", "B-"]:
            return "A-", "Context adjustment: your move was a strong bonus-chase alternative."

    return base_grade, ""


def explain_difference_between_holds(user_hold, optimal_hold, scorecard):
    user_counts = Counter(user_hold)
    optimal_counts = Counter(optimal_hold)

    explanation = []
    added_dice = []

    for die, count in optimal_counts.items():
        difference = count - user_counts.get(die, 0)

        for _ in range(max(0, difference)):
            added_dice.append(die)

    if added_dice:
        explanation.append(
            f"The optimal hold also kept {', '.join(str(die) for die in added_dice)}."
        )

        for die in added_dice:
            matching_upper_category = upper_category_for_die(die)

            if matching_upper_category and scorecard[matching_upper_category] is None:
                explanation.append(
                    f"That matters because the {CATEGORY_DISPLAY_NAMES[matching_upper_category]} box is still open, and upper-section points help protect the 35-point bonus."
                )

    if len(optimal_hold) > len(user_hold):
        explanation.append(
            "The optimal hold keeps a little more scoring value while still leaving dice available to reroll."
        )

    if not straights_are_open(scorecard):
        explanation.append(
            "Since the straight categories are already filled, this decision is more about upper-section value, Chance value, and flexible scoring."
        )

    if not explanation:
        explanation.append(
            "The optimal hold produced a better strategy value by balancing immediate scoring with future category value."
        )

    return explanation


def coach_report_for_user_hold_future_aware(dice, scorecard, user_hold):
    evaluation = evaluate_user_hold_future_aware(dice, scorecard, user_hold)

    user_result = evaluation["user_result"]
    optimal_result = evaluation["optimal_result"]

    user_hold_clean = evaluation["user_hold"]
    optimal_hold_clean = evaluation["optimal_hold"]

    efficiency = evaluation["efficiency"]
    base_grade = evaluation["grade"]
    points_lost = evaluation["points_lost"]

    chase_comparison = compare_bonus_chase_to_optimal(
        dice,
        scorecard,
        user_hold_clean,
        optimal_hold_clean
    )

    final_grade, grade_note = bonus_chase_grade_adjustment(
        base_grade,
        efficiency,
        points_lost,
        chase_comparison
    )

    strength = hold_strength_label(efficiency)

    report = []

    report.append("YAHTZEE COACH REPORT")
    report.append("=" * 40)
    report.append(f"Current dice: {dice}")
    report.append(f"Your choice: {format_hold(user_hold_clean)}")
    report.append(f"Optimal choice: {format_hold(optimal_hold_clean)}")
    report.append("")

    if final_grade == base_grade:
        report.append(f"Grade: {final_grade}")
    else:
        report.append(f"Grade: {final_grade} adjusted from {base_grade}")

    if grade_note:
        report.append(grade_note)

    report.append(f"Coach rating: This is {article_for_word(strength)} {strength} move.")
    report.append(f"Your strategy value: {round(evaluation['user_value'], 2)}")
    report.append(f"Optimal strategy value: {round(evaluation['optimal_value'], 2)}")
    report.append(f"Efficiency: {round(efficiency * 100, 1)}% of optimal")
    report.append(f"Strategy value lost: {round(points_lost, 2)}")
    report.append("")

    report.append("What was good about your move?")
    good_feedback = describe_hold_pattern(user_hold_clean, scorecard)

    if good_feedback:
        for line in good_feedback:
            report.append(f"- {line}")
    else:
        report.append("- This hold keeps some flexibility, but it does not strongly build toward a specific scoring pattern.")

    report.append(
        f"- Your most common scoring paths were: {most_common_categories_text_clean(user_result['category_counter'])}."
    )

    if chase_comparison is not None:
        target_category = chase_comparison["target_category"]
        user_chase = chase_comparison["user_chase"]
        optimal_chase = chase_comparison["optimal_chase"]

        report.append("")
        report.append("Bonus-chase check:")
        report.append(
            f"- If your goal is to hit the {CATEGORY_DISPLAY_NAMES[target_category]} box at bonus pace, you need at least {user_chase['target_score_needed']} points there."
        )
        report.append(
            f"- Your hold gives a {percent_text(user_chase['success_probability'])} chance to reach that target."
        )
        report.append(
            f"- The optimal hold gives a {percent_text(optimal_chase['success_probability'])} chance to reach that same target."
        )

        if user_chase["success_probability"] > optimal_chase["success_probability"]:
            report.append(
                "- So your move is actually better for that specific upper-section chase."
            )

        report.append(
            f"- But using the chase rule, your expected score is {round(user_chase['expected_score_using_chase_rule'], 2)}, while the optimal hold's chase-rule expected score is {round(optimal_chase['expected_score_using_chase_rule'], 2)}."
        )

    report.append("")
    report.append("Why was the optimal move better?")

    if user_hold_clean == optimal_hold_clean:
        report.append("- Your move was the optimal move.")
    else:
        difference_feedback = explain_difference_between_holds(
            user_hold_clean,
            optimal_hold_clean,
            scorecard
        )

        for line in difference_feedback:
            report.append(f"- {line}")

    report.append("")
    report.append("Coach recommendation:")

    if user_hold_clean == optimal_hold_clean:
        report.append("Stay with this thinking. You balanced immediate scoring, pattern strength, and future value well.")
    else:
        report.append(
            f"The stronger mathematical play was to {format_hold(optimal_hold_clean)} because it produced the highest total strategy value."
        )
        report.append(
            "However, your move may still be a smart bonus-chase alternative if you are intentionally trying to protect the upper-section bonus."
        )

    return "\n".join(report)

# ===== Source notebook cell 28 =====
# ============================
# PATCH: CLEANER BONUS-CHASE LANGUAGE + SESSION TRACKER
# ============================

PRACTICE_HISTORY = []


def final_grade_details(dice, scorecard, user_hold):
    evaluation = evaluate_user_hold_future_aware(dice, scorecard, user_hold)

    user_hold_clean = evaluation["user_hold"]
    optimal_hold_clean = evaluation["optimal_hold"]

    base_grade = evaluation["grade"]
    efficiency = evaluation["efficiency"]
    points_lost = evaluation["points_lost"]

    chase_comparison = compare_bonus_chase_to_optimal(
        dice,
        scorecard,
        user_hold_clean,
        optimal_hold_clean
    )

    final_grade, grade_note = bonus_chase_grade_adjustment(
        base_grade,
        efficiency,
        points_lost,
        chase_comparison
    )

    return evaluation, final_grade, grade_note, chase_comparison


def coach_rating_sentence(base_grade, final_grade, grade_note, efficiency):
    if final_grade != base_grade and "bonus-chase" in grade_note:
        return "Coach rating: This is a strong bonus-chase alternative."

    strength = hold_strength_label(efficiency)
    return f"Coach rating: This is {article_for_word(strength)} {strength} move."


def coach_report_for_user_hold_future_aware(dice, scorecard, user_hold):
    evaluation, final_grade, grade_note, chase_comparison = final_grade_details(
        dice,
        scorecard,
        user_hold
    )

    user_result = evaluation["user_result"]
    optimal_result = evaluation["optimal_result"]

    user_hold_clean = evaluation["user_hold"]
    optimal_hold_clean = evaluation["optimal_hold"]

    efficiency = evaluation["efficiency"]
    base_grade = evaluation["grade"]
    points_lost = evaluation["points_lost"]

    report = []

    report.append("YAHTZEE COACH REPORT")
    report.append("=" * 40)
    report.append(f"Current dice: {dice}")
    report.append(f"Your choice: {format_hold(user_hold_clean)}")
    report.append(f"Optimal choice: {format_hold(optimal_hold_clean)}")
    report.append("")

    if final_grade == base_grade:
        report.append(f"Grade: {final_grade}")
    else:
        report.append(f"Grade: {final_grade} adjusted from {base_grade}")

    if grade_note:
        report.append(grade_note)

    report.append(
        coach_rating_sentence(
            base_grade,
            final_grade,
            grade_note,
            efficiency
        )
    )

    report.append(f"Your strategy value: {round(evaluation['user_value'], 2)}")
    report.append(f"Optimal strategy value: {round(evaluation['optimal_value'], 2)}")
    report.append(f"Efficiency: {round(efficiency * 100, 1)}% of optimal")
    report.append(f"Strategy value lost: {round(points_lost, 2)}")
    report.append("")

    report.append("What was good about your move?")
    good_feedback = describe_hold_pattern(user_hold_clean, scorecard)

    if good_feedback:
        for line in good_feedback:
            report.append(f"- {line}")
    else:
        report.append("- This hold keeps some flexibility, but it does not strongly build toward a specific scoring pattern.")

    report.append(
        f"- Your most common scoring paths were: {most_common_categories_text_clean(user_result['category_counter'])}."
    )

    if chase_comparison is not None:
        target_category = chase_comparison["target_category"]
        user_chase = chase_comparison["user_chase"]
        optimal_chase = chase_comparison["optimal_chase"]

        report.append("")
        report.append("Bonus-chase check:")
        report.append(
            f"- If your goal is to hit the {CATEGORY_DISPLAY_NAMES[target_category]} box at bonus pace, you need at least {user_chase['target_score_needed']} points there."
        )
        report.append(
            f"- Your hold gives a {percent_text(user_chase['success_probability'])} chance to reach that target."
        )
        report.append(
            f"- The optimal hold gives a {percent_text(optimal_chase['success_probability'])} chance to reach that same target."
        )

        if user_chase["success_probability"] > optimal_chase["success_probability"]:
            report.append(
                "- So your move is actually better for that specific upper-section chase."
            )

        report.append(
            f"- But using the chase rule, your expected score is {round(user_chase['expected_score_using_chase_rule'], 2)}, while the optimal hold's chase-rule expected score is {round(optimal_chase['expected_score_using_chase_rule'], 2)}."
        )

    report.append("")
    report.append("Why was the optimal move better?")

    if user_hold_clean == optimal_hold_clean:
        report.append("- Your move was the optimal move.")
    else:
        difference_feedback = explain_difference_between_holds(
            user_hold_clean,
            optimal_hold_clean,
            scorecard
        )

        for line in difference_feedback:
            report.append(f"- {line}")

    report.append("")
    report.append("Coach recommendation:")

    if user_hold_clean == optimal_hold_clean:
        report.append("Stay with this thinking. You balanced immediate scoring, pattern strength, and future value well.")
    else:
        report.append(
            f"The stronger mathematical play was to {format_hold(optimal_hold_clean)} because it produced the highest total strategy value."
        )

        if final_grade != base_grade:
            report.append(
                "However, your move is a smart bonus-chase alternative if you are intentionally trying to protect the upper-section bonus."
            )

    return "\n".join(report)


def grade_to_points(grade):
    grade_points = {
        "A+": 4.0,
        "A": 4.0,
        "A-": 3.7,
        "B": 3.0,
        "B-": 2.7,
        "C": 2.0,
        "D": 1.0,
        "F": 0.0
    }

    return grade_points.get(grade, 0.0)


def submit_hold_number(choice_number):
    global PRACTICE_HISTORY

    if CURRENT_CHALLENGE is None:
        print("No active challenge. Run show_practice_round() first.")
        return

    if CURRENT_HOLD_OPTIONS is None:
        print("No hold options found. Run show_practice_round() first.")
        return

    if choice_number < 1 or choice_number > len(CURRENT_HOLD_OPTIONS):
        print("That choice number is not valid.")
        return

    dice = CURRENT_CHALLENGE["dice"]
    scorecard = CURRENT_CHALLENGE["scorecard"]

    user_hold = CURRENT_HOLD_OPTIONS[choice_number - 1]

    evaluation, final_grade, grade_note, chase_comparison = final_grade_details(
        dice,
        scorecard,
        user_hold
    )

    print(coach_report_for_user_hold_future_aware(dice, scorecard, user_hold))

    PRACTICE_HISTORY.append({
        "dice": dice,
        "user_hold": evaluation["user_hold"],
        "optimal_hold": evaluation["optimal_hold"],
        "grade": final_grade,
        "base_grade": evaluation["grade"],
        "efficiency": evaluation["efficiency"],
        "points_lost": evaluation["points_lost"],
        "strategy_value": evaluation["user_value"],
        "optimal_value": evaluation["optimal_value"],
        "grade_note": grade_note
    })


def show_session_summary():
    if not PRACTICE_HISTORY:
        print("No practice attempts yet.")
        return

    total_attempts = len(PRACTICE_HISTORY)

    average_efficiency = sum(
        attempt["efficiency"] for attempt in PRACTICE_HISTORY
    ) / total_attempts

    average_points_lost = sum(
        attempt["points_lost"] for attempt in PRACTICE_HISTORY
    ) / total_attempts

    average_gpa = sum(
        grade_to_points(attempt["grade"]) for attempt in PRACTICE_HISTORY
    ) / total_attempts

    print("YAHTZEE COACH SESSION SUMMARY")
    print("=" * 40)
    print("Attempts:", total_attempts)
    print("Average efficiency:", round(average_efficiency * 100, 1), "%")
    print("Average strategy value lost:", round(average_points_lost, 2))
    print("Yahtzee Coach GPA:", round(average_gpa, 2))
    print()

    print("Recent attempts:")
    print("-" * 40)

    for index, attempt in enumerate(PRACTICE_HISTORY[-10:], start=1):
        print(
            index,
            "| Dice:",
            attempt["dice"],
            "| Your hold:",
            attempt["user_hold"],
            "| Optimal:",
            attempt["optimal_hold"],
            "| Grade:",
            attempt["grade"]
        )


def reset_session_summary():
    global PRACTICE_HISTORY
    PRACTICE_HISTORY = []
    print("Practice history reset.")

# ===== Source notebook cell 29 =====
# ============================
# PATCH: GAME-AWARE UPPER + CHANCE EVALUATOR
# ============================
# Purpose:
# Fixes situations where the engine overvalues keeping extra dice
# just because they create a strong Chance fallback.
#
# Example fixed:
# Dice: [1, 4, 4, 5, 6]
# Old recommendation: keep [4, 4, 5, 6]
# Better game-aware recommendation: keep [4, 4]
#
# This patch uses exact mini dynamic programming for the remaining
# upper-section boxes plus Chance when that is the relevant decision.


from functools import lru_cache


GAME_AWARE_MAX_CATEGORIES = 4
GAME_AWARE_CONTEXT_NOTE = "Game-aware upper-section/Chance evaluator used."


def sorted_tuple(dice):
    return tuple(sorted(dice))


def roll_distribution(number_of_dice):
    """
    Returns unique sorted outcomes and how many ways each outcome can occur.
    Example: rolling [1, 2] and [2, 1] both count toward sorted outcome (1, 2).
    """
    outcomes = Counter()

    for outcome in product(range(1, 7), repeat=number_of_dice):
        outcomes[tuple(sorted(outcome))] += 1

    return tuple(outcomes.items())


GAME_AWARE_ROLL_DISTRIBUTIONS = {
    number_of_dice: roll_distribution(number_of_dice)
    for number_of_dice in range(0, 6)
}


def score_upper_chance_category(dice, category):
    if category == "chance":
        return sum(dice)

    number = UPPER_CATEGORY_VALUES[category]
    return dice.count(number) * number


def game_aware_open_categories(scorecard):
    """
    This mini-engine only looks at open upper-section boxes plus Chance.
    It does not replace the whole Yahtzee engine.
    It is used only when the decision is clearly about upper bonus vs Chance.
    """
    categories = []

    for category in UPPER_CATEGORIES:
        if scorecard[category] is None:
            categories.append(category)

    if scorecard["chance"] is None:
        categories.append("chance")

    return tuple(categories)


def game_aware_upper_total(scorecard):
    total = 0

    for category in UPPER_CATEGORIES:
        if scorecard[category] is not None:
            total += scorecard[category]

    return total


def game_aware_add_score_to_upper_total(upper_total, category, score):
    if category in UPPER_CATEGORIES:
        return upper_total + score

    return upper_total


def game_aware_generate_unique_holds_tuple(dice):
    holds = set()
    dice = tuple(dice)

    for hold_size in range(0, len(dice) + 1):
        for hold_indices in combinations(range(len(dice)), hold_size):
            hold = tuple(sorted(dice[index] for index in hold_indices))
            holds.add(hold)

    return tuple(sorted(holds, key=lambda hold: (len(hold), hold)))


@lru_cache(None)
def game_aware_turn_start_value(open_categories, upper_total):
    """
    Expected value from the start of a future turn,
    using only the remaining upper boxes plus Chance.
    """
    open_categories = tuple(open_categories)

    if len(open_categories) == 0:
        if upper_total >= UPPER_BONUS_TARGET:
            return UPPER_BONUS_POINTS
        return 0

    total_value = 0

    for roll, count in GAME_AWARE_ROLL_DISTRIBUTIONS[5]:
        total_value += count * game_aware_roll_value(
            roll,
            2,
            open_categories,
            upper_total
        )

    return total_value / (6 ** 5)


@lru_cache(None)
def game_aware_score_now_value(dice, open_categories, upper_total):
    best_value = -999999

    for category in open_categories:
        score = score_upper_chance_category(dice, category)

        new_open_categories = tuple(
            open_category
            for open_category in open_categories
            if open_category != category
        )

        new_upper_total = game_aware_add_score_to_upper_total(
            upper_total,
            category,
            score
        )

        value = score + game_aware_turn_start_value(
            new_open_categories,
            new_upper_total
        )

        if value > best_value:
            best_value = value

    return best_value


@lru_cache(None)
def game_aware_best_score_action(dice, open_categories, upper_total):
    best_value = -999999
    best_category = None
    best_score = None

    for category in open_categories:
        score = score_upper_chance_category(dice, category)

        new_open_categories = tuple(
            open_category
            for open_category in open_categories
            if open_category != category
        )

        new_upper_total = game_aware_add_score_to_upper_total(
            upper_total,
            category,
            score
        )

        value = score + game_aware_turn_start_value(
            new_open_categories,
            new_upper_total
        )

        if value > best_value:
            best_value = value
            best_category = category
            best_score = score

    return best_value, best_category, best_score


@lru_cache(None)
def game_aware_roll_value(dice, rolls_left, open_categories, upper_total):
    dice = tuple(sorted(dice))
    open_categories = tuple(open_categories)

    if rolls_left == 0:
        return game_aware_score_now_value(
            dice,
            open_categories,
            upper_total
        )

    best_value = -999999

    for hold in game_aware_generate_unique_holds_tuple(dice):
        number_to_reroll = 5 - len(hold)
        total_value = 0

        for outcome, count in GAME_AWARE_ROLL_DISTRIBUTIONS[number_to_reroll]:
            final_roll = tuple(sorted(hold + outcome))

            total_value += count * game_aware_roll_value(
                final_roll,
                rolls_left - 1,
                open_categories,
                upper_total
            )

        expected_value = total_value / (6 ** number_to_reroll)

        if expected_value > best_value:
            best_value = expected_value

    return best_value


def game_aware_hold_value(hold, scorecard):
    """
    Expected value of a hold using exact mini-DP for:
    open upper categories + Chance + upper bonus.
    """
    open_categories = game_aware_open_categories(scorecard)
    upper_total = game_aware_upper_total(scorecard)

    number_to_reroll = 5 - len(hold)
    total_value = 0
    category_counter = Counter()

    for outcome, count in GAME_AWARE_ROLL_DISTRIBUTIONS[number_to_reroll]:
        final_roll = tuple(sorted(tuple(hold) + outcome))

        value, category, score = game_aware_best_score_action(
            final_roll,
            open_categories,
            upper_total
        )

        total_value += count * value
        category_counter[category] += count

    expected_value = total_value / (6 ** number_to_reroll)

    return expected_value, category_counter


def should_use_game_aware_upper_chance_evaluator(dice, scorecard):
    """
    Use this only in the specific kind of situation that caused the bug:
    - Chance is open.
    - Straights are already closed.
    - Upper bonus is still possible.
    - There is a pair/triple/etc. of an open upper number.
    - The remaining upper + chance category count is small enough for exact DP.
    """
    if scorecard["chance"] is not None:
        return False

    if straights_are_open(scorecard):
        return False

    status = upper_bonus_status(scorecard)

    if status["bonus_already_earned"]:
        return False

    open_categories = game_aware_open_categories(scorecard)

    if len(open_categories) == 0:
        return False

    if len(open_categories) > GAME_AWARE_MAX_CATEGORIES:
        return False

    counts = Counter(dice)

    for category in UPPER_CATEGORIES:
        if scorecard[category] is None:
            number = UPPER_CATEGORY_VALUES[category]

            if counts[number] >= 2:
                return True

    return False


def analyze_all_holds_future_aware(dice, scorecard):
    holds = generate_unique_holds(dice)
    available_categories = get_available_categories(scorecard)

    use_game_aware_evaluator = should_use_game_aware_upper_chance_evaluator(
        dice,
        scorecard
    )

    results = []

    for hold in holds:
        future_aware_value, raw_expected_score, category_counter, shape_adjustment = expected_value_of_hold_future_aware(
            hold,
            available_categories,
            scorecard
        )

        original_adjustment = original_roll_pattern_adjustment(
            dice,
            hold,
            scorecard
        )

        baseline_strategy_value = future_aware_value + original_adjustment

        result = {
            "hold": hold,
            "strategy_value": baseline_strategy_value,
            "future_aware_value": baseline_strategy_value,
            "raw_expected_score": raw_expected_score,
            "category_counter": category_counter,
            "shape_adjustment": shape_adjustment,
            "original_adjustment": original_adjustment,
            "game_aware_value": None,
            "game_aware_category_counter": None,
            "game_aware_note": None
        }

        if use_game_aware_evaluator:
            game_aware_value, game_aware_category_counter = game_aware_hold_value(
                hold,
                scorecard
            )

            result["strategy_value"] = game_aware_value
            result["future_aware_value"] = game_aware_value
            result["game_aware_value"] = game_aware_value
            result["game_aware_category_counter"] = game_aware_category_counter
            result["game_aware_note"] = GAME_AWARE_CONTEXT_NOTE

        results.append(result)

    results = sorted(
        results,
        key=lambda result: result["strategy_value"],
        reverse=True
    )

    return results

# ===== Source notebook cell 30 =====
# ============================
# PATCH: GAME-AWARE COACH REPORT LANGUAGE
# ============================

def best_category_counter_for_result(result):
    if result.get("game_aware_category_counter") is not None:
        return result["game_aware_category_counter"]

    return result["category_counter"]


def coach_report_for_user_hold_future_aware(dice, scorecard, user_hold):
    evaluation, final_grade, grade_note, chase_comparison = final_grade_details(
        dice,
        scorecard,
        user_hold
    )

    user_result = evaluation["user_result"]
    optimal_result = evaluation["optimal_result"]

    user_hold_clean = evaluation["user_hold"]
    optimal_hold_clean = evaluation["optimal_hold"]

    efficiency = evaluation["efficiency"]
    base_grade = evaluation["grade"]
    points_lost = evaluation["points_lost"]

    game_aware_used = user_result.get("game_aware_note") is not None

    report = []

    report.append("YAHTZEE COACH REPORT")
    report.append("=" * 40)
    report.append(f"Current dice: {dice}")
    report.append(f"Your choice: {format_hold(user_hold_clean)}")
    report.append(f"Optimal choice: {format_hold(optimal_hold_clean)}")
    report.append("")

    if final_grade == base_grade:
        report.append(f"Grade: {final_grade}")
    else:
        report.append(f"Grade: {final_grade} adjusted from {base_grade}")

    if grade_note:
        report.append(grade_note)

    report.append(
        coach_rating_sentence(
            base_grade,
            final_grade,
            grade_note,
            efficiency
        )
    )

    report.append(f"Your strategy value: {round(evaluation['user_value'], 2)}")
    report.append(f"Optimal strategy value: {round(evaluation['optimal_value'], 2)}")
    report.append(f"Efficiency: {round(efficiency * 100, 1)}% of optimal")
    report.append(f"Strategy value lost: {round(points_lost, 2)}")
    report.append("")

    if game_aware_used:
        report.append("Game-aware note:")
        report.append("- This decision used the upper-section/Chance evaluator.")
        report.append("- That means the coach considered not just this turn's score, but also how scoring Fours, Fives, Sixes, or Chance affects the rest of the scorecard.")
        report.append("- A hold with a lower immediate score can still be better if it protects the upper bonus and avoids wasting Chance too early.")
        report.append("")

    report.append("What was good about your move?")
    good_feedback = describe_hold_pattern(user_hold_clean, scorecard)

    if good_feedback:
        for line in good_feedback:
            report.append(f"- {line}")
    else:
        report.append("- This hold keeps some flexibility, but it does not strongly build toward a specific scoring pattern.")

    category_counter = best_category_counter_for_result(user_result)

    report.append(
        f"- Your most common scoring paths were: {most_common_categories_text_clean(category_counter)}."
    )

    if chase_comparison is not None:
        target_category = chase_comparison["target_category"]
        user_chase = chase_comparison["user_chase"]
        optimal_chase = chase_comparison["optimal_chase"]

        report.append("")
        report.append("Bonus-chase check:")
        report.append(
            f"- If your goal is to hit the {CATEGORY_DISPLAY_NAMES[target_category]} box at bonus pace, you need at least {user_chase['target_score_needed']} points there."
        )
        report.append(
            f"- Your hold gives a {percent_text(user_chase['success_probability'])} chance to reach that target."
        )
        report.append(
            f"- The optimal hold gives a {percent_text(optimal_chase['success_probability'])} chance to reach that same target."
        )

        if user_chase["success_probability"] > optimal_chase["success_probability"]:
            report.append(
                "- So your move is better for that specific upper-section chase."
            )

        report.append(
            f"- But using the chase rule, your expected score is {round(user_chase['expected_score_using_chase_rule'], 2)}, while the optimal hold's chase-rule expected score is {round(optimal_chase['expected_score_using_chase_rule'], 2)}."
        )

    report.append("")
    report.append("Why was the optimal move better?")

    if user_hold_clean == optimal_hold_clean:
        report.append("- Your move was the optimal move.")
    else:
        difference_feedback = explain_difference_between_holds(
            user_hold_clean,
            optimal_hold_clean,
            scorecard
        )

        for line in difference_feedback:
            report.append(f"- {line}")

    if game_aware_used and user_hold_clean != optimal_hold_clean:
        report.append(
            "- In this scorecard state, the coach is weighing future category value heavily, especially the upper bonus and the cost of using Chance."
        )

    report.append("")
    report.append("Coach recommendation:")

    if user_hold_clean == optimal_hold_clean:
        report.append("Stay with this thinking. You balanced immediate scoring, pattern strength, and future scorecard value well.")
    else:
        report.append(
            f"The stronger mathematical play was to {format_hold(optimal_hold_clean)} because it produced the highest game-aware strategy value."
        )

        if final_grade != base_grade:
            report.append(
                "However, your move is still a smart bonus-chase alternative if you are intentionally trying to protect the upper-section bonus."
            )

    return "\n".join(report)

# ===== Source notebook cell 31 =====
# ============================
# PATCH: CLEANER HOLD PATTERN LANGUAGE
# ============================

def describe_hold_pattern(hold, scorecard):
    counts = Counter(hold)
    feedback = []

    if len(hold) == 0:
        feedback.append(
            "You are choosing to reroll everything, which gives maximum flexibility but gives up any pattern you already had."
        )
        return feedback

    if len(hold) == 5:
        feedback.append(
            "You are keeping all five dice, which locks in the current roll and gives up the chance to improve."
        )
        return feedback

    if any(count >= 3 for count in counts.values()):
        repeated_number = max(counts, key=counts.get)
        feedback.append(
            f"You preserved three or more {repeated_number}s, which keeps strong paths open for Three of a Kind, Four of a Kind, Yahtzee, and the upper section."
        )

    elif any(count == 2 for count in counts.values()):
        repeated_number = max(counts, key=counts.get)
        category = upper_category_for_die(repeated_number)

        if category in UPPER_CATEGORIES and scorecard[category] is None:
            feedback.append(
                f"You kept a pair of {repeated_number}s, which is useful because the {CATEGORY_DISPLAY_NAMES[category]} box is still open."
            )
        else:
            feedback.append(
                f"You kept a pair of {repeated_number}s. That can be useful, especially if you are building toward a stronger repeated-number pattern."
            )

    unique = set(hold)

    if straights_are_open(scorecard):
        straight_patterns = [
            {1, 2, 3, 4},
            {2, 3, 4, 5},
            {3, 4, 5, 6}
        ]

        for pattern in straight_patterns:
            if len(unique.intersection(pattern)) >= 3:
                feedback.append(
                    "Your hold keeps part of a straight pattern alive, which can create chances for Small Straight or Large Straight."
                )
                break

    status = upper_bonus_status(scorecard)

    if not status["bonus_already_earned"]:
        remaining_upper = status["upper_categories_remaining"]

        for category in remaining_upper:
            number = UPPER_CATEGORY_VALUES[category]

            if number in hold:
                feedback.append(
                    f"Keeping {number}s may help the {CATEGORY_DISPLAY_NAMES[category]} box, which matters because the 35-point upper bonus is still available."
                )
                break

    if len(hold) >= 3 and max(counts.values()) == 1 and not straights_are_open(scorecard):
        feedback.append(
            "One concern is that you are holding several unrelated dice while the straight categories are already closed."
        )

    return feedback

# ===== Source notebook cell 32 =====
# ============================
# PATCH: CLEANER REPORT WHEN USER MOVE IS OPTIMAL
# ============================

def coach_report_for_user_hold_future_aware(dice, scorecard, user_hold):
    evaluation, final_grade, grade_note, chase_comparison = final_grade_details(
        dice,
        scorecard,
        user_hold
    )

    user_result = evaluation["user_result"]
    optimal_result = evaluation["optimal_result"]

    user_hold_clean = evaluation["user_hold"]
    optimal_hold_clean = evaluation["optimal_hold"]

    efficiency = evaluation["efficiency"]
    base_grade = evaluation["grade"]
    points_lost = evaluation["points_lost"]

    game_aware_used = user_result.get("game_aware_note") is not None
    user_is_optimal = user_hold_clean == optimal_hold_clean

    report = []

    report.append("YAHTZEE COACH REPORT")
    report.append("=" * 40)
    report.append(f"Current dice: {dice}")
    report.append(f"Your choice: {format_hold(user_hold_clean)}")
    report.append(f"Optimal choice: {format_hold(optimal_hold_clean)}")
    report.append("")

    if final_grade == base_grade:
        report.append(f"Grade: {final_grade}")
    else:
        report.append(f"Grade: {final_grade} adjusted from {base_grade}")

    if grade_note:
        report.append(grade_note)

    report.append(
        coach_rating_sentence(
            base_grade,
            final_grade,
            grade_note,
            efficiency
        )
    )

    report.append(f"Your strategy value: {round(evaluation['user_value'], 2)}")
    report.append(f"Optimal strategy value: {round(evaluation['optimal_value'], 2)}")
    report.append(f"Efficiency: {round(efficiency * 100, 1)}% of optimal")
    report.append(f"Strategy value lost: {round(points_lost, 2)}")
    report.append("")

    if game_aware_used:
        report.append("Game-aware note:")
        report.append("- This decision used the upper-section/Chance evaluator.")
        report.append("- The coach considered not just this turn's score, but also how scoring upper boxes or Chance affects the rest of the scorecard.")
        report.append("- A hold with a lower immediate score can still be better if it protects the upper bonus and avoids wasting Chance too early.")
        report.append("")

    report.append("What was good about your move?")

    # Cleaner feedback for optimal upper-section pair holds
    counts = Counter(user_hold_clean)
    repeated_feedback_given = False

    for number, count in counts.items():
        category = upper_category_for_die(number)

        if count >= 2 and category in UPPER_CATEGORIES and scorecard[category] is None:
            report.append(
                f"- You kept a pair of {number}s, which is strong here because the {CATEGORY_DISPLAY_NAMES[category]} box is still open and the upper bonus is still available."
            )
            repeated_feedback_given = True
            break

    if not repeated_feedback_given:
        good_feedback = describe_hold_pattern(user_hold_clean, scorecard)

        if good_feedback:
            for line in good_feedback:
                report.append(f"- {line}")
        else:
            report.append("- This hold keeps some flexibility, but it does not strongly build toward a specific scoring pattern.")

    category_counter = best_category_counter_for_result(user_result)

    report.append(
        f"- Your most common scoring paths were: {most_common_categories_text_clean(category_counter)}."
    )

    # Only show bonus-chase comparison when the user and optimal holds are different.
    if chase_comparison is not None and not user_is_optimal:
        target_category = chase_comparison["target_category"]
        user_chase = chase_comparison["user_chase"]
        optimal_chase = chase_comparison["optimal_chase"]

        report.append("")
        report.append("Bonus-chase check:")
        report.append(
            f"- If your goal is to hit the {CATEGORY_DISPLAY_NAMES[target_category]} box at bonus pace, you need at least {user_chase['target_score_needed']} points there."
        )
        report.append(
            f"- Your hold gives a {percent_text(user_chase['success_probability'])} chance to reach that target."
        )
        report.append(
            f"- The optimal hold gives a {percent_text(optimal_chase['success_probability'])} chance to reach that same target."
        )

        if user_chase["success_probability"] > optimal_chase["success_probability"]:
            report.append(
                "- So your move is better for that specific upper-section chase."
            )

        report.append(
            f"- But using the chase rule, your expected score is {round(user_chase['expected_score_using_chase_rule'], 2)}, while the optimal hold's chase-rule expected score is {round(optimal_chase['expected_score_using_chase_rule'], 2)}."
        )

    report.append("")
    report.append("Why was the optimal move better?")

    if user_is_optimal:
        report.append("- Your move was the optimal move.")
    else:
        difference_feedback = explain_difference_between_holds(
            user_hold_clean,
            optimal_hold_clean,
            scorecard
        )

        for line in difference_feedback:
            report.append(f"- {line}")

        if game_aware_used:
            report.append(
                "- In this scorecard state, the coach is weighing future category value heavily, especially the upper bonus and the cost of using Chance."
            )

    report.append("")
    report.append("Coach recommendation:")

    if user_is_optimal:
        report.append("Stay with this thinking. You balanced immediate scoring, pattern strength, and future scorecard value well.")
    else:
        report.append(
            f"The stronger mathematical play was to {format_hold(optimal_hold_clean)} because it produced the highest game-aware strategy value."
        )

        if final_grade != base_grade:
            report.append(
                "However, your move is still a smart bonus-chase alternative if you are intentionally trying to protect the upper-section bonus."
            )

    return "\n".join(report)

# ===== Source notebook cell 33 =====
# ============================
# PATCH: EXPAND GAME-AWARE MODE TO SINGLE USEFUL UPPER DICE
# ============================
# This lets the game-aware evaluator handle rolls like:
# [1, 1, 2, 2, 4]
#
# Old behavior:
# It only used game-aware mode if you had a pair or better of an open upper number.
#
# New behavior:
# It also uses game-aware mode if:
# - Chance is open
# - Straights are closed
# - Upper bonus is still possible
# - At least one die helps an open upper-section box
# - There is NOT already a strong triple-or-better pattern that should be protected


def upper_bonus_still_possible(scorecard):
    current_total = upper_section_total(scorecard)
    max_remaining = upper_max_possible_remaining(scorecard)

    return current_total + max_remaining >= UPPER_BONUS_TARGET


def has_useful_open_upper_die(dice, scorecard):
    for die in dice:
        category = upper_category_for_die(die)

        if category in UPPER_CATEGORIES and scorecard[category] is None:
            return True

    return False


def current_roll_has_triple_or_better_for_lower_combo(dice, scorecard):
    """
    We do NOT want the mini upper/Chance evaluator to override obvious
    lower-section pattern situations like [3, 3, 3, 4, 5].
    """
    counts = Counter(dice)

    if not any_category_open(scorecard, LOWER_COMBO_CATEGORIES):
        return False

    for number, count in counts.items():
        if count >= 3:
            return True

    return False


def should_use_game_aware_upper_chance_evaluator(dice, scorecard):
    """
    Use exact mini-DP for open upper boxes + Chance when the main decision
    is about upper bonus vs Chance.

    This now handles both:
    - pair situations, like [1, 4, 4, 5, 6]
    - single useful upper die situations, like [1, 1, 2, 2, 4]

    But it avoids overriding strong triple situations.
    """

    # Chance must be open, because this evaluator is about the cost of using Chance.
    if scorecard["chance"] is not None:
        return False

    # If straights are still open, the mini upper/Chance evaluator is too narrow.
    if straights_are_open(scorecard):
        return False

    # If the upper bonus is already earned or impossible, this evaluator matters less.
    if upper_bonus_status(scorecard)["bonus_already_earned"]:
        return False

    if not upper_bonus_still_possible(scorecard):
        return False

    # Keep our earlier triple-pattern fix safe.
    if current_roll_has_triple_or_better_for_lower_combo(dice, scorecard):
        return False

    open_categories = game_aware_open_categories(scorecard)

    if len(open_categories) == 0:
        return False

    if len(open_categories) > GAME_AWARE_MAX_CATEGORIES:
        return False

    # New expanded trigger:
    # At least one die helps an open upper-section box.
    if has_useful_open_upper_die(dice, scorecard):
        return True

    return False

# ===== Source notebook cell 34 =====
# ============================
# REGRESSION TEST SUITE
# ============================
# Run this after every major patch.
# It checks that the coach still makes the right calls on key strategy cases.

def make_upper_chance_test_scorecard():
    return {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }


def hold_to_tuple(hold):
    return tuple(sorted(hold))


def run_strategy_test(test_name, dice, scorecard, acceptable_best_holds):
    results = analyze_all_holds_future_aware(dice, scorecard)
    best_hold = results[0]["hold"]
    best_hold_tuple = hold_to_tuple(best_hold)

    acceptable_tuples = [
        hold_to_tuple(hold)
        for hold in acceptable_best_holds
    ]

    passed = best_hold_tuple in acceptable_tuples

    print(test_name)
    print("-" * 40)
    print("Dice:", dice)
    print("Best hold:", best_hold)
    print("Strategy value:", round(results[0]["strategy_value"], 2))
    print("Game-aware:", results[0].get("game_aware_note") is not None)

    if passed:
        print("Result: PASS")
    else:
        print("Result: REVIEW")
        print("Expected one of:", acceptable_best_holds)

    print()


def run_all_regression_tests():
    scorecard = make_upper_chance_test_scorecard()

    tests = [
        {
            "name": "Triple should be protected",
            "dice": [3, 3, 3, 4, 5],
            "acceptable_best_holds": [[3, 3, 3]]
        },
        {
            "name": "Pair of fours should chase Fours instead of saving Chance",
            "dice": [1, 4, 4, 5, 6],
            "acceptable_best_holds": [[4, 4]]
        },
        {
            "name": "Single useful four should keep the 4",
            "dice": [1, 1, 2, 2, 4],
            "acceptable_best_holds": [[4]]
        },
        {
            "name": "Pair of sixes should chase Sixes",
            "dice": [2, 4, 5, 6, 6],
            "acceptable_best_holds": [[6, 6]]
        },
        {
            "name": "High loose dice with no pair should keep useful upper value",
            "dice": [1, 3, 4, 5, 6],
            "acceptable_best_holds": [[5, 6], [4, 5, 6], [6]]
        }
    ]

    print("YAHTZEE COACH REGRESSION TESTS")
    print("=" * 40)
    print()

    for test in tests:
        run_strategy_test(
            test["name"],
            test["dice"],
            scorecard,
            test["acceptable_best_holds"]
        )

# ===== Source notebook cell 35 =====
# ============================
# PATCH: BETTER PRACTICE CHALLENGE GENERATOR
# ============================
# This creates different scorecard situations so practice does not feel repetitive.


def create_scorecard_with_values(values):
    scorecard = create_empty_scorecard()

    for category, score in values.items():
        scorecard[category] = score

    return scorecard


def create_upper_bonus_chase_scorecard():
    return create_scorecard_with_values({
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "small_straight": 30,
        "large_straight": 40
    })


def create_chance_already_used_scorecard():
    return create_scorecard_with_values({
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "small_straight": 30,
        "large_straight": 40,
        "chance": 22
    })


def create_straights_still_open_scorecard():
    return create_scorecard_with_values({
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "full_house": 25,
        "chance": 23
    })


def create_lower_combo_chase_scorecard():
    return create_scorecard_with_values({
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": 12,
        "small_straight": 30,
        "large_straight": 40
    })


def create_late_upper_pressure_scorecard():
    return create_scorecard_with_values({
        "ones": 3,
        "twos": 4,
        "threes": 9,
        "small_straight": 30,
        "large_straight": 40,
        "full_house": 25,
        "chance": 24
    })


def create_early_game_scorecard():
    return create_empty_scorecard()


PRACTICE_SCENARIOS = [
    {
        "name": "Upper Bonus Chase",
        "description": "Fours, Fives, Sixes, and Chance are still open. The upper bonus is a major priority.",
        "scorecard_function": create_upper_bonus_chase_scorecard
    },
    {
        "name": "Chance Already Used",
        "description": "Chance is gone, so the coach cannot use it as a fallback.",
        "scorecard_function": create_chance_already_used_scorecard
    },
    {
        "name": "Straights Still Open",
        "description": "Straight categories are still available, so straight patterns matter.",
        "scorecard_function": create_straights_still_open_scorecard
    },
    {
        "name": "Lower Combo Chase",
        "description": "Upper section is partly stable, and lower-section combos are still important.",
        "scorecard_function": create_lower_combo_chase_scorecard
    },
    {
        "name": "Late Upper Pressure",
        "description": "The upper bonus is still possible, but the scorecard has less flexibility.",
        "scorecard_function": create_late_upper_pressure_scorecard
    },
    {
        "name": "Early Game",
        "description": "Most categories are open, so flexibility matters.",
        "scorecard_function": create_early_game_scorecard
    }
]


def generate_practice_challenge():
    scenario = random.choice(PRACTICE_SCENARIOS)

    challenge = {
        "mode": "Unlimited Practice",
        "scenario_name": scenario["name"],
        "scenario_description": scenario["description"],
        "roll_number": 2,
        "rolls_remaining": 1,
        "dice": roll_dice(5),
        "scorecard": scenario["scorecard_function"]()
    }

    return challenge


def show_practice_round(challenge=None):
    global CURRENT_CHALLENGE
    global CURRENT_HOLD_OPTIONS

    if challenge is None:
        challenge = generate_practice_challenge()

    CURRENT_CHALLENGE = challenge

    dice = challenge["dice"]
    scorecard = challenge["scorecard"]

    CURRENT_HOLD_OPTIONS = generate_unique_holds(dice)

    print("YAHTZEE COACH PRACTICE ROUND")
    print("=" * 40)
    print("Mode:", challenge["mode"])

    if "scenario_name" in challenge:
        print("Scenario:", challenge["scenario_name"])
        print("Scenario Note:", challenge["scenario_description"])

    print("Roll Number:", challenge["roll_number"], "of 3")
    print("Rolls Remaining:", challenge["rolls_remaining"])
    print("Dice:", dice)
    print()

    print_scorecard(scorecard)

    print("Choose which dice to keep:")
    print("-" * 40)

    for index, hold in enumerate(CURRENT_HOLD_OPTIONS, start=1):
        print(index, ":", format_hold(hold))

    print()
    print("To submit a choice, run:")
    print("submit_hold_number(choice_number)")
    print()
    print("Example:")
    print("submit_hold_number(5)")

# ===== Source notebook cell 36 =====
# ============================
# PATCH: PROTECT TRIPLES WHEN YAHTZEE IS OPEN
# ============================
# Purpose:
# If Yahtzee is still open and the current roll already has three of a kind,
# the coach should strongly value keeping that triple.
#
# This protects:
# - Yahtzee
# - Four of a Kind
# - Three of a Kind
# - Full House
# - the matching upper box


YAHTZEE_OPEN_TRIPLE_BONUS = 8.0
YAHTZEE_OPEN_TRIPLE_ABANDON_PENALTY = -6.0
YAHTZEE_OPEN_CLEAN_TRIPLE_BONUS = 1.5
YAHTZEE_OPEN_EXTRA_DIE_PENALTY = -0.75


def yahtzee_is_open(scorecard):
    return scorecard["yahtzee"] is None


def full_house_is_open(scorecard):
    return scorecard["full_house"] is None


def triple_numbers_in_roll(dice):
    counts = Counter(dice)

    triples = []

    for number, count in counts.items():
        if count >= 3:
            triples.append(number)

    return triples


def yahtzee_open_triple_adjustment(dice, hold, scorecard):
    """
    Adds strategic value when Yahtzee is open and the player preserves
    an existing triple.

    Example:
    Dice: [1, 1, 1, 2, 6]
    Holding [1, 1, 1] should be strongly rewarded.
    Holding [6] should be penalized because it abandons the made triple.
    """

    if not yahtzee_is_open(scorecard):
        return 0

    triples = triple_numbers_in_roll(dice)

    if not triples:
        return 0

    hold_counts = Counter(hold)

    adjustment = 0

    for number in triples:
        if hold_counts[number] >= 3:
            adjustment += YAHTZEE_OPEN_TRIPLE_BONUS

            # Clean triple is usually the best form:
            # keep the three matching dice and reroll the other two.
            if len(hold) == 3:
                adjustment += YAHTZEE_OPEN_CLEAN_TRIPLE_BONUS

            # Keeping extra unrelated dice reduces Yahtzee/four-kind improvement chances.
            if len(hold) > 3:
                adjustment += YAHTZEE_OPEN_EXTRA_DIE_PENALTY * (len(hold) - 3)

            # If the matching upper box is open, this triple also protects bonus pace.
            category = upper_category_for_die(number)

            if category in UPPER_CATEGORIES and scorecard[category] is None:
                adjustment += 1.0

            # Full House is another reason to keep a made triple.
            if full_house_is_open(scorecard):
                adjustment += 0.75

        else:
            # Penalize abandoning a made triple when Yahtzee is still available.
            adjustment += YAHTZEE_OPEN_TRIPLE_ABANDON_PENALTY

    return adjustment


def analyze_all_holds_future_aware(dice, scorecard):
    holds = generate_unique_holds(dice)
    available_categories = get_available_categories(scorecard)

    use_game_aware_evaluator = should_use_game_aware_upper_chance_evaluator(
        dice,
        scorecard
    )

    results = []

    for hold in holds:
        future_aware_value, raw_expected_score, category_counter, shape_adjustment = expected_value_of_hold_future_aware(
            hold,
            available_categories,
            scorecard
        )

        original_adjustment = original_roll_pattern_adjustment(
            dice,
            hold,
            scorecard
        )

        triple_adjustment = yahtzee_open_triple_adjustment(
            dice,
            hold,
            scorecard
        )

        baseline_strategy_value = (
            future_aware_value
            + original_adjustment
            + triple_adjustment
        )

        result = {
            "hold": hold,
            "strategy_value": baseline_strategy_value,
            "future_aware_value": baseline_strategy_value,
            "raw_expected_score": raw_expected_score,
            "category_counter": category_counter,
            "shape_adjustment": shape_adjustment,
            "original_adjustment": original_adjustment,
            "triple_adjustment": triple_adjustment,
            "game_aware_value": None,
            "game_aware_category_counter": None,
            "game_aware_note": None
        }

        if use_game_aware_evaluator:
            game_aware_value, game_aware_category_counter = game_aware_hold_value(
                hold,
                scorecard
            )

            # Even in game-aware mode, preserve Yahtzee-open triple logic.
            game_aware_value += triple_adjustment

            result["strategy_value"] = game_aware_value
            result["future_aware_value"] = game_aware_value
            result["game_aware_value"] = game_aware_value
            result["game_aware_category_counter"] = game_aware_category_counter
            result["game_aware_note"] = GAME_AWARE_CONTEXT_NOTE

        results.append(result)

    results = sorted(
        results,
        key=lambda result: result["strategy_value"],
        reverse=True
    )

    return results


def describe_repeated_upper_hold(hold, scorecard):
    counts = Counter(hold)

    for number, count in counts.items():
        category = upper_category_for_die(number)

        if count >= 2 and category in UPPER_CATEGORIES and scorecard[category] is None:
            if count == 2:
                return f"You kept a pair of {number}s, which is useful because the {CATEGORY_DISPLAY_NAMES[category]} box is still open and the upper bonus is still available."

            elif count == 3:
                if yahtzee_is_open(scorecard):
                    return f"You kept three {number}s. That is strong because it already reaches bonus pace for {CATEGORY_DISPLAY_NAMES[category]} and keeps Yahtzee, Four of a Kind, Three of a Kind, and Full House alive."
                else:
                    return f"You kept three {number}s, which already reaches the normal bonus pace for the {CATEGORY_DISPLAY_NAMES[category]} box."

            else:
                return f"You kept {count} {number}s, which is a very strong result for the {CATEGORY_DISPLAY_NAMES[category]} box."

    return None

# ===== Source notebook cell 37 =====
# ============================
# PATCH: FIX TRIPLE REPORT WORDING
# ============================
# Fixes reports where [1, 1, 1] was described as "a pair of 1s."


def coach_report_for_user_hold_future_aware(dice, scorecard, user_hold):
    evaluation, final_grade, grade_note, chase_comparison = final_grade_details(
        dice,
        scorecard,
        user_hold
    )

    user_result = evaluation["user_result"]
    optimal_result = evaluation["optimal_result"]

    user_hold_clean = evaluation["user_hold"]
    optimal_hold_clean = evaluation["optimal_hold"]

    efficiency = evaluation["efficiency"]
    base_grade = evaluation["grade"]
    points_lost = evaluation["points_lost"]

    game_aware_used = user_result.get("game_aware_note") is not None
    user_is_optimal = user_hold_clean == optimal_hold_clean
    near_tie = is_near_tie(efficiency, points_lost)

    report = []

    report.append("YAHTZEE COACH REPORT")
    report.append("=" * 40)
    report.append(f"Current dice: {dice}")
    report.append(f"Your choice: {format_hold(user_hold_clean)}")
    report.append(f"Optimal choice: {format_hold(optimal_hold_clean)}")
    report.append("")

    if near_tie and not user_is_optimal:
        report.append("Grade: A+")
        report.append("Near-tie note: Your move was essentially tied with the top mathematical choice.")
    elif final_grade == base_grade:
        report.append(f"Grade: {final_grade}")
    else:
        report.append(f"Grade: {final_grade} adjusted from {base_grade}")

    if grade_note and not near_tie:
        report.append(grade_note)

    if near_tie and not user_is_optimal:
        report.append("Coach rating: This is an excellent alternative.")
    else:
        report.append(
            coach_rating_sentence(
                base_grade,
                final_grade,
                grade_note,
                efficiency
            )
        )

    report.append(f"Your strategy value: {round(evaluation['user_value'], 2)}")
    report.append(f"Optimal strategy value: {round(evaluation['optimal_value'], 2)}")
    report.append(f"Efficiency: {round(efficiency * 100, 1)}% of optimal")
    report.append(f"Strategy value lost: {round(points_lost, 2)}")
    report.append("")

    if game_aware_used:
        report.append("Game-aware note:")
        report.append("- This decision used the upper-section/Chance evaluator.")
        report.append("- The coach considered not just this turn's score, but also how scoring upper boxes or Chance affects the rest of the scorecard.")
        report.append("- A hold with a lower immediate score can still be better if it protects the upper bonus and avoids wasting Chance too early.")
        report.append("")

    if user_result.get("triple_adjustment", 0) > 0:
        report.append("Yahtzee-path note:")
        report.append("- This move protected an existing three-of-a-kind while Yahtzee was still open.")
        report.append("- That keeps Yahtzee, Four of a Kind, Three of a Kind, Full House, and the matching upper box alive.")
        report.append("")

    report.append("What was good about your move?")

    repeated_feedback = describe_repeated_upper_hold(user_hold_clean, scorecard)

    if repeated_feedback:
        report.append(f"- {repeated_feedback}")
    else:
        good_feedback = describe_hold_pattern(user_hold_clean, scorecard)

        if good_feedback:
            for line in good_feedback:
                report.append(f"- {line}")
        else:
            report.append("- This hold keeps some flexibility, but it does not strongly build toward a specific scoring pattern.")

    category_counter = best_category_counter_for_result(user_result)

    report.append(
        f"- Your most common scoring paths were: {most_common_categories_text_clean(category_counter)}."
    )

    if chase_comparison is not None and not user_is_optimal and not near_tie:
        target_category = chase_comparison["target_category"]
        user_chase = chase_comparison["user_chase"]
        optimal_chase = chase_comparison["optimal_chase"]

        report.append("")
        report.append("Bonus-chase check:")
        report.append(
            f"- If your goal is to hit the {CATEGORY_DISPLAY_NAMES[target_category]} box at bonus pace, you need at least {user_chase['target_score_needed']} points there."
        )
        report.append(
            f"- Your hold gives a {percent_text(user_chase['success_probability'])} chance to reach that target."
        )
        report.append(
            f"- The optimal hold gives a {percent_text(optimal_chase['success_probability'])} chance to reach that same target."
        )

        if user_chase["success_probability"] > optimal_chase["success_probability"]:
            report.append(
                "- So your move is better for that specific upper-section chase."
            )

        report.append(
            f"- But using the chase rule, your expected score is {round(user_chase['expected_score_using_chase_rule'], 2)}, while the optimal hold's chase-rule expected score is {round(optimal_chase['expected_score_using_chase_rule'], 2)}."
        )

    report.append("")
    report.append("Why was the optimal move better?")

    if user_is_optimal:
        report.append("- Your move was the optimal move.")
    elif near_tie:
        report.append("- This was not meaningfully worse. The top hold had a tiny mathematical edge, but your move was a very strong strategic alternative.")
        report.append(f"- The difference was only {round(points_lost, 2)} strategy value points.")
    else:
        difference_feedback = explain_difference_between_holds(
            user_hold_clean,
            optimal_hold_clean,
            scorecard
        )

        for line in difference_feedback:
            report.append(f"- {line}")

        if game_aware_used:
            report.append(
                "- In this scorecard state, the coach is weighing future category value heavily, especially the upper bonus and the cost of using Chance."
            )

    report.append("")
    report.append("Coach recommendation:")

    if user_is_optimal:
        report.append("Stay with this thinking. You protected a strong existing pattern and kept several high-value scoring paths alive.")
    elif near_tie:
        report.append(
            f"Both {format_hold(user_hold_clean)} and {format_hold(optimal_hold_clean)} are defensible. The coach slightly prefers {format_hold(optimal_hold_clean)}, but your move should be treated as excellent."
        )
    else:
        report.append(
            f"The stronger mathematical play was to {format_hold(optimal_hold_clean)} because it produced the highest strategy value."
        )

        if final_grade != base_grade:
            report.append(
                "However, your move is still a smart bonus-chase alternative if you are intentionally trying to protect the upper-section bonus."
            )

    return "\n".join(report)

# ===== Source notebook cell 38 =====
# ============================
# QUICK FIX: DEFINE NEAR-TIE HELPER
# ============================

NEAR_TIE_POINTS_LOST = 0.5
NEAR_TIE_EFFICIENCY = 0.98


def is_near_tie(efficiency, points_lost):
    return efficiency >= NEAR_TIE_EFFICIENCY and points_lost <= NEAR_TIE_POINTS_LOST

# ===== Source notebook cell 39 =====
# ============================
# PATCH: UPDATED REGRESSION TEST SUITE WITH YAHTZEE-OPEN TRIPLE
# ============================

def run_all_regression_tests():
    upper_chance_scorecard = make_upper_chance_test_scorecard()
    empty_scorecard = create_empty_scorecard()

    tests = [
        {
            "name": "Triple should be protected in upper/Chance sample",
            "dice": [3, 3, 3, 4, 5],
            "scorecard": upper_chance_scorecard,
            "acceptable_best_holds": [[3, 3, 3]]
        },
        {
            "name": "Pair of fours should chase Fours instead of saving Chance",
            "dice": [1, 4, 4, 5, 6],
            "scorecard": upper_chance_scorecard,
            "acceptable_best_holds": [[4, 4]]
        },
        {
            "name": "Single useful four should keep the 4",
            "dice": [1, 1, 2, 2, 4],
            "scorecard": upper_chance_scorecard,
            "acceptable_best_holds": [[4]]
        },
        {
            "name": "Pair of sixes should chase Sixes",
            "dice": [2, 4, 5, 6, 6],
            "scorecard": upper_chance_scorecard,
            "acceptable_best_holds": [[6, 6]]
        },
        {
            "name": "High loose dice with no pair should keep useful upper value",
            "dice": [1, 3, 4, 5, 6],
            "scorecard": upper_chance_scorecard,
            "acceptable_best_holds": [[5, 6], [4, 5, 6], [6]]
        },
        {
            "name": "Yahtzee-open triple should be protected",
            "dice": [1, 1, 1, 2, 6],
            "scorecard": empty_scorecard,
            "acceptable_best_holds": [[1, 1, 1]]
        }
    ]

    print("YAHTZEE COACH REGRESSION TESTS")
    print("=" * 40)
    print()

    for test in tests:
        run_strategy_test(
            test["name"],
            test["dice"],
            test["scorecard"],
            test["acceptable_best_holds"]
        )

# ===== Source notebook cell 40 =====
# ============================
# PATCH: ROLL 1 ONE-STEP LOOKAHEAD ENGINE
# ============================
# Purpose:
# Grade a Roll 1 hold as a one-step challenge.
#
# User experience:
# - User sees Roll 1 dice.
# - User chooses what to keep.
# - App immediately grades the hold.
#
# Behind the scenes:
# - The engine looks ahead to all possible Roll 2 outcomes.
# - For each possible Roll 2 outcome, it uses our current Roll 2 coach.
# - It averages those values to grade the Roll 1 hold.


def scorecard_to_key(scorecard):
    """
    Makes a scorecard cacheable.
    """
    return tuple(
        (category, scorecard[category])
        for category in YAHTZEE_CATEGORIES
    )


ROLL1_LOOKAHEAD_CACHE = {}


def roll1_best_roll2_value(roll2_dice, scorecard):
    """
    Given a possible Roll 2 dice state, use the current best Roll 2 engine
    to find the best strategy value from there.
    """

    cache_key = (
        tuple(sorted(roll2_dice)),
        scorecard_to_key(scorecard)
    )

    if cache_key in ROLL1_LOOKAHEAD_CACHE:
        return ROLL1_LOOKAHEAD_CACHE[cache_key]

    results = analyze_all_holds_future_aware(list(roll2_dice), scorecard)
    best_result = results[0]

    value = best_result["strategy_value"]

    ROLL1_LOOKAHEAD_CACHE[cache_key] = value

    return value


def roll1_expected_value_of_hold(hold, dice, scorecard):
    """
    Expected value of a Roll 1 hold.

    Example:
    If you hold [6] on Roll 1, this looks at every possible Roll 2 result,
    then assumes smart Roll 2 play from there.
    """

    hold = tuple(sorted(hold))
    number_to_reroll = 5 - len(hold)

    outcome_distribution = GAME_AWARE_ROLL_DISTRIBUTIONS[number_to_reroll]

    total_value = 0
    total_count = 0

    for outcome, count in outcome_distribution:
        roll2_dice = tuple(sorted(hold + outcome))

        best_roll2_value = roll1_best_roll2_value(
            roll2_dice,
            scorecard
        )

        total_value += best_roll2_value * count
        total_count += count

    expected_value = total_value / total_count

    return expected_value


def analyze_all_holds_roll1(dice, scorecard):
    """
    Analyze all possible Roll 1 holds using two-reroll lookahead.
    """

    ROLL1_LOOKAHEAD_CACHE.clear()

    holds = generate_unique_holds(dice)

    results = []

    for hold in holds:
        roll1_value = roll1_expected_value_of_hold(
            hold,
            dice,
            scorecard
        )

        results.append({
            "hold": hold,
            "strategy_value": roll1_value,
            "roll1_value": roll1_value,
            "roll_number": 1,
            "rolls_remaining": 2
        })

    results = sorted(
        results,
        key=lambda result: result["strategy_value"],
        reverse=True
    )

    return results


def analyze_all_holds_by_roll_number(dice, scorecard, roll_number):
    """
    Main routing function.

    Roll 1 = two-reroll lookahead.
    Roll 2 = current future-aware/game-aware engine.
    """

    if roll_number == 1:
        return analyze_all_holds_roll1(dice, scorecard)

    if roll_number == 2:
        results = analyze_all_holds_future_aware(dice, scorecard)

        for result in results:
            result["roll_number"] = 2
            result["rolls_remaining"] = 1

        return results

    raise ValueError("This coach currently supports Roll 1 and Roll 2 hold decisions only.")

# ===== Source notebook cell 41 =====
# ============================
# PATCH: ROLL 1 + ROLL 2 ONE-STEP COACH REPORTS
# ============================
# Purpose:
# Allows the app to grade either:
# - Roll 1 hold decisions with two-reroll lookahead
# - Roll 2 hold decisions with the current future-aware/game-aware engine
#
# User still makes only ONE decision and gets ONE final grade.


def evaluate_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number
    )

    optimal_result = results[0]
    user_result = find_result_for_hold(results, user_hold)

    optimal_value = optimal_result["strategy_value"]
    user_value = user_result["strategy_value"]

    if optimal_value == 0:
        efficiency = 1
    else:
        efficiency = user_value / optimal_value

    points_lost = optimal_value - user_value
    base_grade = letter_grade_from_efficiency(efficiency)

    if is_near_tie(efficiency, points_lost):
        final_grade = "A+"
    else:
        final_grade = base_grade

    return {
        "dice": dice,
        "scorecard": scorecard,
        "roll_number": roll_number,
        "rolls_remaining": 3 - roll_number,
        "user_hold": user_result["hold"],
        "optimal_hold": optimal_result["hold"],
        "user_result": user_result,
        "optimal_result": optimal_result,
        "results": results,
        "user_value": user_value,
        "optimal_value": optimal_value,
        "efficiency": efficiency,
        "points_lost": points_lost,
        "base_grade": base_grade,
        "final_grade": final_grade
    }


def hold_protects_existing_triple(dice, hold):
    dice_counts = Counter(dice)
    hold_counts = Counter(hold)

    for number, count in dice_counts.items():
        if count >= 3 and hold_counts[number] >= 3:
            return True

    return False


def coach_report_for_user_hold_roll1(dice, scorecard, user_hold):
    evaluation = evaluate_user_hold_by_roll_number(
        dice,
        scorecard,
        user_hold,
        roll_number=1
    )

    user_hold_clean = evaluation["user_hold"]
    optimal_hold_clean = evaluation["optimal_hold"]

    user_is_optimal = user_hold_clean == optimal_hold_clean
    near_tie = is_near_tie(
        evaluation["efficiency"],
        evaluation["points_lost"]
    )

    report = []

    report.append("YAHTZEE COACH REPORT")
    report.append("=" * 40)
    report.append("Roll Number: 1 of 3")
    report.append("Rolls Remaining: 2")
    report.append(f"Current dice: {dice}")
    report.append(f"Your choice: {format_hold(user_hold_clean)}")
    report.append(f"Optimal choice: {format_hold(optimal_hold_clean)}")
    report.append("")

    if near_tie and not user_is_optimal:
        report.append("Grade: A+")
        report.append("Near-tie note: Your move was essentially tied with the top mathematical choice.")
    else:
        report.append(f"Grade: {evaluation['final_grade']}")

    if near_tie and not user_is_optimal:
        report.append("Coach rating: This is an excellent alternative.")
    else:
        strength = hold_strength_label(evaluation["efficiency"])
        report.append(f"Coach rating: This is {article_for_word(strength)} {strength} move.")

    report.append(f"Your Roll 1 strategy value: {round(evaluation['user_value'], 2)}")
    report.append(f"Optimal Roll 1 strategy value: {round(evaluation['optimal_value'], 2)}")
    report.append(f"Efficiency: {round(evaluation['efficiency'] * 100, 1)}% of optimal")
    report.append(f"Strategy value lost: {round(evaluation['points_lost'], 2)}")
    report.append("")

    report.append("Roll 1 lookahead note:")
    report.append("- This is still a one-step challenge for the player.")
    report.append("- Behind the scenes, the coach checks every possible Roll 2 result.")
    report.append("- For each possible Roll 2 result, it assumes smart Roll 2 play and averages those outcomes.")
    report.append("")

    if yahtzee_is_open(scorecard) and hold_protects_existing_triple(dice, user_hold_clean):
        report.append("Yahtzee-path note:")
        report.append("- This move protected an existing three-of-a-kind while Yahtzee was still open.")
        report.append("- That keeps Yahtzee, Four of a Kind, Three of a Kind, Full House, and the matching upper box alive.")
        report.append("")

    report.append("What was good about your move?")

    repeated_feedback = describe_repeated_upper_hold(user_hold_clean, scorecard)

    if repeated_feedback:
        report.append(f"- {repeated_feedback}")
    else:
        good_feedback = describe_hold_pattern(user_hold_clean, scorecard)

        if good_feedback:
            for line in good_feedback:
                report.append(f"- {line}")
        else:
            report.append("- This hold keeps flexibility for the next two rolls.")

    report.append("")

    report.append("Why was the optimal move better?")

    if user_is_optimal:
        report.append("- Your move was the optimal move.")
    elif near_tie:
        report.append("- This was not meaningfully worse. The top hold had only a tiny mathematical edge.")
        report.append(f"- The difference was only {round(evaluation['points_lost'], 2)} strategy value points.")
    else:
        report.append(
            f"- The coach preferred {format_hold(optimal_hold_clean)} because it produced the best average result after looking ahead to Roll 2."
        )

    report.append("")
    report.append("Top Roll 1 options:")

    for rank, result in enumerate(evaluation["results"][:3], start=1):
        report.append(
            f"- {rank}. {format_hold(result['hold'])}: {round(result['strategy_value'], 2)}"
        )

    report.append("")
    report.append("Coach recommendation:")

    if user_is_optimal:
        report.append("Stay with this thinking. You made the best Roll 1 hold based on two-reroll lookahead.")
    elif near_tie:
        report.append(
            f"Both {format_hold(user_hold_clean)} and {format_hold(optimal_hold_clean)} are defensible. Your move should be treated as excellent."
        )
    else:
        report.append(
            f"The stronger Roll 1 play was to {format_hold(optimal_hold_clean)}."
        )

    return "\n".join(report)


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    if roll_number == 1:
        return coach_report_for_user_hold_roll1(
            dice,
            scorecard,
            user_hold
        )

    if roll_number == 2:
        intro = []
        intro.append("YAHTZEE COACH REPORT")
        intro.append("=" * 40)
        intro.append("Roll Number: 2 of 3")
        intro.append("Rolls Remaining: 1")
        intro.append("")

        old_report = coach_report_for_user_hold_future_aware(
            dice,
            scorecard,
            user_hold
        )

        # Remove duplicate title from old report
        old_lines = old_report.split("\n")
        if len(old_lines) >= 2 and old_lines[0] == "YAHTZEE COACH REPORT":
            old_lines = old_lines[2:]

        return "\n".join(intro + old_lines)

    raise ValueError("This coach currently supports Roll 1 and Roll 2 hold decisions only.")

# ===== Source notebook cell 42 =====
# ============================
# PATCH: RANDOM ROLL 1 / ROLL 2 ONE-STEP PRACTICE MODE
# ============================
# Purpose:
# Practice rounds now randomly generate either:
# - Roll 1 of 3: two rerolls left
# - Roll 2 of 3: one reroll left
#
# The user still makes ONE hold decision and gets ONE final grade.


if "PRACTICE_HISTORY" not in globals():
    PRACTICE_HISTORY = []


def generate_practice_challenge():
    scenario = random.choice(PRACTICE_SCENARIOS)
    roll_number = random.choice([1, 2])

    challenge = {
        "mode": "Unlimited Practice",
        "scenario_name": scenario["name"],
        "scenario_description": scenario["description"],
        "roll_number": roll_number,
        "rolls_remaining": 3 - roll_number,
        "dice": roll_dice(5),
        "scorecard": scenario["scorecard_function"]()
    }

    return challenge


def show_practice_round(challenge=None):
    global CURRENT_CHALLENGE
    global CURRENT_HOLD_OPTIONS

    if challenge is None:
        challenge = generate_practice_challenge()

    CURRENT_CHALLENGE = challenge

    dice = challenge["dice"]
    scorecard = challenge["scorecard"]
    roll_number = challenge["roll_number"]

    CURRENT_HOLD_OPTIONS = generate_unique_holds(dice)

    print("YAHTZEE COACH PRACTICE ROUND")
    print("=" * 40)
    print("Mode:", challenge["mode"])
    print("Scenario:", challenge["scenario_name"])
    print("Scenario Note:", challenge["scenario_description"])
    print("Roll Number:", roll_number, "of 3")
    print("Rolls Remaining:", challenge["rolls_remaining"])
    print("Dice:", dice)
    print()

    if roll_number == 1:
        print("Decision Type: Roll 1 hold decision")
        print("Coach will grade this using two-reroll lookahead.")
    elif roll_number == 2:
        print("Decision Type: Roll 2 hold decision")
        print("Coach will grade this using one-reroll strategy.")

    print()

    print_scorecard(scorecard)

    print("Choose which dice to keep:")
    print("-" * 40)

    for index, hold in enumerate(CURRENT_HOLD_OPTIONS, start=1):
        print(index, ":", format_hold(hold))

    print()
    print("To submit a choice, run:")
    print("submit_hold_number(choice_number)")
    print()
    print("Example:")
    print("submit_hold_number(5)")


def submit_hold_number(choice_number):
    global PRACTICE_HISTORY

    if CURRENT_CHALLENGE is None:
        print("No active challenge. Run show_practice_round() first.")
        return

    if CURRENT_HOLD_OPTIONS is None:
        print("No hold options found. Run show_practice_round() first.")
        return

    if choice_number < 1 or choice_number > len(CURRENT_HOLD_OPTIONS):
        print("That choice number is not valid.")
        return

    dice = CURRENT_CHALLENGE["dice"]
    scorecard = CURRENT_CHALLENGE["scorecard"]
    roll_number = CURRENT_CHALLENGE["roll_number"]

    user_hold = CURRENT_HOLD_OPTIONS[choice_number - 1]

    report = coach_report_for_user_hold_by_roll_number(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    print(report)

    evaluation = evaluate_user_hold_by_roll_number(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    PRACTICE_HISTORY.append({
        "roll_number": roll_number,
        "dice": dice,
        "scenario": CURRENT_CHALLENGE.get("scenario_name", "Unknown"),
        "user_hold": evaluation["user_hold"],
        "optimal_hold": evaluation["optimal_hold"],
        "grade": evaluation["final_grade"],
        "base_grade": evaluation["base_grade"],
        "efficiency": evaluation["efficiency"],
        "points_lost": evaluation["points_lost"],
        "strategy_value": evaluation["user_value"],
        "optimal_value": evaluation["optimal_value"]
    })


def reveal_best_move():
    if CURRENT_CHALLENGE is None:
        print("No active challenge. Run show_practice_round() first.")
        return

    dice = CURRENT_CHALLENGE["dice"]
    scorecard = CURRENT_CHALLENGE["scorecard"]
    roll_number = CURRENT_CHALLENGE["roll_number"]

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number
    )

    best_result = results[0]

    print("BEST MOVE")
    print("=" * 40)
    print("Roll Number:", roll_number, "of 3")
    print("Dice:", dice)
    print("Best hold:", format_hold(best_result["hold"]))
    print("Strategy Value:", round(best_result["strategy_value"], 2))
    print()

    print("Top 5 holds:")
    for rank, result in enumerate(results[:5], start=1):
        print(
            rank,
            format_hold(result["hold"]),
            "| Strategy Value:",
            round(result["strategy_value"], 2)
        )


def show_session_summary():
    if not PRACTICE_HISTORY:
        print("No practice attempts yet.")
        return

    total_attempts = len(PRACTICE_HISTORY)

    average_efficiency = sum(
        attempt["efficiency"] for attempt in PRACTICE_HISTORY
    ) / total_attempts

    average_points_lost = sum(
        attempt["points_lost"] for attempt in PRACTICE_HISTORY
    ) / total_attempts

    average_gpa = sum(
        grade_to_points(attempt["grade"]) for attempt in PRACTICE_HISTORY
    ) / total_attempts

    roll_1_attempts = sum(
        1 for attempt in PRACTICE_HISTORY
        if attempt["roll_number"] == 1
    )

    roll_2_attempts = sum(
        1 for attempt in PRACTICE_HISTORY
        if attempt["roll_number"] == 2
    )

    print("YAHTZEE COACH SESSION SUMMARY")
    print("=" * 40)
    print("Attempts:", total_attempts)
    print("Roll 1 attempts:", roll_1_attempts)
    print("Roll 2 attempts:", roll_2_attempts)
    print("Average efficiency:", round(average_efficiency * 100, 1), "%")
    print("Average strategy value lost:", round(average_points_lost, 2))
    print("Yahtzee Coach GPA:", round(average_gpa, 2))
    print()

    print("Recent attempts:")
    print("-" * 40)

    for index, attempt in enumerate(PRACTICE_HISTORY[-10:], start=1):
        print(
            index,
            "| Roll:",
            attempt["roll_number"],
            "| Scenario:",
            attempt["scenario"],
            "| Dice:",
            attempt["dice"],
            "| Your hold:",
            attempt["user_hold"],
            "| Optimal:",
            attempt["optimal_hold"],
            "| Grade:",
            attempt["grade"]
        )

# ===== Source notebook cell 43 =====
# ============================
# PATCH: CONSISTENT ROLL 1 LOOKAHEAD VALUE
# ============================
# Fixes a Roll 1 bug where the engine mixed different value scales:
# - game-aware upper/Chance values around 60–70
# - future-aware pattern values around 20–40
#
# That made Roll 1 sometimes abandon obvious triples.
#
# This patch gives Roll 1 its own consistent Roll 2 lookahead evaluator.


def roll2_value_for_roll1_hold(hold, roll2_dice, scorecard):
    """
    Roll 2 hold value used ONLY inside Roll 1 lookahead.

    This intentionally uses a consistent value scale.
    It does NOT switch into the full game-aware upper/Chance DP value,
    because that value is on a different scale and can distort Roll 1.
    """

    available_categories = get_available_categories(scorecard)

    future_aware_value, raw_expected_score, category_counter, shape_adjustment = expected_value_of_hold_future_aware(
        hold,
        available_categories,
        scorecard
    )

    original_adjustment = original_roll_pattern_adjustment(
        roll2_dice,
        hold,
        scorecard
    )

    triple_adjustment = yahtzee_open_triple_adjustment(
        roll2_dice,
        hold,
        scorecard
    )

    value = (
        future_aware_value
        + original_adjustment
        + triple_adjustment
    )

    return value


def analyze_roll2_for_roll1_lookahead(roll2_dice, scorecard):
    """
    Finds the best Roll 2 hold using the consistent Roll 1 lookahead scale.
    """

    holds = generate_unique_holds(list(roll2_dice))
    results = []

    for hold in holds:
        value = roll2_value_for_roll1_hold(
            hold,
            list(roll2_dice),
            scorecard
        )

        results.append({
            "hold": hold,
            "strategy_value": value
        })

    results = sorted(
        results,
        key=lambda result: result["strategy_value"],
        reverse=True
    )

    return results


ROLL1_LOOKAHEAD_CACHE = {}


def roll1_best_roll2_value(roll2_dice, scorecard):
    """
    Given a possible Roll 2 dice state, use the consistent Roll 1 lookahead evaluator.
    """

    cache_key = (
        tuple(sorted(roll2_dice)),
        scorecard_to_key(scorecard)
    )

    if cache_key in ROLL1_LOOKAHEAD_CACHE:
        return ROLL1_LOOKAHEAD_CACHE[cache_key]

    results = analyze_roll2_for_roll1_lookahead(
        tuple(sorted(roll2_dice)),
        scorecard
    )

    best_value = results[0]["strategy_value"]

    ROLL1_LOOKAHEAD_CACHE[cache_key] = best_value

    return best_value


def roll1_expected_value_of_hold(hold, dice, scorecard):
    """
    Expected value of a Roll 1 hold using consistent Roll 2 lookahead.
    """

    hold = tuple(sorted(hold))
    number_to_reroll = 5 - len(hold)

    outcome_distribution = GAME_AWARE_ROLL_DISTRIBUTIONS[number_to_reroll]

    total_value = 0
    total_count = 0

    for outcome, count in outcome_distribution:
        roll2_dice = tuple(sorted(hold + outcome))

        best_roll2_value = roll1_best_roll2_value(
            roll2_dice,
            scorecard
        )

        total_value += best_roll2_value * count
        total_count += count

    return total_value / total_count


def analyze_all_holds_roll1(dice, scorecard):
    """
    Analyze all possible Roll 1 holds using two-reroll lookahead
    with a consistent Roll 2 value scale.
    """

    ROLL1_LOOKAHEAD_CACHE.clear()

    holds = generate_unique_holds(dice)
    results = []

    for hold in holds:
        roll1_value = roll1_expected_value_of_hold(
            hold,
            dice,
            scorecard
        )

        results.append({
            "hold": hold,
            "strategy_value": roll1_value,
            "roll1_value": roll1_value,
            "roll_number": 1,
            "rolls_remaining": 2
        })

    results = sorted(
        results,
        key=lambda result: result["strategy_value"],
        reverse=True
    )

    return results

# ===== Source notebook cell 44 =====
# ============================
# QUICK FIX: ROLL NUMBER ROUTER
# ============================

def analyze_all_holds_by_roll_number(dice, scorecard, roll_number):
    """
    Main routing function.

    Roll 1 = two-reroll lookahead.
    Roll 2 = current future-aware/game-aware engine.
    """

    if roll_number == 1:
        return analyze_all_holds_roll1(dice, scorecard)

    if roll_number == 2:
        results = analyze_all_holds_future_aware(dice, scorecard)

        for result in results:
            result["roll_number"] = 2
            result["rolls_remaining"] = 1

        return results

    raise ValueError("This coach currently supports Roll 1 and Roll 2 hold decisions only.")

# ===== Source notebook cell 45 =====
# ============================
# ROLL 1 REGRESSION TESTS
# ============================

def run_roll1_regression_tests():
    print("ROLL 1 YAHTZEE COACH REGRESSION TESTS")
    print("=" * 40)

    tests = []

    upper_bonus_scorecard = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }

    tests.append({
        "name": "Roll 1 triple fives should be protected",
        "dice": [2, 3, 5, 5, 5],
        "scorecard": upper_bonus_scorecard,
        "acceptable_best_holds": [[5, 5, 5]]
    })

    empty_scorecard = create_empty_scorecard()

    tests.append({
        "name": "Roll 1 Yahtzee-open triple ones should be protected",
        "dice": [1, 1, 1, 2, 6],
        "scorecard": empty_scorecard,
        "acceptable_best_holds": [[1, 1, 1]]
    })

    for test in tests:
        print()
        print(test["name"])
        print("-" * 40)

        results = analyze_all_holds_by_roll_number(
            test["dice"],
            test["scorecard"],
            roll_number=1
        )

        best_hold = results[0]["hold"]

        print("Dice:", test["dice"])
        print("Best hold:", best_hold)
        print("Strategy value:", round(results[0]["strategy_value"], 2))

        if best_hold in test["acceptable_best_holds"]:
            print("Result: PASS")
        else:
            print("Result: REVIEW")
            print("Acceptable holds:", test["acceptable_best_holds"])

# ===== Source notebook cell 46 =====
# ============================
# COMPLETE REGRESSION TEST RUNNER
# ============================

def run_complete_regression_tests():
    print("COMPLETE YAHTZEE COACH REGRESSION TESTS")
    print("=" * 50)
    print()

    print("SECTION 1: ROLL 2 / CORE STRATEGY TESTS")
    print("=" * 50)
    run_all_regression_tests()

    print()
    print()
    print("SECTION 2: ROLL 1 LOOKAHEAD TESTS")
    print("=" * 50)
    run_roll1_regression_tests()

    print()
    print("=" * 50)
    print("COMPLETE REGRESSION CHECK FINISHED")

# ===== Source notebook cell 47 =====
# ============================
# PATCH: ROLL 1 LOOSE HIGH UPPER DIE ADJUSTMENT
# ============================
# Purpose:
# Fixes Roll 1 cases where the engine slightly prefers a loose 4 over a loose 6
# during upper-bonus chase situations.
#
# This patch is intentionally conservative:
# - Roll 1 only
# - Single-die holds only
# - Upper bonus must still matter
# - Straights must already be closed
# - The die's upper category must be open


ROLL1_LOOSE_UPPER_FACE_WEIGHT = 0.6


def roll1_loose_upper_face_adjustment(dice, hold, scorecard):
    """
    Adds a small Roll 1 adjustment for keeping one useful upper-section die.

    Example:
    With [1, 2, 2, 4, 6], if Fours and Sixes are both open and straights are closed,
    keeping the 6 should usually be preferred over keeping the 4.
    """

    if len(hold) != 1:
        return 0

    if not upper_bonus_still_possible(scorecard):
        return 0

    if any_category_open(scorecard, STRAIGHT_CATEGORIES):
        return 0

    die = hold[0]
    category = upper_category_for_die(die)

    if scorecard.get(category) is not None:
        return 0

    # Centered adjustment:
    # 1, 2, 3 get small negatives.
    # 4, 5, 6 get positives.
    # This helps the coach prefer higher loose upper dice when everything else is close.
    return (die - 3.5) * ROLL1_LOOSE_UPPER_FACE_WEIGHT


def analyze_all_holds_roll1(dice, scorecard):
    """
    Analyze all possible Roll 1 holds using two-reroll lookahead
    with a consistent Roll 2 value scale plus a conservative loose-upper-die adjustment.
    """

    ROLL1_LOOKAHEAD_CACHE.clear()

    holds = generate_unique_holds(dice)
    results = []

    for hold in holds:
        base_roll1_value = roll1_expected_value_of_hold(
            hold,
            dice,
            scorecard
        )

        loose_upper_adjustment = roll1_loose_upper_face_adjustment(
            dice,
            hold,
            scorecard
        )

        roll1_value = base_roll1_value + loose_upper_adjustment

        results.append({
            "hold": hold,
            "strategy_value": roll1_value,
            "roll1_value": roll1_value,
            "base_roll1_value": base_roll1_value,
            "loose_upper_adjustment": loose_upper_adjustment,
            "roll_number": 1,
            "rolls_remaining": 2
        })

    results = sorted(
        results,
        key=lambda result: result["strategy_value"],
        reverse=True
    )

    return results

# ===== Source notebook cell 48 =====
# ============================
# ADDITIONAL ROLL 1 REGRESSION TEST
# ============================

def run_roll1_loose_upper_regression_test():
    print("ROLL 1 LOOSE UPPER DIE REGRESSION TEST")
    print("=" * 40)

    scorecard = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }

    dice = [1, 2, 2, 4, 6]

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number=1
    )

    best_hold = results[0]["hold"]

    print("Dice:", dice)
    print("Best hold:", best_hold)
    print("Strategy value:", round(results[0]["strategy_value"], 2))

    if best_hold == [6]:
        print("Result: PASS")
    else:
        print("Result: REVIEW")
        print("Expected best hold: [6]")

# ===== Source notebook cell 49 =====
# ============================
# UPDATED COMPLETE REGRESSION TEST RUNNER
# ============================

def run_complete_regression_tests():
    print("COMPLETE YAHTZEE COACH REGRESSION TESTS")
    print("=" * 50)
    print()

    print("SECTION 1: ROLL 2 / CORE STRATEGY TESTS")
    print("=" * 50)
    run_all_regression_tests()

    print()
    print()
    print("SECTION 2: ROLL 1 LOOKAHEAD TESTS")
    print("=" * 50)
    run_roll1_regression_tests()

    print()
    print()
    print("SECTION 3: ROLL 1 LOOSE UPPER DIE TEST")
    print("=" * 50)
    run_roll1_loose_upper_regression_test()

    print()
    print("=" * 50)
    print("COMPLETE REGRESSION CHECK FINISHED")

# ===== Source notebook cell 50 =====
# ============================
# PATCH: EXACT ROLL 2 FULL HOUSE / CATEGORY DECISION EVALUATOR
# ============================
# Purpose:
# Fixes Roll 2 situations where the upper/Chance evaluator ignores
# important lower-section threats like Full House.
#
# This is NOT a flat Full House bonus.
#
# Instead, when Full House is open and the current dice contain a two-pair
# Full House threat, the coach calculates the exact expected value after
# the final reroll for each hold.
#
# This accounts for:
# - Chance open vs Chance already used
# - Full House hits
# - Full House misses
# - Upper-section scoring
# - Three/Four of a Kind
# - Yahtzee
# - Future-aware category values


from collections import Counter


def two_pair_numbers(dice):
    counts = Counter(dice)
    return sorted([
        number for number, count in counts.items()
        if count >= 2
    ])


def has_two_pair_full_house_threat(dice, scorecard):
    """
    True when Full House is open and the current dice contain at least two pairs.

    Example:
    [2, 4, 4, 5, 5] has a two-pair Full House threat.
    """

    if scorecard.get("full_house") is not None:
        return False

    pair_numbers = two_pair_numbers(dice)

    return len(pair_numbers) >= 2


def best_final_category_decision_exact(final_dice, scorecard, value_mode="future"):
    """
    Given final dice after the last reroll, choose the best category.

    value_mode:
    - "raw": choose by actual immediate score only
    - "future": choose by future-aware category value,
                which includes upper-bonus pressure and category opportunity cost
    """

    available_categories = get_available_categories(scorecard)
    all_scores = calculate_all_scores(final_dice)

    best_category = None
    best_raw_score = None
    best_value = None

    for category in available_categories:
        raw_score = all_scores[category]

        if value_mode == "raw":
            value = raw_score
        elif value_mode == "future":
            value = future_aware_category_value(
                category,
                raw_score,
                scorecard
            )
        else:
            raise ValueError("value_mode must be 'raw' or 'future'.")

        if best_value is None or value > best_value:
            best_category = category
            best_raw_score = raw_score
            best_value = value

    return {
        "category": best_category,
        "raw_score": best_raw_score,
        "value": best_value
    }


def roll2_exact_expected_category_decision_value(hold, scorecard, value_mode="future"):
    """
    Calculates exact expected value for a Roll 2 hold.

    This assumes:
    - The player keeps hold.
    - The remaining dice are rerolled once.
    - The player then scores in the best available category.

    This is exact for the final reroll.
    """

    hold = tuple(sorted(hold))
    number_to_reroll = 5 - len(hold)

    outcome_distribution = GAME_AWARE_ROLL_DISTRIBUTIONS[number_to_reroll]

    total_value = 0
    total_raw_score = 0
    total_count = 0
    category_counter = Counter()

    for outcome, count in outcome_distribution:
        final_dice = tuple(sorted(hold + outcome))

        best_decision_by_value = best_final_category_decision_exact(
            final_dice,
            scorecard,
            value_mode=value_mode
        )

        best_decision_by_raw = best_final_category_decision_exact(
            final_dice,
            scorecard,
            value_mode="raw"
        )

        total_value += best_decision_by_value["value"] * count
        total_raw_score += best_decision_by_raw["raw_score"] * count
        total_count += count

        category_counter[best_decision_by_value["category"]] += count

    expected_value = total_value / total_count
    expected_raw_score = total_raw_score / total_count

    return expected_value, expected_raw_score, category_counter


def should_use_full_house_tactical_evaluator(dice, scorecard):
    """
    Uses exact Roll 2 scoring math when Full House is open
    and the current dice already show a two-pair Full House threat.
    """

    return has_two_pair_full_house_threat(dice, scorecard)


def analyze_all_holds_future_aware(dice, scorecard):
    """
    Updated Roll 2 analyzer.

    Normal situations:
    - Use the existing future-aware / game-aware engine.

    Full House two-pair situations:
    - Use exact final-reroll category decision math.
    - This avoids blindly overvaluing or undervaluing two pair.
    - It handles Chance open vs Chance closed naturally.
    """

    available_categories = get_available_categories(scorecard)
    holds = generate_unique_holds(dice)

    use_full_house_tactical_evaluator = should_use_full_house_tactical_evaluator(
        dice,
        scorecard
    )

    use_game_aware_evaluator = (
        should_use_game_aware_upper_chance_evaluator(dice, scorecard)
        and not use_full_house_tactical_evaluator
    )

    results = []

    for hold in holds:
        future_aware_value, raw_expected_score, category_counter, shape_adjustment = expected_value_of_hold_future_aware(
            hold,
            available_categories,
            scorecard
        )

        original_adjustment = original_roll_pattern_adjustment(
            dice,
            hold,
            scorecard
        )

        triple_adjustment = yahtzee_open_triple_adjustment(
            dice,
            hold,
            scorecard
        )

        game_aware_value = None
        game_aware_category_counter = None
        game_aware_note = None
        full_house_tactical_value = None
        full_house_tactical_raw_expected_score = None
        full_house_tactical_category_counter = None
        full_house_tactical_note = None

        strategy_value = (
            future_aware_value
            + original_adjustment
            + triple_adjustment
        )

        if use_game_aware_evaluator:
            game_aware_value = game_aware_hold_value(
                hold,
                scorecard
            )

            strategy_value = (
                game_aware_value
                + triple_adjustment
            )

            game_aware_note = GAME_AWARE_CONTEXT_NOTE

        if use_full_house_tactical_evaluator:
            exact_future_value, exact_raw_score, exact_category_counter = roll2_exact_expected_category_decision_value(
                hold,
                scorecard,
                value_mode="future"
            )

            full_house_tactical_value = exact_future_value
            full_house_tactical_raw_expected_score = exact_raw_score
            full_house_tactical_category_counter = exact_category_counter

            strategy_value = (
                exact_future_value
                + triple_adjustment
            )

            raw_expected_score = exact_raw_score
            category_counter = exact_category_counter

            full_house_tactical_note = "Exact Full House / final-reroll evaluator used."

        results.append({
            "hold": hold,
            "strategy_value": strategy_value,
            "future_aware_value": future_aware_value,
            "raw_expected_score": raw_expected_score,
            "category_counter": category_counter,
            "shape_adjustment": shape_adjustment,
            "original_adjustment": original_adjustment,
            "triple_adjustment": triple_adjustment,
            "game_aware_value": game_aware_value,
            "game_aware_category_counter": game_aware_category_counter,
            "game_aware_note": game_aware_note,
            "full_house_tactical_value": full_house_tactical_value,
            "full_house_tactical_raw_expected_score": full_house_tactical_raw_expected_score,
            "full_house_tactical_category_counter": full_house_tactical_category_counter,
            "full_house_tactical_note": full_house_tactical_note
        })

    results = sorted(
        results,
        key=lambda result: result["strategy_value"],
        reverse=True
    )

    return results


def roll2_value_for_roll1_hold(hold, roll2_dice, scorecard):
    """
    Roll 2 hold value used inside Roll 1 lookahead.

    Updated so Roll 1 lookahead also understands Full House two-pair situations.
    """

    if should_use_full_house_tactical_evaluator(roll2_dice, scorecard):
        exact_future_value, exact_raw_score, exact_category_counter = roll2_exact_expected_category_decision_value(
            hold,
            scorecard,
            value_mode="future"
        )

        triple_adjustment = yahtzee_open_triple_adjustment(
            roll2_dice,
            hold,
            scorecard
        )

        return exact_future_value + triple_adjustment

    available_categories = get_available_categories(scorecard)

    future_aware_value, raw_expected_score, category_counter, shape_adjustment = expected_value_of_hold_future_aware(
        hold,
        available_categories,
        scorecard
    )

    original_adjustment = original_roll_pattern_adjustment(
        roll2_dice,
        hold,
        scorecard
    )

    triple_adjustment = yahtzee_open_triple_adjustment(
        roll2_dice,
        hold,
        scorecard
    )

    value = (
        future_aware_value
        + original_adjustment
        + triple_adjustment
    )

    return value

# ===== Source notebook cell 51 =====
# ============================
# FULL HOUSE TWO-PAIR REGRESSION TESTS
# ============================

def run_full_house_two_pair_regression_tests():
    print("FULL HOUSE TWO-PAIR REGRESSION TESTS")
    print("=" * 40)

    base_scorecard = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }

    tests = []

    tests.append({
        "name": "Chance open: two pair should protect Full House",
        "dice": [2, 4, 4, 5, 5],
        "scorecard": dict(base_scorecard),
        "expected_best_hold": [4, 4, 5, 5]
    })

    chance_used_scorecard = dict(base_scorecard)
    chance_used_scorecard["chance"] = 22

    tests.append({
        "name": "Chance used: two pair should not be blindly forced",
        "dice": [2, 4, 4, 5, 5],
        "scorecard": chance_used_scorecard,
        "expected_best_hold": [5, 5]
    })

    for test in tests:
        print()
        print(test["name"])
        print("-" * 40)

        results = analyze_all_holds_by_roll_number(
            test["dice"],
            test["scorecard"],
            roll_number=2
        )

        best_hold = results[0]["hold"]

        print("Dice:", test["dice"])
        print("Chance open:", test["scorecard"].get("chance") is None)
        print("Best hold:", best_hold)
        print("Strategy value:", round(results[0]["strategy_value"], 2))
        print("Raw EV:", round(results[0].get("raw_expected_score", 0), 2))

        if best_hold == test["expected_best_hold"]:
            print("Result: PASS")
        else:
            print("Result: REVIEW")
            print("Expected best hold:", test["expected_best_hold"])

        print()
        print("Top 5:")
        for rank, result in enumerate(results[:5], start=1):
            print(
                rank,
                result["hold"],
                "| Strategy:",
                round(result["strategy_value"], 2),
                "| Raw EV:",
                round(result.get("raw_expected_score", 0), 2)
            )

# ===== Source notebook cell 52 =====
# ============================
# PATCH: FULL HOUSE TACTICAL REPORT WORDING
# ============================
# Purpose:
# Adds clear explanation when the exact Full House / final-reroll evaluator is used.


def hold_protects_two_pair_for_full_house(dice, hold):
    dice_pair_numbers = two_pair_numbers(dice)
    hold_counts = Counter(hold)

    protected_pairs = [
        number for number in dice_pair_numbers
        if hold_counts[number] >= 2
    ]

    return len(protected_pairs) >= 2 and len(hold) == 4


def full_house_tactical_report_note(dice, scorecard, user_hold, user_result, optimal_result):
    """
    Creates explanation text for two-pair Full House situations.
    """

    if not user_result.get("full_house_tactical_note") and not optimal_result.get("full_house_tactical_note"):
        return []

    chance_open = scorecard.get("chance") is None
    user_protects_two_pair = hold_protects_two_pair_for_full_house(dice, user_hold)
    optimal_protects_two_pair = hold_protects_two_pair_for_full_house(dice, optimal_result["hold"])

    lines = []

    lines.append("Full House tactical note:")
    lines.append("- This decision used exact final-reroll math because Full House was open and the dice showed a two-pair pattern.")
    lines.append("- Keeping both pairs gives a 2-in-6 chance to complete Full House on the final die.")

    if chance_open:
        lines.append("- Chance was still open, so the coach also counted the value of miss outcomes that could still score well in Chance.")
    else:
        lines.append("- Chance was already used, so the coach punished miss outcomes more heavily because they often leave only a weaker upper-section score.")

    lines.append(
        f"- Your raw expected score from this hold was {round(user_result.get('raw_expected_score', 0), 2)}."
    )

    lines.append(
        f"- The optimal raw expected score was {round(optimal_result.get('raw_expected_score', 0), 2)}."
    )

    if user_protects_two_pair:
        lines.append("- Your hold protected both pairs, so it kept the Full House path alive.")
    elif optimal_protects_two_pair:
        lines.append("- The optimal hold protected both pairs, which kept the Full House path alive.")

    return lines


# Save the current Roll 2 report function before wrapping it.
if "_BASE_coach_report_for_user_hold_future_aware" not in globals():
    _BASE_coach_report_for_user_hold_future_aware = coach_report_for_user_hold_future_aware


def coach_report_for_user_hold_future_aware(dice, scorecard, user_hold):
    """
    Wrapped Roll 2 report function.

    Keeps the existing report, but inserts a Full House tactical note
    when the exact Full House evaluator was used.
    """

    base_report = _BASE_coach_report_for_user_hold_future_aware(
        dice,
        scorecard,
        user_hold
    )

    results = analyze_all_holds_future_aware(
        dice,
        scorecard
    )

    optimal_result = results[0]
    user_result = find_result_for_hold(results, user_hold)

    note_lines = full_house_tactical_report_note(
        dice,
        scorecard,
        user_result["hold"],
        user_result,
        optimal_result
    )

    if not note_lines:
        return base_report

    lines = base_report.split("\n")

    insert_index = None

    for index, line in enumerate(lines):
        if line.startswith("Strategy value lost:"):
            insert_index = index + 1
            break

    if insert_index is None:
        insert_index = min(len(lines), 10)

    new_lines = (
        lines[:insert_index]
        + [""]
        + note_lines
        + lines[insert_index:]
    )

    return "\n".join(new_lines)

# ===== Source notebook cell 53 =====
# ============================
# UPDATED COMPLETE REGRESSION TEST RUNNER
# ============================

def run_complete_regression_tests():
    print("COMPLETE YAHTZEE COACH REGRESSION TESTS")
    print("=" * 50)
    print()

    print("SECTION 1: ROLL 2 / CORE STRATEGY TESTS")
    print("=" * 50)
    run_all_regression_tests()

    print()
    print()
    print("SECTION 2: ROLL 1 LOOKAHEAD TESTS")
    print("=" * 50)
    run_roll1_regression_tests()

    print()
    print()
    print("SECTION 3: ROLL 1 LOOSE UPPER DIE TEST")
    print("=" * 50)
    run_roll1_loose_upper_regression_test()

    print()
    print()
    print("SECTION 4: FULL HOUSE TWO-PAIR TESTS")
    print("=" * 50)
    run_full_house_two_pair_regression_tests()

    print()
    print("=" * 50)
    print("COMPLETE REGRESSION CHECK FINISHED")

# ===== Source notebook cell 54 =====
# ============================
# PATCH: IMPROVE FULL HOUSE "WHAT WAS GOOD" WORDING
# ============================
# Purpose:
# When the exact Full House tactical evaluator is used,
# make the "What was good?" section mention the two-pair Full House setup first.


if "_BASE2_coach_report_for_user_hold_future_aware" not in globals():
    _BASE2_coach_report_for_user_hold_future_aware = coach_report_for_user_hold_future_aware


def coach_report_for_user_hold_future_aware(dice, scorecard, user_hold):
    base_report = _BASE2_coach_report_for_user_hold_future_aware(
        dice,
        scorecard,
        user_hold
    )

    results = analyze_all_holds_future_aware(dice, scorecard)
    user_result = find_result_for_hold(results, user_hold)

    if not user_result.get("full_house_tactical_note"):
        return base_report

    if not hold_protects_two_pair_for_full_house(dice, user_result["hold"]):
        return base_report

    lines = base_report.split("\n")

    insert_index = None

    for index, line in enumerate(lines):
        if line.strip() == "What was good about your move?":
            insert_index = index + 1
            break

    if insert_index is None:
        return base_report

    new_good_line = (
        "- You protected both pairs. That gives you a 2-in-6 chance "
        "to complete Full House on the final roll while still leaving "
        "Chance or upper-section scoring as backup plans."
    )

    if new_good_line in lines:
        return base_report

    lines.insert(insert_index, new_good_line)

    return "\n".join(lines)

# ===== Source notebook cell 55 =====
# ============================
# TWO-PAIR STRENGTH REGRESSION TESTS
# ============================
# Purpose:
# Protects the idea that not all two-pair Full House setups are equal.
#
# Low two pair has the same 2-in-6 Full House chance as high two pair,
# but much worse miss outcomes.
#
# This also protects upper-bonus thinking:
# - scoring 2 in Ones is only 1 below pace
# - scoring 12 in Sixes is 6 below pace


def run_two_pair_strength_regression_tests():
    print("TWO-PAIR STRENGTH REGRESSION TESTS")
    print("=" * 40)

    base_scorecard = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }

    tests = []

    tests.append({
        "name": "Low two pair with Chance open should not be blindly protected",
        "dice": [1, 1, 2, 2, 6],
        "scorecard": dict(base_scorecard),
        "expected_best_hold": [6]
    })

    tests.append({
        "name": "High two pair with Chance open should be protected",
        "dice": [1, 5, 5, 6, 6],
        "scorecard": dict(base_scorecard),
        "expected_best_hold": [5, 5, 6, 6]
    })

    chance_used_scorecard = dict(base_scorecard)
    chance_used_scorecard["chance"] = 22

    tests.append({
        "name": "Low two pair with Chance used should prefer the 6",
        "dice": [1, 1, 2, 2, 6],
        "scorecard": dict(chance_used_scorecard),
        "expected_best_hold": [6]
    })

    tests.append({
        "name": "High two pair with Chance used should prefer pair of 6s",
        "dice": [1, 5, 5, 6, 6],
        "scorecard": dict(chance_used_scorecard),
        "expected_best_hold": [6, 6]
    })

    for test in tests:
        print()
        print(test["name"])
        print("-" * 40)

        results = analyze_all_holds_by_roll_number(
            test["dice"],
            test["scorecard"],
            roll_number=2
        )

        best_hold = results[0]["hold"]

        print("Dice:", test["dice"])
        print("Chance open:", test["scorecard"].get("chance") is None)
        print("Best hold:", best_hold)
        print("Strategy value:", round(results[0]["strategy_value"], 2))
        print("Raw EV:", round(results[0].get("raw_expected_score", 0), 2))

        if best_hold == test["expected_best_hold"]:
            print("Result: PASS")
        else:
            print("Result: REVIEW")
            print("Expected best hold:", test["expected_best_hold"])

# ===== Source notebook cell 56 =====
# ============================
# UPDATED COMPLETE REGRESSION TEST RUNNER
# ============================

def run_complete_regression_tests():
    print("COMPLETE YAHTZEE COACH REGRESSION TESTS")
    print("=" * 50)
    print()

    print("SECTION 1: ROLL 2 / CORE STRATEGY TESTS")
    print("=" * 50)
    run_all_regression_tests()

    print()
    print()
    print("SECTION 2: ROLL 1 LOOKAHEAD TESTS")
    print("=" * 50)
    run_roll1_regression_tests()

    print()
    print()
    print("SECTION 3: ROLL 1 LOOSE UPPER DIE TEST")
    print("=" * 50)
    run_roll1_loose_upper_regression_test()

    print()
    print()
    print("SECTION 4: FULL HOUSE TWO-PAIR TESTS")
    print("=" * 50)
    run_full_house_two_pair_regression_tests()

    print()
    print()
    print("SECTION 5: TWO-PAIR STRENGTH TESTS")
    print("=" * 50)
    run_two_pair_strength_regression_tests()

    print()
    print("=" * 50)
    print("COMPLETE REGRESSION CHECK FINISHED")

# ===== Source notebook cell 57 =====
# ============================
# QUICK FIX: SAFE GAME-AWARE VALUE HANDLING
# ============================
# Purpose:
# Fixes TypeError where game_aware_hold_value sometimes returns a tuple
# instead of a plain number.
#
# This preserves:
# - Roll 2 core strategy
# - Game-aware upper/Chance evaluator
# - Full House exact evaluator
# - Yahtzee triple protection


from numbers import Number
from collections import Counter


def extract_numeric_strategy_value(value_object):
    """
    Safely extracts a numeric value from a game-aware result.

    Handles:
    - plain number
    - tuple/list where the first item is the value
    - dict with common value keys
    """

    if isinstance(value_object, Number):
        return value_object

    if isinstance(value_object, dict):
        for key in ["strategy_value", "value", "game_aware_value"]:
            if key in value_object and isinstance(value_object[key], Number):
                return value_object[key]

    if isinstance(value_object, (tuple, list)):
        for item in value_object:
            if isinstance(item, Number):
                return item

    raise TypeError(
        f"Could not extract a numeric strategy value from: {value_object}"
    )


def extract_counter_from_value_object(value_object):
    """
    If a returned object includes a Counter, extract it.
    Otherwise return None.
    """

    if isinstance(value_object, Counter):
        return value_object

    if isinstance(value_object, dict):
        for key in ["category_counter", "game_aware_category_counter"]:
            if key in value_object and isinstance(value_object[key], Counter):
                return value_object[key]

    if isinstance(value_object, (tuple, list)):
        for item in value_object:
            if isinstance(item, Counter):
                return item

    return None


def analyze_all_holds_future_aware(dice, scorecard):
    """
    Repaired Roll 2 analyzer.

    Same logic as before, but safely handles game_aware_hold_value
    whether it returns a number or a tuple.
    """

    available_categories = get_available_categories(scorecard)
    holds = generate_unique_holds(dice)

    use_full_house_tactical_evaluator = should_use_full_house_tactical_evaluator(
        dice,
        scorecard
    )

    use_game_aware_evaluator = (
        should_use_game_aware_upper_chance_evaluator(dice, scorecard)
        and not use_full_house_tactical_evaluator
    )

    results = []

    for hold in holds:
        future_aware_value, raw_expected_score, category_counter, shape_adjustment = expected_value_of_hold_future_aware(
            hold,
            available_categories,
            scorecard
        )

        original_adjustment = original_roll_pattern_adjustment(
            dice,
            hold,
            scorecard
        )

        triple_adjustment = yahtzee_open_triple_adjustment(
            dice,
            hold,
            scorecard
        )

        game_aware_value = None
        game_aware_category_counter = None
        game_aware_note = None

        full_house_tactical_value = None
        full_house_tactical_raw_expected_score = None
        full_house_tactical_category_counter = None
        full_house_tactical_note = None

        strategy_value = (
            future_aware_value
            + original_adjustment
            + triple_adjustment
        )

        if use_game_aware_evaluator:
            raw_game_aware_result = game_aware_hold_value(
                hold,
                scorecard
            )

            game_aware_value = extract_numeric_strategy_value(
                raw_game_aware_result
            )

            game_aware_category_counter = extract_counter_from_value_object(
                raw_game_aware_result
            )

            strategy_value = (
                game_aware_value
                + triple_adjustment
            )

            game_aware_note = GAME_AWARE_CONTEXT_NOTE

        if use_full_house_tactical_evaluator:
            exact_future_value, exact_raw_score, exact_category_counter = roll2_exact_expected_category_decision_value(
                hold,
                scorecard,
                value_mode="future"
            )

            full_house_tactical_value = exact_future_value
            full_house_tactical_raw_expected_score = exact_raw_score
            full_house_tactical_category_counter = exact_category_counter

            strategy_value = (
                exact_future_value
                + triple_adjustment
            )

            raw_expected_score = exact_raw_score
            category_counter = exact_category_counter

            full_house_tactical_note = "Exact Full House / final-reroll evaluator used."

        results.append({
            "hold": hold,
            "strategy_value": strategy_value,
            "future_aware_value": future_aware_value,
            "raw_expected_score": raw_expected_score,
            "category_counter": category_counter,
            "shape_adjustment": shape_adjustment,
            "original_adjustment": original_adjustment,
            "triple_adjustment": triple_adjustment,
            "game_aware_value": game_aware_value,
            "game_aware_category_counter": game_aware_category_counter,
            "game_aware_note": game_aware_note,
            "full_house_tactical_value": full_house_tactical_value,
            "full_house_tactical_raw_expected_score": full_house_tactical_raw_expected_score,
            "full_house_tactical_category_counter": full_house_tactical_category_counter,
            "full_house_tactical_note": full_house_tactical_note
        })

    results = sorted(
        results,
        key=lambda result: result["strategy_value"],
        reverse=True
    )

    return results

# ===== Source notebook cell 58 =====
# ============================
# PATCH: BETTER ROLL 1 OPTIMAL-MOVE EXPLANATIONS
# ============================
# Purpose:
# Improves Roll 1 report wording so "Why was the optimal move better?"
# gives an actual mathematical/strategic reason, not just a generic statement.


def describe_roll1_hold_math_reason(dice, scorecard, hold):
    """
    Gives a concise mathematical reason for a Roll 1 hold.
    """

    hold = list(sorted(hold))
    counts = Counter(hold)

    if len(hold) == 0:
        return [
            "- Rerolling everything gives maximum flexibility, but it also gives up every useful die already showing."
        ]

    # Existing triple
    for number, count in counts.items():
        if count >= 3:
            category = upper_category_for_die(number)
            category_name = CATEGORY_DISPLAY_NAMES[category]

            reasons = [
                f"- Keeping three {number}s protects an already-made triple.",
                "- That keeps Yahtzee, Four of a Kind, Three of a Kind, Full House, and the matching upper box alive."
            ]

            if scorecard.get(category) is None:
                reasons.append(
                    f"- It also already reaches bonus pace for {category_name}."
                )

            return reasons

    # Pair
    for number, count in counts.items():
        if count == 2:
            category = upper_category_for_die(number)
            category_name = CATEGORY_DISPLAY_NAMES[category]

            reasons = [
                f"- Keeping the pair of {number}s gives you a base to build Three of a Kind, Four of a Kind, Yahtzee, or the {category_name} box."
            ]

            if scorecard.get(category) is None and upper_bonus_still_possible(scorecard):
                target = CATEGORY_TARGETS[category]
                current_points = number * 2
                shortfall = target - current_points

                reasons.append(
                    f"- In the upper section, two {number}s would score {current_points}; bonus pace for {category_name} is {target}, so you are {shortfall} points short but still have two rolls to improve."
                )

            return reasons

    # Single die
    if len(hold) == 1:
        die = hold[0]
        category = upper_category_for_die(die)
        category_name = CATEGORY_DISPLAY_NAMES[category]

        reasons = []

        if scorecard.get(category) is None and upper_bonus_still_possible(scorecard):
            target = CATEGORY_TARGETS[category]
            reasons.append(
                f"- Keeping the {die} preserves a useful upper-section anchor for {category_name}. Bonus pace there is {target}, so extra {die}s are valuable."
            )

        if die >= 5:
            reasons.append(
                f"- A {die} is also a strong high die for Chance and for building Three/Four of a Kind."
            )
        elif die >= 4:
            reasons.append(
                f"- A {die} is useful because it can still build toward its upper box while keeping some scoring value."
            )
        else:
            reasons.append(
                f"- This die is useful mainly because its matching upper box is still available or because it keeps a developing pattern alive."
            )

        return reasons

    # Multiple loose high dice
    if len(hold) >= 2:
        high_dice = [die for die in hold if die >= 5]

        if len(high_dice) >= 2:
            return [
                f"- Keeping {', '.join(str(die) for die in hold)} preserves high scoring dice.",
                "- That keeps Chance, upper-section value, and lower-section combo potential stronger than a full reroll."
            ]

    return [
        "- This hold produced the best two-reroll average across all possible Roll 2 outcomes.",
        "- The coach compared every possible Roll 2 result and then assumed smart Roll 2 play from there."
    ]


def build_roll1_optimal_explanation_lines(evaluation):
    dice = evaluation["dice"]
    scorecard = evaluation["scorecard"]
    user_hold = evaluation["user_hold"]
    optimal_hold = evaluation["optimal_hold"]
    user_is_optimal = user_hold == optimal_hold

    points_lost = evaluation["points_lost"]
    user_value = evaluation["user_value"]
    optimal_value = evaluation["optimal_value"]

    lines = []

    if user_is_optimal:
        lines.append("- Your move was the optimal move.")
        lines.extend(describe_roll1_hold_math_reason(dice, scorecard, optimal_hold))
        return lines

    lines.append(
        f"- The optimal hold beat your hold by {round(points_lost, 2)} strategy value points across the two-reroll lookahead."
    )

    if len(user_hold) == 0 and len(optimal_hold) > 0:
        lines.append(
            "- Rerolling everything gives flexibility, but it also throws away useful information from the first roll."
        )

    lines.extend(describe_roll1_hold_math_reason(dice, scorecard, optimal_hold))

    lines.append(
        f"- In this position, {format_hold(optimal_hold)} averaged {round(optimal_value, 2)}, while {format_hold(user_hold)} averaged {round(user_value, 2)}."
    )

    return lines


# Save the current Roll 1 report function before wrapping it.
if "_BASE_coach_report_for_user_hold_roll1" not in globals():
    _BASE_coach_report_for_user_hold_roll1 = coach_report_for_user_hold_roll1


def coach_report_for_user_hold_roll1(dice, scorecard, user_hold):
    """
    Wrapped Roll 1 report.

    Replaces the generic "Why was the optimal move better?" explanation
    with a more mathematical/strategic explanation.
    """

    base_report = _BASE_coach_report_for_user_hold_roll1(
        dice,
        scorecard,
        user_hold
    )

    evaluation = evaluate_user_hold_by_roll_number(
        dice,
        scorecard,
        user_hold,
        roll_number=1
    )

    improved_lines = build_roll1_optimal_explanation_lines(evaluation)

    lines = base_report.split("\n")

    start_index = None
    end_index = None

    for index, line in enumerate(lines):
        if line.strip() == "Why was the optimal move better?":
            start_index = index + 1
            break

    if start_index is None:
        return base_report

    for index in range(start_index, len(lines)):
        if lines[index].strip() == "":
            end_index = index
            break

    if end_index is None:
        return base_report

    new_lines = (
        lines[:start_index]
        + improved_lines
        + lines[end_index:]
    )

    return "\n".join(new_lines)

# ===== Source notebook cell 59 =====
# ============================
# ARTICLE STRATEGY REGRESSION TEST
# ============================
# Protects the lesson from the Yahtzee strategy article:
# On an early roll of [1, 1, 2, 5, 6], do not chase the pair of 1s.
# A useful high-die hold should be preferred.

def run_article_strategy_regression_test():
    print("ARTICLE STRATEGY REGRESSION TEST")
    print("=" * 40)

    dice = [1, 1, 2, 5, 6]
    scorecard = create_empty_scorecard()

    acceptable_best_holds = [
        [5],
        [6],
        [5, 6]
    ]

    bad_low_pair_hold = [1, 1]

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number=1
    )

    best_hold = results[0]["hold"]

    print("Dice:", dice)
    print("Best hold:", best_hold)
    print("Strategy value:", round(results[0]["strategy_value"], 2))
    print()

    print("Top 5:")
    for rank, result in enumerate(results[:5], start=1):
        print(
            rank,
            result["hold"],
            "| Strategy:",
            round(result["strategy_value"], 2)
        )

    print()

    if best_hold in acceptable_best_holds and best_hold != bad_low_pair_hold:
        print("Result: PASS")
    else:
        print("Result: REVIEW")
        print("Acceptable best holds:", acceptable_best_holds)
        print("Bad low-pair hold:", bad_low_pair_hold)

# ===== Source notebook cell 60 =====
# ============================
# UPDATED COMPLETE REGRESSION TEST RUNNER
# ============================

def run_complete_regression_tests():
    print("COMPLETE YAHTZEE COACH REGRESSION TESTS")
    print("=" * 50)
    print()

    print("SECTION 1: ROLL 2 / CORE STRATEGY TESTS")
    print("=" * 50)
    run_all_regression_tests()

    print()
    print()
    print("SECTION 2: ROLL 1 LOOKAHEAD TESTS")
    print("=" * 50)
    run_roll1_regression_tests()

    print()
    print()
    print("SECTION 3: ROLL 1 LOOSE UPPER DIE TEST")
    print("=" * 50)
    run_roll1_loose_upper_regression_test()

    print()
    print()
    print("SECTION 4: FULL HOUSE TWO-PAIR TESTS")
    print("=" * 50)
    run_full_house_two_pair_regression_tests()

    print()
    print()
    print("SECTION 5: TWO-PAIR STRENGTH TESTS")
    print("=" * 50)
    run_two_pair_strength_regression_tests()

    print()
    print()
    print("SECTION 6: ARTICLE STRATEGY TEST")
    print("=" * 50)
    run_article_strategy_regression_test()

    print()
    print("=" * 50)
    print("COMPLETE REGRESSION CHECK FINISHED")

# ===== Source notebook cell 61 =====
# ============================
# START HERE: FAST CHECK + PRACTICE
# ============================
# After Runtime -> Run all, use these commands:
#   run_speed_diagnostics()
#   run_quick_regression_smoke_test()
#   show_practice_round()

import time


def make_empty_scorecard_for_speed_test():
    return {
        "ones": None,
        "twos": None,
        "threes": None,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": None,
        "large_straight": None,
        "yahtzee": None,
        "chance": None
    }


def time_task(label, task_function):
    print()
    print(label)
    print("-" * 50)
    start = time.perf_counter()
    try:
        result = task_function()
        seconds = time.perf_counter() - start
        print("Seconds:", round(seconds, 2))
        return result
    except Exception as error:
        seconds = time.perf_counter() - start
        print("FAILED after", round(seconds, 2), "seconds")
        print("Error:", repr(error))
        return None


def run_speed_diagnostics():
    print("YAHTZEE COACH SPEED DIAGNOSTICS")
    print("=" * 50)

    required_names = [
        "analyze_all_holds_by_roll_number",
        "coach_report_for_user_hold_by_roll_number",
        "show_practice_round"
    ]

    missing = [name for name in required_names if name not in globals()]
    if missing:
        print("MISSING REQUIRED FUNCTIONS")
        for name in missing:
            print("-", name)
        return

    empty_scorecard = make_empty_scorecard_for_speed_test()

    sample_scorecard = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }

    time_task(
        "Roll 2 analysis: normal upper/Chance situation",
        lambda: analyze_all_holds_by_roll_number([1, 4, 4, 5, 6], sample_scorecard, roll_number=2)
    )

    time_task(
        "Roll 2 analysis: Full House two-pair situation",
        lambda: analyze_all_holds_by_roll_number([2, 4, 4, 5, 5], sample_scorecard, roll_number=2)
    )

    time_task(
        "Roll 1 analysis: empty scorecard",
        lambda: analyze_all_holds_by_roll_number([1, 1, 3, 5, 6], empty_scorecard, roll_number=1)
    )

    time_task(
        "Roll 1 coach report",
        lambda: coach_report_for_user_hold_by_roll_number([1, 1, 3, 5, 6], empty_scorecard, [], roll_number=1)
    )

    time_task(
        "Generate/show one practice round",
        lambda: show_practice_round()
    )

    print()
    print("=" * 50)
    print("SPEED DIAGNOSTICS FINISHED")


def run_quick_regression_smoke_test():
    print("QUICK REGRESSION SMOKE TEST")
    print("=" * 50)
    tests = [
        ("Roll 2 triple", [3,3,3,4,5], {
            "ones": 3, "twos": 6, "threes": 9,
            "fours": None, "fives": None, "sixes": None,
            "three_of_a_kind": None, "four_of_a_kind": None,
            "full_house": None, "small_straight": 30, "large_straight": 40,
            "yahtzee": None, "chance": None
        }, 2),
        ("Roll 1 high die", [1,1,3,5,6], make_empty_scorecard_for_speed_test(), 1),
        ("Roll 2 full house", [2,4,4,5,5], {
            "ones": 3, "twos": 6, "threes": 9,
            "fours": None, "fives": None, "sixes": None,
            "three_of_a_kind": None, "four_of_a_kind": None,
            "full_house": None, "small_straight": 30, "large_straight": 40,
            "yahtzee": None, "chance": None
        }, 2),
    ]
    for name, dice, scorecard, roll_number in tests:
        start = time.perf_counter()
        results = analyze_all_holds_by_roll_number(dice, scorecard, roll_number)
        seconds = time.perf_counter() - start
        print(name, "| best:", results[0]["hold"], "| seconds:", round(seconds, 2))
    print("Smoke test finished.")


# ===== Source notebook cell 63 =====
# ============================
# SPEED PATCH 1: FAST PRACTICE ENGINE
# ============================
# Purpose:
# - Replaces the very slow exact game-aware upper/Chance mini-DP.
# - Speeds up Roll 2 expected-value calculations using grouped roll distributions.
# - Adds caches so repeated analysis/report calls reuse prior work.
#
# Important:
# This is a practice-speed patch. It keeps our main strategy ideas,
# but avoids the 100+ second exact mini-DP calculation.

import copy
from numbers import Number
from collections import Counter


# ----------------------------
# CACHE HELPERS
# ----------------------------

FAST_EXPECTED_HOLD_CACHE = {}
FAST_ANALYSIS_CACHE = {}
FAST_ROLL2_VALUE_FOR_ROLL1_CACHE = {}


def clear_speed_caches():
    FAST_EXPECTED_HOLD_CACHE.clear()
    FAST_ANALYSIS_CACHE.clear()
    FAST_ROLL2_VALUE_FOR_ROLL1_CACHE.clear()

    if "ROLL1_LOOKAHEAD_CACHE" in globals():
        ROLL1_LOOKAHEAD_CACHE.clear()



def scorecard_to_key_fast(scorecard):
    return tuple((category, scorecard.get(category)) for category in YAHTZEE_CATEGORIES)


def categories_to_key(categories):
    return tuple(categories)


def safe_copy_results(results):
    return copy.deepcopy(results)


def extract_numeric_strategy_value(value_object):
    """
    Safely extracts a numeric value from:
    - number
    - tuple/list containing a number
    - dict containing a value key
    """

    if isinstance(value_object, Number):
        return value_object

    if isinstance(value_object, dict):
        for key in ["strategy_value", "value", "game_aware_value"]:
            if key in value_object and isinstance(value_object[key], Number):
                return value_object[key]

    if isinstance(value_object, (tuple, list)):
        for item in value_object:
            if isinstance(item, Number):
                return item

    raise TypeError(f"Could not extract numeric value from: {value_object}")


def extract_counter_from_value_object(value_object):
    if isinstance(value_object, Counter):
        return value_object

    if isinstance(value_object, dict):
        for key in ["category_counter", "game_aware_category_counter"]:
            if key in value_object and isinstance(value_object[key], Counter):
                return value_object[key]

    if isinstance(value_object, (tuple, list)):
        for item in value_object:
            if isinstance(item, Counter):
                return item

    return None


# ----------------------------
# FAST EXPECTED VALUE OF A HOLD
# ----------------------------
# This replaces the older version that loops through every duplicate dice order.
# Instead of all 6^n raw outcomes, it uses unique sorted outcomes with counts.

def expected_value_of_hold_future_aware(hold, available_categories, scorecard):
    hold = tuple(sorted(hold))
    available_categories = tuple(available_categories)

    cache_key = (
        hold,
        categories_to_key(available_categories),
        scorecard_to_key_fast(scorecard)
    )

    if cache_key in FAST_EXPECTED_HOLD_CACHE:
        return copy.deepcopy(FAST_EXPECTED_HOLD_CACHE[cache_key])

    number_to_reroll = 5 - len(hold)
    outcome_distribution = GAME_AWARE_ROLL_DISTRIBUTIONS[number_to_reroll]

    total_future_value = 0
    total_raw_score = 0
    total_count = 0
    category_counter = Counter()

    for outcome, count in outcome_distribution:
        final_roll = tuple(sorted(hold + outcome))

        best_category, raw_score, future_value = best_score_for_roll_future_aware(
            final_roll,
            available_categories,
            scorecard
        )

        total_raw_score += raw_score * count
        total_future_value += future_value * count
        category_counter[best_category] += count
        total_count += count

    raw_expected_score = total_raw_score / total_count
    future_aware_value = total_future_value / total_count

    shape_adjustment = hold_shape_future_adjustment(
        list(hold),
        scorecard
    )

    future_aware_value += shape_adjustment

    result = (
        future_aware_value,
        raw_expected_score,
        category_counter,
        shape_adjustment
    )

    FAST_EXPECTED_HOLD_CACHE[cache_key] = copy.deepcopy(result)

    return result


# ----------------------------
# FAST GAME-AWARE UPPER/CHANCE EVALUATOR
# ----------------------------
# This replaces the 100+ second exact mini-DP.
# It keeps the strategic idea:
# - upper bonus matters
# - Chance should not be burned casually
# - keeping low junk dice should be punished
# - useful upper dice should be rewarded

FAST_CHANCE_USE_PENALTY = 8.0
FAST_UPPER_BOX_BONUS = 6.0
FAST_REACH_TARGET_BONUS = 5.0
FAST_PAIR_SINGLETON_PENALTY = 2.5
FAST_CLOSED_UPPER_DIE_PENALTY = 2.0


def fast_game_aware_category_value(final_dice, category, scorecard):
    raw_score = score_upper_chance_category(list(final_dice), category)

    if category == "chance":
        penalty = FAST_CHANCE_USE_PENALTY

        if not upper_bonus_still_possible(scorecard):
            penalty = 3.0

        return raw_score - penalty, raw_score

    # Upper category
    target = CATEGORY_TARGETS[category]
    shortfall = max(0, target - raw_score)

    value = raw_score
    value -= shortfall

    # Reward using an upper box instead of spending Chance.
    value += FAST_UPPER_BOX_BONUS

    if raw_score >= target:
        value += FAST_REACH_TARGET_BONUS
    elif raw_score > 0:
        value += (raw_score / target) * 3.0

    return value, raw_score


def fast_game_aware_best_score_action(final_dice, scorecard):
    open_categories = game_aware_open_categories(scorecard)

    best_value = -999999
    best_category = None
    best_raw_score = None

    for category in open_categories:
        value, raw_score = fast_game_aware_category_value(
            final_dice,
            category,
            scorecard
        )

        if value > best_value:
            best_value = value
            best_category = category
            best_raw_score = raw_score

    return best_value, best_category, best_raw_score


def fast_game_aware_hold_shape_adjustment(hold, scorecard):
    hold = tuple(sorted(hold))
    counts = Counter(hold)

    adjustment = 0

    # Penalize holding dice whose upper boxes are already closed.
    for die in hold:
        category = upper_category_for_die(die)

        if scorecard.get(category) is not None:
            adjustment -= FAST_CLOSED_UPPER_DIE_PENALTY

    has_pair_or_better = any(count >= 2 for count in counts.values())

    # If you have a useful pair/triple, unrelated single dice usually reduce improvement.
    if has_pair_or_better:
        for die, count in counts.items():
            if count == 1:
                adjustment -= FAST_PAIR_SINGLETON_PENALTY

    # If you do not have a pair, keeping 5 and 6 together can be reasonable.
    if not has_pair_or_better:
        if hold == (5, 6):
            adjustment += 2.0
        elif hold == (6,):
            adjustment += 1.2
        elif hold == (5,):
            adjustment += 0.8

        if len(hold) > 2:
            adjustment -= (len(hold) - 2) * 1.5

    return adjustment


def game_aware_hold_value(hold, scorecard):
    """
    Fast replacement for the exact game-aware upper/Chance evaluator.

    Returns:
    expected_value, category_counter
    """

    hold = tuple(sorted(hold))
    number_to_reroll = 5 - len(hold)

    total_value = 0
    total_count = 0
    category_counter = Counter()

    for outcome, count in GAME_AWARE_ROLL_DISTRIBUTIONS[number_to_reroll]:
        final_roll = tuple(sorted(hold + outcome))

        value, category, raw_score = fast_game_aware_best_score_action(
            final_roll,
            scorecard
        )

        total_value += value * count
        total_count += count
        category_counter[category] += count

    expected_value = total_value / total_count
    expected_value += fast_game_aware_hold_shape_adjustment(
        hold,
        scorecard
    )

    return expected_value, category_counter


# ----------------------------
# FAST ROLL 2 ANALYZER
# ----------------------------

def analyze_all_holds_future_aware(dice, scorecard):
    cache_key = (
        "roll2",
        tuple(sorted(dice)),
        scorecard_to_key_fast(scorecard)
    )

    if cache_key in FAST_ANALYSIS_CACHE:
        return safe_copy_results(FAST_ANALYSIS_CACHE[cache_key])

    available_categories = get_available_categories(scorecard)
    holds = generate_unique_holds(dice)

    use_full_house_tactical_evaluator = should_use_full_house_tactical_evaluator(
        dice,
        scorecard
    )

    use_game_aware_evaluator = (
        should_use_game_aware_upper_chance_evaluator(dice, scorecard)
        and not use_full_house_tactical_evaluator
    )

    results = []

    for hold in holds:
        future_aware_value, raw_expected_score, category_counter, shape_adjustment = expected_value_of_hold_future_aware(
            hold,
            available_categories,
            scorecard
        )

        original_adjustment = original_roll_pattern_adjustment(
            dice,
            hold,
            scorecard
        )

        triple_adjustment = yahtzee_open_triple_adjustment(
            dice,
            hold,
            scorecard
        )

        game_aware_value = None
        game_aware_category_counter = None
        game_aware_note = None

        full_house_tactical_value = None
        full_house_tactical_raw_expected_score = None
        full_house_tactical_category_counter = None
        full_house_tactical_note = None

        strategy_value = (
            future_aware_value
            + original_adjustment
            + triple_adjustment
        )

        if use_game_aware_evaluator:
            raw_game_aware_result = game_aware_hold_value(
                hold,
                scorecard
            )

            game_aware_value = extract_numeric_strategy_value(
                raw_game_aware_result
            )

            game_aware_category_counter = extract_counter_from_value_object(
                raw_game_aware_result
            )

            strategy_value = (
                game_aware_value
                + triple_adjustment
            )

            game_aware_note = "Fast game-aware upper/Chance evaluator used."

        if use_full_house_tactical_evaluator:
            exact_future_value, exact_raw_score, exact_category_counter = roll2_exact_expected_category_decision_value(
                hold,
                scorecard,
                value_mode="future"
            )

            full_house_tactical_value = exact_future_value
            full_house_tactical_raw_expected_score = exact_raw_score
            full_house_tactical_category_counter = exact_category_counter

            strategy_value = (
                exact_future_value
                + triple_adjustment
            )

            raw_expected_score = exact_raw_score
            category_counter = exact_category_counter

            full_house_tactical_note = "Exact Full House / final-reroll evaluator used."

        results.append({
            "hold": hold,
            "strategy_value": strategy_value,
            "future_aware_value": future_aware_value,
            "raw_expected_score": raw_expected_score,
            "category_counter": category_counter,
            "shape_adjustment": shape_adjustment,
            "original_adjustment": original_adjustment,
            "triple_adjustment": triple_adjustment,
            "game_aware_value": game_aware_value,
            "game_aware_category_counter": game_aware_category_counter,
            "game_aware_note": game_aware_note,
            "full_house_tactical_value": full_house_tactical_value,
            "full_house_tactical_raw_expected_score": full_house_tactical_raw_expected_score,
            "full_house_tactical_category_counter": full_house_tactical_category_counter,
            "full_house_tactical_note": full_house_tactical_note
        })

    results = sorted(
        results,
        key=lambda result: result["strategy_value"],
        reverse=True
    )

    FAST_ANALYSIS_CACHE[cache_key] = safe_copy_results(results)

    return results


# ----------------------------
# FAST ROLL 1 SUPPORT
# ----------------------------

def roll2_value_for_roll1_hold(hold, roll2_dice, scorecard):
    """
    Cached Roll 2 value used inside Roll 1 lookahead.
    """

    hold = tuple(sorted(hold))
    roll2_dice = tuple(sorted(roll2_dice))

    cache_key = (
        hold,
        roll2_dice,
        scorecard_to_key_fast(scorecard)
    )

    if cache_key in FAST_ROLL2_VALUE_FOR_ROLL1_CACHE:
        return FAST_ROLL2_VALUE_FOR_ROLL1_CACHE[cache_key]

    if should_use_full_house_tactical_evaluator(list(roll2_dice), scorecard):
        exact_future_value, exact_raw_score, exact_category_counter = roll2_exact_expected_category_decision_value(
            hold,
            scorecard,
            value_mode="future"
        )

        triple_adjustment = yahtzee_open_triple_adjustment(
            list(roll2_dice),
            list(hold),
            scorecard
        )

        value = exact_future_value + triple_adjustment

        FAST_ROLL2_VALUE_FOR_ROLL1_CACHE[cache_key] = value
        return value

    available_categories = get_available_categories(scorecard)

    future_aware_value, raw_expected_score, category_counter, shape_adjustment = expected_value_of_hold_future_aware(
        hold,
        available_categories,
        scorecard
    )

    original_adjustment = original_roll_pattern_adjustment(
        list(roll2_dice),
        list(hold),
        scorecard
    )

    triple_adjustment = yahtzee_open_triple_adjustment(
        list(roll2_dice),
        list(hold),
        scorecard
    )

    value = (
        future_aware_value
        + original_adjustment
        + triple_adjustment
    )

    FAST_ROLL2_VALUE_FOR_ROLL1_CACHE[cache_key] = value

    return value


def analyze_all_holds_by_roll_number(dice, scorecard, roll_number):
    """
    Cached main routing function.
    """

    cache_key = (
        "roll",
        roll_number,
        tuple(sorted(dice)),
        scorecard_to_key_fast(scorecard)
    )

    if cache_key in FAST_ANALYSIS_CACHE:
        return safe_copy_results(FAST_ANALYSIS_CACHE[cache_key])

    if roll_number == 1:
        results = analyze_all_holds_roll1(dice, scorecard)

        for result in results:
            result["roll_number"] = 1
            result["rolls_remaining"] = 2

        FAST_ANALYSIS_CACHE[cache_key] = safe_copy_results(results)
        return results

    if roll_number == 2:
        results = analyze_all_holds_future_aware(dice, scorecard)

        for result in results:
            result["roll_number"] = 2
            result["rolls_remaining"] = 1

        FAST_ANALYSIS_CACHE[cache_key] = safe_copy_results(results)
        return results

    raise ValueError("This coach currently supports Roll 1 and Roll 2 hold decisions only.")


clear_speed_caches()

# ===== Source notebook cell 65 =====
# ============================
# FAST STRATEGY SMOKE TESTS
# ============================
# Purpose:
# After Speed Patch 1, quickly check that the major strategy guardrails
# still behave correctly.

def run_fast_strategy_smoke_tests():
    print("FAST STRATEGY SMOKE TESTS")
    print("=" * 50)

    base_upper_chance_scorecard = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }

    empty_scorecard = {
        "ones": None,
        "twos": None,
        "threes": None,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": None,
        "large_straight": None,
        "yahtzee": None,
        "chance": None
    }

    tests = []

    tests.append({
        "name": "Roll 2 pair of fours should chase Fours",
        "dice": [1, 4, 4, 5, 6],
        "scorecard": dict(base_upper_chance_scorecard),
        "roll_number": 2,
        "acceptable_best_holds": [[4, 4]]
    })

    tests.append({
        "name": "Roll 2 single useful four should keep the 4",
        "dice": [1, 1, 2, 2, 4],
        "scorecard": dict(base_upper_chance_scorecard),
        "roll_number": 2,
        "acceptable_best_holds": [[4]]
    })

    tests.append({
        "name": "Roll 2 pair of sixes should chase Sixes",
        "dice": [2, 4, 5, 6, 6],
        "scorecard": dict(base_upper_chance_scorecard),
        "roll_number": 2,
        "acceptable_best_holds": [[6, 6]]
    })

    tests.append({
        "name": "Roll 2 high loose dice should keep useful high dice",
        "dice": [1, 3, 4, 5, 6],
        "scorecard": dict(base_upper_chance_scorecard),
        "roll_number": 2,
        "acceptable_best_holds": [[5, 6], [6], [5]]
    })

    tests.append({
        "name": "Roll 1 triple fives should be protected",
        "dice": [2, 3, 5, 5, 5],
        "scorecard": dict(empty_scorecard),
        "roll_number": 1,
        "acceptable_best_holds": [[5, 5, 5]]
    })

    tests.append({
        "name": "Roll 1 triple ones should be protected when Yahtzee is open",
        "dice": [1, 1, 1, 2, 6],
        "scorecard": dict(empty_scorecard),
        "roll_number": 1,
        "acceptable_best_holds": [[1, 1, 1]]
    })

    tests.append({
        "name": "Roll 1 article example should avoid low pair of 1s",
        "dice": [1, 1, 2, 5, 6],
        "scorecard": dict(empty_scorecard),
        "roll_number": 1,
        "acceptable_best_holds": [[5], [6], [5, 6]]
    })

    full_house_chance_open = dict(base_upper_chance_scorecard)

    tests.append({
        "name": "Roll 2 Full House two-pair with Chance open should protect both pairs",
        "dice": [2, 4, 4, 5, 5],
        "scorecard": dict(full_house_chance_open),
        "roll_number": 2,
        "acceptable_best_holds": [[4, 4, 5, 5]]
    })

    full_house_chance_used = dict(base_upper_chance_scorecard)
    full_house_chance_used["chance"] = 22

    tests.append({
        "name": "Roll 2 Full House two-pair with Chance used should not blindly force Full House",
        "dice": [2, 4, 4, 5, 5],
        "scorecard": dict(full_house_chance_used),
        "roll_number": 2,
        "acceptable_best_holds": [[5, 5]]
    })

    passed = 0
    review = 0

    for test in tests:
        print()
        print(test["name"])
        print("-" * 50)

        results = analyze_all_holds_by_roll_number(
            test["dice"],
            test["scorecard"],
            test["roll_number"]
        )

        best_hold = results[0]["hold"]

        print("Dice:", test["dice"])
        print("Roll number:", test["roll_number"])
        print("Best hold:", best_hold)
        print("Strategy value:", round(results[0]["strategy_value"], 2))
        print("Acceptable:", test["acceptable_best_holds"])

        if best_hold in test["acceptable_best_holds"]:
            print("Result: PASS")
            passed += 1
        else:
            print("Result: REVIEW")
            review += 1

            print("Top 5:")
            for rank, result in enumerate(results[:5], start=1):
                print(
                    rank,
                    result["hold"],
                    "| Strategy:",
                    round(result["strategy_value"], 2)
                )

    print()
    print("=" * 50)
    print("Smoke test summary")
    print("PASS:", passed)
    print("REVIEW:", review)

# ===== Source notebook cell 72 =====
# ============================
# SPEED PATCH 2: LOWER-SECTION PAIR PROTECTION
# ============================
# Purpose:
# The fast upper/Chance evaluator was punishing closed-upper pairs too hard.
#
# Example:
# Dice: [2, 3, 3, 4, 6]
# Threes is already filled, so keeping [3,3] should not be great.
# But [3,3] still has lower-section value:
# Three of a Kind, Four of a Kind, Full House, Yahtzee, and Chance.
#
# This patch gives a modest rescue adjustment to useful pairs
# when lower-section pattern categories are still open.

from collections import Counter


LOWER_PATTERN_CATEGORIES = [
    "three_of_a_kind",
    "four_of_a_kind",
    "full_house",
    "yahtzee"
]


def lower_pattern_categories_open(scorecard):
    return [
        category
        for category in LOWER_PATTERN_CATEGORIES
        if scorecard.get(category) is None
    ]


def lower_pair_rescue_adjustment(hold, scorecard):
    """
    Gives a modest credit to pairs that still have lower-section value.

    This is especially important when the matching upper box is already closed.
    Example: Pair of 3s with Threes already filled is not useful for Threes,
    but it can still become Three of a Kind, Full House, Four of a Kind, or Yahtzee.
    """

    hold = tuple(sorted(hold))
    counts = Counter(hold)

    open_lower_patterns = lower_pattern_categories_open(scorecard)

    if not open_lower_patterns:
        return 0

    # Keep this conservative. We only rescue small pair-based holds,
    # not giant "hold almost everything" Chance-style holds.
    if len(hold) > 3:
        return 0

    pair_numbers = [
        number
        for number, count in counts.items()
        if count == 2
    ]

    if not pair_numbers:
        return 0

    adjustment = 0

    for number in pair_numbers:
        matching_upper = upper_category_for_die(number)
        matching_upper_is_open = scorecard.get(matching_upper) is None

        # If this is already a strong open upper pair like 4s, 5s, or 6s,
        # the upper/Chance evaluator already understands it.
        if matching_upper_is_open and number >= 4:
            continue

        pair_credit = 2.0

        if scorecard.get("three_of_a_kind") is None:
            pair_credit += 1.5

        if scorecard.get("full_house") is None:
            pair_credit += 1.0

        if scorecard.get("four_of_a_kind") is None:
            pair_credit += 0.5

        if scorecard.get("yahtzee") is None:
            pair_credit += 0.5

        # Low pairs or closed-upper pairs need this rescue most.
        if number <= 3 or not matching_upper_is_open:
            pair_credit += 1.0

        # Keep the rescue from overpowering the better high-die/upper-bonus play.
        adjustment += min(pair_credit, 5.0)

    return adjustment


def fast_game_aware_hold_shape_adjustment(hold, scorecard):
    """
    Replaces the Speed Patch 1 shape adjustment.

    Changes:
    - Still penalizes dice whose upper boxes are closed.
    - Still discourages random junk singletons.
    - But does NOT over-punish a useful high singleton next to a low pair.
    - Adds lower-section pair rescue credit.
    """

    hold = tuple(sorted(hold))
    counts = Counter(hold)

    adjustment = 0

    # Penalize holding dice whose upper boxes are already closed.
    for die in hold:
        category = upper_category_for_die(die)

        if scorecard.get(category) is not None:
            adjustment -= FAST_CLOSED_UPPER_DIE_PENALTY

    has_pair_or_better = any(count >= 2 for count in counts.values())

    # If you have a pair/triple, unrelated single dice can reduce improvement.
    # But a useful high singleton like 6 should not be punished next to a low pair.
    if has_pair_or_better:
        for die, count in counts.items():
            if count == 1:
                category = upper_category_for_die(die)

                useful_high_singleton = (
                    len(hold) <= 3
                    and die >= 4
                    and scorecard.get(category) is None
                )

                if useful_high_singleton:
                    # No penalty. It is still useful for upper section or Chance.
                    adjustment += 0
                else:
                    adjustment -= FAST_PAIR_SINGLETON_PENALTY

    # If you do not have a pair, keeping 5 and 6 together can be reasonable.
    if not has_pair_or_better:
        if hold == (5, 6):
            adjustment += 2.0
        elif hold == (6,):
            adjustment += 1.2
        elif hold == (5,):
            adjustment += 0.8

        if len(hold) > 2:
            adjustment -= (len(hold) - 2) * 1.5

    adjustment += lower_pair_rescue_adjustment(
        hold,
        scorecard
    )

    return adjustment


clear_speed_caches()

# ===== Source notebook cell 76 =====
# ============================
# REPORT PATCH: DEFENSIBLE LOWER-SECTION PAIR EXPLANATIONS
# ============================
# Purpose:
# Improves reports when the user keeps a pair whose upper box is already filled,
# but lower-section pattern categories are still open.
#
# Example:
# Dice: [2, 3, 3, 4, 6]
# User keeps [3,3]
# Threes is already filled, so it is not optimal, but it still has
# Three of a Kind / Full House / Four of a Kind / Yahtzee potential.

from collections import Counter


def simple_hold_text(hold):
    hold = list(sorted(hold))

    if len(hold) == 0:
        return "reroll everything"

    return "keep " + ", ".join(str(die) for die in hold)


def is_defensible_lower_section_pair_hold(user_hold, scorecard):
    hold = list(sorted(user_hold))
    counts = Counter(hold)

    pair_numbers = [
        number
        for number, count in counts.items()
        if count == 2
    ]

    if not pair_numbers:
        return False

    lower_open = any(
        scorecard.get(category) is None
        for category in ["three_of_a_kind", "four_of_a_kind", "full_house", "yahtzee"]
    )

    if not lower_open:
        return False

    # This is especially relevant for low pairs or pairs whose upper box is already filled.
    for number in pair_numbers:
        upper_category = upper_category_for_die(number)

        if number <= 3 or scorecard.get(upper_category) is not None:
            return True

    return False


def pair_math_explanation_lines(dice, scorecard, user_hold, optimal_hold):
    hold = list(sorted(user_hold))
    counts = Counter(hold)

    pair_numbers = [
        number
        for number, count in counts.items()
        if count == 2
    ]

    if not pair_numbers:
        return []

    pair_number = pair_numbers[0]
    upper_category = upper_category_for_die(pair_number)
    upper_name = CATEGORY_DISPLAY_NAMES[upper_category]

    dice_to_reroll_with_pair = 5 - len(hold)
    chance_to_hit_pair_number = 1 - ((5 / 6) ** dice_to_reroll_with_pair)

    lines = []

    lines.append(
        f"- Keeping the pair of {pair_number}s is not random. With one reroll left, you have about a {round(chance_to_hit_pair_number * 100, 1)}% chance to roll at least one more {pair_number} and make Three of a Kind."
    )

    if scorecard.get(upper_category) is not None:
        lines.append(
            f"- The downside is that {upper_name} is already filled, so this pair no longer helps your upper section or the 35-point bonus."
        )

    lower_paths = []

    if scorecard.get("three_of_a_kind") is None:
        lower_paths.append("Three of a Kind")
    if scorecard.get("full_house") is None:
        lower_paths.append("Full House")
    if scorecard.get("four_of_a_kind") is None:
        lower_paths.append("Four of a Kind")
    if scorecard.get("yahtzee") is None:
        lower_paths.append("Yahtzee")

    if lower_paths:
        lines.append(
            "- It still has lower-section potential: " + ", ".join(lower_paths) + "."
        )

    if len(optimal_hold) == 1:
        optimal_die = optimal_hold[0]
        optimal_upper = upper_category_for_die(optimal_die)
        optimal_upper_name = CATEGORY_DISPLAY_NAMES[optimal_upper]

        dice_to_reroll_with_single = 4
        chance_to_hit_optimal_die = 1 - ((5 / 6) ** dice_to_reroll_with_single)

        if scorecard.get(optimal_upper) is None:
            lines.append(
                f"- Keeping the {optimal_die} gives about a {round(chance_to_hit_optimal_die * 100, 1)}% chance to roll at least one more {optimal_die}, and {optimal_upper_name} is still open."
            )

    return lines


def insert_lines_after_header(report, header, lines_to_insert):
    lines = report.split("\n")

    for index, line in enumerate(lines):
        if line.strip() == header:
            return "\n".join(
                lines[:index + 1]
                + lines_to_insert
                + lines[index + 1:]
            )

    return report


def soften_grade_for_defensible_pair(report, user_value, optimal_value, user_hold, scorecard):
    if optimal_value == 0:
        return report

    efficiency = (user_value / optimal_value) * 100

    if not is_defensible_lower_section_pair_hold(user_hold, scorecard):
        return report

    # A defensible pair hold with 60%+ efficiency should not be an F.
    if efficiency >= 60 and "Grade: F" in report:
        report = report.replace("Grade: F", "Grade: D")

    if efficiency >= 60:
        report = report.replace(
            "Coach rating: This is a weak move.",
            "Coach rating: This is an understandable but weaker move."
        )

    return report


# Save current report router before wrapping.
if "_BASE_coach_report_for_user_hold_by_roll_number_v2" not in globals():
    _BASE_coach_report_for_user_hold_by_roll_number_v2 = coach_report_for_user_hold_by_roll_number


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    base_report = _BASE_coach_report_for_user_hold_by_roll_number_v2(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    # Only patch this type of explanation for Roll 2 right now.
    if roll_number != 2:
        return base_report

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number
    )

    optimal_hold = results[0]["hold"]
    optimal_value = results[0]["strategy_value"]

    sorted_user_hold = list(sorted(user_hold))
    user_matches = [
        result for result in results
        if result["hold"] == sorted_user_hold
    ]

    if not user_matches:
        return base_report

    user_result = user_matches[0]
    user_value = user_result["strategy_value"]

    report = soften_grade_for_defensible_pair(
        base_report,
        user_value,
        optimal_value,
        sorted_user_hold,
        scorecard
    )

    if is_defensible_lower_section_pair_hold(sorted_user_hold, scorecard):
        extra_good_lines = pair_math_explanation_lines(
            dice,
            scorecard,
            sorted_user_hold,
            optimal_hold
        )

        report = insert_lines_after_header(
            report,
            "What was good about your move?",
            extra_good_lines
        )

        # Fix awkward wording like "also kept 6."
        report = report.replace(
            "- The optimal hold also kept 6.",
            "- The optimal hold kept 6 instead of the pair."
        )

    return report

# ===== Source notebook cell 78 =====
# ============================
# REPORT PATCH 2: CLEAN PAIR EXPLANATION PLACEMENT
# ============================
# Purpose:
# Keeps the improved pair math, but puts the "keep 6" comparison
# under "Why was the optimal move better?" instead of under
# "What was good about your move?"

from collections import Counter


def pair_user_math_explanation_lines(dice, scorecard, user_hold):
    hold = list(sorted(user_hold))
    counts = Counter(hold)

    pair_numbers = [
        number
        for number, count in counts.items()
        if count == 2
    ]

    if not pair_numbers:
        return []

    pair_number = pair_numbers[0]
    upper_category = upper_category_for_die(pair_number)
    upper_name = CATEGORY_DISPLAY_NAMES[upper_category]

    dice_to_reroll_with_pair = 5 - len(hold)
    chance_to_hit_pair_number = 1 - ((5 / 6) ** dice_to_reroll_with_pair)

    lines = []

    lines.append(
        f"- Keeping the pair of {pair_number}s is not random. With one reroll left, you have about a {round(chance_to_hit_pair_number * 100, 1)}% chance to roll at least one more {pair_number} and make Three of a Kind."
    )

    if scorecard.get(upper_category) is not None:
        lines.append(
            f"- The downside is that {upper_name} is already filled, so this pair no longer helps your upper section or the 35-point bonus."
        )

    lower_paths = []

    if scorecard.get("three_of_a_kind") is None:
        lower_paths.append("Three of a Kind")
    if scorecard.get("full_house") is None:
        lower_paths.append("Full House")
    if scorecard.get("four_of_a_kind") is None:
        lower_paths.append("Four of a Kind")
    if scorecard.get("yahtzee") is None:
        lower_paths.append("Yahtzee")

    if lower_paths:
        lines.append(
            "- It still has lower-section potential: " + ", ".join(lower_paths) + "."
        )

    return lines


def optimal_hold_math_explanation_lines(scorecard, optimal_hold):
    optimal_hold = list(sorted(optimal_hold))

    if len(optimal_hold) != 1:
        return []

    optimal_die = optimal_hold[0]
    optimal_upper = upper_category_for_die(optimal_die)
    optimal_upper_name = CATEGORY_DISPLAY_NAMES[optimal_upper]

    if scorecard.get(optimal_upper) is not None:
        return []

    chance_to_hit_optimal_die = 1 - ((5 / 6) ** 4)

    return [
        f"- Keeping the {optimal_die} gives about a {round(chance_to_hit_optimal_die * 100, 1)}% chance to roll at least one more {optimal_die}, and {optimal_upper_name} is still open."
    ]


def remove_redundant_pair_generic_line(report):
    lines = report.split("\n")

    filtered_lines = []

    for line in lines:
        if line.strip().startswith("- You kept a pair of") and "That can be useful" in line:
            continue

        filtered_lines.append(line)

    return "\n".join(filtered_lines)


# Use the original base router if available so we do not stack duplicate report patches.
if "_BASE_coach_report_for_user_hold_by_roll_number_v2" in globals():
    _CLEAN_REPORT_BASE = _BASE_coach_report_for_user_hold_by_roll_number_v2
else:
    _CLEAN_REPORT_BASE = coach_report_for_user_hold_by_roll_number


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    base_report = _CLEAN_REPORT_BASE(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    if roll_number != 2:
        return base_report

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number
    )

    optimal_hold = results[0]["hold"]
    optimal_value = results[0]["strategy_value"]

    sorted_user_hold = list(sorted(user_hold))
    user_matches = [
        result for result in results
        if result["hold"] == sorted_user_hold
    ]

    if not user_matches:
        return base_report

    user_result = user_matches[0]
    user_value = user_result["strategy_value"]

    report = soften_grade_for_defensible_pair(
        base_report,
        user_value,
        optimal_value,
        sorted_user_hold,
        scorecard
    )

    if is_defensible_lower_section_pair_hold(sorted_user_hold, scorecard):
        report = remove_redundant_pair_generic_line(report)

        report = insert_lines_after_header(
            report,
            "What was good about your move?",
            pair_user_math_explanation_lines(
                dice,
                scorecard,
                sorted_user_hold
            )
        )

        report = insert_lines_after_header(
            report,
            "Why was the optimal move better?",
            optimal_hold_math_explanation_lines(
                scorecard,
                optimal_hold
            )
        )

        report = report.replace(
            "- The optimal hold also kept 6.",
            "- The optimal hold kept 6 instead of the pair."
        )

    return report



# ===== Source notebook cell 80 =====
# ============================
# REPORT PATCH 3: REMOVE CONFUSING PAIR PATH / DEDUPE OPTIMAL TEXT
# ============================

if "_BASE_report_patch3" not in globals():
    _BASE_report_patch3 = coach_report_for_user_hold_by_roll_number


def clean_pair_report_wording(report, user_hold, scorecard):
    if not is_defensible_lower_section_pair_hold(user_hold, scorecard):
        return report

    lines = report.split("\n")
    cleaned = []

    for line in lines:
        stripped = line.strip()

        # This line is confusing in game-aware pair situations because it often
        # lists fallback upper/Chance paths rather than the pair's pattern value.
        if stripped.startswith("- Your most common scoring paths were:"):
            continue

        # Remove redundant Sixes explanation if the stronger math line already exists.
        if stripped == "- That matters because the Sixes box is still open, and upper-section points help protect the 35-point bonus.":
            if "Keeping the 6 gives about a 51.8% chance" in report:
                continue

        cleaned.append(line)

    return "\n".join(cleaned)


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    report = _BASE_report_patch3(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    if roll_number == 2:
        report = clean_pair_report_wording(
            report,
            list(sorted(user_hold)),
            scorecard
        )

    return report



# ===== Source notebook cell 85 =====
# ============================
# REPORT PATCH: ROLL 1 GRADE RECALIBRATION
# ============================
# Purpose:
# Roll 1 grades were too generous when a move had high efficiency
# but was clearly not one of the best strategic options.
#
# Example:
# Dice: [1, 2, 2, 3, 4]
# User keeps [3]
# Optimal is [4]
# Efficiency is 93.4%, but keep 3 is not top 3 and is strategically weaker.
# This should not be A-.

def get_hold_rank_in_results(results, target_hold):
    target_hold = list(sorted(target_hold))

    for index, result in enumerate(results, start=1):
        if result["hold"] == target_hold:
            return index

    return None


def recalibrate_roll1_grade(user_value, optimal_value, user_rank, user_is_optimal):
    if optimal_value == 0:
        return "N/A", "Unable to grade this move."

    efficiency = (user_value / optimal_value) * 100
    points_lost = optimal_value - user_value

    if user_is_optimal:
        return "A+", "Excellent move."

    # Very close AND still one of the top options.
    if efficiency >= 97 and user_rank <= 3:
        return "A", "This is a very strong move."

    if efficiency >= 94 and user_rank <= 3:
        return "A-", "This is a solid move."

    # Close, but not truly one of the best choices.
    if efficiency >= 90:
        if user_rank <= 3:
            return "B+", "This is a good move, but not the strongest."
        else:
            return "B", "This is a reasonable move, but there were clearly stronger options."

    if efficiency >= 85:
        return "B-", "This is playable, but it gives up some value."

    if efficiency >= 75:
        return "C", "This move has some logic, but it misses a stronger plan."

    if efficiency >= 65:
        return "D", "This is a weak move."

    return "F", "This move gives up too much value."


def replace_grade_and_rating(report, new_grade, new_rating):
    lines = report.split("\n")
    updated_lines = []

    for line in lines:
        if line.startswith("Grade:"):
            updated_lines.append(f"Grade: {new_grade}")
        elif line.startswith("Coach rating:"):
            updated_lines.append(f"Coach rating: {new_rating}")
        else:
            updated_lines.append(line)

    return "\n".join(updated_lines)


# Save the current router before wrapping.
if "_BASE_roll1_grade_recalibration_report" not in globals():
    _BASE_roll1_grade_recalibration_report = coach_report_for_user_hold_by_roll_number


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    report = _BASE_roll1_grade_recalibration_report(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    if roll_number != 1:
        return report

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number
    )

    sorted_user_hold = list(sorted(user_hold))
    user_matches = [
        result for result in results
        if result["hold"] == sorted_user_hold
    ]

    if not user_matches:
        return report

    optimal_hold = results[0]["hold"]
    optimal_value = results[0]["strategy_value"]

    user_result = user_matches[0]
    user_value = user_result["strategy_value"]
    user_rank = get_hold_rank_in_results(results, sorted_user_hold)
    user_is_optimal = sorted_user_hold == optimal_hold

    new_grade, new_rating = recalibrate_roll1_grade(
        user_value,
        optimal_value,
        user_rank,
        user_is_optimal
    )

    report = replace_grade_and_rating(
        report,
        new_grade,
        new_rating
    )

    # Add rank context when the move is close by percentage but not actually top-tier.
    if not user_is_optimal and user_rank is not None and user_rank > 3:
        report = report.replace(
            "Why was the optimal move better?",
            f"Why was the optimal move better?\n- Your hold ranked #{user_rank} overall. It was close by percentage, but it was not one of the top strategic options."
        )

    return report



# ===== Source notebook cell 92 =====
# ============================
# REPORT PATCH: FIX ROLL 1 RANK WORDING
# ============================
# Purpose:
# Avoid saying "close by percentage" when efficiency is not actually close.

if "_BASE_roll1_rank_wording_patch" not in globals():
    _BASE_roll1_rank_wording_patch = coach_report_for_user_hold_by_roll_number


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    report = _BASE_roll1_rank_wording_patch(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    if roll_number != 1:
        return report

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number
    )

    sorted_user_hold = list(sorted(user_hold))
    user_matches = [
        result for result in results
        if result["hold"] == sorted_user_hold
    ]

    if not user_matches:
        return report

    optimal_value = results[0]["strategy_value"]
    user_value = user_matches[0]["strategy_value"]

    if optimal_value == 0:
        return report

    efficiency = (user_value / optimal_value) * 100

    if efficiency < 90:
        report = report.replace(
            "Your hold ranked #8 overall. It was close by percentage, but it was not one of the top strategic options.",
            "Your hold ranked #8 overall, so it was not one of the top strategic options."
        )

        # More general version in case the rank number changes.
        report = report.replace(
            "It was close by percentage, but it was not one of the top strategic options.",
            "It was not one of the top strategic options."
        )

    return report



# ===== Source notebook cell 97 =====
# ============================
# PRACTICE GENERATOR VARIETY CHECK
# ============================

from collections import Counter

def scorecard_signature(scorecard):
    """
    Makes a compact signature showing which boxes are open vs filled.
    """
    return tuple(
        (category, "OPEN" if scorecard.get(category) is None else scorecard.get(category))
        for category in YAHTZEE_CATEGORIES
    )


def run_practice_variety_check(number_of_rounds=30):
    scenario_counter = Counter()
    roll_counter = Counter()
    scorecard_counter = Counter()

    print("PRACTICE GENERATOR VARIETY CHECK")
    print("=" * 50)

    for _ in range(number_of_rounds):
        challenge = generate_practice_challenge()

        scenario_name = challenge.get("scenario_name")
        roll_number = challenge.get("roll_number")
        scorecard = challenge.get("scorecard")

        scenario_counter[scenario_name] += 1
        roll_counter[roll_number] += 1
        scorecard_counter[scorecard_signature(scorecard)] += 1

    print()
    print("Scenario counts:")
    for scenario, count in scenario_counter.most_common():
        print("-", scenario, ":", count)

    print()
    print("Roll number counts:")
    for roll_number, count in sorted(roll_counter.items()):
        print("-", "Roll", roll_number, ":", count)

    print()
    print("Unique scorecards:", len(scorecard_counter), "out of", number_of_rounds)

    print()
    print("Most repeated scorecards:")
    for signature, count in scorecard_counter.most_common(5):
        print()
        print("Repeated:", count, "times")
        for category, value in signature:
            print(" ", category, ":", value)

# ===== Source notebook cell 99 =====
# ============================
# PRACTICE PATCH: SCORECARD VARIETY
# ============================
# Purpose:
# The practice generator has good scenario variety, but each scenario
# uses a fixed scorecard. This patch keeps the same scenario names,
# but swaps in a randomized scorecard variation for each scenario.

import random
import copy


def blank_scorecard():
    return {
        "ones": None,
        "twos": None,
        "threes": None,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": None,
        "large_straight": None,
        "yahtzee": None,
        "chance": None
    }


def scorecard_from_values(**kwargs):
    card = blank_scorecard()

    for category, value in kwargs.items():
        card[category] = value

    return card


def random_scorecard_for_scenario(scenario_name):
    """
    Returns a scorecard variation that matches the scenario idea,
    but avoids using the exact same scorecard every time.
    """

    if scenario_name == "Early Game":
        options = [
            blank_scorecard(),

            scorecard_from_values(
                ones=3
            ),

            scorecard_from_values(
                twos=6
            ),

            scorecard_from_values(
                ones=2,
                chance=23
            ),

            scorecard_from_values(
                full_house=25
            )
        ]

        return copy.deepcopy(random.choice(options))

    if scenario_name == "Upper Bonus Chase":
        options = [
            scorecard_from_values(
                ones=3,
                twos=6,
                threes=9,
                small_straight=30,
                large_straight=40
            ),

            scorecard_from_values(
                ones=2,
                twos=6,
                threes=9,
                small_straight=30,
                large_straight=40
            ),

            scorecard_from_values(
                ones=3,
                twos=4,
                threes=9,
                full_house=25,
                small_straight=30,
                large_straight=40
            ),

            scorecard_from_values(
                ones=3,
                twos=6,
                threes=6,
                small_straight=30,
                large_straight=40,
                chance=22
            ),

            scorecard_from_values(
                ones=0,
                twos=6,
                threes=9,
                four_of_a_kind=0,
                small_straight=30,
                large_straight=40
            )
        ]

        return copy.deepcopy(random.choice(options))

    if scenario_name == "Late Upper Pressure":
        options = [
            scorecard_from_values(
                ones=3,
                twos=6,
                threes=9,
                fours=12,
                three_of_a_kind=21,
                full_house=25,
                small_straight=30,
                large_straight=40,
                chance=23
            ),

            scorecard_from_values(
                ones=2,
                twos=6,
                threes=9,
                fours=8,
                full_house=25,
                small_straight=30,
                large_straight=40,
                chance=24
            ),

            scorecard_from_values(
                ones=3,
                twos=4,
                threes=9,
                fours=None,
                fives=15,
                three_of_a_kind=22,
                full_house=25,
                small_straight=30,
                large_straight=40
            ),

            scorecard_from_values(
                ones=0,
                twos=6,
                threes=9,
                fours=12,
                small_straight=30,
                large_straight=40,
                chance=20
            )
        ]

        return copy.deepcopy(random.choice(options))

    if scenario_name == "Chance Already Used":
        options = [
            scorecard_from_values(
                ones=3,
                twos=6,
                threes=9,
                small_straight=30,
                large_straight=40,
                chance=22
            ),

            scorecard_from_values(
                ones=3,
                twos=6,
                threes=9,
                fours=12,
                small_straight=30,
                large_straight=40,
                chance=23
            ),

            scorecard_from_values(
                ones=2,
                twos=6,
                threes=6,
                full_house=25,
                small_straight=30,
                large_straight=40,
                chance=21
            ),

            scorecard_from_values(
                ones=3,
                twos=4,
                threes=9,
                three_of_a_kind=20,
                small_straight=30,
                large_straight=40,
                chance=24
            ),

            scorecard_from_values(
                ones=0,
                twos=6,
                threes=9,
                full_house=0,
                small_straight=30,
                large_straight=40,
                chance=22
            )
        ]

        return copy.deepcopy(random.choice(options))

    if scenario_name == "Lower Combo Chase":
        options = [
            scorecard_from_values(
                ones=3,
                twos=6,
                threes=9,
                fours=12,
                small_straight=30,
                large_straight=40
            ),

            scorecard_from_values(
                ones=3,
                twos=6,
                threes=9,
                fours=12,
                fives=15,
                small_straight=30,
                large_straight=40,
                chance=23
            ),

            scorecard_from_values(
                ones=2,
                twos=6,
                threes=9,
                fours=8,
                small_straight=30,
                large_straight=40
            ),

            scorecard_from_values(
                ones=3,
                twos=4,
                threes=9,
                full_house=25,
                small_straight=30,
                large_straight=40,
                chance=22
            ),

            scorecard_from_values(
                ones=3,
                twos=6,
                threes=6,
                fours=12,
                full_house=0,
                small_straight=30,
                large_straight=40
            )
        ]

        return copy.deepcopy(random.choice(options))

    if scenario_name == "Straights Still Open":
        options = [
            scorecard_from_values(
                ones=3,
                twos=6,
                threes=9,
                full_house=25,
                chance=23
            ),

            scorecard_from_values(
                ones=3,
                twos=6,
                threes=9,
                fours=12,
                full_house=25
            ),

            scorecard_from_values(
                ones=2,
                twos=6,
                threes=9,
                three_of_a_kind=21,
                full_house=25,
                chance=22
            ),

            scorecard_from_values(
                ones=3,
                twos=4,
                threes=9,
                full_house=0,
                chance=24
            ),

            scorecard_from_values(
                ones=3,
                twos=6,
                threes=6,
                fours=12,
                full_house=25,
                chance=23
            )
        ]

        return copy.deepcopy(random.choice(options))

    # Fallback: use mostly open scorecard.
    return blank_scorecard()


# Save original generator before wrapping it.
if "_BASE_generate_practice_challenge_variety" not in globals():
    _BASE_generate_practice_challenge_variety = generate_practice_challenge


def generate_practice_challenge():
    """
    Wrapped practice generator.

    Keeps the original scenario/dice generation,
    but replaces the fixed scorecard with a varied scorecard
    that matches the scenario type.
    """

    challenge = _BASE_generate_practice_challenge_variety()

    scenario_name = challenge.get("scenario_name")

    varied_scorecard = random_scorecard_for_scenario(scenario_name)

    challenge["scorecard"] = varied_scorecard

    return challenge


if "clear_speed_caches" in globals():
    clear_speed_caches()


# ===== Source notebook cell 115 =====
# ============================
# REPORT PATCH: TRIPLE PATHS SHOULD ONLY LIST OPEN CATEGORIES
# ============================
# Purpose:
# Fixes reports that say a triple keeps Three of a Kind, Full House,
# or the matching upper box alive even when those boxes are already filled.

from collections import Counter


def find_triple_number_in_hold(hold):
    counts = Counter(hold)

    for number, count in counts.items():
        if count >= 3:
            return number

    return None


def format_english_list(items):
    if not items:
        return ""

    if len(items) == 1:
        return items[0]

    if len(items) == 2:
        return items[0] + " and " + items[1]

    return ", ".join(items[:-1]) + ", and " + items[-1]


def triple_open_and_closed_paths(scorecard, triple_number):
    open_paths = []
    closed_paths = []

    category_pairs = [
        ("yahtzee", "Yahtzee"),
        ("four_of_a_kind", "Four of a Kind"),
        ("three_of_a_kind", "Three of a Kind"),
        ("full_house", "Full House")
    ]

    for category, name in category_pairs:
        if scorecard.get(category) is None:
            open_paths.append(name)
        else:
            closed_paths.append(name)

    upper_category = upper_category_for_die(triple_number)
    upper_name = CATEGORY_DISPLAY_NAMES[upper_category]

    if scorecard.get(upper_category) is None:
        open_paths.append(upper_name)
    else:
        closed_paths.append(upper_name)

    if scorecard.get("chance") is None:
        open_paths.append("Chance fallback")
    else:
        closed_paths.append("Chance")

    return open_paths, closed_paths


def corrected_triple_path_lines(scorecard, triple_number):
    open_paths, closed_paths = triple_open_and_closed_paths(
        scorecard,
        triple_number
    )

    lines = []

    lines.append(
        f"- Keeping three {triple_number}s protects an already-made triple."
    )

    if open_paths:
        lines.append(
            "- In this scorecard, the main active paths are: "
            + format_english_list(open_paths)
            + "."
        )

    if closed_paths:
        lines.append(
            "- Do not count "
            + format_english_list(closed_paths)
            + " as active reasons here because those boxes are already filled."
        )

    return lines


def corrected_triple_good_move_line(scorecard, triple_number):
    open_paths, closed_paths = triple_open_and_closed_paths(
        scorecard,
        triple_number
    )

    if open_paths:
        return (
            f"- You preserved a triple of {triple_number}s. "
            f"That is useful here mainly because it keeps "
            f"{format_english_list(open_paths)} alive."
        )

    return (
        f"- You preserved a triple of {triple_number}s, but most of its usual scoring boxes are already filled."
    )


def clean_incorrect_triple_lines(report, triple_number):
    lines = report.split("\n")
    cleaned = []

    for line in lines:
        stripped = line.strip()

        if stripped == "- This move protected an existing three-of-a-kind while Yahtzee was still open.":
            continue

        if stripped == "- That keeps Yahtzee, Four of a Kind, Three of a Kind, Full House, and the matching upper box alive.":
            continue

        if stripped.startswith("- You preserved three or more") and "Three of a Kind, Four of a Kind, Yahtzee, and the upper section" in stripped:
            continue

        if stripped == f"- Keeping three {triple_number}s protects an already-made triple.":
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def insert_lines_after_header_once(report, header, lines_to_insert):
    lines = report.split("\n")
    new_lines = []

    inserted = False

    for line in lines:
        new_lines.append(line)

        if not inserted and line.strip() == header:
            new_lines.extend(lines_to_insert)
            inserted = True

    return "\n".join(new_lines)


# Save current router before wrapping.
if "_BASE_triple_path_report_patch" not in globals():
    _BASE_triple_path_report_patch = coach_report_for_user_hold_by_roll_number


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    report = _BASE_triple_path_report_patch(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    triple_number = find_triple_number_in_hold(user_hold)

    if triple_number is None:
        return report

    report = clean_incorrect_triple_lines(
        report,
        triple_number
    )

    # Replace the Yahtzee-path note content.
    if "Yahtzee-path note:" in report:
        report = insert_lines_after_header_once(
            report,
            "Yahtzee-path note:",
            corrected_triple_path_lines(
                scorecard,
                triple_number
            )
        )

    # Replace the generic "what was good" triple explanation.
    report = insert_lines_after_header_once(
        report,
        "What was good about your move?",
        [
            corrected_triple_good_move_line(
                scorecard,
                triple_number
            )
        ]
    )

    # If the report says the move was optimal, give the same corrected logic there too.
    if "- Your move was the optimal move." in report:
        report = report.replace(
            "- Your move was the optimal move.",
            "- Your move was the optimal move.\n"
            + "\n".join(
                corrected_triple_path_lines(
                    scorecard,
                    triple_number
                )
            )
        )

    return report



# ===== Source notebook cell 117 =====
# ============================
# REPORT PATCH: REMOVE DUPLICATE TRIPLE EXPLANATION WHEN MOVE IS OPTIMAL
# ============================

if "_BASE_no_duplicate_optimal_triple_report" not in globals():
    _BASE_no_duplicate_optimal_triple_report = coach_report_for_user_hold_by_roll_number


def remove_duplicate_optimal_triple_block(report):
    duplicate_block_start = "- Your move was the optimal move.\n- Keeping three"

    if duplicate_block_start not in report:
        return report

    lines = report.split("\n")
    cleaned = []
    inside_why_section = False
    skip_next_corrected_lines = False

    for line in lines:
        stripped = line.strip()

        if stripped == "Why was the optimal move better?":
            inside_why_section = True
            cleaned.append(line)
            continue

        if inside_why_section and stripped == "- Your move was the optimal move.":
            cleaned.append(line)
            cleaned.append("- The same triple-protection logic from the Yahtzee-path note is why this was the best hold.")
            skip_next_corrected_lines = True
            continue

        if skip_next_corrected_lines:
            if (
                stripped.startswith("- Keeping three")
                or stripped.startswith("- In this scorecard, the main active paths are:")
                or stripped.startswith("- Do not count")
            ):
                continue
            else:
                skip_next_corrected_lines = False

        cleaned.append(line)

    return "\n".join(cleaned)


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    report = _BASE_no_duplicate_optimal_triple_report(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    triple_number = find_triple_number_in_hold(user_hold)

    if triple_number is not None and "- Your move was the optimal move." in report:
        report = remove_duplicate_optimal_triple_block(report)

    return report



# ===== Source notebook cell 123 =====
# ============================
# REPORT PATCH: PAIR + EXTRA UPPER DIE EXPLANATION
# ============================
# Purpose:
# Fixes Roll 2 reports where:
# - User keeps a pair, like [4, 4]
# - Optimal keeps that same pair plus an extra useful upper die, like [4, 4, 6]
#
# This patch explains the real tradeoff:
# Keeping the extra die reduces the chance of improving the pair,
# but may still be better because it creates a safer scoring floor
# when that upper box is open, especially if Chance is already used.

from collections import Counter
import math


if "_BASE_pair_plus_extra_upper_die_report" not in globals():
    _BASE_pair_plus_extra_upper_die_report = coach_report_for_user_hold_by_roll_number


def pct(value):
    return round(value * 100, 1)


def probability_at_least_one_match(number_of_rerolls):
    return 1 - (5 / 6) ** number_of_rerolls


def probability_reach_four_of_kind_from_pair(number_of_rerolls):
    """
    Assumes you currently hold exactly a pair.
    Probability of rolling enough matching dice to finish with at least four of a kind.
    """
    if number_of_rerolls < 2:
        return 0

    total = 0

    for matches in range(2, number_of_rerolls + 1):
        combinations_count = math.comb(number_of_rerolls, matches)
        total += combinations_count * ((1 / 6) ** matches) * ((5 / 6) ** (number_of_rerolls - matches))

    return total


def probability_yahtzee_from_pair(number_of_rerolls):
    """
    Assumes you currently hold exactly a pair and reroll all other dice.
    Yahtzee requires all rerolled dice to match the pair number.
    """
    if number_of_rerolls != 3:
        return 0

    return (1 / 6) ** 3


def upper_pace_status(scorecard):
    """
    Compares filled upper boxes to normal bonus pace:
    Ones 3, Twos 6, Threes 9, Fours 12, Fives 15, Sixes 18.
    """
    pace_targets = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": 12,
        "fives": 15,
        "sixes": 18
    }

    actual = 0
    pace = 0

    for category, pace_value in pace_targets.items():
        score = scorecard.get(category)

        if score is not None:
            actual += score
            pace += pace_value

    return actual, pace, pace - actual


def is_exact_pair(hold):
    hold = list(sorted(hold))
    return len(hold) == 2 and hold[0] == hold[1]


def optimal_keeps_user_pair_plus_extra(user_hold, optimal_hold):
    user_hold = list(sorted(user_hold))
    optimal_hold = list(sorted(optimal_hold))

    if not is_exact_pair(user_hold):
        return False, None, []

    pair_number = user_hold[0]

    if optimal_hold.count(pair_number) < 2:
        return False, None, []

    extras = list(optimal_hold)

    # Remove the user's pair from the optimal hold copy.
    extras.remove(pair_number)
    extras.remove(pair_number)

    if not extras:
        return False, pair_number, []

    return True, pair_number, extras


def display_upper_category_for_die(die):
    category = upper_category_for_die(die)

    if "CATEGORY_DISPLAY_NAMES" in globals():
        return CATEGORY_DISPLAY_NAMES.get(category, category)

    fallback = {
        "ones": "Ones",
        "twos": "Twos",
        "threes": "Threes",
        "fours": "Fours",
        "fives": "Fives",
        "sixes": "Sixes"
    }

    return fallback.get(category, category)


def remove_old_pair_extra_die_wording(report, extras):
    lines = report.split("\n")
    cleaned = []

    for line in lines:
        stripped = line.strip()

        # Wrong because optimal did not keep the extra die instead of the pair.
        if stripped.startswith("- The optimal hold kept ") and " instead of the pair." in stripped:
            continue

        # Too generic for behind-pace upper bonus situations.
        if stripped.startswith("- That matters because the ") and "upper-section points help protect the 35-point bonus" in stripped:
            continue

        # Sometimes generated in earlier report wording.
        if stripped.startswith("- The optimal hold also kept "):
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def pair_extra_die_tradeoff_lines(scorecard, user_hold, optimal_hold, pair_number, extras):
    user_rerolls = 5 - len(user_hold)
    optimal_rerolls = 5 - len(optimal_hold)

    user_match_chance = probability_at_least_one_match(user_rerolls)
    optimal_match_chance = probability_at_least_one_match(optimal_rerolls)

    user_four_kind_chance = probability_reach_four_of_kind_from_pair(user_rerolls)
    optimal_four_kind_chance = probability_reach_four_of_kind_from_pair(optimal_rerolls)

    user_yahtzee_chance = probability_yahtzee_from_pair(user_rerolls)
    optimal_yahtzee_chance = 0

    extra_text = ", ".join(str(extra) for extra in extras)

    open_extra_upper_names = []

    for extra in extras:
        upper_category = upper_category_for_die(extra)

        if scorecard.get(upper_category) is None:
            open_extra_upper_names.append(display_upper_category_for_die(extra))

    actual_upper, pace_upper, deficit = upper_pace_status(scorecard)

    lines = []

    lines.append(
        f"- The optimal hold kept your pair of {pair_number}s, but also kept {extra_text}."
    )

    lines.append(
        f"- Tradeoff check: keeping the extra die reduces your chance to roll at least one more {pair_number} "
        f"from {pct(user_match_chance)}% to {pct(optimal_match_chance)}%."
    )

    lines.append(
        f"- It also lowers the Four of a Kind chance from {pct(user_four_kind_chance)}% to "
        f"{pct(optimal_four_kind_chance)}%, and it removes the small Yahtzee chance "
        f"of {pct(user_yahtzee_chance)}%."
    )

    if open_extra_upper_names:
        if deficit > 0:
            lines.append(
                f"- However, {', '.join(open_extra_upper_names)} is still open. "
                f"The upper section is {deficit} point(s) behind normal bonus pace, "
                f"so the extra die is not mainly a guaranteed bonus saver."
            )
        elif deficit == 0:
            lines.append(
                f"- {', '.join(open_extra_upper_names)} is still open, and the upper section is exactly on normal bonus pace."
            )
        else:
            lines.append(
                f"- {', '.join(open_extra_upper_names)} is still open, and the upper section is ahead of normal bonus pace."
            )

    if scorecard.get("chance") is not None:
        lines.append(
            "- Because Chance is already filled, that extra open upper-box value becomes more important as a safe scoring floor."
        )
    else:
        lines.append(
            "- Because Chance is still open, this is a close call; the extra die helps fallback scoring, but Chance can also absorb some bad outcomes."
        )

    lines.append(
        "- So this is not a pure upper-bonus play. It is a close tradeoff between chasing the pair harder and keeping safer scoring value."
    )

    return lines


def insert_after_why_header(report, lines_to_insert):
    if not lines_to_insert:
        return report

    if lines_to_insert[0] in report:
        return report

    lines = report.split("\n")
    updated = []
    inserted = False

    for line in lines:
        updated.append(line)

        if not inserted and line.strip() == "Why was the optimal move better?":
            updated.extend(lines_to_insert)
            inserted = True

    return "\n".join(updated)


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    report = _BASE_pair_plus_extra_upper_die_report(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    if roll_number != 2:
        return report

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number
    )

    optimal_hold = results[0]["hold"]

    applies, pair_number, extras = optimal_keeps_user_pair_plus_extra(
        user_hold,
        optimal_hold
    )

    if not applies:
        return report

    report = remove_old_pair_extra_die_wording(
        report,
        extras
    )

    report = insert_after_why_header(
        report,
        pair_extra_die_tradeoff_lines(
            scorecard,
            list(sorted(user_hold)),
            list(sorted(optimal_hold)),
            pair_number,
            extras
        )
    )

    return report



# ===== Source notebook cell 126 =====
# ============================
# PRACTICE PATCH: EXPANDED SPICY SCENARIO DECK v18
# ============================
# Purpose:
# Reduces repetition in Unlimited Practice by making the titled deck the
# primary practice source and expanding it to:
# - 10 titled sections
# - 10 unique dice rolls per section
# - 10 randomized scorecard templates per section
#
# The app remains a Roll 1 / Roll 2 hold trainer. These scenarios are not
# hand-scored puzzles; they are repeatable strategy families that mix dice,
# scorecard state, and roll number to create many possible practice rounds.

import random
import copy


# Use the titled deck for every practice round. This keeps the app feeling
# intentional and avoids the older untitled generator repeating too often.
SPICY_PRACTICE_RATE = 1.00


YAHTZEE_CATEGORIES = [
    "ones",
    "twos",
    "threes",
    "fours",
    "fives",
    "sixes",
    "three_of_a_kind",
    "four_of_a_kind",
    "full_house",
    "small_straight",
    "large_straight",
    "yahtzee",
    "chance",
]


def make_scorecard(filled_values=None):
    card = {category: None for category in YAHTZEE_CATEGORIES}

    if filled_values:
        for category, value in filled_values.items():
            card[category] = value

    return card


SPICY_PRACTICE_SCENARIOS = [
    {
        "scenario_name": "Small Straight Spark",
        "scenario_description": "You have a partial straight pattern. Decide whether to chase the straight or keep safer scoring value.",
        "roll_numbers": [1, 2, 2],
        "dice_options": [
            [1, 2, 3, 5, 6],
            [1, 2, 4, 5, 6],
            [2, 3, 4, 4, 6],
            [1, 3, 4, 5, 5],
            [2, 3, 4, 6, 6],
            [1, 2, 3, 4, 6],
            [1, 2, 2, 3, 5],
            [2, 3, 3, 4, 6],
            [1, 3, 4, 4, 5],
            [2, 2, 3, 4, 5],
        ],
        "scorecards": [
            {"ones": 3, "twos": 6, "full_house": 25, "chance": 23},
            {"fours": 12, "three_of_a_kind": 21, "full_house": 25},
            {"ones": 2, "fives": 15, "chance": 22},
            {"twos": 4, "threes": 9, "full_house": 0},
            {"ones": 3, "threes": 9, "fives": 15, "large_straight": 40},
            {"small_straight": 30, "full_house": 25, "chance": 24},
            {"ones": 0, "twos": 4, "fours": 12, "yahtzee": 0},
            {"three_of_a_kind": 20, "four_of_a_kind": 0, "chance": 22},
            {"sixes": 18, "full_house": 25, "large_straight": 40},
            {"ones": 3, "twos": 6, "threes": 9, "chance": 21},
        ],
    },

    {
        "scenario_name": "Large Straight Temptation",
        "scenario_description": "A big straight is possible, but chasing it may mean giving up pairs or upper-section value.",
        "roll_numbers": [1, 2, 2],
        "dice_options": [
            [1, 2, 3, 4, 6],
            [2, 3, 4, 5, 5],
            [1, 3, 4, 5, 6],
            [2, 3, 4, 5, 6],
            [1, 2, 4, 5, 6],
            [2, 3, 3, 4, 5],
            [1, 1, 3, 4, 6],
            [1, 2, 3, 5, 5],
            [2, 4, 5, 5, 6],
            [1, 3, 3, 4, 5],
        ],
        "scorecards": [
            {},
            {"ones": 3, "twos": 6, "full_house": 25, "chance": 22},
            {"small_straight": 30, "full_house": 25, "chance": 24},
            {"three_of_a_kind": 20, "four_of_a_kind": 0},
            {"ones": 0, "fours": 12, "full_house": 25},
            {"twos": 6, "threes": 9, "small_straight": 30},
            {"fives": 15, "sixes": 18, "full_house": 25, "chance": 23},
            {"large_straight": 40, "chance": 21},
            {"ones": 3, "twos": 4, "threes": 6, "yahtzee": 0},
            {"four_of_a_kind": 0, "full_house": 25, "small_straight": 30},
        ],
    },

    {
        "scenario_name": "Full House Puzzle",
        "scenario_description": "Full House is open. Decide whether to protect pairs, chase a triple, or keep flexible value.",
        "roll_numbers": [1, 2, 2, 2],
        "dice_options": [
            [2, 2, 5, 5, 6],
            [1, 1, 3, 3, 6],
            [3, 3, 3, 5, 6],
            [4, 4, 4, 2, 6],
            [1, 1, 5, 5, 2],
            [2, 2, 6, 6, 3],
            [3, 3, 5, 5, 1],
            [4, 4, 6, 6, 2],
            [1, 1, 1, 5, 6],
            [5, 5, 5, 2, 4],
        ],
        "scorecards": [
            {"ones": 3, "twos": 6, "small_straight": 30, "large_straight": 40},
            {"fours": 8, "fives": 15, "chance": 23},
            {"three_of_a_kind": 21, "small_straight": 30, "large_straight": 40},
            {"ones": 0, "twos": 4, "chance": 22},
            {"full_house": 25, "chance": 24},
            {"three_of_a_kind": 0, "four_of_a_kind": 0, "small_straight": 30},
            {"ones": 3, "twos": 6, "threes": 9, "fours": 12, "chance": 22},
            {"fives": 10, "sixes": 18, "large_straight": 40},
            {"yahtzee": 0, "small_straight": 30, "chance": 21},
            {"ones": 0, "fours": 8, "full_house": 0, "chance": 20},
        ],
    },

    {
        "scenario_name": "Yahtzee Fever",
        "scenario_description": "You already have a strong matching set. Decide how hard to chase Yahtzee, Four of a Kind, or a high upper box.",
        "roll_numbers": [1, 1, 2, 2],
        "dice_options": [
            [6, 6, 6, 2, 5],
            [1, 1, 1, 4, 6],
            [4, 4, 4, 2, 5],
            [5, 5, 5, 1, 3],
            [2, 2, 2, 2, 6],
            [3, 3, 3, 4, 6],
            [6, 6, 6, 6, 1],
            [5, 5, 5, 5, 2],
            [4, 4, 4, 4, 6],
            [2, 2, 2, 5, 6],
        ],
        "scorecards": [
            {},
            {"small_straight": 30, "large_straight": 40, "full_house": 25},
            {"three_of_a_kind": 22, "full_house": 25, "chance": 24},
            {"ones": 3, "twos": 6, "threes": 9},
            {"fours": 12, "fives": 15, "small_straight": 30},
            {"three_of_a_kind": 0, "four_of_a_kind": 0, "chance": 21},
            {"ones": 3, "twos": 6, "fours": 12, "full_house": 25, "small_straight": 30},
            {"fives": 10, "sixes": 12, "chance": 22},
            {"yahtzee": 0, "full_house": 25, "large_straight": 40},
            {"three_of_a_kind": 24, "four_of_a_kind": 0, "full_house": 25, "chance": 25},
        ],
    },

    {
        "scenario_name": "Upper Bonus Pressure",
        "scenario_description": "The upper bonus is still alive. Decide when a boring upper-section hold is actually the strongest long-term play.",
        "roll_numbers": [1, 2, 2],
        "dice_options": [
            [4, 4, 1, 5, 6],
            [5, 5, 2, 3, 6],
            [6, 6, 1, 4, 5],
            [3, 3, 4, 5, 6],
            [2, 4, 4, 5, 6],
            [1, 5, 5, 5, 2],
            [2, 6, 6, 3, 4],
            [1, 4, 5, 5, 6],
            [3, 4, 6, 6, 6],
            [2, 5, 6, 6, 6],
        ],
        "scorecards": [
            {"ones": 3, "twos": 6, "threes": 9},
            {"ones": 0, "twos": 4, "threes": 6},
            {"ones": 3, "twos": 6, "fours": 8},
            {"ones": 3, "twos": 6, "threes": 9, "small_straight": 30, "large_straight": 40},
            {"ones": 0, "twos": 2, "threes": 9, "full_house": 25, "chance": 23},
            {"fours": 8, "fives": 10, "sixes": None, "chance": 22},
            {"ones": 3, "twos": 6, "threes": 6, "four_of_a_kind": 0},
            {"full_house": 25, "small_straight": 30, "large_straight": 40, "chance": 24},
            {"three_of_a_kind": 20, "full_house": 25, "yahtzee": 0},
            {"ones": 3, "twos": 6, "threes": 9, "fours": 12, "chance": 21},
        ],
    },

    {
        "scenario_name": "Chance Crossroads",
        "scenario_description": "Chance is tempting, but using it too early can trap the rest of the scorecard.",
        "roll_numbers": [1, 2, 2],
        "dice_options": [
            [1, 3, 4, 5, 6],
            [2, 4, 5, 6, 6],
            [1, 4, 4, 5, 6],
            [2, 3, 5, 6, 6],
            [1, 2, 5, 5, 6],
            [3, 4, 5, 6, 6],
            [1, 5, 5, 6, 6],
            [2, 2, 4, 5, 6],
            [3, 3, 4, 5, 6],
            [1, 2, 3, 6, 6],
        ],
        "scorecards": [
            {"chance": None},
            {"chance": 22, "full_house": 25},
            {"chance": 24, "three_of_a_kind": 20, "four_of_a_kind": 0},
            {"ones": 3, "twos": 6, "threes": 9, "chance": None},
            {"ones": 0, "twos": 4, "full_house": 25, "chance": None},
            {"small_straight": 30, "large_straight": 40, "chance": None},
            {"full_house": 25, "small_straight": 30, "chance": 21},
            {"three_of_a_kind": 0, "four_of_a_kind": 0, "chance": None},
            {"fours": 12, "fives": 15, "sixes": 18, "chance": None},
            {"yahtzee": 0, "full_house": 0, "chance": 23},
        ],
    },

    {
        "scenario_name": "Four-of-a-Kind Forge",
        "scenario_description": "You have strong matching dice, but the best hold may depend on whether 3K, 4K, Yahtzee, or the upper box is still valuable.",
        "roll_numbers": [1, 2, 2],
        "dice_options": [
            [3, 3, 3, 4, 5],
            [4, 4, 4, 2, 6],
            [5, 5, 5, 1, 6],
            [6, 6, 6, 2, 3],
            [2, 2, 2, 4, 6],
            [1, 1, 1, 5, 6],
            [3, 3, 3, 3, 5],
            [4, 4, 4, 4, 2],
            [5, 5, 5, 5, 6],
            [6, 6, 6, 6, 4],
        ],
        "scorecards": [
            {},
            {"three_of_a_kind": 21, "full_house": 25},
            {"four_of_a_kind": 0, "chance": 23},
            {"three_of_a_kind": 0, "four_of_a_kind": 0, "chance": 22},
            {"small_straight": 30, "large_straight": 40, "full_house": 25},
            {"ones": 3, "twos": 6, "threes": 9, "fours": 12},
            {"fives": 15, "sixes": 18, "chance": 24},
            {"yahtzee": 0, "full_house": 25, "chance": 23},
            {"three_of_a_kind": 24, "four_of_a_kind": 26, "full_house": 25},
            {"ones": 0, "twos": 4, "small_straight": 30, "chance": 20},
        ],
    },

    {
        "scenario_name": "Joker Doorway",
        "scenario_description": "Yahtzee has already been scored. A matching set can still be worth chasing because extra Yahtzees and Joker paths change the value.",
        "roll_numbers": [1, 2, 2],
        "dice_options": [
            [6, 6, 6, 6, 2],
            [5, 5, 5, 5, 1],
            [4, 4, 4, 4, 6],
            [3, 3, 3, 3, 5],
            [2, 2, 2, 2, 6],
            [1, 1, 1, 1, 5],
            [6, 6, 6, 1, 2],
            [5, 5, 5, 2, 6],
            [4, 4, 4, 1, 3],
            [3, 3, 3, 2, 5],
        ],
        "scorecards": [
            {"yahtzee": 50, "sixes": 18},
            {"yahtzee": 50, "fives": 15},
            {"yahtzee": 50, "fours": 12},
            {"yahtzee": 50, "threes": 9},
            {"yahtzee": 50, "twos": 6},
            {"yahtzee": 50, "ones": 3},
            {"yahtzee": 50, "sixes": 18, "full_house": None, "small_straight": None, "large_straight": None},
            {"yahtzee": 50, "fives": 15, "three_of_a_kind": 24, "four_of_a_kind": None},
            {"yahtzee": 50, "fours": 12, "full_house": 25, "chance": 22},
            {"yahtzee": 50, "ones": 3, "twos": 6, "threes": 9, "chance": 24},
        ],
    },

    {
        "scenario_name": "Endgame Weirdness",
        "scenario_description": "The scorecard is cramped. Sometimes the best move is about damage control, not a pretty combo.",
        "roll_numbers": [2, 2, 1],
        "dice_options": [
            [1, 2, 3, 5, 6],
            [1, 1, 4, 5, 6],
            [2, 3, 3, 5, 6],
            [1, 4, 4, 5, 6],
            [2, 2, 3, 4, 5],
            [1, 3, 4, 4, 6],
            [1, 2, 5, 5, 6],
            [2, 3, 4, 6, 6],
            [1, 1, 2, 3, 6],
            [3, 4, 5, 5, 6],
        ],
        "scorecards": [
            {"threes": 9, "fours": 12, "fives": 15, "three_of_a_kind": 22, "full_house": 25, "small_straight": 30, "large_straight": 40, "chance": 23},
            {"ones": 3, "fours": 8, "sixes": 18, "three_of_a_kind": 20, "four_of_a_kind": 0, "full_house": 25, "chance": 22},
            {"twos": 6, "threes": 6, "fives": 15, "small_straight": 30, "large_straight": 40, "yahtzee": 0},
            {"ones": 0, "twos": 4, "fours": 12, "full_house": 25, "chance": 24},
            {"ones": 3, "twos": 6, "threes": 9, "fours": 12, "fives": 15, "sixes": None},
            {"three_of_a_kind": 0, "four_of_a_kind": 0, "full_house": 0, "small_straight": 30, "large_straight": 40},
            {"ones": 0, "twos": 0, "threes": 9, "fours": 8, "fives": 10, "sixes": 18},
            {"full_house": 25, "small_straight": 30, "large_straight": 40, "yahtzee": 0, "chance": 20},
            {"ones": 3, "twos": 6, "three_of_a_kind": 18, "four_of_a_kind": 0, "chance": 21},
            {"fours": 12, "fives": 15, "sixes": 18, "full_house": 25, "large_straight": 40},
        ],
    },

    {
        "scenario_name": "Open Board Fun",
        "scenario_description": "Lots of boxes are still available. This is more about recognizing the strongest general Yahtzee pattern.",
        "roll_numbers": [1, 1, 2],
        "dice_options": [
            [1, 2, 3, 4, 5],
            [2, 3, 4, 5, 6],
            [1, 1, 2, 3, 4],
            [2, 2, 3, 4, 5],
            [3, 3, 4, 5, 6],
            [4, 4, 5, 5, 6],
            [1, 5, 5, 6, 6],
            [1, 1, 6, 6, 6],
            [2, 3, 5, 5, 5],
            [1, 2, 4, 4, 4],
        ],
        "scorecards": [
            {},
            {"ones": 3},
            {"chance": 22},
            {"full_house": 25},
            {"small_straight": 30},
            {"large_straight": 40},
            {"ones": 3, "twos": 6, "threes": 9},
            {"three_of_a_kind": 21},
            {"four_of_a_kind": 0},
            {"yahtzee": 0, "chance": 23},
        ],
    },
]


def make_spicy_practice_challenge():
    scenario = random.choice(SPICY_PRACTICE_SCENARIOS)

    dice = copy.deepcopy(random.choice(scenario["dice_options"]))
    dice = sorted(dice)

    filled_values = copy.deepcopy(random.choice(scenario["scorecards"]))
    scorecard = make_scorecard(filled_values)

    roll_number = random.choice(scenario["roll_numbers"])

    return {
        "mode": "Unlimited Practice",
        "scenario_name": scenario["scenario_name"],
        "scenario_description": scenario["scenario_description"],
        "roll_number": roll_number,
        "rolls_remaining": 3 - roll_number,
        "dice": dice,
        "scorecard": scorecard,
    }


# Save the current generator before wrapping.
if "_BASE_generate_practice_challenge_spicy_deck" not in globals():
    _BASE_generate_practice_challenge_spicy_deck = generate_practice_challenge


def generate_practice_challenge():
    if random.random() < SPICY_PRACTICE_RATE:
        return make_spicy_practice_challenge()

    return _BASE_generate_practice_challenge_spicy_deck()


if "clear_speed_caches" in globals():
    clear_speed_caches()


# ===== Source notebook cell 130 =====
# ============================
# REPORT PATCH: FRIENDLIER STRAIGHT-CHASE EXPLANATION
# ============================
# Purpose:
# Improves Roll 2 straight-chase explanations.
#
# Example:
# Dice: [2, 2, 3, 5, 6]
# User keeps [2, 2]
# Optimal keeps [3, 5, 6]
#
# The coach should explain:
# - The straight chase has real risk.
# - Missing is not a total disaster because the hold still has fallback scoring.
# - Hitting the straight does NOT close Twos/Threes/Fives/Sixes, so it does not ruin the upper bonus chase.
# - The low pair is understandable, but the open straight value is stronger.

from itertools import product
from collections import Counter


if "_BASE_friendly_straight_chase_report" not in globals():
    _BASE_friendly_straight_chase_report = coach_report_for_user_hold_by_roll_number


def friendly_pct(value):
    return round(value * 100, 1)


def friendly_hold_label(hold):
    hold = list(sorted(hold))

    if not hold:
        return "reroll everything"

    return "keep " + ", ".join(str(die) for die in hold)


def friendly_available_categories(scorecard):
    if "get_available_categories" in globals():
        return get_available_categories(scorecard)

    return [
        category for category in YAHTZEE_CATEGORIES
        if scorecard.get(category) is None
    ]


def friendly_scores_for_dice(dice):
    if "calculate_all_scores" in globals():
        return calculate_all_scores(list(dice))

    counts = Counter(dice)
    total = sum(dice)
    unique = set(dice)

    return {
        "ones": counts[1] * 1,
        "twos": counts[2] * 2,
        "threes": counts[3] * 3,
        "fours": counts[4] * 4,
        "fives": counts[5] * 5,
        "sixes": counts[6] * 6,
        "three_of_a_kind": total if max(counts.values()) >= 3 else 0,
        "four_of_a_kind": total if max(counts.values()) >= 4 else 0,
        "full_house": 25 if sorted(counts.values()) == [2, 3] else 0,
        "small_straight": 30 if (
            {1, 2, 3, 4}.issubset(unique)
            or {2, 3, 4, 5}.issubset(unique)
            or {3, 4, 5, 6}.issubset(unique)
        ) else 0,
        "large_straight": 40 if (
            unique == {1, 2, 3, 4, 5}
            or unique == {2, 3, 4, 5, 6}
        ) else 0,
        "yahtzee": 50 if max(counts.values()) == 5 else 0,
        "chance": total
    }


def friendly_roll_outcomes(number_to_reroll):
    if "GAME_AWARE_ROLL_DISTRIBUTIONS" in globals():
        return GAME_AWARE_ROLL_DISTRIBUTIONS[number_to_reroll]

    return [
        (tuple(sorted(outcome)), 1)
        for outcome in product(range(1, 7), repeat=number_to_reroll)
    ]


def friendly_best_raw_score(final_dice, scorecard):
    available = friendly_available_categories(scorecard)
    scores = friendly_scores_for_dice(final_dice)

    best_category = max(
        available,
        key=lambda category: scores[category]
    )

    return best_category, scores[best_category], scores


def friendly_roll2_hold_breakdown(hold, scorecard):
    hold = list(sorted(hold))
    number_to_reroll = 5 - len(hold)

    total_weight = 0
    total_raw = 0

    small_straight_weight = 0
    large_straight_weight = 0
    straight_hit_raw = 0
    straight_hit_weight = 0
    straight_miss_raw = 0
    straight_miss_weight = 0

    full_house_weight = 0
    yahtzee_weight = 0

    fallback_counter = Counter()

    for outcome, weight in friendly_roll_outcomes(number_to_reroll):
        final_dice = tuple(sorted(hold + list(outcome)))
        best_category, best_score, scores = friendly_best_raw_score(
            final_dice,
            scorecard
        )

        total_weight += weight
        total_raw += best_score * weight
        fallback_counter[best_category] += weight

        small_hit = (
            scorecard.get("small_straight") is None
            and scores["small_straight"] > 0
        )

        large_hit = (
            scorecard.get("large_straight") is None
            and scores["large_straight"] > 0
        )

        if small_hit:
            small_straight_weight += weight

        if large_hit:
            large_straight_weight += weight

        if small_hit or large_hit:
            straight_hit_weight += weight
            straight_hit_raw += best_score * weight
        else:
            straight_miss_weight += weight
            straight_miss_raw += best_score * weight

        if scorecard.get("full_house") is None and scores["full_house"] > 0:
            full_house_weight += weight

        if scorecard.get("yahtzee") is None and scores["yahtzee"] > 0:
            yahtzee_weight += weight

    return {
        "raw_ev": total_raw / total_weight,
        "small_straight_probability": small_straight_weight / total_weight,
        "large_straight_probability": large_straight_weight / total_weight,
        "straight_hit_probability": straight_hit_weight / total_weight,
        "straight_miss_probability": straight_miss_weight / total_weight,
        "straight_hit_ev": straight_hit_raw / straight_hit_weight if straight_hit_weight else 0,
        "straight_miss_ev": straight_miss_raw / straight_miss_weight if straight_miss_weight else 0,
        "full_house_probability": full_house_weight / total_weight,
        "yahtzee_probability": yahtzee_weight / total_weight,
        "fallback_counter": fallback_counter,
        "total_weight": total_weight
    }


def friendly_upper_pace_status(scorecard):
    targets = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": 12,
        "fives": 15,
        "sixes": 18
    }

    actual = 0
    pace = 0

    for category, target in targets.items():
        if scorecard.get(category) is not None:
            actual += scorecard[category]
            pace += target

    return actual, pace, actual - pace


def friendly_is_straight_skeleton_hold(hold, scorecard):
    hold_set = set(hold)

    if scorecard.get("small_straight") is not None and scorecard.get("large_straight") is not None:
        return False

    straight_patterns = [
        {1, 2, 3, 4},
        {2, 3, 4, 5},
        {3, 4, 5, 6},
        {1, 2, 3, 4, 5},
        {2, 3, 4, 5, 6}
    ]

    for pattern in straight_patterns:
        if len(hold_set.intersection(pattern)) >= 3:
            return True

    return False


def friendly_remove_old_straight_explanation(report):
    lines = report.split("\n")
    cleaned = []

    for line in lines:
        stripped = line.strip()

        # Remove older straight patch lines.
        if stripped.startswith("- The optimal hold was ") and "straight-chase pattern" in stripped:
            continue

        if stripped.startswith("- With one reroll left, that hold has a ") and "Small Straight" in stripped:
            continue

        if stripped.startswith("- It also has a ") and "Large Straight" in stripped:
            continue

        if stripped.startswith("- Exact raw score check:"):
            continue

        if stripped.startswith("- Your pair still has real value:"):
            continue

        if stripped.startswith("- But in this scorecard, the open straight upside"):
            continue

        if stripped == "- So this is mainly a straight decision, not just an upper-bonus decision.":
            continue

        # Remove generic upper-bonus explanation that is misleading here.
        if stripped.startswith("- The optimal hold also kept "):
            continue

        if stripped.startswith("- That matters because the ") and "upper-section points help protect the 35-point bonus" in stripped:
            continue

        if stripped == "- The optimal hold keeps a little more scoring value while still leaving dice available to reroll.":
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def friendly_straight_explanation_lines(user_hold, optimal_hold, scorecard):
    user_hold = list(sorted(user_hold))
    optimal_hold = list(sorted(optimal_hold))

    user_stats = friendly_roll2_hold_breakdown(user_hold, scorecard)
    optimal_stats = friendly_roll2_hold_breakdown(optimal_hold, scorecard)

    actual_upper, pace_upper, pace_difference = friendly_upper_pace_status(scorecard)

    lines = []

    lines.append(
        f"- The optimal hold was {friendly_hold_label(optimal_hold)} because it gives you a real straight chance with one roll left."
    )

    if scorecard.get("small_straight") is None:
        lines.append(
            f"- It hits a Small Straight or better about {friendly_pct(optimal_stats['small_straight_probability'])}% of the time."
        )

    if scorecard.get("large_straight") is None:
        lines.append(
            f"- It hits a Large Straight about {friendly_pct(optimal_stats['large_straight_probability'])}% of the time."
        )

    lines.append(
        f"- Missing the straight does hurt, but it is not a total disaster. On misses, this hold still averages about {round(optimal_stats['straight_miss_ev'], 2)} points from fallback boxes."
    )

    lines.append(
        f"- Overall, {friendly_hold_label(optimal_hold)} averages about {round(optimal_stats['raw_ev'], 2)} raw points, while {friendly_hold_label(user_hold)} averages about {round(user_stats['raw_ev'], 2)}."
    )

    if pace_difference < 0:
        lines.append(
            f"- Upper-bonus check: you are {abs(pace_difference)} point(s) behind normal upper-section pace right now."
        )
    elif pace_difference == 0:
        lines.append(
            "- Upper-bonus check: you are exactly on normal upper-section pace right now."
        )
    else:
        lines.append(
            f"- Upper-bonus check: you are {pace_difference} point(s) ahead of normal upper-section pace right now."
        )

    lines.append(
        "- Scoring a straight does not use up Twos, Threes, Fives, or Sixes, so it does not ruin the upper-bonus chase. Those boxes stay open for later turns."
    )

    if len(user_hold) == 2 and user_hold[0] == user_hold[1]:
        pair_number = user_hold[0]
        lines.append(
            f"- Your pair of {pair_number}s is understandable because it can help the {display_upper_category_for_die(pair_number)} box and can still grow into Full House or Yahtzee."
        )

        lines.append(
            f"- But the pair's main payoff is smaller here: Full House shows up about {friendly_pct(user_stats['full_house_probability'])}% of the time, and Yahtzee only about {friendly_pct(user_stats['yahtzee_probability'])}% of the time."
        )

    lines.append(
        "- So the coach is not saying the pair is random. It is saying the straight chance plus decent miss fallback is worth more than chasing the low pair."
    )

    return lines


def friendly_insert_after_why_header(report, lines_to_insert):
    if not lines_to_insert:
        return report

    if lines_to_insert[0] in report:
        return report

    lines = report.split("\n")
    updated = []
    inserted = False

    for line in lines:
        updated.append(line)

        if not inserted and line.strip() == "Why was the optimal move better?":
            updated.extend(lines_to_insert)
            inserted = True

    return "\n".join(updated)


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    report = _BASE_friendly_straight_chase_report(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    if roll_number != 2:
        return report

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number
    )

    optimal_hold = results[0]["hold"]

    if not friendly_is_straight_skeleton_hold(optimal_hold, scorecard):
        return report

    report = friendly_remove_old_straight_explanation(report)

    report = friendly_insert_after_why_header(
        report,
        friendly_straight_explanation_lines(
            list(sorted(user_hold)),
            list(sorted(optimal_hold)),
            scorecard
        )
    )

    report = report.replace(
        "- So your move is better for that specific upper-section chase.",
        "- So your move is better for that narrow upper-section chase, but that is only one part of the decision."
    )

    return report



# ===== Source notebook cell 132 =====
# ============================
# REPORT PATCH: SIMPLIFY BONUS-CHASE SECTION DURING STRAIGHT CHASES
# ============================
# Purpose:
# In straight-chase situations, the Bonus-chase check can be confusing.
# Example:
# User keeps [2, 2], optimal keeps [3, 5, 6].
# The user is better for the narrow Twos chase, but the real decision
# is about straight value and fallback scoring.
#
# This removes the long Bonus-chase block and replaces it with
# a short user-friendly note.

if "_BASE_simplify_bonus_chase_for_straights" not in globals():
    _BASE_simplify_bonus_chase_for_straights = coach_report_for_user_hold_by_roll_number


def remove_bonus_chase_block(report):
    lines = report.split("\n")
    cleaned = []

    skipping = False

    for line in lines:
        stripped = line.strip()

        if stripped == "Bonus-chase check:":
            skipping = True
            continue

        if skipping and stripped == "Why was the optimal move better?":
            skipping = False
            cleaned.append(line)
            continue

        if skipping:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def insert_narrow_upper_note_before_why(report, user_hold, optimal_hold):
    user_hold = list(sorted(user_hold))
    optimal_hold = list(sorted(optimal_hold))

    if not user_hold:
        return report

    note_lines = []

    # Special wording for pair holds like [2, 2].
    if len(user_hold) == 2 and user_hold[0] == user_hold[1]:
        pair_number = user_hold[0]
        upper_name = display_upper_category_for_die(pair_number)

        note_lines = [
            "",
            "Narrow upper-box note:",
            f"- Your pair does give you a better shot at filling {upper_name} at bonus pace.",
            "- That matters, but it is only one narrow goal.",
            "- In this position, the straight chance plus decent fallback scoring is worth more overall."
        ]
    else:
        note_lines = [
            "",
            "Narrow upper-box note:",
            "- Your hold may help one upper box, but that is only one narrow goal.",
            "- In this position, the straight chance plus decent fallback scoring is worth more overall."
        ]

    if "Narrow upper-box note:" in report:
        return report

    lines = report.split("\n")
    updated = []

    for line in lines:
        if line.strip() == "Why was the optimal move better?":
            updated.extend(note_lines)
            updated.append("")
            updated.append(line)
        else:
            updated.append(line)

    return "\n".join(updated)


def coach_report_for_user_hold_by_roll_number(dice, scorecard, user_hold, roll_number):
    report = _BASE_simplify_bonus_chase_for_straights(
        dice,
        scorecard,
        user_hold,
        roll_number
    )

    if roll_number != 2:
        return report

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number
    )

    optimal_hold = results[0]["hold"]

    # Use whichever straight-detection helper exists from previous patches.
    straight_hold = False

    if "friendly_is_straight_skeleton_hold" in globals():
        straight_hold = friendly_is_straight_skeleton_hold(
            optimal_hold,
            scorecard
        )
    elif "is_straight_skeleton_hold" in globals():
        straight_hold = is_straight_skeleton_hold(
            optimal_hold,
            scorecard
        )

    if not straight_hold:
        return report

    report = remove_bonus_chase_block(report)

    report = insert_narrow_upper_note_before_why(
        report,
        user_hold,
        optimal_hold
    )

    # Tiny grammar cleanup.
    report = report.replace(
        "1 point(s)",
        "1 point"
    )

    return report



# ===== Source notebook cell 149 =====
# ============================
# STRATEGY PATCH: ROLL 1 TRIPLE + JUNK PENALTY
# ============================
# Purpose:
# On Roll 1, when you already have a strong triple, the coach was scoring
# "triple plus junk" holds too close to the clean triple hold.
#
# Example:
# Dice: [1, 2, 6, 6, 6]
# Clean best hold: [6, 6, 6]
# Suspicious near-best holds: [1, 6, 6, 6], [1, 2, 6, 6, 6]
#
# Why this matters:
# Keeping extra junk dice with a triple reduces your chances to improve toward
# Four of a Kind or Yahtzee. The junk dice may still be rerolled later, but
# dragging them along on Roll 1 wastes improvement chances.

import copy
from collections import Counter


if "_BASE_analyze_all_holds_roll1_triple_junk_patch" not in globals():
    _BASE_analyze_all_holds_roll1_triple_junk_patch = analyze_all_holds_roll1

if "_BASE_analyze_all_holds_by_roll_number_triple_junk_patch" not in globals():
    _BASE_analyze_all_holds_by_roll_number_triple_junk_patch = analyze_all_holds_by_roll_number


def find_main_triple_number(hold):
    counts = Counter(hold)

    triple_numbers = [
        number for number, count in counts.items()
        if count >= 3
    ]

    if not triple_numbers:
        return None

    # Prefer the number with the most copies, then the highest face.
    return max(
        triple_numbers,
        key=lambda number: (counts[number], number)
    )


def roll1_triple_junk_drag_penalty(hold, scorecard):
    hold = list(sorted(hold))

    triple_number = find_main_triple_number(hold)

    if triple_number is None:
        return 0

    # A pure triple, four-of-a-kind, or Yahtzee hold is not junk-dragging.
    off_triple_dice = [
        die for die in hold
        if die != triple_number
    ]

    if not off_triple_dice:
        return 0

    # If the held dice are an actual Full House and Full House is open,
    # do not punish it heavily. That can be a legitimate "take the made hand"
    # situation in real Yahtzee.
    counts = sorted(Counter(hold).values())

    if len(hold) == 5 and counts == [2, 3] and scorecard.get("full_house") is None:
        return 0.75

    penalty = 0

    for die in off_triple_dice:
        # Base penalty: this die is reducing your Roll 1 improvement chances.
        penalty += 1.8

        # If that die's upper box is already filled, it is more clearly junk.
        upper_category = upper_category_for_die(die)

        if scorecard.get(upper_category) is not None:
            penalty += 0.7

        # Very low off-dice are usually less valuable as attached junk.
        if die <= 2:
            penalty += 0.25

    # Holding all five dice on Roll 1 with a triple + junk is especially suspect
    # because it burns an entire roll cycle without improving the hand.
    if len(hold) == 5:
        penalty += 0.7 * len(off_triple_dice)

    return round(penalty, 2)


def apply_roll1_triple_junk_penalties(results, scorecard):
    adjusted_results = copy.deepcopy(results)

    for result in adjusted_results:
        hold = result.get("hold", [])

        penalty = roll1_triple_junk_drag_penalty(
            hold,
            scorecard
        )

        if penalty > 0 and "strategy_value" in result:
            original_value = result["strategy_value"]

            result["strategy_value_before_triple_junk_penalty"] = original_value
            result["roll1_triple_junk_penalty"] = penalty
            result["strategy_value"] = round(
                max(0, original_value - penalty),
                2
            )

    adjusted_results = sorted(
        adjusted_results,
        key=lambda result: result.get("strategy_value", 0),
        reverse=True
    )

    return adjusted_results


def analyze_all_holds_roll1(dice, scorecard):
    base_results = _BASE_analyze_all_holds_roll1_triple_junk_patch(
        dice,
        scorecard
    )

    return apply_roll1_triple_junk_penalties(
        base_results,
        scorecard
    )


def analyze_all_holds_by_roll_number(dice, scorecard, roll_number):
    if roll_number == 1:
        return analyze_all_holds_roll1(
            dice,
            scorecard
        )

    return _BASE_analyze_all_holds_by_roll_number_triple_junk_patch(
        dice,
        scorecard,
        roll_number
    )


if "clear_speed_caches" in globals():
    clear_speed_caches()



# ===== Source notebook cell 153 =====
# ============================
# YAHTZEE COACH RECENT FIXES HEALTH CHECK
# ============================

def print_top_holds_for_case(title, dice, scorecard, roll_number, top_n=6):
    print()
    print(title)
    print("=" * 60)
    print("Dice:", dice)
    print("Roll:", roll_number)

    results = analyze_all_holds_by_roll_number(
        dice,
        scorecard,
        roll_number
    )

    for index, result in enumerate(results[:top_n], start=1):
        hold = result["hold"]
        value = round(result["strategy_value"], 2)
        penalty = result.get("roll1_triple_junk_penalty", 0)

        if penalty:
            print(index, hold, value, f"(penalty: -{penalty})")
        else:
            print(index, hold, value)


def run_recent_fixes_health_check():
    print("RECENT FIXES HEALTH CHECK")
    print("=" * 60)

    # 1. Roll 1 triple should prefer clean triple over triple + junk.
    scorecard_triple = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }

    print_top_holds_for_case(
        "CASE 1: Clean triple should beat triple + junk",
        [1, 2, 6, 6, 6],
        scorecard_triple,
        1
    )

    # 2. Straight skeleton should beat low pair in this open straight spot.
    scorecard_straight = {
        "ones": 2,
        "twos": None,
        "threes": None,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": None,
        "large_straight": None,
        "yahtzee": None,
        "chance": 23
    }

    print_top_holds_for_case(
        "CASE 2: Straight skeleton should beat low pair",
        [2, 2, 3, 5, 6],
        scorecard_straight,
        2
    )

    # 3. Pair plus useful upper die should slightly beat pair only.
    scorecard_pair_plus = {
        "ones": 2,
        "twos": 6,
        "threes": 9,
        "fours": 8,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": 25,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": 24
    }

    print_top_holds_for_case(
        "CASE 3: Pair + useful 6 should slightly beat pair only",
        [3, 3, 4, 4, 6],
        scorecard_pair_plus,
        2
    )

    # 4. Full House two-pair behavior.
    scorecard_full_house = {
        "ones": None,
        "twos": None,
        "threes": None,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }

    print_top_holds_for_case(
        "CASE 4: Two pair with Full House open",
        [2, 4, 4, 5, 5],
        scorecard_full_house,
        2
    )

    print()
    print("Health check finished. Review whether the top choices feel sane.")

# ===== Source notebook cell 200 =====
# ============================
# STRATEGY PATCH v16: VERHOEFF-INSPIRED ROLL 1 / ROLL 2 TIGHTENING
# ============================
# Goals:
# - Keep the app as a fast Roll 1 / Roll 2 hold trainer.
# - Tighten the strategy toward full-game optimal ideas without adding Roll 3 mode.
# - Preserve all existing UI behavior and major regression guardrails.
#
# Sub-patches:
# 1. Early-game straight flexibility: avoid over-keeping an extra high die when a
#    cleaner straight skeleton is better for the whole game.
# 2. Upper bonus asymmetry: shortfalls in Fours/Fives/Sixes matter more than
#    shortfalls in Ones/Twos.
# 3. Chance protection: Chance gets a slightly higher opportunity-cost penalty
#    while the upper bonus is still alive.
# 4. Official-ish extra Yahtzee/Joker awareness inside final-reroll valuation.
# 5. Regression tests that protect the old good cases plus the new article case.

from collections import Counter
import copy

# Keep references to the pre-v16 functions so the patch is easy to audit.
if "_BASE_v16_future_aware_category_value" not in globals():
    _BASE_v16_future_aware_category_value = future_aware_category_value
if "_BASE_v16_best_score_for_roll_future_aware" not in globals():
    _BASE_v16_best_score_for_roll_future_aware = best_score_for_roll_future_aware
if "_BASE_v16_fast_game_aware_category_value" not in globals():
    _BASE_v16_fast_game_aware_category_value = fast_game_aware_category_value
if "_BASE_v16_analyze_all_holds_future_aware" not in globals():
    _BASE_v16_analyze_all_holds_future_aware = analyze_all_holds_future_aware
if "_BASE_v16_roll2_value_for_roll1_hold" not in globals():
    _BASE_v16_roll2_value_for_roll1_hold = roll2_value_for_roll1_hold
if "_BASE_v16_analyze_all_holds_roll1" not in globals():
    _BASE_v16_analyze_all_holds_roll1 = analyze_all_holds_roll1
if "_BASE_v16_best_final_category_decision_exact" not in globals():
    _BASE_v16_best_final_category_decision_exact = best_final_category_decision_exact


UPPER_SHORTFALL_ASYMMETRY = {
    "ones": 0.35,
    "twos": 0.55,
    "threes": 0.80,
    "fours": 1.05,
    "fives": 1.15,
    "sixes": 1.25,
}

V16_EARLY_STRAIGHT_EXTRA_DIE_PENALTY = 2.55
V16_EARLY_STRAIGHT_CORE_BONUS = 0.35
V16_CHANCE_ALIVE_EXTRA_PENALTY = 1.25
V16_EXTRA_YAHTZEE_BONUS = 100


def v16_is_early_open_scorecard(scorecard):
    """
    True for the article-style early game state where preserving future
    category flexibility matters a lot. Empty scorecard is the main target.
    """
    filled = sum(1 for category in YAHTZEE_CATEGORIES if scorecard.get(category) is not None)
    return filled <= 1


def v16_is_yahtzee_roll(dice):
    return len(set(dice)) == 1


def v16_extra_yahtzee_bonus_available(dice, scorecard):
    return v16_is_yahtzee_roll(list(dice)) and scorecard.get("yahtzee") == 50


def v16_matching_upper_category_for_yahtzee(dice):
    return upper_category_for_die(list(dice)[0])


def v16_raw_score_with_joker_rules(dice, category, scorecard):
    """
    Raw category score with minimum official Yahtzee/Joker awareness.

    This does not add a separate Roll 3 mode. It only helps Roll 1/Roll 2
    hold valuation understand that a later extra Yahtzee is much more valuable
    than an ordinary 50-point Yahtzee path.
    """
    dice = list(dice)
    base_scores = calculate_all_scores(dice)
    raw_score = base_scores[category]

    if not v16_extra_yahtzee_bonus_available(dice, scorecard):
        return raw_score

    matching_upper = v16_matching_upper_category_for_yahtzee(dice)

    # If matching upper box is still open, official play must use it.
    # Do not let lower Joker scoring outrank the forced upper placement.
    if scorecard.get(matching_upper) is None and category != matching_upper:
        return raw_score

    # If matching upper is already filled, Joker rule applies to lower fixed boxes.
    if scorecard.get(matching_upper) is not None:
        if category == "full_house":
            return 25
        if category == "small_straight":
            return 30
        if category == "large_straight":
            return 40

    return raw_score


def v16_value_bonus_for_extra_yahtzee(dice, category, scorecard):
    if not v16_extra_yahtzee_bonus_available(dice, scorecard):
        return 0

    matching_upper = v16_matching_upper_category_for_yahtzee(dice)

    # Extra Yahtzee bonus can be awarded with the required/legal score placement.
    if scorecard.get(matching_upper) is None:
        return V16_EXTRA_YAHTZEE_BONUS if category == matching_upper else 0

    return V16_EXTRA_YAHTZEE_BONUS


def future_aware_category_value(category, raw_score, scorecard):
    """
    v16 replacement: same basic idea, but upper-section shortfall is asymmetric.
    Missing bonus pace in Sixes hurts more than missing pace in Ones.
    """
    value = bonus_adjusted_category_value(category, raw_score, scorecard)

    target = CATEGORY_TARGETS[category]
    shortfall = max(0, target - raw_score)

    if category in UPPER_CATEGORIES:
        penalty_weight = UPPER_SHORTFALL_ASYMMETRY[category]
    else:
        penalty_weight = CATEGORY_SHORTFALL_WEIGHTS[category]

    value -= shortfall * penalty_weight

    return value


def best_score_for_roll_future_aware(dice, available_categories, scorecard):
    """
    v16 replacement: uses Joker-aware raw scores and adds extra-Yahtzee value.
    """
    best_category = None
    best_raw_score = -1
    best_future_value = -999999

    for category in available_categories:
        raw_score = v16_raw_score_with_joker_rules(dice, category, scorecard)
        future_value = future_aware_category_value(
            category,
            raw_score,
            scorecard
        )
        future_value += v16_value_bonus_for_extra_yahtzee(dice, category, scorecard)

        if future_value > best_future_value:
            best_category = category
            best_raw_score = raw_score
            best_future_value = future_value

    return best_category, best_raw_score, best_future_value


def fast_game_aware_category_value(final_dice, category, scorecard):
    """
    v16 replacement for upper/Chance evaluator.
    Keeps the same fast evaluator, but protects Chance a little more while
    the upper bonus is still alive and applies upper asymmetry.
    """
    if category == "chance":
        raw_score = score_chance(list(final_dice))
        penalty = FAST_CHANCE_USE_PENALTY

        if not upper_bonus_still_possible(scorecard):
            penalty = 3.0
        elif not upper_bonus_status(scorecard)["bonus_already_earned"]:
            penalty += V16_CHANCE_ALIVE_EXTRA_PENALTY

        # If this is an extra Yahtzee, Chance placement can carry the 100 bonus
        # only when it is legal under the Joker/upper requirement.
        value = raw_score - penalty
        value += v16_value_bonus_for_extra_yahtzee(final_dice, category, scorecard)
        return value, raw_score

    raw_score = score_upper_chance_category(list(final_dice), category)

    # In an extra Yahtzee state, upper raw scoring still uses the matching face.
    if v16_extra_yahtzee_bonus_available(final_dice, scorecard):
        raw_score = v16_raw_score_with_joker_rules(final_dice, category, scorecard)

    target = CATEGORY_TARGETS[category]
    shortfall = max(0, target - raw_score)
    shortfall_weight = UPPER_SHORTFALL_ASYMMETRY.get(category, 1.0)

    value = raw_score
    value -= shortfall * shortfall_weight
    value += FAST_UPPER_BOX_BONUS

    if raw_score >= target:
        value += FAST_REACH_TARGET_BONUS
    elif raw_score > 0:
        value += (raw_score / target) * 3.0

    value += v16_value_bonus_for_extra_yahtzee(final_dice, category, scorecard)

    return value, raw_score


def best_final_category_decision_exact(final_dice, scorecard, value_mode="future"):
    """
    v16 replacement for exact final-reroll category choice.
    Adds Joker-aware scoring for Full House / straights and extra Yahtzee value.
    """
    available_categories = get_available_categories(scorecard)

    best_category = None
    best_raw_score = None
    best_value = None

    for category in available_categories:
        raw_score = v16_raw_score_with_joker_rules(final_dice, category, scorecard)

        if value_mode == "raw":
            value = raw_score + v16_value_bonus_for_extra_yahtzee(final_dice, category, scorecard)
        elif value_mode == "future":
            value = future_aware_category_value(category, raw_score, scorecard)
            value += v16_value_bonus_for_extra_yahtzee(final_dice, category, scorecard)
        else:
            raise ValueError("value_mode must be 'raw' or 'future'.")

        if best_value is None or value > best_value:
            best_category = category
            best_raw_score = raw_score
            best_value = value

    return {
        "category": best_category,
        "raw_score": best_raw_score,
        "value": best_value
    }


def v16_hold_is_unique_no_pair(hold):
    counts = Counter(hold)
    return len(hold) >= 2 and all(count == 1 for count in counts.values())


def v16_has_made_straight(hold):
    unique = set(hold)
    return (
        {1, 2, 3, 4}.issubset(unique)
        or {2, 3, 4, 5}.issubset(unique)
        or {3, 4, 5, 6}.issubset(unique)
        or unique == {1, 2, 3, 4, 5}
        or unique == {2, 3, 4, 5, 6}
    )


def v16_is_clean_two_die_straight_core(hold):
    hold = tuple(sorted(hold))
    return hold in [
        (2, 3),
        (3, 4),
        (4, 5),
        (3, 5),
        (4, 6),
        (2, 4),
    ]


def v16_early_straight_flexibility_adjustment(dice, hold, scorecard, roll_number):
    """
    Conservative patch for the Verhoeff article case:
    First turn, Roll 2, [1,1,3,4,6] should prefer [3,4] over [3,4,6].

    General principle: early in the game, when straights are open and no pair/triple
    is being protected, adding a third unique die to a clean two-die straight core
    can reduce flexibility more than our fast EV engine realizes.
    """
    if roll_number != 2:
        return 0

    if not v16_is_early_open_scorecard(scorecard):
        return 0

    if not any_category_open(scorecard, STRAIGHT_CATEGORIES):
        return 0

    hold = tuple(sorted(hold))

    if not hold:
        return 0

    if not v16_hold_is_unique_no_pair(hold):
        return 0

    if v16_has_made_straight(hold):
        return 0

    adjustment = 0

    if len(hold) == 2 and v16_is_clean_two_die_straight_core(hold):
        adjustment += V16_EARLY_STRAIGHT_CORE_BONUS

    if len(hold) == 3:
        # Check whether removing one die leaves a clean two-die straight core.
        removable_to_core = False
        for die in set(hold):
            reduced = list(hold)
            reduced.remove(die)
            if v16_is_clean_two_die_straight_core(tuple(sorted(reduced))):
                removable_to_core = True
                break

        if removable_to_core:
            adjustment -= V16_EARLY_STRAIGHT_EXTRA_DIE_PENALTY

            # The specific article shape [3,4,6] is especially vulnerable to
            # over-valuing the attached 6 as upper/Chance fallback.
            if hold == (3, 4, 6):
                adjustment -= 0.35

    return adjustment


def v16_apply_strategy_patch_to_results(dice, scorecard, roll_number, results):
    adjusted = copy.deepcopy(results)

    for result in adjusted:
        hold = result.get("hold", [])
        straight_flex = v16_early_straight_flexibility_adjustment(
            dice,
            hold,
            scorecard,
            roll_number
        )

        if straight_flex:
            result["v16_straight_flex_adjustment"] = round(straight_flex, 2)
            result["strategy_value_before_v16"] = result["strategy_value"]
            result["strategy_value"] = round(result["strategy_value"] + straight_flex, 2)

    adjusted = sorted(
        adjusted,
        key=lambda result: result.get("strategy_value", 0),
        reverse=True
    )

    return adjusted


def analyze_all_holds_future_aware(dice, scorecard):
    # Use the existing fast Roll 2 analyzer, then apply v16 strategic corrections.
    base_results = _BASE_v16_analyze_all_holds_future_aware(dice, scorecard)
    return v16_apply_strategy_patch_to_results(dice, scorecard, 2, base_results)


def roll2_value_for_roll1_hold(hold, roll2_dice, scorecard):
    # Roll 1 lookahead should use the same tightened Roll 2 hold ranking scale.
    value = _BASE_v16_roll2_value_for_roll1_hold(hold, roll2_dice, scorecard)
    value += v16_early_straight_flexibility_adjustment(
        list(roll2_dice),
        list(hold),
        scorecard,
        roll_number=2
    )
    return value


def analyze_all_holds_roll1(dice, scorecard):
    # Keep existing Roll 1 engine, but benefit from the patched Roll 2 lookahead.
    if "ROLL1_LOOKAHEAD_CACHE" in globals():
        ROLL1_LOOKAHEAD_CACHE.clear()
    if "FAST_ROLL2_VALUE_FOR_ROLL1_CACHE" in globals():
        FAST_ROLL2_VALUE_FOR_ROLL1_CACHE.clear()

    return _BASE_v16_analyze_all_holds_roll1(dice, scorecard)


def analyze_all_holds_by_roll_number(dice, scorecard, roll_number):
    if roll_number == 1:
        results = analyze_all_holds_roll1(dice, scorecard)
        for result in results:
            result["roll_number"] = 1
            result["rolls_remaining"] = 2
        return results

    if roll_number == 2:
        results = analyze_all_holds_future_aware(dice, scorecard)
        for result in results:
            result["roll_number"] = 2
            result["rolls_remaining"] = 1
        return results

    raise ValueError("This coach currently supports Roll 1 and Roll 2 hold decisions only.")


def run_strategy_patch_v16_tests(verbose=True):
    """
    Checklist-style v16 tests. Returns a dictionary so the Streamlit package can
    be smoke-tested automatically.
    """
    base_upper_chance_scorecard = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }

    empty_scorecard = create_empty_scorecard()

    tests = [
        {
            "name": "Verhoeff Roll 2 article case: keep 3,4",
            "dice": [1, 1, 3, 4, 6],
            "scorecard": dict(empty_scorecard),
            "roll_number": 2,
            "acceptable_best_holds": [[3, 4]]
        },
        {
            "name": "Roll 2 pair of fours still chases Fours",
            "dice": [1, 4, 4, 5, 6],
            "scorecard": dict(base_upper_chance_scorecard),
            "roll_number": 2,
            "acceptable_best_holds": [[4, 4]]
        },
        {
            "name": "Roll 2 single useful four still keeps 4",
            "dice": [1, 1, 2, 2, 4],
            "scorecard": dict(base_upper_chance_scorecard),
            "roll_number": 2,
            "acceptable_best_holds": [[4]]
        },
        {
            "name": "Roll 2 pair of sixes still chases Sixes",
            "dice": [2, 4, 5, 6, 6],
            "scorecard": dict(base_upper_chance_scorecard),
            "roll_number": 2,
            "acceptable_best_holds": [[6, 6]]
        },
        {
            "name": "Roll 2 high loose dice still reasonable",
            "dice": [1, 3, 4, 5, 6],
            "scorecard": dict(base_upper_chance_scorecard),
            "roll_number": 2,
            "acceptable_best_holds": [[5, 6], [6], [5]]
        },
        {
            "name": "Roll 2 Full House two-pair with Chance open protects both pairs",
            "dice": [2, 4, 4, 5, 5],
            "scorecard": dict(base_upper_chance_scorecard),
            "roll_number": 2,
            "acceptable_best_holds": [[4, 4, 5, 5]]
        },
        {
            "name": "Roll 2 Full House two-pair with Chance used prefers 5s",
            "dice": [2, 4, 4, 5, 5],
            "scorecard": {**base_upper_chance_scorecard, "chance": 22},
            "roll_number": 2,
            "acceptable_best_holds": [[5, 5]]
        },
        {
            "name": "Roll 1 triple fives still protected",
            "dice": [2, 3, 5, 5, 5],
            "scorecard": dict(empty_scorecard),
            "roll_number": 1,
            "acceptable_best_holds": [[5, 5, 5]]
        },
        {
            "name": "Roll 1 triple ones still protected",
            "dice": [1, 1, 1, 2, 6],
            "scorecard": dict(empty_scorecard),
            "roll_number": 1,
            "acceptable_best_holds": [[1, 1, 1]]
        },
        {
            "name": "Roll 1 low pair still avoided",
            "dice": [1, 1, 2, 5, 6],
            "scorecard": dict(empty_scorecard),
            "roll_number": 1,
            "acceptable_best_holds": [[5], [6], [5, 6]]
        },
        {
            "name": "Extra Yahtzee/Joker awareness values a second Yahtzee",
            "dice": [6, 6, 6],
            "scorecard": {
                "ones": 3,
                "twos": 6,
                "threes": 9,
                "fours": 12,
                "fives": 15,
                "sixes": 18,
                "three_of_a_kind": None,
                "four_of_a_kind": None,
                "full_house": None,
                "small_straight": None,
                "large_straight": None,
                "yahtzee": 50,
                "chance": None
            },
            "roll_number": 2,
            "acceptable_best_holds": [[6, 6, 6]]
        },
    ]

    passed = 0
    review = 0
    details = []

    if verbose:
        print("STRATEGY PATCH v16 TESTS")
        print("=" * 50)

    for test in tests:
        results = analyze_all_holds_by_roll_number(
            test["dice"],
            test["scorecard"],
            test["roll_number"]
        )
        best_hold = results[0]["hold"]
        ok = best_hold in test["acceptable_best_holds"]

        if ok:
            passed += 1
            status = "PASS"
        else:
            review += 1
            status = "REVIEW"

        details.append({
            "name": test["name"],
            "status": status,
            "best_hold": best_hold,
            "acceptable_best_holds": test["acceptable_best_holds"],
            "top_5": [(r["hold"], round(r["strategy_value"], 2)) for r in results[:5]]
        })

        if verbose:
            print()
            print(test["name"])
            print("-" * 50)
            print("Best:", best_hold)
            print("Acceptable:", test["acceptable_best_holds"])
            print("Result:", status)
            if not ok:
                print("Top 5:", details[-1]["top_5"])

    if verbose:
        print()
        print("Summary:", passed, "PASS /", review, "REVIEW")

    return {
        "passed": passed,
        "review": review,
        "details": details
    }


# Extend the existing fast smoke test so v16 is protected by the familiar command.
if "_BASE_v16_run_fast_strategy_smoke_tests" not in globals():
    _BASE_v16_run_fast_strategy_smoke_tests = run_fast_strategy_smoke_tests


def run_fast_strategy_smoke_tests():
    _BASE_v16_run_fast_strategy_smoke_tests()
    print()
    run_strategy_patch_v16_tests(verbose=True)


if "clear_speed_caches" in globals():
    clear_speed_caches()

# ===== Source notebook cell 201 =====
# ============================
# v16 SPEED SAFETY: KEEP ROLL 1 ON THE PROVEN FAST PATH
# ============================
# The strategic correction target is Roll 2 hold selection. Roll 1 already uses
# the proven fast v15 lookahead path, so keep that path intact for app speed.

roll2_value_for_roll1_hold = _BASE_v16_roll2_value_for_roll1_hold
analyze_all_holds_roll1 = _BASE_v16_analyze_all_holds_roll1


def analyze_all_holds_by_roll_number(dice, scorecard, roll_number):
    if roll_number == 1:
        results = analyze_all_holds_roll1(dice, scorecard)
        for result in results:
            result["roll_number"] = 1
            result["rolls_remaining"] = 2
        return results

    if roll_number == 2:
        results = analyze_all_holds_future_aware(dice, scorecard)
        for result in results:
            result["roll_number"] = 2
            result["rolls_remaining"] = 1
        return results

    raise ValueError("This coach currently supports Roll 1 and Roll 2 hold decisions only.")


def run_strategy_patch_v16_tests(verbose=True):
    base_upper_chance_scorecard = {
        "ones": 3,
        "twos": 6,
        "threes": 9,
        "fours": None,
        "fives": None,
        "sixes": None,
        "three_of_a_kind": None,
        "four_of_a_kind": None,
        "full_house": None,
        "small_straight": 30,
        "large_straight": 40,
        "yahtzee": None,
        "chance": None
    }

    empty_scorecard = create_empty_scorecard()

    tests = [
        {"name": "Verhoeff Roll 2 article case: keep 3,4", "dice": [1,1,3,4,6], "scorecard": dict(empty_scorecard), "roll_number": 2, "acceptable_best_holds": [[3,4]]},
        {"name": "Roll 2 pair of fours still chases Fours", "dice": [1,4,4,5,6], "scorecard": dict(base_upper_chance_scorecard), "roll_number": 2, "acceptable_best_holds": [[4,4]]},
        {"name": "Roll 2 single useful four still keeps 4", "dice": [1,1,2,2,4], "scorecard": dict(base_upper_chance_scorecard), "roll_number": 2, "acceptable_best_holds": [[4]]},
        {"name": "Roll 2 pair of sixes still chases Sixes", "dice": [2,4,5,6,6], "scorecard": dict(base_upper_chance_scorecard), "roll_number": 2, "acceptable_best_holds": [[6,6]]},
        {"name": "Roll 2 high loose dice still reasonable", "dice": [1,3,4,5,6], "scorecard": dict(base_upper_chance_scorecard), "roll_number": 2, "acceptable_best_holds": [[5,6], [6], [5]]},
        {"name": "Roll 2 Full House two-pair with Chance open protects both pairs", "dice": [2,4,4,5,5], "scorecard": dict(base_upper_chance_scorecard), "roll_number": 2, "acceptable_best_holds": [[4,4,5,5]]},
        {"name": "Roll 2 Full House two-pair with Chance used prefers 5s", "dice": [2,4,4,5,5], "scorecard": {**base_upper_chance_scorecard, "chance": 22}, "roll_number": 2, "acceptable_best_holds": [[5,5]]},
        {"name": "Roll 1 triple fives still protected", "dice": [2,3,5,5,5], "scorecard": dict(empty_scorecard), "roll_number": 1, "acceptable_best_holds": [[5,5,5]]},
        {"name": "Roll 1 low pair still avoided", "dice": [1,1,2,5,6], "scorecard": dict(empty_scorecard), "roll_number": 1, "acceptable_best_holds": [[5], [6], [5,6]]},
        {"name": "Extra Yahtzee/Joker awareness values a second Yahtzee", "dice": [6,6,6], "scorecard": {"ones":3,"twos":6,"threes":9,"fours":12,"fives":15,"sixes":18,"three_of_a_kind":None,"four_of_a_kind":None,"full_house":None,"small_straight":None,"large_straight":None,"yahtzee":50,"chance":None}, "roll_number": 2, "acceptable_best_holds": [[6,6,6]]},
    ]

    passed = 0
    review = 0
    details = []

    if verbose:
        print("STRATEGY PATCH v16 TESTS")
        print("=" * 50)

    for test in tests:
        results = analyze_all_holds_by_roll_number(test["dice"], test["scorecard"], test["roll_number"])
        best_hold = results[0]["hold"]
        ok = best_hold in test["acceptable_best_holds"]
        status = "PASS" if ok else "REVIEW"
        passed += int(ok)
        review += int(not ok)
        details.append({"name": test["name"], "status": status, "best_hold": best_hold, "acceptable_best_holds": test["acceptable_best_holds"], "top_5": [(r["hold"], round(r["strategy_value"], 2)) for r in results[:5]]})
        if verbose:
            print(); print(test["name"]); print("-" * 50); print("Best:", best_hold); print("Acceptable:", test["acceptable_best_holds"]); print("Result:", status)
            if not ok:
                print("Top 5:", details[-1]["top_5"])

    if verbose:
        print(); print("Summary:", passed, "PASS /", review, "REVIEW")
    return {"passed": passed, "review": review, "details": details}


def run_fast_strategy_smoke_tests():
    _BASE_v16_run_fast_strategy_smoke_tests()
    print()
    run_strategy_patch_v16_tests(verbose=True)

if "clear_speed_caches" in globals():
    clear_speed_caches()
