import re
import streamlit as st
import pandas as pd

import yahtzee_engine as yc

st.set_page_config(
    page_title="Yahtzee Coach",
    page_icon="🎲",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DICE_EMOJI = {
    1: "⚀",
    2: "⚁",
    3: "⚂",
    4: "⚃",
    5: "⚄",
    6: "⚅",
}

CATEGORY_DISPLAY = getattr(yc, "CATEGORY_DISPLAY_NAMES", {
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
    "chance": "Chance",
})

CATEGORY_SHORT = {
    "ones": "1s",
    "twos": "2s",
    "threes": "3s",
    "fours": "4s",
    "fives": "5s",
    "sixes": "6s",
    "three_of_a_kind": "3K",
    "four_of_a_kind": "4K",
    "full_house": "FH",
    "small_straight": "SS",
    "large_straight": "LS",
    "yahtzee": "YTZ",
    "chance": "CH",
}

UPPER_CATEGORIES = ["ones", "twos", "threes", "fours", "fives", "sixes"]
LOWER_CATEGORIES = [
    "three_of_a_kind", "four_of_a_kind", "full_house",
    "small_straight", "large_straight", "yahtzee", "chance"
]
CATEGORIES = UPPER_CATEGORIES + LOWER_CATEGORIES

GRADE_POINTS = {
    "A+": 4.3,
    "A": 4.0,
    "A-": 3.7,
    "B+": 3.3,
    "B": 3.0,
    "B-": 2.7,
    "C+": 2.3,
    "C": 2.0,
    "C-": 1.7,
    "D+": 1.3,
    "D": 1.0,
    "D-": 0.7,
    "F": 0.0,
}

GRADE_BADGE_CLASS = {
    "A+": "grade-a", "A": "grade-a", "A-": "grade-a",
    "B+": "grade-b", "B": "grade-b", "B-": "grade-b",
    "C+": "grade-c", "C": "grade-c", "C-": "grade-c",
    "D+": "grade-d", "D": "grade-d", "D-": "grade-d",
    "F": "grade-f",
}

# Streamlit has limited button styling hooks, so this CSS creates a cleaner,
# game-screen feel without relying on custom JavaScript.
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 2.5rem;
        max-width: 760px;
    }
    h1, h2, h3 { letter-spacing: -0.03em; }
    .top-title {
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        text-align: center;
        color: #5f6368;
        font-size: 0.95rem;
        margin-top: -0.35rem;
        margin-bottom: 0.9rem;
    }
    .game-card, .result-card, .score-card {
        border: 1px solid rgba(49, 51, 63, 0.13);
        border-radius: 20px;
        padding: 1rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(250,250,250,0.88));
        box-shadow: 0 3px 14px rgba(0,0,0,0.045);
        margin-bottom: 0.8rem;
    }
    .scenario-pill {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        background: #eef4ff;
        color: #174ea6;
        border: 1px solid #d2e3fc;
        font-weight: 700;
        padding: 0.22rem 0.55rem;
        font-size: 0.82rem;
        margin-bottom: 0.35rem;
    }
    .muted {
        color: #5f6368;
        font-size: 0.92rem;
    }
    .session-strip {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.55rem;
        margin-bottom: 0.85rem;
    }
    .session-box {
        border: 1px solid rgba(49, 51, 63, 0.12);
        border-radius: 16px;
        padding: 0.7rem 0.8rem;
        background: white;
        text-align: center;
    }
    .session-label {
        color: #5f6368;
        font-size: 0.8rem;
        margin-bottom: 0.1rem;
    }
    .session-value {
        font-size: 1.35rem;
        font-weight: 850;
        line-height: 1.15;
    }
    .dice-row-display {
        display: flex;
        gap: 0.42rem;
        align-items: center;
        justify-content: center;
        margin: 0.55rem 0 0.35rem 0;
        flex-wrap: nowrap;
    }
    .die-display {
        width: 3.45rem;
        height: 3.45rem;
        border: 1px solid rgba(49, 51, 63, 0.18);
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: white;
        font-size: 2.35rem;
        line-height: 1;
        box-shadow: 0 2px 5px rgba(0,0,0,0.06);
    }
    .selected-summary {
        border-radius: 14px;
        background: #f6f8fa;
        border: 1px solid rgba(49, 51, 63, 0.12);
        padding: 0.55rem 0.7rem;
        margin-top: 0.65rem;
        font-weight: 700;
        text-align: center;
    }
    .score-section-title {
        font-weight: 800;
        margin: 0.7rem 0 0.35rem 0;
        color: #202124;
    }
    .score-grid {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 0.35rem;
    }
    .score-grid.lower {
        grid-template-columns: repeat(7, minmax(0, 1fr));
    }
    .score-box {
        border: 1px solid rgba(49, 51, 63, 0.14);
        border-radius: 13px;
        padding: 0.42rem 0.25rem;
        background: white;
        text-align: center;
        min-height: 3.2rem;
    }
    .score-label {
        font-size: 0.72rem;
        color: #5f6368;
        margin-bottom: 0.12rem;
        white-space: nowrap;
    }
    .score-value {
        font-size: 0.95rem;
        font-weight: 850;
    }
    .open-value { color: #188038; }
    .filled-value { color: #3c4043; }
    .open-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.32rem;
        margin-top: 0.35rem;
        margin-bottom: 0.2rem;
    }
    .open-chip {
        border-radius: 999px;
        background: #e6f4ea;
        border: 1px solid #ceead6;
        color: #137333;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 0.22rem 0.5rem;
    }
    .grade-row {
        display: flex;
        gap: 0.75rem;
        align-items: center;
        margin-bottom: 0.6rem;
    }
    .grade-badge {
        border-radius: 20px;
        padding: 0.34rem 0.8rem;
        font-size: 2.15rem;
        font-weight: 900;
        min-width: 4.7rem;
        text-align: center;
        color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }
    .grade-a { background: #188038; }
    .grade-b { background: #1967d2; }
    .grade-c { background: #f29900; }
    .grade-d { background: #d93025; }
    .grade-f { background: #a50e0e; }
    .result-mini {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.45rem;
        margin: 0.45rem 0 0.65rem 0;
    }
    .result-mini-box {
        border: 1px solid rgba(49, 51, 63, 0.12);
        border-radius: 14px;
        padding: 0.55rem 0.65rem;
        background: white;
    }
    .result-mini-label {
        color: #5f6368;
        font-size: 0.77rem;
    }
    .result-mini-value {
        font-weight: 800;
        font-size: 0.96rem;
    }
    .coach-says {
        border-left: 5px solid #1967d2;
        background: #f3f7ff;
        border-radius: 14px;
        padding: 0.65rem 0.75rem;
        margin: 0.55rem 0;
    }
    ul.tight-list {
        margin-top: 0.35rem;
        padding-left: 1.15rem;
    }
    ul.tight-list li { margin-bottom: 0.2rem; }

    /* Streamlit button polish: keep action buttons big enough, but not enormous. */
    div[data-testid="stButton"] > button {
        border-radius: 15px;
        min-height: 2.65rem;
        font-weight: 800;
    }

    /* Dice picker: the dice themselves are the buttons. */
    div[data-testid="stPills"] {
        margin-top: 0.25rem;
        margin-bottom: 0.25rem;
    }
    div[data-testid="stPills"] button {
        font-size: 2.15rem !important;
        line-height: 1 !important;
        min-width: 3.45rem !important;
        min-height: 3.45rem !important;
        border-radius: 16px !important;
        padding: 0.25rem 0.55rem !important;
        font-weight: 900 !important;
    }
    div[data-testid="stPills"] button p {
        font-size: 2.15rem !important;
        line-height: 1 !important;
        margin: 0 !important;
    }
    .dice-help {
        text-align: center;
        color: #5f6368;
        font-size: 0.88rem;
        margin: 0.1rem 0 0.55rem 0;
    }

    @media (max-width: 640px) {
        .block-container { padding-left: 0.65rem; padding-right: 0.65rem; }
        .game-card, .result-card, .score-card { padding: 0.8rem; border-radius: 18px; }
        .session-strip { grid-template-columns: 1fr 1fr; gap: 0.45rem; }
        .session-value { font-size: 1.18rem; }
        .dice-row-display { gap: 0.28rem; }
        .die-display { width: 2.82rem; height: 2.82rem; font-size: 1.95rem; border-radius: 13px; }
        .score-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .score-grid.lower { grid-template-columns: repeat(4, minmax(0, 1fr)); }
        .score-box { min-height: 2.85rem; padding: 0.36rem 0.2rem; }
        .score-label { font-size: 0.68rem; }
        .score-value { font-size: 0.9rem; }
        .grade-badge { font-size: 1.85rem; min-width: 4.1rem; }
        .result-mini { grid-template-columns: 1fr; }
        div[data-testid="stPills"] button {
            font-size: 2.05rem !important;
            min-width: 3.25rem !important;
            min-height: 3.25rem !important;
            padding: 0.2rem 0.45rem !important;
        }
        div[data-testid="stPills"] button p {
            font-size: 2.05rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def hold_label(hold):
    hold = list(sorted(hold))
    if not hold:
        return "reroll everything"
    return "keep " + ", ".join(str(d) for d in hold)


def dice_html(dice, selected_indices=None):
    selected_indices = set(selected_indices or [])
    parts = []
    for index, die in enumerate(dice):
        extra = " box-shadow: 0 0 0 3px #1967d2 inset; background:#eef4ff;" if index in selected_indices else ""
        parts.append(
            f"<div class='die-display' style='{extra}'>{DICE_EMOJI.get(int(die), str(die))}</div>"
        )
    return "<div class='dice-row-display'>" + "".join(parts) + "</div>"


def extract_line(report, prefix):
    for line in report.splitlines():
        if line.startswith(prefix):
            return line.replace(prefix, "").strip()
    return ""


def extract_section(report, header):
    lines = report.splitlines()
    headers = {
        "Roll 1 lookahead note:", "Game-aware note:", "Yahtzee-path note:",
        "What was good about your move?", "Bonus-chase check:",
        "Narrow upper-box note:", "Why was the optimal move better?",
        "Top Roll 1 options:", "Coach recommendation:",
    }
    capture = False
    items = []
    for line in lines:
        stripped = line.strip()
        if stripped == header:
            capture = True
            continue
        if capture and stripped in headers:
            break
        if capture and stripped.startswith("- "):
            items.append(stripped[2:])
    return items


def extract_recommendation(report):
    lines = report.splitlines()
    capture = False
    rec_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped == "Coach recommendation:":
            capture = True
            continue
        if capture and stripped:
            rec_lines.append(stripped)
    return " ".join(rec_lines)


def clean_coach_sentence(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    text = text.replace("The stronger mathematical play was to ", "Best play: ")
    text = text.replace(" because it produced the highest strategy value.", ".")
    text = text.replace("Stay with this thinking. ", "")
    return text


def grade_to_points(grade):
    return GRADE_POINTS.get((grade or "").strip(), None)


def points_to_letter(points):
    if points is None:
        return "—"
    if points >= 4.15: return "A+"
    if points >= 3.85: return "A"
    if points >= 3.5: return "A-"
    if points >= 3.15: return "B+"
    if points >= 2.85: return "B"
    if points >= 2.5: return "B-"
    if points >= 2.15: return "C+"
    if points >= 1.85: return "C"
    if points >= 1.5: return "C-"
    if points >= 1.15: return "D+"
    if points >= 0.85: return "D"
    if points >= 0.5: return "D-"
    return "F"


def session_average_grade(history):
    scores = []
    for item in history:
        points = grade_to_points(item.get("grade", ""))
        if points is not None:
            scores.append(points)
    if not scores:
        return "—", None
    avg = sum(scores) / len(scores)
    return points_to_letter(avg), avg


def score_box_html(category, scorecard):
    value = scorecard.get(category)
    label = CATEGORY_SHORT.get(category, CATEGORY_DISPLAY.get(category, category))
    if value is None:
        value_html = "<span class='open-value'>OPEN</span>"
    else:
        value_html = f"<span class='filled-value'>{value}</span>"
    return f"<div class='score-box'><div class='score-label'>{label}</div><div class='score-value'>{value_html}</div></div>"


def score_grid_html(scorecard, categories, lower=False):
    class_name = "score-grid lower" if lower else "score-grid"
    return f"<div class='{class_name}'>" + "".join(score_box_html(cat, scorecard) for cat in categories) + "</div>"


def open_chips_html(scorecard):
    open_upper = [CATEGORY_SHORT[c] for c in UPPER_CATEGORIES if scorecard.get(c) is None]
    open_lower = [CATEGORY_SHORT[c] for c in LOWER_CATEGORIES if scorecard.get(c) is None]
    chips = []
    for label in open_upper[:6]:
        chips.append(f"<span class='open-chip'>{label}</span>")
    for label in open_lower[:7]:
        chips.append(f"<span class='open-chip'>{label}</span>")
    if not chips:
        return "<span class='muted'>No open categories found.</span>"
    return "<div class='open-chip-row'>" + "".join(chips) + "</div>"


def get_selected_indices(round_id):
    return list(st.session_state.get(f"selected_indices_{round_id}", []))


def set_selected_indices(round_id, indices):
    st.session_state[f"selected_indices_{round_id}"] = sorted(set(indices))


def selected_hold_from_indices(dice, indices):
    return sorted([dice[i] for i in sorted(indices)])


def toggle_die(round_id, index):
    selected = set(get_selected_indices(round_id))
    if index in selected:
        selected.remove(index)
    else:
        selected.add(index)
    set_selected_indices(round_id, selected)


def reset_selection(round_id):
    set_selected_indices(round_id, [])


def new_round():
    st.session_state.challenge = yc.generate_practice_challenge()
    st.session_state.report = None
    st.session_state.round_id = st.session_state.get("round_id", 0) + 1
    reset_selection(st.session_state.round_id)


def initialize_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "round_id" not in st.session_state:
        st.session_state.round_id = 0
    if "challenge" not in st.session_state:
        new_round()


def render_scorecard(scorecard):
    st.markdown("<div class='score-card'>", unsafe_allow_html=True)
    st.markdown("**Open boxes**")
    st.markdown(open_chips_html(scorecard), unsafe_allow_html=True)
    with st.expander("Full scorecard", expanded=True):
        st.markdown("<div class='score-section-title'>Upper</div>", unsafe_allow_html=True)
        st.markdown(score_grid_html(scorecard, UPPER_CATEGORIES), unsafe_allow_html=True)
        st.markdown("<div class='score-section-title'>Lower</div>", unsafe_allow_html=True)
        st.markdown(score_grid_html(scorecard, LOWER_CATEGORIES, lower=True), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_result(report):
    grade = extract_line(report, "Grade:")
    rating = extract_line(report, "Coach rating:")
    your_choice = extract_line(report, "Your choice:")
    optimal_choice = extract_line(report, "Optimal choice:")
    efficiency = extract_line(report, "Efficiency:")
    lost = extract_line(report, "Strategy value lost:")
    recommendation = clean_coach_sentence(extract_recommendation(report))
    good_items = extract_section(report, "What was good about your move?")
    why_items = extract_section(report, "Why was the optimal move better?")
    note_items = extract_section(report, "Narrow upper-box note:")
    grade_class = GRADE_BADGE_CLASS.get(grade, "grade-b")

    st.markdown("<div class='result-card'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='grade-row'><div class='grade-badge {grade_class}'>{grade or '—'}</div>"
        f"<div><b>{rating or 'Coach feedback'}</b><br>"
        f"<span class='muted'>Best hold: {optimal_choice or '—'}</span></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='result-mini'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='result-mini-box'><div class='result-mini-label'>You kept</div><div class='result-mini-value'>{your_choice or '—'}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='result-mini-box'><div class='result-mini-label'>Efficiency</div><div class='result-mini-value'>{efficiency or '—'}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if recommendation:
        st.markdown(f"<div class='coach-says'><b>Coach says:</b><br>{recommendation}</div>", unsafe_allow_html=True)

    short_lines = []
    if note_items:
        short_lines.extend(note_items[:2])
    if good_items:
        short_lines.append(good_items[0])
    if why_items:
        short_lines.extend(why_items[:2])

    # Keep it punchy: at most 4 useful bullets in the main card.
    if short_lines:
        seen = set()
        unique_lines = []
        for line in short_lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        st.markdown("**Quick breakdown**")
        st.markdown(
            "<ul class='tight-list'>" + "".join(f"<li>{line}</li>" for line in unique_lines[:4]) + "</ul>",
            unsafe_allow_html=True,
        )

    if lost:
        st.caption(f"Strategy value lost: {lost}")

    with st.expander("Full coach report"):
        st.code(report, language="text")

    st.markdown("</div>", unsafe_allow_html=True)


initialize_state()
challenge = st.session_state.challenge
round_id = st.session_state.round_id
history = st.session_state.history

st.markdown("<h1 class='top-title'>🎲 Yahtzee Coach</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Hold Strategy Trainer</div>", unsafe_allow_html=True)

avg_letter, avg_points = session_average_grade(history)
best_holds = sum(1 for item in history if item.get("grade") == "A+")

st.markdown(
    f"""
    <div class='session-strip'>
        <div class='session-box'><div class='session-label'>Rounds</div><div class='session-value'>{len(history)}</div></div>
        <div class='session-box'><div class='session-label'>Session Grade</div><div class='session-value'>{avg_letter}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Session details", expanded=False):
    st.write(f"Best holds: {best_holds} / {len(history)}")
    if avg_points is not None:
        st.write(f"Average grade points: {avg_points:.2f}")
    if st.button("Clear session", use_container_width=True):
        st.session_state.history = []
        new_round()
        st.rerun()

roll_number = challenge["roll_number"]
dice = challenge["dice"]
scorecard = challenge["scorecard"]
answer_submitted = st.session_state.report is not None

st.markdown("<div class='game-card'>", unsafe_allow_html=True)
st.markdown(f"<span class='scenario-pill'>{challenge.get('scenario_name', 'Practice Round')}</span>", unsafe_allow_html=True)
st.markdown(f"<div class='muted'>{challenge.get('scenario_description', '')}</div>", unsafe_allow_html=True)
st.markdown(f"**Roll {roll_number} of 3** · **{challenge.get('rolls_remaining', 3 - roll_number)} roll(s) remaining**")
st.markdown("</div>", unsafe_allow_html=True)

# Show the current scorecard before the dice decision so players can reason first.
render_scorecard(scorecard)

st.markdown("<div class='game-card'>", unsafe_allow_html=True)
st.markdown("### Tap dice to hold")
st.markdown("<div class='dice-help'>Tap the dice you want to keep. Tap again to unhold. Leave all unselected to reroll everything.</div>", unsafe_allow_html=True)

# One control only: the dice picker itself. No duplicate dice display + separate huge buttons.
dice_key = f"dice_picker_{round_id}"
if dice_key not in st.session_state:
    st.session_state[dice_key] = []

try:
    selected_indices = st.pills(
        "Dice",
        options=list(range(len(dice))),
        format_func=lambda i: str(dice[i]),
        selection_mode="multi",
        key=dice_key,
        label_visibility="collapsed",
        disabled=answer_submitted,
    ) or []
except AttributeError:
    # Fallback for older Streamlit versions. The requirements file asks for a
    # modern Streamlit, but this keeps the app from crashing if hosted elsewhere.
    st.warning("This app needs Streamlit 1.46+ for the compact dice picker. Upgrade Streamlit if the dice look wrong.")
    selected_indices = []
    cols = st.columns(5)
    for i, die in enumerate(dice):
        with cols[i]:
            if st.checkbox(str(die), key=f"fallback_die_{round_id}_{i}", disabled=answer_submitted):
                selected_indices.append(i)

selected_hold = selected_hold_from_indices(dice, selected_indices)
st.markdown(f"<div class='selected-summary'>Your hold: {hold_label(selected_hold)}</div>", unsafe_allow_html=True)

submit_col, next_col = st.columns(2)
with submit_col:
    if st.button("Submit hold", type="primary", use_container_width=True, disabled=answer_submitted):
        report = yc.coach_report_for_user_hold_by_roll_number(
            dice,
            scorecard,
            selected_hold,
            roll_number=roll_number,
        )
        st.session_state.report = report
        st.session_state.history.append({
            "scenario": challenge.get("scenario_name", ""),
            "roll": roll_number,
            "dice": str(dice),
            "choice": hold_label(selected_hold),
            "optimal": extract_line(report, "Optimal choice:"),
            "grade": extract_line(report, "Grade:"),
        })
        st.rerun()
with next_col:
    if st.button("Next round", use_container_width=True):
        new_round()
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.report:
    render_result(st.session_state.report)
    if st.button("Play another round", type="primary", use_container_width=True):
        new_round()
        st.rerun()

if history:
    with st.expander("Session history", expanded=False):
        st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)
