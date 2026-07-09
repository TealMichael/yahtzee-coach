import re
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

import yahtzee_engine as yc

st.set_page_config(
    page_title="Yahtzee Coach",
    page_icon="🎲",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DICE_FACE = {
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

GRADE_POINTS = {
    "A+": 4.3, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7,
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
        padding-top: 0.7rem;
        padding-bottom: 2.2rem;
        max-width: 760px;
    }
    h1, h2, h3 { letter-spacing: -0.035em; }
    .top-title { text-align:center; margin:0.05rem 0 0.05rem 0; }
    .subtitle { text-align:center; color:#6b7280; font-size:0.95rem; margin: -0.2rem 0 0.7rem 0; }

    /* Lighter cards: no big gray separator bars. */
    .soft-card {
        border: 1px solid rgba(127,127,127,0.22);
        border-radius: 18px;
        padding: 0.78rem 0.88rem;
        background: rgba(255,255,255,0.90);
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        margin: 0.55rem 0;
        color:#111827 !important;
    }
    .soft-card * { color: inherit; }
    .section-label {
        color:#6b7280;
        font-size:0.78rem;
        text-transform:uppercase;
        letter-spacing:0.055em;
        font-weight:800;
        margin:0.65rem 0 0.32rem 0;
    }
    .scenario-pill {
        display:inline-flex;
        align-items:center;
        border-radius:999px;
        background:#eef4ff;
        color:#174ea6;
        border:1px solid #d2e3fc;
        font-weight:800;
        padding:0.22rem 0.6rem;
        font-size:0.8rem;
        margin-bottom:0.35rem;
    }
    .muted { color:#6b7280; font-size:0.92rem; }
    .round-line { font-weight:800; margin-top:0.35rem; }

    .session-strip {
        display:grid;
        grid-template-columns:repeat(4, minmax(0, 1fr));
        gap:0.45rem;
        margin:0.55rem 0 0.65rem 0;
    }
    .session-box {
        border:1px solid rgba(127,127,127,0.24);
        border-radius:16px;
        padding:0.58rem 0.42rem;
        background:#f3f4f6;
        text-align:center;
        color:#111827 !important;
    }
    .session-box * { color:inherit; }
    .session-label { color:#6b7280; font-size:0.78rem; margin-bottom:0.1rem; }
    .session-value { font-size:1.24rem; font-weight:900; line-height:1.1; }

    .open-chip-row { display:flex; flex-wrap:wrap; gap:0.28rem; margin:0.2rem 0 0.45rem 0; }
    .open-chip {
        border-radius:999px;
        background:#e6f4ea;
        border:1px solid #ceead6;
        color:#137333;
        font-size:0.76rem;
        font-weight:800;
        padding:0.2rem 0.46rem;
    }
    .score-section-title { font-weight:900; margin:0.45rem 0 0.3rem 0; }
    .score-grid { display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:0.32rem; }
    .score-grid.lower { grid-template-columns:repeat(7, minmax(0,1fr)); }
    .score-box {
        border:1px solid rgba(127,127,127,0.22);
        border-radius:12px;
        padding:0.38rem 0.2rem;
        background:rgba(255,255,255,0.78);
        text-align:center;
        min-height:2.85rem;
    }
    .score-label { font-size:0.68rem; color:#6b7280; margin-bottom:0.1rem; white-space:nowrap; }
    .score-value { font-size:0.92rem; font-weight:900; }
    .open-value { color:#188038; }
    .filled-value { color:#3c4043; }

    .selected-summary {
        border-radius:14px;
        background:#fff7ed;
        border:1px solid #fed7aa;
        padding:0.55rem 0.65rem;
        margin:0.65rem 0 0.55rem 0;
        font-weight:900;
        text-align:center;
        color:#9a3412;
    }
    .dice-help { text-align:center; color:#6b7280; font-size:0.86rem; margin:0.15rem 0 0.5rem 0; }

    .dice-picker-row {
        display:flex;
        justify-content:center;
        align-items:center;
        gap:0.45rem;
        flex-wrap:nowrap;
        margin:0.55rem auto 0.7rem auto;
        width:100%;
    }

    /* Dice picker buttons: tight square dice buttons, not full-width rows. */
    .dice-picker-wrap div[data-testid="stHorizontalBlock"] {
        gap:0.42rem !important;
        align-items:center !important;
        justify-content:center !important;
    }
    .dice-picker-wrap div[data-testid="column"] {
        flex:0 0 auto !important;
        width:clamp(54px, 15vw, 64px) !important;
        min-width:clamp(54px, 15vw, 64px) !important;
    }
    .dice-picker-wrap div[data-testid="stButton"] > button {
        width:clamp(54px, 15vw, 64px) !important;
        height:clamp(54px, 15vw, 64px) !important;
        min-height:clamp(54px, 15vw, 64px) !important;
        max-height:clamp(54px, 15vw, 64px) !important;
        padding:0 !important;
        border-radius:15px !important;
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        background:#f8fafc !important;
        color:#111827 !important;
        border:2px solid #d1d5db !important;
        box-shadow:0 4px 0 #c7c9cc, 0 7px 14px rgba(0,0,0,0.16) !important;
        -webkit-tap-highlight-color:transparent !important;
    }
    .dice-picker-wrap div[data-testid="stButton"] > button:active {
        transform:translateY(3px) !important;
        box-shadow:0 1px 0 #c7c9cc, 0 3px 8px rgba(0,0,0,0.18) !important;
    }
    .dice-picker-wrap div[data-testid="stButton"] > button p {
        font-size:2.95rem !important;
        line-height:1 !important;
        margin:0 !important;
        padding:0 !important;
        color:#111827 !important;
        font-family:-apple-system, BlinkMacSystemFont, "Segoe UI Symbol", "Apple Color Emoji", "Noto Color Emoji", sans-serif !important;
    }
    .dice-picker-wrap div[data-testid="stButton"] > button[kind="primary"] {
        background:#ff4b4b !important;
        color:#ffffff !important;
        border-color:#ff4b4b !important;
        box-shadow:0 4px 0 #b91c1c, 0 7px 14px rgba(255,75,75,0.25) !important;
    }
    .dice-picker-wrap div[data-testid="stButton"] > button[kind="primary"] p {
        color:#ffffff !important;
    }

    /* Fallback: Streamlit may not preserve the wrapper around widgets, so scope to horizontal button rows. */
    div[data-testid="stHorizontalBlock"] div[data-testid="column"] div[data-testid="stButton"] > button {
        width:clamp(54px, 15vw, 64px) !important;
        height:clamp(54px, 15vw, 64px) !important;
        min-height:clamp(54px, 15vw, 64px) !important;
        max-height:clamp(54px, 15vw, 64px) !important;
        padding:0 !important;
        border-radius:15px !important;
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        background:#f8fafc !important;
        color:#111827 !important;
        border:2px solid #d1d5db !important;
        box-shadow:0 4px 0 #c7c9cc, 0 7px 14px rgba(0,0,0,0.16) !important;
        -webkit-tap-highlight-color:transparent !important;
    }
    div[data-testid="stHorizontalBlock"] div[data-testid="column"] div[data-testid="stButton"] > button p {
        font-size:2.95rem !important;
        line-height:1 !important;
        margin:0 !important;
        padding:0 !important;
        color:#111827 !important;
        font-family:-apple-system, BlinkMacSystemFont, "Segoe UI Symbol", "Apple Color Emoji", "Noto Color Emoji", sans-serif !important;
    }
    div[data-testid="stHorizontalBlock"] div[data-testid="column"] div[data-testid="stButton"] > button[kind="primary"] {
        background:#ff4b4b !important;
        color:#ffffff !important;
        border-color:#ff4b4b !important;
        box-shadow:0 4px 0 #b91c1c, 0 7px 14px rgba(255,75,75,0.25) !important;
    }
    div[data-testid="stHorizontalBlock"] div[data-testid="column"] div[data-testid="stButton"] > button[kind="primary"] p {
        color:#ffffff !important;
    }

    @media (max-width:380px) {
        .dice-picker-wrap div[data-testid="stHorizontalBlock"] { gap:0.32rem !important; }
        .dice-picker-wrap div[data-testid="column"] {
            width:clamp(48px, 14.5vw, 56px) !important;
            min-width:clamp(48px, 14.5vw, 56px) !important;
        }
        .dice-picker-wrap div[data-testid="stButton"] > button {
            width:clamp(48px, 14.5vw, 56px) !important;
            height:clamp(48px, 14.5vw, 56px) !important;
            min-height:clamp(48px, 14.5vw, 56px) !important;
            max-height:clamp(48px, 14.5vw, 56px) !important;
            border-radius:13px !important;
        }
        .dice-picker-wrap div[data-testid="stButton"] > button p { font-size:2.65rem !important; }
    }

    /* Old HTML dice styles kept harmless in case a cached browser sees them. */
    .die-button { display:none; }

    /* Normal action buttons should not become dice-sized or huge section bars. */
    div[data-testid="stButton"] > button {
        border-radius:14px;
        min-height:2.55rem;
        font-weight:850;
    }

    .grade-row { display:flex; gap:0.7rem; align-items:center; margin-bottom:0.58rem; }
    .grade-badge {
        border-radius:18px;
        padding:0.3rem 0.76rem;
        font-size:2.05rem;
        font-weight:950;
        min-width:4.4rem;
        text-align:center;
        color:white;
        box-shadow:0 2px 8px rgba(0,0,0,0.12);
    }
    .grade-a { background:#188038; }
    .grade-b { background:#1967d2; }
    .grade-c { background:#f29900; }
    .grade-d { background:#d93025; }
    .grade-f { background:#a50e0e; }
    .result-mini { display:grid; grid-template-columns:1fr 1fr; gap:0.45rem; margin:0.45rem 0 0.62rem 0; }
    .result-mini-box {
        border:1px solid rgba(127,127,127,0.22);
        border-radius:13px;
        padding:0.52rem 0.62rem;
        background:rgba(255,255,255,0.82);
        color:#111827 !important;
    }
    .result-mini-box * { color:inherit; }
    .result-mini-label { color:#6b7280; font-size:0.76rem; }
    .result-mini-value { font-weight:850; font-size:0.94rem; }
    .coach-says {
        border-left:5px solid #1967d2;
        background:#f3f7ff;
        border-radius:13px;
        padding:0.62rem 0.72rem;
        margin:0.54rem 0;
        color:#111827 !important;
    }
    .coach-says * { color:#111827 !important; }
    ul.tight-list { margin-top:0.33rem; padding-left:1.15rem; color:inherit; }
    ul.tight-list li { margin-bottom:0.18rem; }

    @media (max-width:640px) {
        .block-container { padding-left:0.7rem; padding-right:0.7rem; }
        .soft-card { padding:0.7rem 0.75rem; border-radius:16px; margin:0.48rem 0; }
        .session-strip { grid-template-columns:repeat(2, minmax(0, 1fr)); }
        .session-box { padding:0.52rem 0.35rem; }
        .session-value { font-size:1.08rem; }
        .score-grid { grid-template-columns:repeat(3, minmax(0,1fr)); }
        .score-grid.lower { grid-template-columns:repeat(4, minmax(0,1fr)); }
        .score-box { min-height:2.65rem; padding:0.32rem 0.16rem; }
        .score-label { font-size:0.66rem; }
        .score-value { font-size:0.86rem; }
        .grade-badge { font-size:1.8rem; min-width:4rem; }
        .result-mini { grid-template-columns:1fr; }
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


def unique_dice_label(index, die):
    # Zero-width spaces make duplicate dice tappable separately while looking identical.
    return DICE_FACE.get(int(die), str(die)) + ("\u200b" * (index + 1))


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
    if points is None: return "—"
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
    chips = [f"<span class='open-chip'>{label}</span>" for label in (open_upper + open_lower)]
    if not chips:
        return "<span class='muted'>No open categories found.</span>"
    return "<div class='open-chip-row'>" + "".join(chips) + "</div>"


def selected_hold_from_indices(dice, indices):
    return sorted([dice[int(i)] for i in sorted(indices)])


def die_pip_classes(die):
    pip_map = {
        1: ["pip-c"],
        2: ["pip-tl", "pip-br"],
        3: ["pip-tl", "pip-c", "pip-br"],
        4: ["pip-tl", "pip-tr", "pip-bl", "pip-br"],
        5: ["pip-tl", "pip-tr", "pip-c", "pip-bl", "pip-br"],
        6: ["pip-tl", "pip-tr", "pip-ml", "pip-mr", "pip-bl", "pip-br"],
    }
    return pip_map.get(int(die), ["pip-c"])


def die_button_html(die, index, round_id, is_held, disabled=False):
    classes = ["die-button"]
    if is_held:
        classes.append("held")
    if disabled:
        classes.append("disabled")
    pip_html = "".join(f"<span class='pip {pip_class}'></span>" for pip_class in die_pip_classes(die))
    label = f"Die {index + 1}, value {die}"
    if disabled:
        return f"<span class='{' '.join(classes)}' aria-label='{label}'>{pip_html}</span>"
    return f"<a class='{' '.join(classes)}' aria-label='{label}' href='?toggle_die={round_id}_{index}#dice-picker'>{pip_html}</a>"


def dice_picker_html(dice, selected_indices, round_id, disabled=False):
    dice_html = [
        die_button_html(die, index, round_id, index in selected_indices, disabled=disabled)
        for index, die in enumerate(dice)
    ]
    return "<div id='dice-picker' class='dice-picker-row'>" + "".join(dice_html) + "</div>"


def get_single_query_param(name):
    value = st.query_params.get(name, None)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def process_dice_toggle_query(held_key, round_id, answer_submitted=False):
    toggle_value = get_single_query_param("toggle_die")
    if not toggle_value:
        return

    # Clear immediately so browser refreshes do not keep re-toggling the same die.
    st.query_params.clear()

    if answer_submitted:
        st.rerun()
        return

    prefix = f"{round_id}_"
    if not str(toggle_value).startswith(prefix):
        st.rerun()
        return

    try:
        die_index = int(str(toggle_value).replace(prefix, "", 1))
    except ValueError:
        st.rerun()
        return

    if die_index < 0 or die_index > 4:
        st.rerun()
        return

    held = list(st.session_state.get(held_key, []))
    if die_index in held:
        held.remove(die_index)
    else:
        held.append(die_index)
        held.sort()
    st.session_state[held_key] = held
    st.rerun()


def new_round(scroll_to_top=False):
    st.session_state.challenge = yc.generate_practice_challenge()
    st.session_state.report = None
    st.session_state.round_id = st.session_state.get("round_id", 0) + 1
    st.session_state.scroll_to_result = False
    st.session_state.scroll_to_top = scroll_to_top
    # Reset held dice for the new round.
    st.session_state[f"held_indices_{st.session_state.round_id}"] = []


def initialize_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "scroll_to_result" not in st.session_state:
        st.session_state.scroll_to_result = False
    if "scroll_to_top" not in st.session_state:
        st.session_state.scroll_to_top = False
    if "round_id" not in st.session_state:
        st.session_state.round_id = 0
    if "challenge" not in st.session_state:
        new_round(scroll_to_top=False)


def render_scorecard(scorecard):
    st.markdown("<div class='section-label'>Current scorecard</div>", unsafe_allow_html=True)
    st.markdown(open_chips_html(scorecard), unsafe_allow_html=True)
    with st.expander("Full scorecard", expanded=True):
        st.markdown("<div class='score-section-title'>Upper</div>", unsafe_allow_html=True)
        st.markdown(score_grid_html(scorecard, UPPER_CATEGORIES), unsafe_allow_html=True)
        st.markdown("<div class='score-section-title'>Lower</div>", unsafe_allow_html=True)
        st.markdown(score_grid_html(scorecard, LOWER_CATEGORIES, lower=True), unsafe_allow_html=True)


def render_result(report):
    st.markdown("<div id='coach-result-anchor'></div>", unsafe_allow_html=True)
    if st.session_state.get("scroll_to_result", False):
        components.html("\n            <script>\n            setTimeout(function() {\n                const el = window.parent.document.getElementById('coach-result-anchor');\n                if (el) { el.scrollIntoView({behavior:'smooth', block:'start'}); }\n            }, 250);\n            </script>\n            ", height=0)
        st.session_state.scroll_to_result = False

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

    st.markdown("<div class='section-label'>Coach result</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='soft-card'>"
        f"<div class='grade-row'><div class='grade-badge {grade_class}'>{grade or '—'}</div>"
        f"<div><b>{rating or 'Coach feedback'}</b><br>"
        f"<span class='muted'>Best hold: {optimal_choice or '—'}</span></div></div>"
        f"<div class='result-mini'>"
        f"<div class='result-mini-box'><div class='result-mini-label'>You kept</div><div class='result-mini-value'>{your_choice or '—'}</div></div>"
        f"<div class='result-mini-box'><div class='result-mini-label'>Efficiency</div><div class='result-mini-value'>{efficiency or '—'}</div></div>"
        f"</div>"
        + (f"<div class='coach-says'><b>Coach says:</b><br>{recommendation}</div>" if recommendation else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    short_lines = []
    if note_items:
        short_lines.extend(note_items[:2])
    if good_items:
        short_lines.append(good_items[0])
    if why_items:
        short_lines.extend(why_items[:2])

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


initialize_state()
challenge = st.session_state.challenge
round_id = st.session_state.round_id
history = st.session_state.history

st.markdown("<div id='app-top-anchor'></div>", unsafe_allow_html=True)
if st.session_state.get("scroll_to_top", False):
    components.html("""
        <script>
        setTimeout(function() {
            const doc = window.parent.document;
            const el = doc.getElementById('app-top-anchor') || doc.querySelector('.block-container');
            if (el) { el.scrollIntoView({behavior: 'smooth', block: 'start'}); }
            window.parent.scrollTo({top: 0, behavior: 'smooth'});
            doc.documentElement.scrollTop = 0;
            doc.body.scrollTop = 0;
        }, 250);
        </script>
        """, height=0)
    st.session_state.scroll_to_top = False

st.markdown("<h1 class='top-title'>🎲 Yahtzee Coach</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Hold Strategy Trainer</div>", unsafe_allow_html=True)

avg_letter, avg_points = session_average_grade(history)
best_holds = sum(1 for item in history if item.get("grade") == "A+")

last_grade = history[-1].get("grade", "—") if history else "—"
best_hold_text = f"{best_holds}/{len(history)}" if history else "—"
avg_points_text = f"{avg_points:.2f}" if avg_points is not None else "—"

st.markdown(
    f"""
    <div class='session-strip'>
        <div class='session-box'><div class='session-label'>Rounds</div><div class='session-value'>{len(history)}</div></div>
        <div class='session-box'><div class='session-label'>Session Grade</div><div class='session-value'>{avg_letter}</div></div>
        <div class='session-box'><div class='session-label'>Best Holds</div><div class='session-value'>{best_hold_text}</div></div>
        <div class='session-box'><div class='session-label'>Last Grade</div><div class='session-value'>{last_grade}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)


roll_number = challenge["roll_number"]
dice = challenge["dice"]
scorecard = challenge["scorecard"]
answer_submitted = st.session_state.report is not None

st.markdown(
    f"""
    <div class='soft-card'>
        <span class='scenario-pill'>{challenge.get('scenario_name', 'Practice Round')}</span>
        <div class='muted'>{challenge.get('scenario_description', '')}</div>
        <div class='round-line'>Roll {roll_number} of 3 · {challenge.get('rolls_remaining', 3 - roll_number)} roll(s) remaining</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Scorecard first, then dice selection.
render_scorecard(scorecard)

st.markdown("<div class='section-label'>Tap dice to hold</div>", unsafe_allow_html=True)
st.markdown("<div class='dice-help'>Tap each die you want to keep. Red dice are held. Leave all unselected to reroll everything.</div>", unsafe_allow_html=True)

held_key = f"held_indices_{round_id}"
if held_key not in st.session_state:
    st.session_state[held_key] = []

selected_indices = list(st.session_state[held_key])

# Streamlit-native dice picker. Each die uses a unique key, so duplicate dice
# are selectable by position and the app updates state without query-param reloads.
st.markdown("<div class='dice-picker-wrap'>", unsafe_allow_html=True)
dice_columns = st.columns(5, gap="small")
for die_index, die_value in enumerate(dice):
    is_held = die_index in st.session_state[held_key]
    with dice_columns[die_index]:
        if st.button(
            DICE_FACE.get(int(die_value), str(die_value)),
            key=f"die_button_{round_id}_{die_index}",
            type="primary" if is_held else "secondary",
            disabled=answer_submitted,
            help=f"Die {die_index + 1}: {die_value}",
            use_container_width=False,
        ):
            held = list(st.session_state.get(held_key, []))
            if die_index in held:
                held.remove(die_index)
            else:
                held.append(die_index)
                held.sort()
            st.session_state[held_key] = held
            st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

selected_indices = list(st.session_state[held_key])
selected_hold = selected_hold_from_indices(dice, selected_indices)
st.markdown(f"<div class='selected-summary'>Your hold: {hold_label(selected_hold)}</div>", unsafe_allow_html=True)

if not answer_submitted:
    if st.button("Submit hold", type="primary", use_container_width=True):
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
        st.session_state.scroll_to_result = True
        st.session_state.scroll_to_top = False
        st.rerun()

if st.session_state.report:
    render_result(st.session_state.report)
    if st.button("Next round", type="primary", use_container_width=True):
        new_round(scroll_to_top=True)
        st.rerun()

if history:
    with st.expander("Session history", expanded=False):
        st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)
