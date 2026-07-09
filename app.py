import re
import streamlit as st
import pandas as pd

import yahtzee_engine as yc

st.set_page_config(
    page_title="Yahtzee Coach",
    page_icon="🎲",
    layout="centered"
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
    "yahtzee": "Ytz",
    "chance": "Ch",
}

CATEGORIES = getattr(yc, "YAHTZEE_CATEGORIES", [
    "ones", "twos", "threes", "fours", "fives", "sixes",
    "three_of_a_kind", "four_of_a_kind", "full_house",
    "small_straight", "large_straight", "yahtzee", "chance"
])

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

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.1rem;
        padding-bottom: 2rem;
        max-width: 980px;
    }
    .hero-card, .coach-card, .score-card, .dice-card {
        border: 1px solid rgba(49, 51, 63, 0.14);
        border-radius: 18px;
        padding: 1rem;
        background: rgba(250, 250, 250, 0.72);
        margin-bottom: 0.8rem;
    }
    .big-dice-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        align-items: center;
        margin: 0.35rem 0 0.6rem 0;
    }
    .die-pill {
        font-size: 2.4rem;
        line-height: 1;
        border: 1px solid rgba(49, 51, 63, 0.18);
        border-radius: 14px;
        padding: 0.42rem 0.55rem;
        background: white;
        min-width: 3.25rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .score-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(82px, 1fr));
        gap: 0.42rem;
        margin-top: 0.45rem;
    }
    .score-box {
        border: 1px solid rgba(49, 51, 63, 0.14);
        border-radius: 12px;
        padding: 0.42rem 0.5rem;
        background: white;
        min-height: 3.05rem;
    }
    .score-label {
        font-size: 0.78rem;
        color: #5f6368;
        margin-bottom: 0.15rem;
        white-space: nowrap;
    }
    .score-value {
        font-size: 1.05rem;
        font-weight: 700;
    }
    .open-value { color: #2e7d32; }
    .filled-value { color: #3c4043; }
    .grade-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.7rem;
        align-items: center;
        margin: 0.3rem 0 0.7rem 0;
    }
    .grade-badge {
        border-radius: 18px;
        padding: 0.3rem 0.72rem;
        font-size: 2.05rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        min-width: 4.6rem;
        text-align: center;
        color: white;
    }
    .grade-a { background: #1b7f37; }
    .grade-b { background: #1976d2; }
    .grade-c { background: #f57c00; }
    .grade-d { background: #d84315; }
    .grade-f { background: #b71c1c; }
    .mini-stat-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 0.45rem;
        margin: 0.5rem 0;
    }
    .mini-stat {
        border: 1px solid rgba(49, 51, 63, 0.12);
        border-radius: 12px;
        padding: 0.55rem;
        background: white;
    }
    .mini-label {
        color: #5f6368;
        font-size: 0.8rem;
    }
    .mini-value {
        font-weight: 750;
        font-size: 1rem;
    }
    ul.compact-list {
        margin-top: 0.2rem;
        padding-left: 1.1rem;
    }
    ul.compact-list li {
        margin-bottom: 0.25rem;
    }
    @media (max-width: 640px) {
        .block-container { padding-left: 0.75rem; padding-right: 0.75rem; }
        .die-pill { font-size: 2rem; min-width: 2.8rem; padding: 0.35rem 0.45rem; }
        .score-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.35rem; }
        .score-box { padding: 0.35rem; min-height: 2.75rem; }
        .score-label { font-size: 0.72rem; }
        .score-value { font-size: 0.95rem; }
        .grade-badge { font-size: 1.75rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def hold_label(hold):
    hold = list(hold)
    if not hold:
        return "reroll everything"
    return "keep " + ", ".join(str(d) for d in hold)


def dice_display_html(dice):
    parts = []
    for die in dice:
        parts.append(f"<span class='die-pill'>{DICE_EMOJI.get(int(die), str(die))}</span>")
    return "<div class='big-dice-row'>" + "".join(parts) + "</div>"


def extract_line(report, prefix):
    for line in report.splitlines():
        if line.startswith(prefix):
            return line.replace(prefix, "").strip()
    return ""


def extract_float_line(report, prefix):
    raw = extract_line(report, prefix)
    if not raw:
        return "—"
    return raw


def extract_section(report, header):
    lines = report.splitlines()
    headers = {
        "Roll 1 lookahead note:",
        "Game-aware note:",
        "Yahtzee-path note:",
        "What was good about your move?",
        "Bonus-chase check:",
        "Narrow upper-box note:",
        "Why was the optimal move better?",
        "Top Roll 1 options:",
        "Coach recommendation:",
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


def grade_to_points(grade):
    return GRADE_POINTS.get(grade.strip(), None)


def points_to_letter(points):
    if points is None:
        return "—"
    if points >= 4.15:
        return "A+"
    if points >= 3.85:
        return "A"
    if points >= 3.5:
        return "A-"
    if points >= 3.15:
        return "B+"
    if points >= 2.85:
        return "B"
    if points >= 2.5:
        return "B-"
    if points >= 2.15:
        return "C+"
    if points >= 1.85:
        return "C"
    if points >= 1.5:
        return "C-"
    if points >= 1.15:
        return "D+"
    if points >= 0.85:
        return "D"
    if points >= 0.5:
        return "D-"
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


def scorecard_grid_html(scorecard):
    boxes = []
    for category in CATEGORIES:
        value = scorecard.get(category)
        label = CATEGORY_SHORT.get(category, CATEGORY_DISPLAY.get(category, category))
        if value is None:
            value_html = "<span class='open-value'>OPEN</span>"
        else:
            value_html = f"<span class='filled-value'>{value}</span>"
        boxes.append(
            f"<div class='score-box'><div class='score-label'>{label}</div><div class='score-value'>{value_html}</div></div>"
        )
    return "<div class='score-grid'>" + "".join(boxes) + "</div>"


def selected_hold_from_dice(dice, round_id):
    selected = []
    for i, die in enumerate(dice):
        if st.session_state.get(f"die_select_{round_id}_{i}", False):
            selected.append(die)
    return sorted(selected)


def reset_die_selection_for_round(dice, round_id):
    for i in range(len(dice)):
        st.session_state[f"die_select_{round_id}_{i}"] = False


def new_round():
    st.session_state.challenge = yc.generate_practice_challenge()
    st.session_state.report = None
    st.session_state.round_id = st.session_state.get("round_id", 0) + 1
    reset_die_selection_for_round(st.session_state.challenge["dice"], st.session_state.round_id)


def initialize_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "round_id" not in st.session_state:
        st.session_state.round_id = 0
    if "challenge" not in st.session_state:
        new_round()


def render_grade_report(report):
    grade = extract_line(report, "Grade:")
    rating = extract_line(report, "Coach rating:")
    your_choice = extract_line(report, "Your choice:")
    optimal_choice = extract_line(report, "Optimal choice:")
    efficiency = extract_float_line(report, "Efficiency:")
    lost = extract_float_line(report, "Strategy value lost:")
    recommendation = extract_recommendation(report)
    good_items = extract_section(report, "What was good about your move?")
    why_items = extract_section(report, "Why was the optimal move better?")
    note_items = extract_section(report, "Narrow upper-box note:")

    grade_class = GRADE_BADGE_CLASS.get(grade, "grade-b")

    st.markdown("<div class='coach-card'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='grade-row'><div class='grade-badge {grade_class}'>{grade or '—'}</div><div><b>{rating or 'Coach feedback'}</b><br><span style='color:#5f6368;'>Best hold: {optimal_choice or '—'}</span></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='mini-stat-row'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='mini-stat'><div class='mini-label'>Your hold</div><div class='mini-value'>{your_choice or '—'}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='mini-stat'><div class='mini-label'>Efficiency</div><div class='mini-value'>{efficiency}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='mini-stat'><div class='mini-label'>Value lost</div><div class='mini-value'>{lost}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if recommendation:
        st.success(recommendation)

    if good_items:
        st.markdown("**What you did well**")
        st.markdown("<ul class='compact-list'>" + "".join(f"<li>{item}</li>" for item in good_items[:3]) + "</ul>", unsafe_allow_html=True)

    if note_items:
        st.markdown("**Quick coach note**")
        st.markdown("<ul class='compact-list'>" + "".join(f"<li>{item}</li>" for item in note_items[:3]) + "</ul>", unsafe_allow_html=True)

    if why_items:
        st.markdown("**Why the best hold works**")
        st.markdown("<ul class='compact-list'>" + "".join(f"<li>{item}</li>" for item in why_items[:5]) + "</ul>", unsafe_allow_html=True)

    with st.expander("Show full coach report"):
        st.code(report, language="text")

    st.markdown("</div>", unsafe_allow_html=True)


initialize_state()
challenge = st.session_state.challenge
round_id = st.session_state.round_id

st.title("🎲 Yahtzee Coach")
st.caption("Hold Strategy Trainer — click dice to choose your hold")

avg_letter, avg_points = session_average_grade(st.session_state.history)
optimal_count = sum(1 for item in st.session_state.history if item.get("grade") == "A+")
rounds_completed = len(st.session_state.history)

stats_cols = st.columns(4)
stats_cols[0].metric("Rounds", rounds_completed)
stats_cols[1].metric("Average grade", avg_letter if avg_letter != "—" else "—")
stats_cols[2].metric("Best holds", optimal_count)
stats_cols[3].metric("Last grade", st.session_state.history[-1]["grade"] if st.session_state.history else "—")

with st.expander("Session details", expanded=False):
    if avg_points is not None:
        st.write(f"Average grade points: {avg_points:.2f}")
    if st.button("Clear session", use_container_width=True):
        st.session_state.history = []
        new_round()
        st.rerun()

st.markdown("<div class='hero-card'>", unsafe_allow_html=True)
st.subheader(challenge.get("scenario_name", "Practice Round"))
st.write(challenge.get("scenario_description", ""))

roll_number = challenge["roll_number"]
rolls_remaining = challenge.get("rolls_remaining", 3 - roll_number)
dice = challenge["dice"]

info_cols = st.columns(2)
info_cols[0].markdown(f"**Roll:** {roll_number} of 3")
info_cols[1].markdown(f"**Rolls remaining:** {rolls_remaining}")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='dice-card'>", unsafe_allow_html=True)
st.markdown("### Dice")
st.markdown(dice_display_html(dice), unsafe_allow_html=True)
st.caption("Click/select the dice you want to hold. Leave all unselected to reroll everything.")

check_cols = st.columns(5)
for i, die in enumerate(dice):
    with check_cols[i]:
        st.checkbox(
            f"Hold {DICE_EMOJI.get(int(die), str(die))} {die}",
            key=f"die_select_{round_id}_{i}",
        )

selected_hold = selected_hold_from_dice(dice, round_id)
st.markdown(f"**Your selected hold:** {hold_label(selected_hold)}")

submit_col, next_col = st.columns(2)
with submit_col:
    if st.button("Submit hold", type="primary", use_container_width=True):
        report = yc.coach_report_for_user_hold_by_roll_number(
            dice,
            challenge["scorecard"],
            selected_hold,
            roll_number=roll_number,
        )
        st.session_state.report = report
        grade = extract_line(report, "Grade:")
        optimal = extract_line(report, "Optimal choice:")
        st.session_state.history.append({
            "scenario": challenge.get("scenario_name", ""),
            "roll": roll_number,
            "dice": str(dice),
            "choice": hold_label(selected_hold),
            "optimal": optimal,
            "grade": grade,
        })
        st.rerun()

with next_col:
    if st.button("Skip / next round", use_container_width=True):
        new_round()
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='score-card'>", unsafe_allow_html=True)
st.markdown("### Scorecard")
st.markdown(scorecard_grid_html(challenge["scorecard"]), unsafe_allow_html=True)
with st.expander("Show full scorecard names"):
    rows = []
    for category in CATEGORIES:
        value = challenge["scorecard"].get(category)
        rows.append({
            "Category": CATEGORY_DISPLAY.get(category, category),
            "Score": "OPEN" if value is None else value,
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.report:
    st.markdown("---")
    render_grade_report(st.session_state.report)

    if st.button("Next round", type="primary", use_container_width=True):
        new_round()
        st.rerun()

if st.session_state.history:
    with st.expander("Session history"):
        st.dataframe(pd.DataFrame(st.session_state.history), hide_index=True, use_container_width=True)
