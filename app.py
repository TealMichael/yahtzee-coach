
import re
import streamlit as st
import pandas as pd

import yahtzee_engine as yc

st.set_page_config(
    page_title="Yahtzee Coach",
    page_icon="🎲",
    layout="wide"
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

CATEGORIES = getattr(yc, "YAHTZEE_CATEGORIES", [
    "ones", "twos", "threes", "fours", "fives", "sixes",
    "three_of_a_kind", "four_of_a_kind", "full_house",
    "small_straight", "large_straight", "yahtzee", "chance"
])


def hold_label(hold):
    hold = list(hold)
    if not hold:
        return "reroll everything"
    return "keep " + ", ".join(str(d) for d in hold)


def dice_display(dice):
    return " ".join(DICE_EMOJI.get(int(d), str(d)) for d in dice)


def scorecard_dataframe(scorecard):
    rows = []
    for category in CATEGORIES:
        value = scorecard.get(category)
        rows.append({
            "Category": CATEGORY_DISPLAY.get(category, category),
            "Score": "OPEN" if value is None else value
        })
    return pd.DataFrame(rows)


def extract_line(report, prefix):
    for line in report.splitlines():
        if line.startswith(prefix):
            return line.replace(prefix, "").strip()
    return ""


def new_round():
    st.session_state.challenge = yc.generate_practice_challenge()
    st.session_state.report = None
    st.session_state.selected_hold_index = 0


def initialize_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "challenge" not in st.session_state:
        new_round()


initialize_state()
challenge = st.session_state.challenge

st.title("🎲 Yahtzee Coach")
st.caption("Hold Strategy Trainer — Roll 1 and Roll 2 decisions only")

with st.sidebar:
    st.header("Session")
    st.metric("Rounds completed", len(st.session_state.history))

    if st.session_state.history:
        grades = [item.get("grade", "") for item in st.session_state.history]
        best_count = sum(1 for grade in grades if grade == "A+")
        st.metric("Optimal holds", best_count)
        st.metric("Last grade", grades[-1] if grades[-1] else "—")

    if st.button("Start new round", use_container_width=True):
        new_round()
        st.rerun()

    if st.button("Clear session", use_container_width=True):
        st.session_state.history = []
        new_round()
        st.rerun()

left, right = st.columns([1.1, 0.9], gap="large")

with left:
    st.subheader(challenge.get("scenario_name", "Practice Round"))
    st.write(challenge.get("scenario_description", ""))

    roll_number = challenge["roll_number"]
    rolls_remaining = challenge.get("rolls_remaining", 3 - roll_number)
    dice = challenge["dice"]

    st.markdown(f"**Roll:** {roll_number} of 3  ")
    st.markdown(f"**Rolls remaining:** {rolls_remaining}")

    st.markdown("### Dice")
    st.markdown(f"<div style='font-size: 56px; letter-spacing: 10px;'>{dice_display(dice)}</div>", unsafe_allow_html=True)
    st.caption(f"Numbers: {dice}")

    hold_options = yc.generate_unique_holds(dice)
    hold_options = sorted(hold_options, key=lambda hold: (len(hold), hold))
    option_labels = [hold_label(hold) for hold in hold_options]

    st.markdown("### Choose dice to keep")
    selected_label = st.radio(
        "Hold choice",
        option_labels,
        index=st.session_state.get("selected_hold_index", 0),
        label_visibility="collapsed"
    )
    st.session_state.selected_hold_index = option_labels.index(selected_label)
    selected_hold = hold_options[st.session_state.selected_hold_index]

    submit_col, next_col = st.columns(2)
    with submit_col:
        if st.button("Submit hold", type="primary", use_container_width=True):
            report = yc.coach_report_for_user_hold_by_roll_number(
                dice,
                challenge["scorecard"],
                selected_hold,
                roll_number=roll_number
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

with right:
    st.markdown("### Scorecard")
    st.dataframe(scorecard_dataframe(challenge["scorecard"]), hide_index=True, use_container_width=True)

if st.session_state.report:
    st.markdown("---")
    st.markdown("### Coach Report")
    st.code(st.session_state.report, language="text")

    if st.button("Next round", type="primary"):
        new_round()
        st.rerun()

if st.session_state.history:
    with st.expander("Session history"):
        st.dataframe(pd.DataFrame(st.session_state.history), hide_index=True, use_container_width=True)
