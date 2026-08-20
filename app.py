import re
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

import yahtzee_engine as yc
from exact_runtime import (
    ExactPolicyTable, build_exact_live_report_from_loader, verify_exact_policy_fingerprint,
)
from session_learning import build_session_learning_summary
from practice_progress import build_practice_progress, newly_unlocked_badges
from puzzle_bank import generate_practice_challenge as generate_expanded_practice_challenge
from daily_challenge import (
    DAILY_CHALLENGE_VERSION, DAILY_TIMEZONE, challenge_set_id,
    current_daily_date_key, daily_challenges as get_daily_challenges, summarize_attempt,
)
from supabase_daily_store import SupabaseDailyStore
from daily_store import (
    AttemptAlreadyComplete, ChallengeMismatch, DailyStoreError, DuplicateAnswer,
    GroupNotFound, InvalidOfficialAnswer, InvalidPin, OutOfOrderAnswer, PlayerNameTaken,
)

APP_ICON_PATH = "apple_touch_icon.png"
PUBLIC_APP_URL = "https://teals-yahtzee-coach.streamlit.app/"
APP_RELEASE = "v43B Phase 2K.9.1"
APP_PUBLIC_VERSION = "Yahtzee Coach Beta · v43B"
PUBLIC_ASSET_BASE = "https://raw.githubusercontent.com/TealMichael/yahtzee-coach/main/"
REMEMBER_COOKIE_NAME = "yc_remember_device_v1"
REMEMBER_STORAGE_KEY = "yc_remember_device_v2"
YESTERDAY_RESULTS_STORAGE_PREFIX = "yc_yesterday_results_seen_v1"
REMEMBER_DEVICE_DAYS = 30
REMEMBER_COOKIE_MAX_AGE = REMEMBER_DEVICE_DAYS * 24 * 60 * 60
APP_ICON_192_PATH = Path(__file__).with_name("home_icon_192.png")
APP_ICON_512_PATH = Path(__file__).with_name("home_icon_512.png")

st.set_page_config(
    page_title="Yahtzee Coach",
    page_icon=APP_ICON_PATH,
    layout="centered",
    initial_sidebar_state="collapsed",
)


# Phase 2K.4.1: browser-local remembered-login bridge.
# Unlike st.context.cookies (read-only on the Python side), Components v2 can
# synchronously move a high-entropy device token between browser localStorage
# and the Streamlit session. The PIN is never stored in the browser.
_remember_storage_component = st.components.v2.component(
    "yahtzee_remember_storage",
    html="<span aria-hidden='true'></span>",
    css=":host { display: none !important; height: 0 !important; }",
    js=r"""
    export default function({ data, setStateValue }) {
      const key = data?.storage_key || "yc_remember_device_v2";
      const action = data?.action || "read";
      const token = data?.token || "";
      const nonce = data?.nonce || "";
      let stored = "";
      try {
        if (action === "set" && token) {
          window.localStorage.setItem(key, token);
        } else if (action === "delete") {
          window.localStorage.removeItem(key);
        }
        stored = window.localStorage.getItem(key) || "";
      } catch (err) {
        stored = "";
      }
      setStateValue("payload", JSON.stringify({
        token: stored,
        ready: true,
        ack: nonce
      }));
    }
    """,
)


# Phase 2K.8: remember whether this player has already viewed the previous day's
# final standings on this browser. This is intentionally browser-local rather
# than a new Supabase table: it prevents repeated ceremonies during ordinary
# reopen/refresh behavior without changing any gameplay or scoring schema.
_yesterday_results_storage_component = st.components.v2.component(
    "yahtzee_yesterday_results_storage",
    html="<span aria-hidden='true'></span>",
    css=":host { display: none !important; height: 0 !important; }",
    js=r"""
    export default function({ data, setStateValue }) {
      const key = data?.storage_key || "";
      const action = data?.action || "read";
      const value = data?.value || "";
      const nonce = data?.nonce || "";
      let stored = "";
      try {
        if (key) {
          if (action === "set" && value) {
            window.localStorage.setItem(key, value);
          } else if (action === "delete") {
            window.localStorage.removeItem(key);
          }
          stored = window.localStorage.getItem(key) || "";
        }
      } catch (err) {
        stored = "";
      }
      setStateValue("payload", JSON.stringify({
        value: stored,
        ready: true,
        ack: nonce
      }));
    }
    """,
)


@st.cache_resource(show_spinner=False)
def load_daily_store():
    """Create the v43B Supabase store from private Streamlit secrets."""
    return SupabaseDailyStore.from_secrets(st.secrets)


@st.cache_data(ttl=60, show_spinner=False)
def _cached_player_groups(player_id: str):
    return load_daily_store().list_groups(str(player_id))


@st.cache_data(ttl=20, show_spinner=False)
def _cached_group_members(group_id: str):
    return load_daily_store().list_group_members(str(group_id))


@st.cache_data(ttl=12, show_spinner=False)
def _cached_group_leaderboard(group_id: str, challenge_id: str):
    return load_daily_store().leaderboard(str(group_id), str(challenge_id))


@st.cache_data(ttl=20, show_spinner=False)
def _cached_group_question_stats(group_id: str, challenge_id: str):
    return load_daily_store().group_question_stats(str(group_id), str(challenge_id))


@st.cache_data(ttl=12, show_spinner=False)
def _cached_group_daily_snapshot(group_id: str, challenge_id: str):
    """Fetch members, standings, and question stats in one batched DB path."""
    return load_daily_store().group_daily_snapshot(str(group_id), str(challenge_id))


@st.cache_data(ttl=300, show_spinner=False)
def _cached_group_player_daily_review(group_id: str, challenge_id: str, viewer_player_id: str, target_player_id: str):
    """Fetch one completed friend's immutable Daily choices after the viewer finishes."""
    return load_daily_store().group_player_daily_review(
        str(group_id), str(challenge_id), str(viewer_player_id), str(target_player_id)
    )


@st.cache_data(ttl=60, show_spinner=False)
def _cached_participation_streak(player_id: str, current_date: str):
    return load_daily_store().current_participation_streak(str(player_id), str(current_date))


def _clear_social_caches():
    """Clear small public-result caches after a write that changes social state."""
    _cached_player_groups.clear()
    _cached_group_members.clear()
    _cached_group_leaderboard.clear()
    _cached_group_question_stats.clear()
    _cached_group_daily_snapshot.clear()
    _cached_group_player_daily_review.clear()
    _cached_participation_streak.clear()


def database_check_enabled():
    """Enable the temporary v43B database smoke-test banner with ?dbcheck=1."""
    try:
        value = st.query_params.get("dbcheck", "0")
    except Exception:
        return False
    if isinstance(value, list):
        value = value[0] if value else "0"
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


if database_check_enabled():
    st.info("🔧 v43B Phase 2K.4 database preflight is loaded.")
    try:
        daily_store = load_daily_store()
        if getattr(daily_store, "url_was_normalized", False):
            st.caption("🔧 Supabase Project URL format was automatically corrected for the Python client.")
        daily_store.health_check()
        st.success("✅ v43B database connection is working.")
    except Exception as exc:
        st.error("❌ v43B database connection failed.")
        st.caption(f"Database check detail: {type(exc).__name__}: {exc}")

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

# The decision scorecard uses the original short Yahtzee labels. Testers found
# them easy to understand, and the shorter labels let the actual score numbers
# stay larger while Roll + full scorecard + dice remain visible together.
CATEGORY_SCORECARD = dict(CATEGORY_SHORT)

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


EXACT_POLICY_PATH = Path(__file__).with_name("exact_policy.npz")


@st.cache_resource(show_spinner=False)
def load_exact_policy():
    """Load only the audited exact-policy artifact; fail closed on any mismatch."""
    verify_exact_policy_fingerprint(EXACT_POLICY_PATH)
    return ExactPolicyTable(EXACT_POLICY_PATH)


def solver_debug_enabled():
    """Developer diagnostics: add ?shadow=1 or ?solver=1 to the app URL."""
    try:
        value = st.query_params.get("solver", st.query_params.get("shadow", "0"))
    except Exception:
        return False
    if isinstance(value, list):
        value = value[0] if value else "0"
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def build_live_report(dice, scorecard, selected_hold, roll_number):
    """Player-facing coaching is exact-only; never substitute heuristic advice."""
    return build_exact_live_report_from_loader(
        load_exact_policy,
        dice=dice,
        scorecard=scorecard,
        user_hold=selected_hold,
        roll_number=roll_number,
    )


def render_solver_panel(records):
    """Hidden developer panel for confirming exact-mode use and fallbacks."""
    if not solver_debug_enabled():
        return

    with st.expander("Exact solver diagnostics", expanded=False):
        st.caption(
            "Daily and Practice require the audited exact policy. Heuristic fallback is disabled."
        )
        if not records:
            st.info("No submitted puzzles in this session yet.")
            return

        exact_count = sum(item.get("source") == "exact" for item in records)
        unavailable_count = sum(item.get("source") == "exact_unavailable" for item in records)
        exact_records = [item for item in records if item.get("source") == "exact"]
        avg_lookup = (
            sum(float(item.get("lookup_ms", 0.0)) for item in exact_records) / len(exact_records)
            if exact_records else 0.0
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Exact", exact_count)
        col2.metric("Unavailable", unavailable_count)
        col3.metric("Avg exact lookup", f"{avg_lookup:.3f} ms")

        frame = pd.DataFrame(records)
        preferred_columns = [
            "source", "scenario", "roll_number", "dice", "user_hold",
            "optimal_hold", "hold_rank", "points_lost", "lookup_ms", "error",
        ]
        visible_columns = [column for column in preferred_columns if column in frame.columns]
        st.dataframe(frame[visible_columns], hide_index=True, use_container_width=True)

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
    .practice-hero {
        border:1px solid #dbeafe;
        background:linear-gradient(135deg,#f8fbff 0%,#ffffff 78%);
        border-radius:18px;
        padding:0.72rem 0.82rem;
        margin:0.42rem 0 0.55rem 0;
        color:#111827 !important;
    }
    .practice-title { font-size:1.18rem; font-weight:950; line-height:1.1; }
    .practice-subtitle { color:#64748b !important; font-size:0.84rem; margin-top:0.14rem; }
    .practice-puzzle-card {
        border:1px solid rgba(127,127,127,0.20);
        border-radius:16px;
        padding:0.7rem 0.78rem;
        background:#fff;
        margin:0.42rem 0 0.38rem 0;
        color:#111827 !important;
    }
    .practice-scenario { font-size:1.03rem; font-weight:950; line-height:1.2; }
    .practice-description { color:#64748b !important; font-size:0.84rem; line-height:1.35; margin-top:0.18rem; }
    .practice-score-label { margin-top:0.7rem; }
    .practice-question { font-size:1.02rem; font-weight:950; margin:0.72rem 0 0.12rem 0; color:#111827; }

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

    .scorecard-heading {
        display:flex; justify-content:space-between; align-items:baseline; gap:0.5rem;
        margin:0.34rem 0 0.12rem 0;
    }
    .scorecard-heading-main {
        color:#6b7280; font-size:0.74rem; text-transform:uppercase;
        letter-spacing:0.055em; font-weight:900;
    }
    .scorecard-heading-sub { color:#64748b; font-size:0.70rem; font-weight:800; }
    .score-section-head {
        display:flex; justify-content:space-between; align-items:baseline;
        font-weight:900; margin:0.20rem 0 0.12rem 0; font-size:0.82rem;
    }
    .score-section-note { color:#64748b; font-size:0.68rem; font-weight:800; }
    .score-grid { display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:0.22rem; }
    .score-grid.lower { grid-template-columns:repeat(4, minmax(0,1fr)); }
    .score-box {
        border:1px solid rgba(127,127,127,0.22);
        border-radius:11px;
        padding:0.27rem 0.14rem;
        background:rgba(255,255,255,0.78);
        text-align:center;
        min-height:2.45rem;
        display:flex; flex-direction:column; justify-content:center;
    }
    .score-label {
        font-size:0.68rem; color:#6b7280; margin-bottom:0.04rem;
        white-space:nowrap; line-height:1.0; min-height:0;
        display:block;
    }
    .score-value { font-size:1.02rem; font-weight:950; line-height:1.05; }
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



    /* V10 dice picker: one tight row of large tappable dice using Streamlit pills. */
    div[data-testid="stPills"] {
        width:100% !important;
        margin:0.45rem auto 0.68rem auto !important;
    }
    div[data-testid="stPills"] div[role="group"] {
        display:flex !important;
        justify-content:center !important;
        align-items:center !important;
        gap:0.52rem !important;
        flex-wrap:nowrap !important;
        width:100% !important;
    }
    div[data-testid="stPills"] button {
        width:clamp(56px, 16.5vw, 68px) !important;
        min-width:clamp(56px, 16.5vw, 68px) !important;
        max-width:clamp(56px, 16.5vw, 68px) !important;
        height:clamp(56px, 16.5vw, 68px) !important;
        min-height:clamp(56px, 16.5vw, 68px) !important;
        max-height:clamp(56px, 16.5vw, 68px) !important;
        border-radius:15px !important;
        padding:0 !important;
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        background:#f8fafc !important;
        border:2px solid #d1d5db !important;
        box-shadow:0 4px 0 #c7c9cc, 0 7px 14px rgba(0,0,0,0.16) !important;
        -webkit-tap-highlight-color:transparent !important;
        color:#111827 !important;
    }
    div[data-testid="stPills"] button:hover {
        border-color:#9ca3af !important;
        background:#ffffff !important;
    }
    div[data-testid="stPills"] button:active {
        transform:translateY(3px) !important;
        box-shadow:0 1px 0 #c7c9cc, 0 3px 8px rgba(0,0,0,0.18) !important;
    }
    div[data-testid="stPills"] button *,
    div[data-testid="stPills"] button p,
    div[data-testid="stPills"] button span {
        font-size:clamp(2.85rem, 11.5vw, 3.55rem) !important;
        line-height:1 !important;
        margin:0 !important;
        padding:0 !important;
        color:#111827 !important;
        font-family:-apple-system, BlinkMacSystemFont, "Segoe UI Symbol", "Apple Color Emoji", "Noto Color Emoji", sans-serif !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"],
    div[data-testid="stPills"] button[aria-pressed="true"],
    div[data-testid="stPills"] button[data-selected="true"] {
        background:#ff4b4b !important;
        border-color:#ff4b4b !important;
        box-shadow:0 4px 0 #b91c1c, 0 7px 14px rgba(255,75,75,0.25) !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"] *,
    div[data-testid="stPills"] button[aria-pressed="true"] *,
    div[data-testid="stPills"] button[data-selected="true"] * {
        color:#ffffff !important;
    }

    @media (max-width:380px) {
        div[data-testid="stPills"] div[role="group"] { gap:0.36rem !important; }
        div[data-testid="stPills"] button {
            width:clamp(52px, 15.7vw, 60px) !important;
            min-width:clamp(52px, 15.7vw, 60px) !important;
            max-width:clamp(52px, 15.7vw, 60px) !important;
            height:clamp(52px, 15.7vw, 60px) !important;
            min-height:clamp(52px, 15.7vw, 60px) !important;
            max-height:clamp(52px, 15.7vw, 60px) !important;
            border-radius:14px !important;
        }
        div[data-testid="stPills"] button *,
        div[data-testid="stPills"] button p,
        div[data-testid="stPills"] button span { font-size:clamp(2.55rem, 10.5vw, 3.05rem) !important; }
    }



    /* V11 dice picker override: keep the working st.pills behavior, but make the dice visually large.
       Streamlit has used both stPills and stButtonGroup test ids, so target both. */
    div[data-testid="stButtonGroup"],
    div[data-testid="stPills"] {
        width:100% !important;
        margin:0.5rem auto 0.7rem auto !important;
    }
    div[data-testid="stButtonGroup"] div[role="group"],
    div[data-testid="stPills"] div[role="group"] {
        display:flex !important;
        flex-direction:row !important;
        justify-content:center !important;
        align-items:center !important;
        gap:0.42rem !important;
        flex-wrap:nowrap !important;
        width:100% !important;
    }

    /* The actual die button. This is intentionally sized like the approved mockup. */
    div[data-testid="stButtonGroup"] button,
    div[data-testid="stPills"] button,
    button[role="checkbox"] {
        width:clamp(58px, 17vw, 68px) !important;
        min-width:clamp(58px, 17vw, 68px) !important;
        max-width:clamp(58px, 17vw, 68px) !important;
        height:clamp(58px, 17vw, 68px) !important;
        min-height:clamp(58px, 17vw, 68px) !important;
        max-height:clamp(58px, 17vw, 68px) !important;
        padding:0 !important;
        margin:0 !important;
        border-radius:15px !important;
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        background:#f8fafc !important;
        color:#111827 !important;
        border:2px solid #d1d5db !important;
        box-shadow:0 4px 0 #c7c9cc, 0 7px 14px rgba(0,0,0,0.16) !important;
        -webkit-tap-highlight-color:transparent !important;
        overflow:hidden !important;
    }
    div[data-testid="stButtonGroup"] button:hover,
    div[data-testid="stPills"] button:hover,
    button[role="checkbox"]:hover {
        background:#ffffff !important;
        border-color:#9ca3af !important;
    }
    div[data-testid="stButtonGroup"] button:active,
    div[data-testid="stPills"] button:active,
    button[role="checkbox"]:active {
        transform:translateY(3px) !important;
        box-shadow:0 1px 0 #c7c9cc, 0 3px 8px rgba(0,0,0,0.18) !important;
    }

    /* Make the die face itself large. Streamlit wraps pill text differently by version,
       so this targets every likely inner text container. */
    div[data-testid="stButtonGroup"] button *,
    div[data-testid="stButtonGroup"] button p,
    div[data-testid="stButtonGroup"] button span,
    div[data-testid="stButtonGroup"] button div,
    div[data-testid="stPills"] button *,
    div[data-testid="stPills"] button p,
    div[data-testid="stPills"] button span,
    div[data-testid="stPills"] button div,
    button[role="checkbox"] *,
    button[role="checkbox"] p,
    button[role="checkbox"] span,
    button[role="checkbox"] div {
        font-size:clamp(3.05rem, 13vw, 3.9rem) !important;
        line-height:0.95 !important;
        margin:0 !important;
        padding:0 !important;
        color:#111827 !important;
        font-family:-apple-system, BlinkMacSystemFont, "Segoe UI Symbol", "Apple Color Emoji", "Noto Color Emoji", sans-serif !important;
        font-weight:500 !important;
    }

    /* Selected/held dice turn red. Cover all Streamlit selection attribute variants. */
    div[data-testid="stButtonGroup"] button[aria-selected="true"],
    div[data-testid="stButtonGroup"] button[aria-pressed="true"],
    div[data-testid="stButtonGroup"] button[aria-checked="true"],
    div[data-testid="stButtonGroup"] button[data-selected="true"],
    div[data-testid="stPills"] button[aria-selected="true"],
    div[data-testid="stPills"] button[aria-pressed="true"],
    div[data-testid="stPills"] button[aria-checked="true"],
    div[data-testid="stPills"] button[data-selected="true"],
    button[role="checkbox"][aria-selected="true"],
    button[role="checkbox"][aria-pressed="true"],
    button[role="checkbox"][aria-checked="true"],
    button[role="checkbox"][data-selected="true"] {
        background:#ff4b4b !important;
        border-color:#ff4b4b !important;
        color:#ffffff !important;
        box-shadow:0 4px 0 #b91c1c, 0 7px 14px rgba(255,75,75,0.25) !important;
    }
    div[data-testid="stButtonGroup"] button[aria-selected="true"] *,
    div[data-testid="stButtonGroup"] button[aria-pressed="true"] *,
    div[data-testid="stButtonGroup"] button[aria-checked="true"] *,
    div[data-testid="stButtonGroup"] button[data-selected="true"] *,
    div[data-testid="stPills"] button[aria-selected="true"] *,
    div[data-testid="stPills"] button[aria-pressed="true"] *,
    div[data-testid="stPills"] button[aria-checked="true"] *,
    div[data-testid="stPills"] button[data-selected="true"] *,
    button[role="checkbox"][aria-selected="true"] *,
    button[role="checkbox"][aria-pressed="true"] *,
    button[role="checkbox"][aria-checked="true"] *,
    button[role="checkbox"][data-selected="true"] * {
        color:#ffffff !important;
    }

    @media (max-width:380px) {
        div[data-testid="stButtonGroup"] div[role="group"],
        div[data-testid="stPills"] div[role="group"] { gap:0.32rem !important; }
        div[data-testid="stButtonGroup"] button,
        div[data-testid="stPills"] button,
        button[role="checkbox"] {
            width:clamp(54px, 16.2vw, 62px) !important;
            min-width:clamp(54px, 16.2vw, 62px) !important;
            max-width:clamp(54px, 16.2vw, 62px) !important;
            height:clamp(54px, 16.2vw, 62px) !important;
            min-height:clamp(54px, 16.2vw, 62px) !important;
            max-height:clamp(54px, 16.2vw, 62px) !important;
            border-radius:14px !important;
        }
        div[data-testid="stButtonGroup"] button *,
        div[data-testid="stPills"] button *,
        button[role="checkbox"] * { font-size:clamp(2.8rem, 12vw, 3.4rem) !important; }
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
    .idea-compare {
        border:1px solid rgba(127,127,127,0.22);
        background:rgba(255,255,255,0.92);
        border-radius:16px;
        padding:0.72rem;
        margin:0.55rem 0;
        color:#111827 !important;
    }
    .idea-compare * { color:#111827 !important; }
    .idea-title {
        font-size:0.78rem;
        text-transform:uppercase;
        letter-spacing:0.055em;
        font-weight:900;
        color:#6b7280 !important;
        margin-bottom:0.45rem;
    }
    .idea-grid {
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:0.48rem;
    }
    .idea-box {
        border-radius:13px;
        padding:0.58rem 0.64rem;
        line-height:1.36;
        background:#f8fafc;
        border:1px solid rgba(127,127,127,0.18);
    }
    .idea-box.best { background:#f3f7ff; border-color:rgba(25,103,210,0.22); }
    .idea-kicker {
        font-size:0.72rem;
        text-transform:uppercase;
        letter-spacing:0.05em;
        font-weight:900;
        color:#6b7280 !important;
        margin-bottom:0.18rem;
    }
    .idea-box.best .idea-kicker { color:#1967d2 !important; }
    .idea-adjust {
        margin-top:0.48rem;
        border-radius:12px;
        padding:0.5rem 0.62rem;
        background:#fff7ed;
        border:1px solid #fed7aa;
        line-height:1.36;
    }
    .lesson-card {
        border:1px solid rgba(25,103,210,0.22);
        background:#f8fbff;
        border-radius:15px;
        padding:0.68rem 0.78rem;
        margin:0.52rem 0 0.58rem 0;
        color:#111827 !important;
    }
    .lesson-card * { color:#111827 !important; }

    .session-coach {
        border:1px solid #bfdbfe;
        border-radius:18px;
        padding:0.82rem 0.88rem;
        background:#eff6ff;
        margin:0.65rem 0;
        color:#111827 !important;
    }
    .session-coach * { color:inherit; }
    .session-coach-title { font-size:1.02rem; font-weight:900; margin-bottom:0.35rem; }
    .session-coach-metrics {
        display:grid;
        grid-template-columns:repeat(3, minmax(0,1fr));
        gap:0.38rem;
        margin:0.45rem 0 0.55rem 0;
    }
    .session-coach-metric {
        background:rgba(255,255,255,0.78);
        border:1px solid #dbeafe;
        border-radius:12px;
        padding:0.42rem 0.35rem;
        text-align:center;
    }
    .session-coach-metric-label { font-size:0.68rem; color:#64748b; }
    .session-coach-metric-value { font-size:1rem; font-weight:900; }
    .session-coach-line { margin:0.38rem 0; line-height:1.35; }
    .session-coach-tag {
        display:inline-block;
        font-size:0.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:0.04em;
        color:#1d4ed8;
        margin-right:0.25rem;
    }
    .lesson-kicker {
        font-size:0.76rem;
        text-transform:uppercase;
        letter-spacing:0.055em;
        font-weight:900;
        color:#1967d2 !important;
        margin-bottom:0.18rem;
    }
    .lesson-text { font-weight:750; line-height:1.38; }
    ul.tight-list { margin-top:0.33rem; padding-left:1.15rem; color:inherit; }
    ul.tight-list li { margin-bottom:0.18rem; }

    @media (max-width:640px) {
        .block-container { padding-left:0.7rem; padding-right:0.7rem; }
        .soft-card { padding:0.7rem 0.75rem; border-radius:16px; margin:0.48rem 0; }
        .session-strip { grid-template-columns:repeat(2, minmax(0, 1fr)); }
        .session-box { padding:0.52rem 0.35rem; }
        .session-value { font-size:1.08rem; }
        .score-grid { grid-template-columns:repeat(3, minmax(0,1fr)); gap:0.20rem; }
        .score-grid.lower { grid-template-columns:repeat(4, minmax(0,1fr)); gap:0.20rem; }
        .score-box { min-height:2.45rem; padding:0.26rem 0.12rem; border-radius:10px; }
        .score-label { font-size:0.68rem; }
        .score-value { font-size:1.02rem; }
        .grade-badge { font-size:1.8rem; min-width:4rem; }
        .result-mini { grid-template-columns:1fr; }
        .idea-grid { grid-template-columns:1fr; }
        .session-coach-metrics { grid-template-columns:repeat(3, minmax(0,1fr)); gap:0.25rem; }
        .session-coach-metric { padding:0.38rem 0.18rem; }
        .session-coach-metric-value { font-size:0.92rem; }
    }


    .daily-review-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0.42rem; margin:0.5rem 0 0.7rem 0; }
    .daily-review-choice { border:1px solid rgba(127,127,127,0.20); border-radius:14px; padding:0.55rem 0.62rem; background:#f8fafc; color:#111827 !important; }
    .daily-review-choice * { color:inherit; }
    .daily-review-choice-top { display:flex; justify-content:space-between; gap:0.5rem; align-items:center; font-size:0.76rem; font-weight:900; color:#64748b !important; }
    .daily-review-choice-dice { font-size:1.45rem; line-height:1.1; margin:0.25rem 0; letter-spacing:0.08rem; }
    .daily-review-choice-hold { font-size:0.84rem; font-weight:800; }
    .leaderboard-list { display:flex; flex-direction:column; gap:0.38rem; margin:0.45rem 0 0.55rem 0; }
    .leaderboard-row { display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:0.55rem; align-items:center; border:1px solid rgba(127,127,127,0.18); border-radius:13px; padding:0.52rem 0.62rem; background:#f8fafc; color:#111827 !important; }
    .leaderboard-row.you { border-color:#bfdbfe; background:#eff6ff; }
    .leaderboard-rank { font-size:0.94rem; font-weight:950; min-width:2.1rem; text-align:center; }
    .leaderboard-name { min-width:0; font-weight:900; line-height:1.15; }
    .leaderboard-name span { display:block; font-size:0.69rem; font-weight:700; color:#64748b !important; margin-top:0.1rem; }
    .leaderboard-score { text-align:right; font-size:0.78rem; line-height:1.2; color:#64748b !important; }
    .leaderboard-score b { display:block; color:#111827 !important; font-size:0.93rem; }
    .friend-review-summary { display:grid; grid-template-columns:1fr 1fr; gap:0.46rem; margin:0.48rem 0 0.62rem 0; }
    .friend-review-card { border:1px solid rgba(127,127,127,0.20); border-radius:14px; padding:0.56rem 0.64rem; background:#f8fafc; color:#111827 !important; }
    .friend-review-card.you { background:#eff6ff; border-color:#bfdbfe; }
    .friend-review-name { font-size:0.82rem; font-weight:950; margin-bottom:0.18rem; }
    .friend-review-metric { font-size:0.78rem; color:#64748b !important; line-height:1.35; }
    .friend-review-metric b { color:#111827 !important; }
    .friend-question-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:0.3rem; margin:0.42rem 0 0.62rem 0; }
    .friend-question-chip { border:1px solid rgba(127,127,127,0.18); border-radius:10px; padding:0.34rem 0.2rem; text-align:center; background:#fff; color:#111827 !important; font-size:0.72rem; line-height:1.2; }
    .friend-question-chip b { display:block; margin-top:0.08rem; font-size:0.78rem; }
    @media (max-width:640px) {
        .daily-review-grid { grid-template-columns:1fr; }
        .score-grid.lower { grid-template-columns:repeat(4, minmax(0,1fr)); }
    }

    /* v41 — result hierarchy and mobile-first coaching polish. */
    .progress-rail {
        display:grid;
        grid-template-columns:repeat(4, minmax(0,1fr));
        gap:0.42rem;
        margin:0.45rem 0 0.72rem 0;
    }
    .progress-chip {
        border:1px solid rgba(127,127,127,0.20);
        border-radius:14px;
        background:#f8fafc;
        padding:0.48rem 0.45rem;
        text-align:center;
        color:#111827 !important;
    }
    .progress-chip * { color:inherit; }
    .progress-kicker { color:#6b7280 !important; font-size:0.69rem; font-weight:800; text-transform:uppercase; letter-spacing:0.045em; }
    .progress-value { margin-top:0.08rem; font-size:1.02rem; line-height:1.12; font-weight:950; }

    .result-hero {
        border:1px solid rgba(127,127,127,0.20);
        border-radius:20px;
        padding:0.82rem 0.9rem;
        background:linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        box-shadow:0 3px 14px rgba(0,0,0,0.055);
        margin:0.5rem 0 0.62rem 0;
        color:#111827 !important;
    }
    .result-hero * { color:inherit; }
    .result-hero-top { display:flex; align-items:center; gap:0.78rem; }
    .result-hero-copy { min-width:0; flex:1; }
    .result-verdict { font-size:1.18rem; font-weight:950; line-height:1.15; letter-spacing:-0.02em; }
    .result-distance { margin-top:0.18rem; color:#6b7280 !important; font-size:0.88rem; line-height:1.3; }
    .result-meta-row { display:flex; flex-wrap:wrap; gap:0.34rem; margin-top:0.42rem; }
    .rank-chip { display:inline-flex; align-items:center; gap:0.24rem; border:1px solid #c7d2fe; background:#eef2ff; color:#3730a3 !important; border-radius:999px; padding:0.24rem 0.52rem; font-size:0.78rem; font-weight:900; line-height:1.2; }
    .result-callout {
        margin-top:0.64rem;
        border-radius:13px;
        background:#f3f7ff;
        border:1px solid #dbe7ff;
        padding:0.58rem 0.66rem;
        line-height:1.38;
    }

    .hold-compare {
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:0.5rem;
        margin:0.55rem 0;
    }
    .hold-card {
        border:1px solid rgba(127,127,127,0.20);
        border-radius:15px;
        padding:0.62rem 0.68rem;
        background:#ffffff;
        min-width:0;
        color:#111827 !important;
    }
    .hold-card.best { background:#eff6ff; border-color:#bfdbfe; }
    .hold-card-label { font-size:0.70rem; text-transform:uppercase; letter-spacing:0.05em; font-weight:900; color:#6b7280 !important; }
    .hold-card.best .hold-card-label { color:#1d4ed8 !important; }
    .hold-card-value { margin-top:0.2rem; font-size:1.04rem; font-weight:950; line-height:1.28; overflow-wrap:anywhere; }

    .coach-three {
        display:grid;
        grid-template-columns:repeat(3, minmax(0,1fr));
        gap:0.5rem;
        margin:0.56rem 0;
    }
    .coach-step {
        border:1px solid rgba(127,127,127,0.18);
        border-radius:14px;
        padding:0.62rem 0.66rem;
        background:#ffffff;
        color:#111827 !important;
        line-height:1.38;
        min-width:0;
    }
    .coach-step * { color:inherit; }
    .coach-step.change { background:#fff7ed; border-color:#fed7aa; }
    .coach-step.why { background:#f3f7ff; border-color:#dbeafe; }
    .coach-step-title { font-size:0.71rem; font-weight:950; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.2rem; color:#6b7280 !important; }
    .coach-step.change .coach-step-title { color:#c2410c !important; }
    .coach-step.why .coach-step-title { color:#1d4ed8 !important; }

    .lesson-card-v41 {
        border:1px solid #c7d2fe;
        background:linear-gradient(135deg,#f5f3ff 0%,#eff6ff 100%);
        border-radius:16px;
        padding:0.74rem 0.82rem;
        margin:0.58rem 0;
        color:#111827 !important;
    }
    .lesson-card-v41 * { color:inherit; }
    .lesson-card-v41 .lesson-kicker { color:#4338ca !important; }

    .detail-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0.42rem; margin:0.35rem 0 0.5rem 0; }
    .detail-box { border:1px solid rgba(127,127,127,0.18); border-radius:12px; padding:0.5rem 0.56rem; background:#f8fafc; }
    .detail-label { color:#6b7280; font-size:0.71rem; }
    .detail-value { font-weight:900; margin-top:0.08rem; overflow-wrap:anywhere; }
    .top-hold-line { padding:0.38rem 0; border-bottom:1px solid rgba(127,127,127,0.14); line-height:1.34; }
    .top-hold-line:last-child { border-bottom:none; }

    /* v42 — lightweight session momentum, achievements, and mastery. */
    .unlock-card {
        border:1px solid #f6c453;
        background:linear-gradient(135deg,#fffbea 0%,#fff7d6 100%);
        border-radius:16px;
        padding:0.68rem 0.76rem;
        margin:0.56rem 0;
        color:#111827 !important;
        box-shadow:0 2px 10px rgba(180,120,0,0.08);
    }
    .unlock-card * { color:inherit; }
    .unlock-kicker { font-size:0.70rem; text-transform:uppercase; letter-spacing:0.055em; font-weight:950; color:#9a6700 !important; margin-bottom:0.34rem; }
    .unlock-badge { display:flex; align-items:center; gap:0.55rem; padding:0.25rem 0; }
    .unlock-icon { font-size:1.42rem; line-height:1; }
    .unlock-name { font-weight:950; line-height:1.15; }
    .unlock-copy { color:#6b7280 !important; font-size:0.82rem; margin-top:0.08rem; line-height:1.3; }

    .mastery-card {
        border:1px solid rgba(127,127,127,0.20);
        background:#ffffff;
        border-radius:17px;
        padding:0.72rem 0.78rem;
        margin:0.58rem 0 0.7rem 0;
        color:#111827 !important;
    }
    .mastery-card * { color:inherit; }
    .mastery-title { font-weight:950; font-size:1rem; }
    .mastery-title span { color:#6b7280 !important; font-size:0.76rem; font-weight:750; margin-left:0.2rem; }
    .mastery-note { color:#6b7280 !important; font-size:0.80rem; line-height:1.32; margin:0.18rem 0 0.44rem 0; }
    .mastery-row { display:flex; align-items:center; justify-content:space-between; gap:0.5rem; border-top:1px solid rgba(127,127,127,0.13); padding:0.48rem 0; }
    .mastery-copy { min-width:0; line-height:1.2; }
    .mastery-copy b { display:block; font-size:0.88rem; }
    .mastery-copy span { display:block; color:#6b7280 !important; font-size:0.73rem; margin-top:0.12rem; }
    .mastery-level { flex:0 0 auto; border-radius:999px; padding:0.20rem 0.46rem; font-size:0.69rem; font-weight:950; border:1px solid #d1d5db; background:#f8fafc; color:#475569 !important; }
    .mastery-level.strong { border-color:#bfdbfe; background:#eff6ff; color:#1d4ed8 !important; }
    .mastery-level.session-mastery { border-color:#c4b5fd; background:#f5f3ff; color:#6d28d9 !important; }
    .achievement-label { color:#6b7280 !important; font-size:0.69rem; font-weight:900; text-transform:uppercase; letter-spacing:0.045em; border-top:1px solid rgba(127,127,127,0.13); padding-top:0.48rem; margin-top:0.04rem; }
    .earned-row { display:flex; flex-wrap:wrap; gap:0.3rem; margin-top:0.3rem; }
    .earned-chip { display:inline-flex; align-items:center; border:1px solid #fde68a; background:#fffbeb; color:#92400e !important; border-radius:999px; padding:0.22rem 0.48rem; font-size:0.72rem; font-weight:900; }

    @media (max-width:640px) {
        .block-container { padding-left:0.62rem; padding-right:0.62rem; padding-top:0.48rem; }
        .progress-rail { grid-template-columns:repeat(2, minmax(0,1fr)); gap:0.3rem; margin-bottom:0.58rem; }
        .progress-chip { padding:0.42rem 0.24rem; border-radius:12px; }
        .progress-kicker { font-size:0.62rem; letter-spacing:0.025em; }
        .progress-value { font-size:0.91rem; }
        .result-hero { padding:0.72rem 0.72rem; border-radius:17px; }
        .result-hero-top { gap:0.58rem; align-items:flex-start; }
        .result-verdict { font-size:1.06rem; }
        .result-distance { font-size:0.82rem; }
        .result-meta-row { margin-top:0.36rem; gap:0.28rem; }
        .rank-chip { font-size:0.74rem; padding:0.22rem 0.46rem; }
        .grade-badge { font-size:1.7rem; min-width:3.75rem; padding:0.28rem 0.58rem; border-radius:15px; }
        .hold-compare { grid-template-columns:1fr; gap:0.38rem; }
        .hold-card { padding:0.56rem 0.62rem; }
        .coach-three { grid-template-columns:1fr; gap:0.38rem; }
        .coach-step { padding:0.56rem 0.62rem; }
        .lesson-card-v41 { padding:0.64rem 0.68rem; }
        .detail-grid { grid-template-columns:1fr 1fr; gap:0.32rem; }
        .detail-box { padding:0.44rem 0.48rem; }
        .session-coach { padding:0.72rem 0.7rem; border-radius:16px; }
        .mastery-card { padding:0.64rem 0.66rem; border-radius:15px; }
        .mastery-row { align-items:flex-start; }
        .mastery-copy span { font-size:0.70rem; }
        .mastery-level { font-size:0.65rem; }
        .unlock-card { padding:0.62rem 0.66rem; }
    }
    @media (max-width:390px) {
        .progress-value { font-size:0.84rem; }
        .progress-kicker { font-size:0.58rem; }
        .result-hero-top { align-items:center; }
        .result-verdict { font-size:1rem; }
        .hold-card-value { font-size:0.98rem; }
        .detail-grid { grid-template-columns:1fr; }
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
        "How close was it?", "Your idea vs. best idea:", "Teaching takeaway:", "Top exact holds:",
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


def render_session_coach(records):
    """Show a cautious session-level learning summary from exact solver metadata."""
    summary = build_session_learning_summary(records)
    if summary["rounds"] == 0:
        return

    if not summary["ready"]:
        needed = summary["rounds_needed"]
        st.caption(
            f"🎯 Session Coach is learning your patterns — {summary['rounds']}/5 practice rounds complete"
            + (f" ({needed} more to unlock the first summary)." if needed else ".")
        )
        return

    optimal_pct = round(summary["optimal_rate"] * 100)
    avg_loss = summary["avg_points_lost"]
    strength = summary["strengths"][0] if summary["strengths"] else None
    focus = summary["focus_areas"][0] if summary["focus_areas"] else None

    lines = []
    if strength:
        lines.append(
            f"<div class='session-coach-line'><span class='session-coach-tag'>Strength</span>"
            f"<b>{strength['skill']}</b> — {strength['strong_count']} of {strength['attempts']} decisions "
            f"were the best hold or within 0.75 points of the best.</div>"
        )
    else:
        lines.append(
            "<div class='session-coach-line'><span class='session-coach-tag'>Strength</span>"
            "No repeated skill has enough evidence yet for a strong label. Keep playing and the pattern tracker will stay conservative.</div>"
        )

    if focus:
        lines.append(
            f"<div class='session-coach-line'><span class='session-coach-tag'>Work on</span>"
            f"<b>{focus['skill']}</b> — {focus['description']}.</div>"
        )
    else:
        lines.append(
            "<div class='session-coach-line'><span class='session-coach-tag'>Work on</span>"
            "No clear recurring weakness yet. That is a good sign; keep building a larger sample.</div>"
        )

    lines.append(
        f"<div class='session-coach-line'><span class='session-coach-tag'>Big lesson</span>"
        f"{summary['biggest_lesson']}</div>"
    )
    if summary.get("trend"):
        lines.append(
            f"<div class='session-coach-line'><span class='session-coach-tag'>Trend</span>"
            f"{summary['trend']}</div>"
        )

    st.markdown(
        "<div class='session-coach'>"
        "<div class='session-coach-title'>🎯 Session Coach</div>"
        "<div class='muted'>A session-only pattern summary based on your hold decisions. "
        "It waits for repeated evidence before calling something a strength or weakness.</div>"
        "<div class='session-coach-metrics'>"
        f"<div class='session-coach-metric'><div class='session-coach-metric-label'>Rounds</div><div class='session-coach-metric-value'>{summary['rounds']}</div></div>"
        f"<div class='session-coach-metric'><div class='session-coach-metric-label'>Best-hold rate</div><div class='session-coach-metric-value'>{optimal_pct}%</div></div>"
        f"<div class='session-coach-metric'><div class='session-coach-metric-label'>Avg pts lost</div><div class='session-coach-metric-value'>{avg_loss:.2f}</div></div>"
        "</div>"
        + "".join(lines)
        + "</div>",
        unsafe_allow_html=True,
    )


def score_box_html(category, scorecard):
    value = scorecard.get(category)
    label = CATEGORY_SCORECARD.get(category, CATEGORY_DISPLAY.get(category, category))
    if value is None:
        value_html = "<span class='open-value'>OPEN</span>"
    else:
        value_html = f"<span class='filled-value'>{value}</span>"
    return f"<div class='score-box'><div class='score-label'>{label}</div><div class='score-value'>{value_html}</div></div>"


def score_grid_html(scorecard, categories, lower=False):
    class_name = "score-grid lower" if lower else "score-grid"
    return f"<div class='{class_name}'>" + "".join(score_box_html(cat, scorecard) for cat in categories) + "</div>"


def open_chips_html(scorecard):
    open_upper = [CATEGORY_SCORECARD[c] for c in UPPER_CATEGORIES if scorecard.get(c) is None]
    open_lower = [CATEGORY_SCORECARD[c] for c in LOWER_CATEGORIES if scorecard.get(c) is None]
    chips = [f"<span class='open-chip'>{label}</span>" for label in (open_upper + open_lower)]
    if not chips:
        return "<span class='muted'>No open categories found.</span>"
    return "<div class='open-chip-row'>" + "".join(chips) + "</div>"


def selected_hold_from_indices(dice, indices):
    return sorted([dice[int(i)] for i in sorted(indices)])


def hold_indices_from_values(dice, held_values):
    """Map a held-value multiset back to concrete die indices for editable Daily questions."""
    remaining = [int(value) for value in held_values]
    indices = []
    for index, die in enumerate(dice):
        try:
            match = remaining.index(int(die))
        except ValueError:
            continue
        indices.append(index)
        remaining.pop(match)
    return indices


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


def app_challenge_signature(challenge):
    """Small session-level signature used to prevent repetitive practice rounds."""
    scorecard = challenge.get("scorecard", {}) or {}
    categories = getattr(yc, "YAHTZEE_CATEGORIES", list(scorecard.keys()))
    filled = tuple(
        (category, scorecard.get(category))
        for category in categories
        if scorecard.get(category) is not None
    )
    return (
        challenge.get("scenario_name"),
        challenge.get("roll_number"),
        tuple(sorted(challenge.get("dice", []))),
        filled,
    )


def new_round(scroll_to_top=False):
    recent_scenarios = list(st.session_state.get("recent_scenario_names", []))
    recent_signatures = list(st.session_state.get("recent_challenge_signatures", []))

    try:
        challenge = generate_expanded_practice_challenge(
            avoid_recent_scenarios=recent_scenarios[-4:],
            avoid_recent_signatures=recent_signatures[-8:],
        )
        st.session_state.practice_bank_error = None
    except Exception as exc:
        # Fail closed: do not silently swap in the older heuristic-era practice deck.
        st.session_state.challenge = None
        st.session_state.practice_bank_error = f"{type(exc).__name__}: {exc}"
        st.session_state.report = None
        st.session_state.scroll_to_result = False
        st.session_state.scroll_to_top = scroll_to_top
        return False

    st.session_state.challenge = challenge

    scenario_name = challenge.get("scenario_name")
    if scenario_name:
        st.session_state.recent_scenario_names = (recent_scenarios + [scenario_name])[-5:]

    signature = app_challenge_signature(challenge)
    st.session_state.recent_challenge_signatures = (recent_signatures + [signature])[-10:]

    st.session_state.report = None
    st.session_state.round_id = st.session_state.get("round_id", 0) + 1
    st.session_state.scroll_to_result = False
    st.session_state.scroll_to_top = scroll_to_top
    st.session_state.new_badges = []
    # Reset held dice for the new round.
    st.session_state[f"held_indices_{st.session_state.round_id}"] = []
    return True


def initialize_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "solver_history" not in st.session_state:
        st.session_state.solver_history = []
    if "recent_scenario_names" not in st.session_state:
        st.session_state.recent_scenario_names = []
    if "recent_challenge_signatures" not in st.session_state:
        st.session_state.recent_challenge_signatures = []
    if "scroll_to_result" not in st.session_state:
        st.session_state.scroll_to_result = False
    if "scroll_to_top" not in st.session_state:
        st.session_state.scroll_to_top = False
    if "new_badges" not in st.session_state:
        st.session_state.new_badges = []
    if "round_id" not in st.session_state:
        st.session_state.round_id = 0
    if "challenge" not in st.session_state:
        new_round(scroll_to_top=False)


def render_scorecard(scorecard):
    """Render the complete decision scorecard without hiding strategy-relevant scores."""
    upper_total = sum(int(scorecard.get(category) or 0) for category in UPPER_CATEGORIES)
    st.markdown(
        "<div class='scorecard-heading'>"
        "<span class='scorecard-heading-main'>Scorecard</span>"
        f"<span class='scorecard-heading-sub'>Upper: {upper_total} / 63</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(score_grid_html(scorecard, UPPER_CATEGORIES), unsafe_allow_html=True)
    st.markdown("<div class='score-section-head'><span>Lower</span></div>", unsafe_allow_html=True)
    st.markdown(score_grid_html(scorecard, LOWER_CATEGORIES, lower=True), unsafe_allow_html=True)




def install_dice_scroll_guard():
    """Preserve scroll position when the user taps dice.

    Dice taps must still rerun Streamlit so the held state and "Your hold" text
    update live. This guard saves the current scroll position before a dice tap
    and restores it immediately after the rerun. It does not affect Submit Hold
    or Next Round, which use their own intentional scrolling.
    """
    components.html(
        """
        <script>
        (function() {
            const STORAGE_KEY = "yc_dice_scroll_y";
            const PENDING_KEY = "yc_dice_scroll_pending";
            const TIME_KEY = "yc_dice_scroll_time";
            const parentWindow = window.parent;
            const doc = parentWindow.document;
            const root = doc.scrollingElement || doc.documentElement || doc.body;

            try { parentWindow.history.scrollRestoration = "manual"; } catch (err) {}

            function currentScrollY() {
                return parentWindow.scrollY || root.scrollTop || doc.documentElement.scrollTop || doc.body.scrollTop || 0;
            }

            function setScrollY(y) {
                parentWindow.scrollTo(0, y);
                if (root) { root.scrollTop = y; }
                if (doc.documentElement) { doc.documentElement.scrollTop = y; }
                if (doc.body) { doc.body.scrollTop = y; }
            }

            function isDiceTap(target) {
                if (!target || !target.closest) { return false; }
                return !!target.closest(
                    'div[data-testid="stPills"] button, div[data-testid="stButtonGroup"] button, button[role="checkbox"]'
                );
            }

            function saveScroll(target) {
                if (!isDiceTap(target)) { return; }
                try {
                    parentWindow.sessionStorage.setItem(STORAGE_KEY, String(currentScrollY()));
                    parentWindow.sessionStorage.setItem(PENDING_KEY, "1");
                    parentWindow.sessionStorage.setItem(TIME_KEY, String(Date.now()));
                } catch (err) {}
            }

            function clearPending() {
                try {
                    parentWindow.sessionStorage.removeItem(PENDING_KEY);
                    parentWindow.sessionStorage.removeItem(STORAGE_KEY);
                    parentWindow.sessionStorage.removeItem(TIME_KEY);
                } catch (err) {}
            }

            function restoreIfNeeded() {
                try {
                    if (parentWindow.sessionStorage.getItem(PENDING_KEY) !== "1") { return; }
                    const savedAt = parseInt(parentWindow.sessionStorage.getItem(TIME_KEY) || "0", 10);
                    if (savedAt && Date.now() - savedAt > 7000) {
                        clearPending();
                        return;
                    }
                    const y = parseInt(parentWindow.sessionStorage.getItem(STORAGE_KEY) || "0", 10);
                    if (Number.isNaN(y)) {
                        clearPending();
                        return;
                    }

                    // Restore many times because Streamlit lays out the rerun in phases.
                    // This keeps the visible screen anchored while the dice turn red.
                    const delays = [0, 1, 10, 25, 50, 90, 140, 210, 320, 480, 700, 950, 1250, 1600];
                    delays.forEach(function(delay) {
                        setTimeout(function() { setScrollY(y); }, delay);
                    });
                    let frames = 0;
                    function restoreFrame() {
                        setScrollY(y);
                        frames += 1;
                        if (frames < 12) { parentWindow.requestAnimationFrame(restoreFrame); }
                    }
                    parentWindow.requestAnimationFrame(restoreFrame);
                    setTimeout(clearPending, 1800);
                } catch (err) {}
            }

            restoreIfNeeded();

            if (!doc.__yahtzeeDiceScrollGuardInstalledV15) {
                doc.__yahtzeeDiceScrollGuardInstalledV15 = true;
                ["pointerdown", "touchstart", "mousedown", "click"].forEach(function(evtName) {
                    doc.addEventListener(evtName, function(event) {
                        saveScroll(event.target);
                    }, true);
                });
            }
        })();
        </script>
        """,
        height=0,
    )

def parse_float_text(text):
    match = re.search(r"-?\d+(?:\.\d+)?", str(text or ""))
    return float(match.group(0)) if match else None


def result_distance_text(lost_text, grade):
    """Student-facing distance from the best hold; exact EV stays in Strategy details."""
    lost_value = parse_float_text(lost_text)
    if lost_value is None:
        return "Your strategy comparison is below."
    if lost_value <= 1e-5:
        return "Best hold — you gave up 0.00 points."
    if lost_value <= 0.25:
        return f"Only {lost_value:.2f} points lost — almost tied with the best hold."
    if lost_value <= 0.75:
        return f"{lost_value:.2f} points lost — a small difference worth noticing."
    if lost_value <= 2.50:
        return f"{lost_value:.2f} points lost — your idea had merit, but there was a better path."
    return f"{lost_value:.2f} points lost — this change can matter a lot over time."


def render_session_progress(history, solver_records):
    progress = build_practice_progress(solver_records)
    avg_letter, _ = session_average_grade(history)
    best_text = f"{progress['optimal_count']}/{progress['rounds']}" if progress['rounds'] else "—"
    loss_text = f"{progress['avg_points_lost']:.2f} pts" if progress['avg_points_lost'] is not None else "—"
    streak = progress['current_exact_streak']
    streak_text = f"🔥 {streak}" if streak else "—"
    st.markdown(
        "<div class='progress-rail'>"
        f"<div class='progress-chip'><div class='progress-kicker'>Rounds</div><div class='progress-value'>{len(history)}</div></div>"
        f"<div class='progress-chip'><div class='progress-kicker'>Best holds</div><div class='progress-value'>{best_text}</div></div>"
        f"<div class='progress-chip'><div class='progress-kicker'>Streak</div><div class='progress-value'>{streak_text}</div></div>"
        f"<div class='progress-chip'><div class='progress-kicker'>Avg loss</div><div class='progress-value'>{loss_text}</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if history:
        best_streak = progress['best_exact_streak']
        streak_note = f" · Best streak: {best_streak}" if best_streak else ""
        st.caption(f"Session grade: {avg_letter}{streak_note} · Progress resets with this browser session.")


def render_new_badges():
    badges = st.session_state.get("new_badges", [])
    if not badges:
        return
    badge_html = "".join(
        f"<div class='unlock-badge'><span class='unlock-icon'>{badge['icon']}</span>"
        f"<div><div class='unlock-name'>{badge['name']}</div><div class='unlock-copy'>{badge['description']}</div></div></div>"
        for badge in badges
    )
    st.markdown(
        "<div class='unlock-card'><div class='unlock-kicker'>Achievement unlocked</div>"
        + badge_html + "</div>",
        unsafe_allow_html=True,
    )


def render_practice_momentum(records):
    progress = build_practice_progress(records)
    if progress["rounds"] < 3:
        return

    mastery_rows = [row for row in progress["mastery"] if row["attempts"] >= 2][:4]
    mastery_html = ""
    for row in mastery_rows:
        level_class = row["level"].lower().replace(" ", "-")
        mastery_html += (
            "<div class='mastery-row'>"
            f"<div class='mastery-copy'><b>{row['skill']}</b>"
            f"<span>{row['strong_count']}/{row['attempts']} strong decisions · {row['avg_loss']:.2f} avg pts lost</span></div>"
            f"<div class='mastery-level {level_class}'>{row['level']}</div>"
            "</div>"
        )

    if not mastery_html:
        mastery_html = (
            "<div class='muted'>Keep playing. A strategy appears here after you have seen it at least twice.</div>"
        )

    badge_html = "".join(
        f"<span class='earned-chip'>{badge['icon']} {badge['name']}</span>"
        for badge in progress["badges"]
    ) or "<span class='muted'>No achievements yet — your first best hold unlocks Bullseye.</span>"

    st.markdown(
        "<div class='mastery-card'>"
        "<div class='mastery-title'>🧩 Strategy mastery <span>this session</span></div>"
        "<div class='mastery-note'>Mastery is intentionally conservative: repeated strong decisions are required before a skill levels up.</div>"
        + mastery_html
        + "<div class='achievement-label'>Session achievements</div>"
        + f"<div class='earned-row'>{badge_html}</div>"
        + "</div>",
        unsafe_allow_html=True,
    )


def render_result(report):
    st.markdown("<div id='coach-result-anchor'></div>", unsafe_allow_html=True)
    if st.session_state.get("scroll_to_result", False):
        components.html("""
            <script>
            setTimeout(function() {
                const el = window.parent.document.getElementById('coach-result-anchor');
                if (el) { el.scrollIntoView({behavior:'smooth', block:'start'}); }
            }, 250);
            </script>
            """, height=0)
        st.session_state.scroll_to_result = False

    grade = extract_line(report, "Grade:")
    rating = extract_line(report, "Coach rating:")
    your_choice = extract_line(report, "Your choice:")
    optimal_choice = extract_line(report, "Optimal choice:")
    hold_rank = extract_line(report, "Hold rank:")
    efficiency = extract_line(report, "Efficiency:")
    decision_metric_label = "Hold rank" if hold_rank else "Efficiency"
    decision_metric_value = hold_rank or efficiency or "—"
    lost = extract_line(report, "Expected game points lost:") or extract_line(report, "Strategy value lost:")
    recommendation = clean_coach_sentence(extract_recommendation(report))
    good_items = extract_section(report, "What was good about your move?")
    why_items = extract_section(report, "Why was the optimal move better?")
    closeness_items = extract_section(report, "How close was it?")
    idea_items = extract_section(report, "Your idea vs. best idea:")
    takeaway_items = extract_section(report, "Teaching takeaway:")
    simple_why_items = extract_section(report, "Simple why:")
    note_items = extract_section(report, "Narrow upper-box note:")
    top_holds = extract_section(report, "Top exact holds:")
    grade_class = GRADE_BADGE_CLASS.get(grade, "grade-b")

    user_idea = next((item[len("Your idea: "):] for item in idea_items if item.startswith("Your idea: ")), "")
    best_idea = next((item[len("Best idea: "):] for item in idea_items if item.startswith("Best idea: ")), "")
    adjustment = next((item[len("Adjustment: "):] for item in idea_items if item.startswith("Adjustment: ")), "")

    st.markdown("<div class='section-label'>Coach result</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='result-hero'>"
        "<div class='result-hero-top'>"
        f"<div class='grade-badge {grade_class}'>{grade or '—'}</div>"
        "<div class='result-hero-copy'>"
        f"<div class='result-verdict'>{rating or 'Coach feedback'}</div>"
        f"<div class='result-distance'>{result_distance_text(lost, grade)}</div>"
        + (f"<div class='result-meta-row'><div class='rank-chip'>🏆 Hold rank: {hold_rank}</div></div>" if hold_rank else "")
        + "</div></div>"
        + (f"<div class='result-callout'><b>Coach says:</b> {recommendation}</div>" if recommendation else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='hold-compare'>"
        f"<div class='hold-card'><div class='hold-card-label'>You kept</div><div class='hold-card-value'>{your_choice or '—'}</div></div>"
        f"<div class='hold-card best'><div class='hold-card-label'>Best hold</div><div class='hold-card-value'>{optimal_choice or '—'}</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    what_went_well = good_items[0] if good_items else (user_idea or "Your hold had a clear strategic target.")
    what_changes = adjustment or (why_items[0] if why_items else "Compare your hold with the exact best hold above.")
    why_it_matters = simple_why_items[0] if simple_why_items else (why_items[0] if why_items else (best_idea or recommendation or "The exact solver compares every legal hold through the rest of the game."))
    if what_changes == why_it_matters and len(why_items) > 1:
        why_it_matters = why_items[1]

    st.markdown(
        "<div class='coach-three'>"
        f"<div class='coach-step'><div class='coach-step-title'>✓ What you did well</div><div>{what_went_well}</div></div>"
        f"<div class='coach-step change'><div class='coach-step-title'>→ What changes</div><div>{what_changes}</div></div>"
        f"<div class='coach-step why'><div class='coach-step-title'>Why it matters</div><div>{why_it_matters}</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    if takeaway_items:
        takeaway = takeaway_items[0]
        if ": " in takeaway:
            lesson_title, lesson_text = takeaway.split(": ", 1)
        else:
            lesson_title, lesson_text = "Key lesson", takeaway
        st.markdown(
            f"<div class='lesson-card-v41'><div class='lesson-kicker'>🧠 {lesson_title}</div>"
            f"<div class='lesson-text'>{lesson_text}</div></div>",
            unsafe_allow_html=True,
        )

    with st.expander("Strategy details", expanded=False):
        st.caption("The exact math is here when you want it; the main coach view stays focused on the lesson.")
        st.markdown(
            "<div class='detail-grid'>"
            f"<div class='detail-box'><div class='detail-label'>{decision_metric_label}</div><div class='detail-value'>{decision_metric_value}</div></div>"
            f"<div class='detail-box'><div class='detail-label'>Expected points lost</div><div class='detail-value'>{lost or '0.00'}</div></div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if closeness_items:
            st.markdown(f"**How close was it?** {closeness_items[0]}")
        if note_items:
            st.markdown("**Scorecard note**")
            st.markdown("<ul class='tight-list'>" + "".join(f"<li>{line}</li>" for line in note_items[:2]) + "</ul>", unsafe_allow_html=True)
        if top_holds:
            st.markdown("**Top exact holds**")
            st.markdown("".join(f"<div class='top-hold-line'>{line}</div>" for line in top_holds[:3]), unsafe_allow_html=True)
        st.markdown("**Full text report**")
        st.code(report, language="text")



# ---------------------------------------------------------------------------
# v43B Phase 2E — invite links, editable Daily review, and home-screen polish
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .mode-note { text-align:center; color:#6b7280; font-size:0.78rem; margin:-0.15rem 0 0.55rem 0; }
    .daily-hero {
        border:1px solid #d8e4ff; background:linear-gradient(135deg,#f4f8ff 0%,#ffffff 72%);
        border-radius:20px; padding:0.9rem 0.95rem; margin:0.45rem 0 0.68rem 0; color:#111827 !important;
    }
    .daily-hero * { color:inherit; }
    .daily-kicker { color:#1d4ed8 !important; font-size:0.75rem; font-weight:950; text-transform:uppercase; letter-spacing:0.055em; }
    .daily-title { font-size:1.35rem; line-height:1.15; font-weight:950; margin:0.14rem 0 0.22rem 0; }
    .daily-rule { color:#5f6b7a !important; font-size:0.88rem; line-height:1.35; }
    .daily-progress {
        display:grid; grid-template-columns:repeat(10,minmax(0,1fr)); gap:0.24rem; margin:0.28rem 0 0.18rem 0;
    }
    .daily-dot {
        height:0.58rem; border-radius:999px; background:#e5e7eb; border:1px solid rgba(127,127,127,.12);
        transition:background .15s ease, transform .15s ease;
    }
    .daily-dot.done { background:#16a34a; }
    .daily-dot.current { background:#2563eb; transform:scaleY(1.22); }
    .daily-progress-copy { display:flex; justify-content:space-between; align-items:center; gap:0.5rem; margin-bottom:0.18rem; }
    .daily-progress-copy b { font-size:0.92rem; }
    .daily-progress-copy span { color:#6b7280; font-size:0.78rem; font-weight:700; }
    .daily-lock-note { color:#6b7280; font-size:0.78rem; text-align:center; margin:0.3rem 0 0.15rem 0; }
    .daily-flash { border:1px solid #bbf7d0; background:#f0fdf4; color:#166534 !important; border-radius:12px; padding:0.46rem 0.62rem; font-weight:800; font-size:0.82rem; margin:0.3rem 0; }
    .daily-roll-stage {
        border-radius:13px;
        padding:0.38rem 0.58rem;
        margin:0.26rem 0 0.30rem 0;
        text-align:center;
        border:2px solid transparent;
        box-shadow:0 1px 5px rgba(0,0,0,0.035);
    }
    .daily-roll-stage.roll-1 { background:#eff6ff; border-color:#93c5fd; color:#1d4ed8 !important; }
    .daily-roll-stage.roll-2 { background:#f0fdf4; border-color:#86efac; color:#15803d !important; }
    .daily-roll-stage-title { font-size:0.92rem; font-weight:950; letter-spacing:.008em; line-height:1.05; }
    .daily-roll-stage-sub { display:none; }
    .daily-result-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:0.4rem; margin:0.6rem 0; }
    .daily-result-box { border:1px solid rgba(127,127,127,.22); border-radius:15px; background:#f8fafc; padding:0.58rem 0.42rem; text-align:center; color:#111827 !important; }
    .daily-result-label { color:#6b7280 !important; font-size:0.68rem; font-weight:800; text-transform:uppercase; letter-spacing:.035em; }
    .daily-result-value { font-size:1.17rem; font-weight:950; margin-top:0.08rem; }
    .daily-result-sub { color:#6b7280 !important; font-size:0.66rem; margin-top:0.04rem; }
    .daily-rank-banner { border:1px solid #fde68a; background:#fffbeb; border-radius:17px; padding:0.72rem 0.78rem; margin:0.5rem 0; color:#78350f !important; }
    .daily-rank-banner b { font-size:1.02rem; }
    .yesterday-podium { border:1px solid #facc15; background:linear-gradient(135deg,#fffbeb,#fff7ed); border-radius:20px; padding:0.9rem 0.86rem; margin:0.58rem 0 0.68rem 0; text-align:center; color:#78350f !important; box-shadow:0 8px 24px rgba(120,53,15,.08); }
    .yesterday-podium .medal { font-size:3.25rem; line-height:1; margin-bottom:.22rem; }
    .yesterday-podium .title { font-size:1.28rem; font-weight:950; color:#78350f !important; }
    .yesterday-podium .copy { margin-top:.18rem; font-size:.88rem; color:#92400e !important; }
    .yesterday-final-note { border:1px solid rgba(127,127,127,.2); background:#f8fafc; border-radius:15px; padding:.66rem .72rem; margin:.5rem 0; color:#334155 !important; }
    .group-story-grid { display:grid; grid-template-columns:1fr 1fr; gap:0.42rem; margin:0.48rem 0; }
    .group-story-card { border:1px solid rgba(127,127,127,.2); border-radius:15px; padding:0.62rem 0.68rem; background:#fff; color:#111827 !important; }
    .group-story-card .story-kicker { color:#6b7280 !important; font-size:0.68rem; font-weight:900; text-transform:uppercase; letter-spacing:.04em; }
    .group-story-card .story-title { font-weight:950; margin:0.12rem 0; }
    .group-story-card .story-copy { color:#5f6b7a !important; font-size:0.79rem; }
    .review-summary { display:grid; grid-template-columns:1fr 1fr; gap:0.35rem; margin:0.3rem 0 0.45rem 0; }
    .review-box { border:1px solid rgba(127,127,127,.18); border-radius:13px; padding:0.5rem 0.58rem; background:#fafafa; color:#111827 !important; }
    .review-box * { color:inherit; }
    .review-label { color:#6b7280 !important; font-size:0.68rem; text-transform:uppercase; font-weight:850; }
    .review-value { color:#111827 !important; font-weight:900; font-size:0.88rem; margin-top:.08rem; }
    .daily-dice-line { font-size:1.9rem; letter-spacing:.12rem; margin:.15rem 0 .42rem 0; }
    .prototype-badge { display:inline-block; border-radius:999px; background:#f3e8ff; color:#6b21a8 !important; border:1px solid #e9d5ff; font-size:.69rem; font-weight:900; padding:.18rem .45rem; }
    .identity-note { border:1px solid #bfdbfe; background:#eff6ff; color:#1e3a8a !important; border-radius:14px; padding:.62rem .7rem; margin:.42rem 0 .62rem 0; font-size:.82rem; line-height:1.35; }
    .identity-note b { color:#1d4ed8 !important; }
    @media (max-width:640px) {
        .daily-result-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:.3rem; }
        .group-story-grid { grid-template-columns:1fr; gap:.32rem; }
        .daily-hero { padding:.72rem .7rem; border-radius:17px; }
        .daily-title { font-size:1.18rem; }
        .daily-progress { gap:.15rem; }
        .daily-dot { height:.48rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _reset_daily_local_attempt(date_key: str | None = None):
    """Reset only the local mirror of a Daily attempt; never delete database data."""
    date_key = date_key or current_daily_date_key()
    st.session_state.daily_date_key = date_key
    st.session_state.daily_challenges = get_daily_challenges(date_key)
    st.session_state.daily_set_id = challenge_set_id(date_key, st.session_state.daily_challenges)
    st.session_state.daily_started = False
    st.session_state.daily_completed = False
    st.session_state.daily_ready_to_submit = False
    st.session_state.daily_question_index = 0
    st.session_state.daily_answers = []
    st.session_state.daily_flash = ""
    st.session_state.daily_attempt_id = None
    st.session_state.daily_persistence_sync_key = None
    st.session_state.daily_display_name = st.session_state.get("daily_display_name", "You") or "You"
    # Held-die widget state is local UI state and must never leak between players/dates.
    for key in list(st.session_state.keys()):
        if str(key).startswith(("daily_held_", "daily_dice_pills_")):
            del st.session_state[key]


def initialize_daily_state():
    today = current_daily_date_key()
    if st.session_state.get("daily_date_key") != today:
        _reset_daily_local_attempt(today)
    elif "daily_challenges" not in st.session_state:
        _reset_daily_local_attempt(today)
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "Daily Challenge"
    if "daily_attempt_id" not in st.session_state:
        st.session_state.daily_attempt_id = None
    if "daily_ready_to_submit" not in st.session_state:
        st.session_state.daily_ready_to_submit = False
    if "daily_persistence_sync_key" not in st.session_state:
        st.session_state.daily_persistence_sync_key = None


def initialize_player_identity_state():
    """Keep private player identity only in this user's Streamlit session."""
    if "active_player_id" not in st.session_state:
        st.session_state.active_player_id = None
    if "active_player_name" not in st.session_state:
        st.session_state.active_player_name = None
    if "player_auth_flash" not in st.session_state:
        st.session_state.player_auth_flash = ""
    if "active_group_id" not in st.session_state:
        st.session_state.active_group_id = None
    if "friend_review_player_id" not in st.session_state:
        st.session_state.friend_review_player_id = None
    if "group_flash" not in st.session_state:
        st.session_state.group_flash = ""
    if "active_device_token" not in st.session_state:
        st.session_state.active_device_token = None
    if "remember_restore_checked" not in st.session_state:
        st.session_state.remember_restore_checked = False
    if "remember_cookie_command" not in st.session_state:
        st.session_state.remember_cookie_command = None
    if "remember_storage_command" not in st.session_state:
        st.session_state.remember_storage_command = None
    if "remember_storage_nonce" not in st.session_state:
        st.session_state.remember_storage_nonce = 0
    if "yesterday_result_seen_command" not in st.session_state:
        st.session_state.yesterday_result_seen_command = None
    if "yesterday_result_seen_nonce" not in st.session_state:
        st.session_state.yesterday_result_seen_nonce = 0
    if "yesterday_result_storage_state" not in st.session_state:
        st.session_state.yesterday_result_storage_state = {"value": "", "ready": False}
    if "yesterday_balloons_date" not in st.session_state:
        st.session_state.yesterday_balloons_date = None


def _browser_remember_cookie() -> str:
    try:
        return str(st.context.cookies.get(REMEMBER_COOKIE_NAME, "") or "").strip()
    except Exception:
        return ""


def _next_remember_storage_nonce() -> str:
    st.session_state.remember_storage_nonce = int(st.session_state.get("remember_storage_nonce", 0)) + 1
    return str(st.session_state.remember_storage_nonce)


def _queue_remember_storage_set(token: str):
    st.session_state.remember_storage_command = {
        "action": "set", "token": str(token), "nonce": _next_remember_storage_nonce()
    }


def _queue_remember_storage_delete():
    st.session_state.remember_storage_command = {
        "action": "delete", "token": "", "nonce": _next_remember_storage_nonce()
    }


def _queue_remember_cookie_set(token: str):
    st.session_state.remember_cookie_command = {"action": "set", "token": str(token)}
    _queue_remember_storage_set(token)


def _queue_remember_cookie_delete():
    st.session_state.remember_cookie_command = {"action": "delete", "token": ""}
    _queue_remember_storage_delete()


def render_remember_storage_bridge() -> dict:
    """Read/write the 30-day device token through first-party browser localStorage."""
    command = st.session_state.get("remember_storage_command") or {}
    action = str(command.get("action") or "read")
    token = str(command.get("token") or "")
    nonce = str(command.get("nonce") or "")
    default_payload = json.dumps({"token": "", "ready": False, "ack": ""})
    try:
        result = _remember_storage_component(
            data={
                "storage_key": REMEMBER_STORAGE_KEY,
                "action": action,
                "token": token,
                "nonce": nonce,
            },
            default={"payload": default_payload},
            on_payload_change=lambda: None,
            key="remember_storage_bridge",
        )
        payload_raw = getattr(result, "payload", default_payload) or default_payload
        payload = json.loads(str(payload_raw))
        if nonce and str(payload.get("ack") or "") == nonce:
            st.session_state.remember_storage_command = None
        return {
            "token": str(payload.get("token") or "").strip(),
            "ready": bool(payload.get("ready")),
        }
    except Exception as exc:
        if database_check_enabled():
            st.caption(f"Remembered-login browser detail: {type(exc).__name__}: {exc}")
        # Cookie restore remains as a compatibility fallback.
        return {"token": "", "ready": True}



def _yesterday_results_storage_key() -> str:
    player_id = str(st.session_state.get("active_player_id") or "").strip()
    return f"{YESTERDAY_RESULTS_STORAGE_PREFIX}_{player_id}" if player_id else ""


def _next_yesterday_result_nonce() -> str:
    st.session_state.yesterday_result_seen_nonce = int(st.session_state.get("yesterday_result_seen_nonce", 0)) + 1
    return str(st.session_state.yesterday_result_seen_nonce)


def _queue_yesterday_result_seen(date_key: str):
    """Persist that this browser/player has acknowledged yesterday's final standings."""
    st.session_state.yesterday_result_seen_command = {
        "action": "set",
        "value": str(date_key),
        "nonce": _next_yesterday_result_nonce(),
    }


def render_yesterday_result_storage_bridge() -> dict:
    """Read/write the per-player last ceremony date through browser localStorage."""
    storage_key = _yesterday_results_storage_key()
    if not storage_key:
        state = {"value": "", "ready": True}
        st.session_state.yesterday_result_storage_state = state
        return state
    command = st.session_state.get("yesterday_result_seen_command") or {}
    action = str(command.get("action") or "read")
    value = str(command.get("value") or "")
    nonce = str(command.get("nonce") or "")
    default_payload = json.dumps({"value": "", "ready": False, "ack": ""})
    try:
        result = _yesterday_results_storage_component(
            data={
                "storage_key": storage_key,
                "action": action,
                "value": value,
                "nonce": nonce,
            },
            default={"payload": default_payload},
            on_payload_change=lambda: None,
            key=f"yesterday_result_storage_bridge_{st.session_state.get('active_player_id')}",
        )
        payload_raw = getattr(result, "payload", default_payload) or default_payload
        payload = json.loads(str(payload_raw))
        if nonce and str(payload.get("ack") or "") == nonce:
            st.session_state.yesterday_result_seen_command = None
        state = {
            "value": str(payload.get("value") or "").strip(),
            "ready": bool(payload.get("ready")),
        }
    except Exception as exc:
        if database_check_enabled():
            st.caption(f"Yesterday-results browser detail: {type(exc).__name__}: {exc}")
        # Fail open: a browser that blocks localStorage may show the recap again
        # on a future fresh session, but gameplay must remain available.
        state = {"value": "", "ready": True}
    st.session_state.yesterday_result_storage_state = state
    return state


def render_pending_remember_cookie_command():
    """Write/delete the first-party remembered-device cookie in the browser."""
    command = st.session_state.get("remember_cookie_command")
    if not command:
        return
    name_js = json.dumps(REMEMBER_COOKIE_NAME)
    if command.get("action") == "set":
        token_js = json.dumps(str(command.get("token") or ""))
        script = f"""
        <script>
        (function() {{
          const name = {name_js};
          const token = {token_js};
          document.cookie = `${{name}}=${{token}}; Path=/; Max-Age={REMEMBER_COOKIE_MAX_AGE}; SameSite=Lax; Secure`;
        }})();
        </script>
        """
    else:
        script = f"""
        <script>
        (function() {{
          const name = {name_js};
          document.cookie = `${{name}}=; Path=/; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax; Secure`;
        }})();
        </script>
        """
    st.html(script, unsafe_allow_javascript=True)
    st.session_state.remember_cookie_command = None


def _restore_remembered_player(storage_state: dict | None = None):
    """Restore a player from localStorage first, with the old cookie as a fallback."""
    if st.session_state.get("active_player_id") or st.session_state.get("remember_restore_checked"):
        return
    storage_state = storage_state or {}
    cookie_token = _browser_remember_cookie()
    storage_token = str(storage_state.get("token") or "").strip()
    storage_ready = bool(storage_state.get("ready"))

    # A Components-v2 localStorage read arrives on the next rerun. Do not mark
    # restore complete until that browser read has finished, unless the legacy
    # first-party cookie already gives us a token immediately.
    if not cookie_token and not storage_ready:
        return

    st.session_state.remember_restore_checked = True
    token = storage_token or cookie_token
    if not token:
        return
    try:
        player = load_daily_store().authenticate_device_session(token)
    except Exception as exc:
        if database_check_enabled():
            st.caption(f"Remembered-login detail: {type(exc).__name__}: {exc}")
        return
    if player is None:
        _queue_remember_cookie_delete()
        return
    _activate_player(player, created=False)
    st.session_state.active_device_token = token


def _remember_this_device(player_id: str) -> bool:
    """Create a revocable browser login after a successful PIN authentication."""
    try:
        token = load_daily_store().create_device_session(str(player_id), REMEMBER_DEVICE_DAYS)
    except Exception as exc:
        st.session_state.player_auth_flash = "Signed in, but this device could not be remembered yet."
        if database_check_enabled():
            st.session_state.player_auth_flash += f" ({type(exc).__name__}: {exc})"
        return False
    st.session_state.active_device_token = token
    _queue_remember_cookie_set(token)
    return True


def _activate_player(player, *, created: bool = False):
    """Switch the active v43B player without carrying another player's Daily state."""
    previous_id = st.session_state.get("active_player_id")
    if previous_id != player.player_id:
        _reset_daily_local_attempt(current_daily_date_key())
        st.session_state.active_group_id = None
        st.session_state.group_flash = ""
        st.session_state.pop("friend_group_selector", None)
        st.session_state.yesterday_result_seen_command = None
        st.session_state.yesterday_result_storage_state = {"value": "", "ready": False}
        st.session_state.yesterday_balloons_date = None
    st.session_state.active_player_id = player.player_id
    st.session_state.active_player_name = player.display_name
    st.session_state.daily_display_name = player.display_name
    st.session_state.player_auth_flash = ""


def _sign_out_player():
    token = st.session_state.get("active_device_token") or _browser_remember_cookie()
    if token:
        try:
            load_daily_store().revoke_device_session(token)
        except Exception:
            pass
    _queue_remember_cookie_delete()
    # Prevent the still-visible cookie snapshot from immediately restoring on the sign-out rerun.
    st.session_state.remember_restore_checked = True
    st.session_state.active_device_token = None
    st.session_state.active_player_id = None
    st.session_state.active_player_name = None
    st.session_state.player_auth_flash = ""
    st.session_state.active_group_id = None
    st.session_state.group_flash = ""
    st.session_state.pop("friend_group_selector", None)
    st.session_state.yesterday_result_seen_command = None
    st.session_state.yesterday_result_storage_state = {"value": "", "ready": False}
    st.session_state.yesterday_balloons_date = None
    _reset_daily_local_attempt(current_daily_date_key())
    st.session_state.daily_display_name = "You"


def _query_param_value(name: str) -> str:
    try:
        value = st.query_params.get(name, "")
    except Exception:
        return ""
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip()


def _pending_invite_code() -> str:
    return re.sub(r"\s+", "", _query_param_value("invite")).upper()[:12]


def _clear_pending_invite():
    try:
        if "invite" in st.query_params:
            del st.query_params["invite"]
    except Exception:
        pass


def _group_invite_url(join_code: str) -> str:
    code = re.sub(r"\s+", "", str(join_code or "")).upper()
    return f"{PUBLIC_APP_URL}?invite={code}"


def process_pending_group_invite() -> bool:
    """Auto-join a group after a player arrives through an invite link and signs in."""
    code = _pending_invite_code()
    if not code or not st.session_state.get("active_player_id"):
        return False
    try:
        group = load_daily_store().join_group(st.session_state.active_player_id, code)
    except GroupNotFound:
        st.session_state.group_flash = "That invite link is no longer valid."
        _clear_pending_invite()
        return False
    except Exception as exc:
        st.warning("Your player is signed in, but the group invite could not be joined yet. Try the invite link again.")
        if database_check_enabled():
            st.caption(f"Invite join detail: {type(exc).__name__}: {exc}")
        return False
    _clear_social_caches()
    st.session_state.active_group_id = group.group_id
    st.session_state.group_flash = f"Joined {group.group_name} from the invite link."
    st.session_state.app_mode = "Daily Challenge"
    _clear_pending_invite()
    return True


def render_group_invite_controls(group):
    """Share/copy a one-tap URL that queues this group before player sign-up/sign-in."""
    invite_url = _group_invite_url(group.join_code)
    url_js = json.dumps(invite_url)
    title_js = json.dumps(f"Join {group.group_name} in Yahtzee Coach")
    components.html(
        f"""
        <div style="display:flex;gap:8px;font-family:Arial,sans-serif;margin:2px 0 4px 0;">
          <button id="shareInvite" style="flex:1;border:1px solid #2563eb;background:#2563eb;color:white;border-radius:9px;padding:9px 10px;font-weight:700;cursor:pointer;">📤 Share invite</button>
          <button id="copyInvite" style="flex:1;border:1px solid #cbd5e1;background:white;color:#0f172a;border-radius:9px;padding:9px 10px;font-weight:700;cursor:pointer;">🔗 Copy invite link</button>
        </div>
        <div id="inviteStatus" style="font-family:Arial,sans-serif;font-size:12px;color:#64748b;text-align:center;height:16px;"></div>
        <script>
          const inviteUrl = {url_js};
          const inviteTitle = {title_js};
          const status = document.getElementById('inviteStatus');
          async function copyInvite() {{
            try {{
              await window.parent.navigator.clipboard.writeText(inviteUrl);
              status.textContent = 'Invite link copied.';
            }} catch (e) {{
              try {{
                await navigator.clipboard.writeText(inviteUrl);
                status.textContent = 'Invite link copied.';
              }} catch (e2) {{
                status.textContent = 'Copy was blocked — use the invite code shown above.';
              }}
            }}
          }}
          document.getElementById('copyInvite').addEventListener('click', copyInvite);
          document.getElementById('shareInvite').addEventListener('click', async () => {{
            const nav = window.parent.navigator || navigator;
            if (nav.share) {{
              try {{
                await nav.share({{title: inviteTitle, text: 'Join my Yahtzee Coach friend group!', url: inviteUrl}});
                status.textContent = 'Invite ready to share.';
                return;
              }} catch (e) {{ if (e && e.name === 'AbortError') return; }}
            }}
            await copyInvite();
          }});
        </script>
        """,
        height=64,
    )


def install_app_shell_metadata():
    """Add Home Screen metadata using real public image URLs instead of temporary data/blob icons."""
    apple_icon_url = f"{PUBLIC_ASSET_BASE}apple_touch_icon.png"
    icon192_url = f"{PUBLIC_ASSET_BASE}home_icon_192.png"
    icon512_url = f"{PUBLIC_ASSET_BASE}home_icon_512.png"
    manifest = {
        "name": "Yahtzee Coach",
        "short_name": "Yahtzee Coach",
        "description": "Daily Yahtzee decision coach with exact strategy, friend groups, and leaderboards.",
        "start_url": PUBLIC_APP_URL,
        "display": "standalone",
        "background_color": "#061b14",
        "theme_color": "#0b3b2e",
        "icons": [
            {"src": icon192_url, "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": icon512_url, "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    html_block = """
        <script>
        (function() {
          const head = document.head;
          function ensureLink(rel, href) {
            let el = head.querySelector(`link[rel="${rel}"]`);
            if (!el) {
              el = document.createElement('link');
              el.setAttribute('rel', rel);
              head.appendChild(el);
            }
            el.setAttribute('href', href);
            return el;
          }
          function ensureMeta(name, content) {
            let el = head.querySelector(`meta[name="${name}"]`);
            if (!el) {
              el = document.createElement('meta');
              el.setAttribute('name', name);
              head.appendChild(el);
            }
            el.setAttribute('content', content);
          }
          let manifestUrl = window.__ycManifestUrl;
          if (!manifestUrl) {
            const blob = new Blob([__MANIFEST__], {type: 'application/manifest+json'});
            manifestUrl = URL.createObjectURL(blob);
            window.__ycManifestUrl = manifestUrl;
          }
          ensureLink('manifest', manifestUrl);
          ensureLink('apple-touch-icon', __APPLE_ICON__);
          ensureLink('icon', __ICON_192__);
          ensureMeta('apple-mobile-web-app-capable', 'yes');
          ensureMeta('mobile-web-app-capable', 'yes');
          ensureMeta('apple-mobile-web-app-title', 'Yahtzee Coach');
          ensureMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');
          ensureMeta('theme-color', '#0b3b2e');
        })();
        </script>
        """
    html_block = html_block.replace("__MANIFEST__", json.dumps(json.dumps(manifest)))
    html_block = html_block.replace("__APPLE_ICON__", json.dumps(apple_icon_url))
    html_block = html_block.replace("__ICON_192__", json.dumps(icon192_url))
    st.html(html_block, unsafe_allow_javascript=True)


def render_install_mode():
    """Render a reliable third-mode Home Screen guide using native Streamlit controls."""
    st.markdown("## 📲 Add Yahtzee Coach to your Home Screen")
    left, center, right = st.columns([1, 1.1, 1])
    with center:
        st.image(str(APP_ICON_512_PATH), width=170)

    st.markdown(
        "Save **Yahtzee Coach** to your phone or computer for quick access with the custom teacher-die icon. "
        "The final Add/Install action is controlled by your browser, so this page gives the exact route instead of showing a button that may do nothing."
    )

    ios_tab, android_tab, computer_tab = st.tabs(["🍎 iPhone / iPad", "🤖 Android", "💻 Computer"])

    with ios_tab:
        st.markdown("""
**Safari**  
1. Tap the **Share** button.  
2. Scroll down and tap **Add to Home Screen**.  
3. Leave **Open as Web App** on if it appears.  
4. Tap **Add**.
""")
        st.caption("Apple requires those final system taps; the website cannot press Add to Home Screen automatically.")

    with android_tab:
        st.markdown("""
**Chrome**  
1. Tap the **⋮** browser menu.  
2. Tap **Add to Home screen** or **Install app**.  
3. Confirm the install.
""")
        st.caption("Chrome may also show its own install option when it considers the site installable.")

    with computer_tab:
        st.markdown("""
**Chrome / Edge**  
Use the browser's install option in the address bar or menu. In Chrome, look under **⋮ → Cast, save, and share → Install page as app**.

**Safari on Mac**  
Choose **File → Add to Dock**.
""")

    st.divider()
    st.caption("Direct app link")
    st.code(PUBLIC_APP_URL, language=None)

def _daily_puzzle_ids():
    return [str(challenge.get("challenge_id", "")) for challenge in st.session_state.daily_challenges]


def _hold_values_from_exact_label(label: str) -> list[int]:
    """Convert exact-mode labels such as 'keep 2, 2, 5' back to die values."""
    text = str(label or "").strip().lower()
    if not text or "reroll" in text:
        return []
    return [int(value) for value in re.findall(r"\b[1-6]\b", text)]


def _register_today_in_database(store):
    challenges = st.session_state.daily_challenges
    version = (
        str(challenges[0].get("daily_version"))
        if challenges
        else DAILY_CHALLENGE_VERSION
    )
    return store.ensure_challenge(
        st.session_state.daily_set_id,
        st.session_state.daily_date_key,
        version,
        _daily_puzzle_ids(),
    )


def _rebuild_persisted_daily_answer(challenge, answer_record):
    """Recreate the rich local review object from the immutable compact DB answer."""
    if str(challenge.get("challenge_id", "")) != str(answer_record.puzzle_id):
        raise ChallengeMismatch("Saved Daily answer does not match today's puzzle order.")
    selected_hold = list(answer_record.chosen_hold)
    report, solver_record = build_live_report(
        challenge["dice"],
        challenge["scorecard"],
        selected_hold,
        challenge["roll_number"],
    )
    if solver_record.get("source") != "exact":
        raise InvalidOfficialAnswer("The exact solver is required to restore an official Daily answer.")
    rebuilt_loss = float(solver_record.get("points_lost", 0.0) or 0.0)
    if abs(rebuilt_loss - float(answer_record.points_lost)) > 1e-6:
        raise ChallengeMismatch("Saved Daily score does not match the locked exact policy.")
    return _daily_solver_record(challenge, solver_record, selected_hold, report)


def _apply_daily_resume_state(resume_state, *, resumed_message: bool = False):
    challenges = st.session_state.daily_challenges
    answers = list(resume_state.answers)
    if len(answers) > len(challenges):
        raise ChallengeMismatch("Saved Daily attempt has too many answers.")
    rebuilt = [
        _rebuild_persisted_daily_answer(challenges[index], answer_record)
        for index, answer_record in enumerate(answers)
    ]
    st.session_state.daily_attempt_id = resume_state.attempt.attempt_id
    st.session_state.daily_started = True
    st.session_state.daily_answers = rebuilt
    st.session_state.daily_completed = bool(resume_state.attempt.complete)
    st.session_state.daily_ready_to_submit = bool(not resume_state.attempt.complete and len(rebuilt) >= len(challenges))
    st.session_state.daily_question_index = (len(challenges) - 1 if st.session_state.daily_ready_to_submit else len(rebuilt))
    st.session_state.daily_display_name = st.session_state.get("active_player_name") or "Player"
    if resumed_message and 0 < len(rebuilt) < len(challenges):
        st.session_state.daily_flash = f"Welcome back — {len(rebuilt)} choice{'s' if len(rebuilt) != 1 else ''} restored."
    elif resumed_message and st.session_state.daily_ready_to_submit:
        st.session_state.daily_flash = "All 10 choices are ready to review."


def _daily_sync_key():
    return f"{st.session_state.get('active_player_id')}|{st.session_state.daily_set_id}"


def _force_daily_resync():
    st.session_state.daily_persistence_sync_key = None


def sync_daily_attempt_from_database(*, force: bool = False) -> bool:
    """Load today's existing attempt once per player/session, including refresh/device resume."""
    if not st.session_state.get("active_player_id"):
        return False
    sync_key = _daily_sync_key()
    if not force and st.session_state.get("daily_persistence_sync_key") == sync_key:
        return True
    try:
        store = load_daily_store()
        _register_today_in_database(store)
        resume_state = store.get_resume_state(
            st.session_state.active_player_id,
            st.session_state.daily_set_id,
        )
        if resume_state is not None:
            _apply_daily_resume_state(resume_state, resumed_message=True)
        else:
            st.session_state.daily_started = False
            st.session_state.daily_completed = False
            st.session_state.daily_ready_to_submit = False
            st.session_state.daily_question_index = 0
            st.session_state.daily_answers = []
            st.session_state.daily_attempt_id = None
        st.session_state.daily_persistence_sync_key = sync_key
        return True
    except Exception as exc:
        st.error("Today's Daily Challenge couldn't be loaded right now. Please try again.")
        if database_check_enabled():
            st.caption(f"Daily persistence detail: {type(exc).__name__}: {exc}")
        return False


def start_persistent_daily_attempt() -> bool:
    """Create the single official attempt, or restore it if another request already created it."""
    try:
        store = load_daily_store()
        _register_today_in_database(store)
        attempt, created = store.get_or_create_attempt(
            st.session_state.active_player_id,
            st.session_state.daily_set_id,
        )
        resume_state = store.get_resume_state(
            st.session_state.active_player_id,
            st.session_state.daily_set_id,
        )
        if resume_state is None:
            raise DailyStoreError("The Daily attempt could not be reloaded after creation.")
        _apply_daily_resume_state(resume_state, resumed_message=not created)
        st.session_state.daily_persistence_sync_key = _daily_sync_key()
        if created:
            st.session_state.daily_flash = ""
        return True
    except Exception as exc:
        st.error("Today's Daily couldn't be started right now. Please try again.")
        if database_check_enabled():
            st.caption(f"Daily start detail: {type(exc).__name__}: {exc}")
        return False


def _set_app_mode(mode: str):
    """Widget callback: switch the top navigation safely before the next rerun renders it."""
    st.session_state.app_mode = mode


def render_player_identity_gate():
    """Create or restore the player used for Daily Challenge."""
    st.markdown(
        "<div class='daily-hero'>"
        "<div class='daily-kicker'>👋 Welcome to Yahtzee Coach</div>"
        "<div class='daily-title'>Play today's Daily Challenge</div>"
        "<div class='daily-rule'>Sign in to save your Daily results and compete with friends.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    invite_code = _pending_invite_code()
    if invite_code:
        st.success("🎟️ You were invited to a friend group. Sign in or create a player and we'll join you automatically.")

    return_tab, create_tab = st.tabs(["Returning Player", "Create Player"])

    with return_tab:
        with st.form("returning_player_form", clear_on_submit=True):
            return_name = st.text_input(
                "Display name",
                max_chars=24,
                key="returning_player_name",
                autocomplete="username",
            )
            return_pin = st.text_input(
                "PIN",
                type="password",
                max_chars=12,
                key="returning_player_pin",
                autocomplete="current-password",
            )
            return_remember = st.checkbox(
                "Keep me signed in on this device for 30 days",
                value=True,
                key="returning_player_remember",
                help="Use this only on a device you trust. Your PIN is never stored in the browser.",
            )
            return_submitted = st.form_submit_button(
                "Sign in", type="primary", use_container_width=True
            )
        st.caption("Your PIN is private.")
        with st.expander("Forgot your PIN?", expanded=False):
            st.write("PIN recovery isn't available during this beta yet. If you get locked out, contact Mike or the person who invited you so we can help.")
            st.caption("Never send anyone your PIN — just share your display name when asking for help.")
        if return_submitted:
            try:
                player = load_daily_store().authenticate_player(return_name, return_pin)
            except Exception:
                st.error("Sign-in isn't available right now. Please try again.")
            else:
                if player is None:
                    st.error("Display name or PIN did not match.")
                else:
                    _activate_player(player, created=False)
                    if return_remember:
                        _remember_this_device(player.player_id)
                    st.rerun()

    with create_tab:
        with st.form("create_player_form", clear_on_submit=True):
            new_name = st.text_input(
                "Display name",
                max_chars=24,
                placeholder="2-24 characters",
                key="create_player_name",
                autocomplete="username",
            )
            new_pin = st.text_input(
                "Choose a PIN",
                type="password",
                max_chars=12,
                placeholder="4-12 digits",
                key="create_player_pin",
                autocomplete="new-password",
            )
            confirm_pin = st.text_input(
                "Confirm PIN",
                type="password",
                max_chars=12,
                key="create_player_pin_confirm",
                autocomplete="new-password",
            )
            create_remember = st.checkbox(
                "Keep me signed in on this device for 30 days",
                value=True,
                key="create_player_remember",
                help="Use this only on a device you trust. Your PIN is never stored in the browser.",
            )
            create_submitted = st.form_submit_button(
                "Create player", type="primary", use_container_width=True
            )
        st.caption("Your display name is visible to friends. Your PIN is private.")
        if create_submitted:
            if new_pin != confirm_pin:
                st.error("Those PINs do not match.")
            else:
                try:
                    player = load_daily_store().create_player(new_name, new_pin)
                except PlayerNameTaken:
                    st.error("That display name is already in use. Try another name or use Returning Player.")
                except InvalidPin as exc:
                    st.error(str(exc))
                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("Player creation isn't available right now. Please try again.")
                else:
                    _activate_player(player, created=True)
                    if create_remember:
                        _remember_this_device(player.player_id)
                    st.rerun()

    st.button(
        "Open Practice without signing in",
        use_container_width=True,
        key="identity_to_practice",
        on_click=_set_app_mode,
        args=("Practice",),
    )


def render_player_status_bar():
    flash = st.session_state.get("player_auth_flash", "")
    if flash:
        st.info(flash)
        st.session_state.player_auth_flash = ""
    name = st.session_state.get("active_player_name") or "Player"
    left, right = st.columns([5, 1])
    with left:
        st.caption(f"👤 **{name}**")
    with right:
        if st.button("Sign out", use_container_width=True, key="player_sign_out"):
            _sign_out_player()
            st.rerun()




def _select_active_group(groups):
    """Keep a stable selected group for this signed-in player."""
    if not groups:
        st.session_state.active_group_id = None
        return None
    group_by_id = {group.group_id: group for group in groups}
    if st.session_state.get("active_group_id") not in group_by_id:
        st.session_state.active_group_id = groups[0].group_id
    return group_by_id.get(st.session_state.active_group_id)


def _load_player_groups():
    if not st.session_state.get("active_player_id"):
        return []
    try:
        return _cached_player_groups(st.session_state.active_player_id)
    except Exception as exc:
        st.warning("Your friend groups could not be loaded right now. Your Daily attempt is unaffected.")
        if database_check_enabled():
            st.caption(f"Group load detail: {type(exc).__name__}: {exc}")
        return []


def render_group_selector(groups, *, key="friend_group_selector"):
    """Let players switch which group's standings they are viewing."""
    active = _select_active_group(groups)
    if not groups:
        return None
    if len(groups) == 1:
        st.session_state.active_group_id = groups[0].group_id
        return groups[0]
    ids = [group.group_id for group in groups]
    labels = {group.group_id: group.group_name for group in groups}
    chosen_id = st.selectbox(
        "Friend group",
        options=ids,
        index=ids.index(active.group_id) if active else 0,
        format_func=lambda group_id: labels[group_id],
        key=key,
    )
    if chosen_id != st.session_state.get("active_group_id"):
        st.session_state.active_group_id = chosen_id
    return next(group for group in groups if group.group_id == chosen_id)


def render_friend_group_hub(*, expanded: bool = False):
    """Keep friend-group administration secondary to the Daily experience."""
    groups = _load_player_groups()
    active = _select_active_group(groups)

    with st.expander("👥 Invite & manage friends", expanded=expanded or not groups):
        if groups:
            active = render_group_selector(groups, key="friend_group_manage_selector")
            try:
                members = _cached_group_members(active.group_id)
            except Exception:
                members = []
            member_count = len(members)
            st.markdown(
                f"**{html.escape(active.group_name)}** · {member_count} member{'s' if member_count != 1 else ''}"
            )
            st.caption(f"Invite code: **{active.join_code}**")
            render_group_invite_controls(active)
            with st.expander("Show invite link", expanded=False):
                st.code(_group_invite_url(active.join_code), language=None)
            if members:
                with st.expander("Group members", expanded=False):
                    st.write(" · ".join(member["display_name"] for member in members))
        else:
            st.markdown("**Play the Daily with friends.** Create a group or join one with an invite code.")

        st.markdown("#### Create or join a group")
        create_tab, join_tab = st.tabs(["Create group", "Join with code"])
        with create_tab:
            with st.form("create_friend_group_form", clear_on_submit=True):
                group_name = st.text_input(
                    "Group name",
                    max_chars=40,
                    placeholder="Example: Sunday Rollers",
                    key="create_friend_group_name",
                )
                create_group_submitted = st.form_submit_button(
                    "Create friend group", type="primary", use_container_width=True
                )
            if create_group_submitted:
                try:
                    group = load_daily_store().create_group(
                        st.session_state.active_player_id,
                        group_name,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error("The friend group could not be created. Please try again.")
                    if database_check_enabled():
                        st.caption(f"Group create detail: {type(exc).__name__}: {exc}")
                else:
                    _clear_social_caches()
                    st.session_state.active_group_id = group.group_id
                    st.session_state.group_flash = f"{group.group_name} created. Invite code: {group.join_code}"
                    st.rerun()

        with join_tab:
            with st.form("join_friend_group_form", clear_on_submit=True):
                join_code = st.text_input(
                    "Invite code",
                    max_chars=12,
                    placeholder="Example: TEAL42",
                    key="join_friend_group_code",
                )
                join_group_submitted = st.form_submit_button(
                    "Join friend group", type="primary", use_container_width=True
                )
            if join_group_submitted:
                try:
                    group = load_daily_store().join_group(
                        st.session_state.active_player_id,
                        join_code,
                    )
                except GroupNotFound:
                    st.error("No friend group matched that invite code.")
                except Exception as exc:
                    st.error("The friend group could not be joined. Please try again.")
                    if database_check_enabled():
                        st.caption(f"Group join detail: {type(exc).__name__}: {exc}")
                else:
                    _clear_social_caches()
                    st.session_state.active_group_id = group.group_id
                    st.session_state.group_flash = f"Joined {group.group_name}."
                    st.rerun()

    flash = st.session_state.get("group_flash", "")
    if flash:
        st.success(flash)
        st.session_state.group_flash = ""
    return active


def _real_group_context():
    """Return active group and one batched social snapshot for today's Daily."""
    groups = _load_player_groups()
    active = _select_active_group(groups)
    if active is None:
        return None, [], [], []
    snapshot = _cached_group_daily_snapshot(active.group_id, st.session_state.daily_set_id)
    members = list(snapshot.get("members", []))
    board = [dict(row) for row in snapshot.get("leaderboard", [])]
    for row in board:
        row["is_user"] = row.get("player_id") == st.session_state.get("active_player_id")
    stats = list(snapshot.get("question_stats", []))
    return active, members, board, stats


def _user_real_rank(board):
    for row in board:
        if row.get("is_user"):
            return int(row.get("rank", 0)) or None
    return None


def _rank_is_tied(board, rank) -> bool:
    if rank is None:
        return False
    try:
        target = int(rank)
    except Exception:
        return False
    return sum(1 for row in board if int(row.get("rank") or 0) == target) > 1


def _story_from_group_stats(stats):
    if not stats:
        return {"toughest": None, "easiest": None}
    toughest = min(stats, key=lambda row: (row["exact_rate"], -row["avg_loss"], row["question_number"]))
    easiest = max(stats, key=lambda row: (row["exact_rate"], -row["avg_loss"], -row["question_number"]))
    return {"toughest": toughest, "easiest": easiest}

def _daily_date_label(date_key: str) -> str:
    try:
        value = datetime.strptime(date_key, "%Y-%m-%d")
        return value.strftime("%B %d, %Y").replace(" 0", " ")
    except Exception:
        return date_key


def render_daily_progress(index: int, saved: int, *, complete: bool = False):
    dots = []
    for i in range(10):
        if complete:
            css = "done"
        elif i == index:
            css = "current"
        elif i < saved:
            css = "done"
        else:
            css = ""
        dots.append(f"<div class='daily-dot {css}' title='Question {i + 1}'></div>")
    question_text = "Challenge complete" if complete else ("Review your 10" if saved >= 10 else f"Question {index + 1} of 10")
    status_text = "Finished" if complete else f"{saved} saved"
    st.markdown(
        "<div class='daily-progress-copy'>"
        f"<b>{question_text}</b><span>{status_text}</span>"
        "</div><div class='daily-progress'>" + "".join(dots) + "</div>",
        unsafe_allow_html=True,
    )


def _daily_solver_record(challenge, solver_record, selected_hold, report):
    record = dict(solver_record)
    record["scenario"] = challenge.get("scenario_name", "")
    record["bank_version"] = challenge.get("bank_version", "")
    record["daily_version"] = challenge.get("daily_version", DAILY_CHALLENGE_VERSION)
    record["skill_tag"] = challenge.get("skill_tag", "")
    record["difficulty"] = challenge.get("difficulty", "")
    record["stage"] = challenge.get("stage", "")
    record["bonus_status"] = challenge.get("bonus_status", "")
    record["challenge_id"] = challenge.get("challenge_id", "")
    record["daily_number"] = challenge.get("daily_number")
    record["timestamp_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "challenge": challenge,
        "solver_record": record,
        "selected_hold": list(selected_hold),
        "report": report,
    }


def _participation_streak() -> int:
    if not st.session_state.get("active_player_id"):
        return 0
    try:
        return int(_cached_participation_streak(
            st.session_state.active_player_id,
            st.session_state.daily_date_key,
        ))
    except Exception as exc:
        if database_check_enabled():
            st.caption(f"Streak detail: {type(exc).__name__}: {exc}")
        return 0


def _daily_streak_copy(streak: int, *, completed_today: bool) -> str:
    streak = max(0, int(streak or 0))
    if streak <= 0:
        return ""
    if completed_today and streak == 1:
        return "🔥 First Daily complete — your streak has started!"
    suffix = "day" if streak == 1 else "days"
    if completed_today:
        return f"🔥 {streak}-{suffix} Daily streak"
    return f"🔥 {streak}-{suffix} streak alive — finish today's Daily to keep it going"



def _previous_daily_date_key(date_key: str) -> str:
    """Return the prior calendar day for the shared Eastern Daily clock."""
    current = datetime.strptime(str(date_key), "%Y-%m-%d").date()
    return (current - timedelta(days=1)).isoformat()


def _challenge_set_id_for_date(date_key: str) -> str:
    challenges = get_daily_challenges(str(date_key))
    return challenge_set_id(str(date_key), challenges)


def _find_player_rank(board) -> int | None:
    player_id = str(st.session_state.get("active_player_id") or "")
    for row in board:
        if str(row.get("player_id") or "") == player_id:
            try:
                return int(row.get("rank") or 0) or None
            except Exception:
                return None
    return None


def _start_today_from_yesterday_recap():
    st.session_state.daily_display_name = st.session_state.get("active_player_name") or "Player"
    if start_persistent_daily_attempt():
        _queue_yesterday_result_seen(st.session_state.daily_date_key)
        st.rerun()


def render_yesterday_final_standings_if_needed() -> bool:
    """Show yesterday's final group standings once before an unstarted new Daily.

    Returns True when the recap (or its browser-storage loading state) owns the
    screen, so the normal Daily intro should not render underneath it.
    """
    today = st.session_state.daily_date_key
    storage_state = st.session_state.get("yesterday_result_storage_state") or {}
    if str(storage_state.get("value") or "") == today:
        return False

    groups = _load_player_groups()
    if not groups:
        return False

    yesterday = _previous_daily_date_key(today)
    yesterday_set_id = _challenge_set_id_for_date(yesterday)
    snapshots = {}
    eligible_groups = []
    for group in groups:
        try:
            snapshot = _cached_group_daily_snapshot(group.group_id, yesterday_set_id)
        except Exception:
            continue
        snapshots[group.group_id] = snapshot
        if snapshot.get("leaderboard"):
            eligible_groups.append(group)

    if not eligible_groups:
        return False

    if not bool(storage_state.get("ready")):
        st.caption("Loading yesterday's final standings…")
        return True

    active = render_group_selector(eligible_groups, key="yesterday_final_group_selector")
    snapshot = snapshots.get(active.group_id) or {}
    board = [dict(row) for row in snapshot.get("leaderboard", [])]
    members = list(snapshot.get("members", []))
    if not board:
        return False

    rank = _find_player_rank(board)
    rank_tied = _rank_is_tied(board, rank)
    medals = {1: ("🥇", "GOLD", "1st"), 2: ("🥈", "SILVER", "2nd"), 3: ("🥉", "BRONZE", "3rd")}
    podium = rank in medals and len(members) > 1

    st.markdown(
        "<div class='daily-hero'>"
        "<div class='daily-kicker'>🏆 Yesterday's Final Standings</div>"
        f"<div class='daily-title'>{_daily_date_label(yesterday)}</div>"
        f"<div class='daily-rule'><b>{html.escape(active.group_name)}</b> is final. See where everyone landed before today's 10 begin.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    if podium:
        medal, medal_name, place = medals[rank]
        if st.session_state.get("yesterday_balloons_date") != today:
            st.balloons()
            st.session_state.yesterday_balloons_date = today
        podium_result = f"You tied for {place} yesterday!" if rank_tied else f"You finished {place} yesterday!"
        st.markdown(
            "<div class='yesterday-podium'>"
            f"<div class='medal'>{medal}</div>"
            f"<div class='title'>{medal_name}! {podium_result}</div>"
            f"<div class='copy'>Nice run, {html.escape(st.session_state.get('active_player_name') or 'Player')}. Your medal is locked in.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    elif rank is not None:
        yesterday_result = f"You tied for #{rank} of {len(board)} yesterday." if rank_tied else f"You finished #{rank} of {len(board)} yesterday."
        st.markdown(
            f"<div class='yesterday-final-note'><b>{yesterday_result}</b><br>Here's the final board.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='yesterday-final-note'><b>You didn't record a finish yesterday.</b><br>You can still see how your group finished before starting today's challenge.</div>",
            unsafe_allow_html=True,
        )

    render_leaderboard_cards(board, allow_review=False)
    if st.button(
        "🎲 Start today's Daily Challenge",
        type="primary",
        use_container_width=True,
        key="yesterday_final_start_today",
    ):
        _start_today_from_yesterday_recap()
    return True


def render_daily_intro():
    date_key = st.session_state.daily_date_key
    st.markdown(
        "<div class='daily-hero'>"
        "<div class='daily-kicker'>🎲 Daily Challenge</div>"
        f"<div class='daily-title'>{_daily_date_label(date_key)}</div>"
        "<div class='daily-rule'><b>10 hold decisions. Same challenge for everyone.</b><br>"
        "Try to make the best hold on each puzzle. Lower <b>Points Lost</b> is better. You can review your choices before you submit, and coaching unlocks when you finish.<br>"
        "<span style='font-size:.80rem'>5 Roll 1 · 5 Roll 2 · new challenge at midnight Eastern</span></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    streak = _participation_streak()
    streak_copy = _daily_streak_copy(streak, completed_today=False)
    if streak_copy:
        st.caption(streak_copy)

    groups = _load_player_groups()
    if groups:
        active = render_group_selector(groups, key="daily_intro_group_selector")
        try:
            snapshot = _cached_group_daily_snapshot(active.group_id, st.session_state.daily_set_id)
            member_count = len(snapshot.get("members", []))
            finished_count = len(snapshot.get("leaderboard", []))
        except Exception:
            member_count = 0
            finished_count = 0
        group_line = f"👥 Competing in **{active.group_name}**"
        if member_count:
            group_line += f" · {member_count} member{'s' if member_count != 1 else ''}"
        if member_count > 1:
            if finished_count == 0:
                group_line += " · nobody has finished yet"
            elif finished_count < member_count:
                group_line += f" · {finished_count} finished"
            else:
                group_line += " · everyone has finished"
        st.caption(group_line)

    if st.button("Start today's Daily Challenge", type="primary", use_container_width=True):
        st.session_state.daily_display_name = st.session_state.get("active_player_name") or "Player"
        if start_persistent_daily_attempt():
            st.rerun()

    st.button(
        "Open Practice",
        use_container_width=True,
        on_click=_set_app_mode,
        args=("Practice",),
    )

    with st.expander("How the Daily Challenge works", expanded=False):
        st.markdown(
            "- **One Daily each day:** everyone gets the same 10 decisions.\n"
            "- **Your choices save automatically:** leave and come back without losing your place.\n"
            "- **Review before submitting:** use Back or the final review to fix accidental taps.\n"
            "- **No hints during the run:** grades, best answers, and coaching appear only after you finish.\n"
            "- **Friends:** completed players appear on your group's leaderboard.\n"
            "- **Reset:** a new challenge begins at midnight Eastern."
        )

    render_friend_group_hub(expanded=not groups)


def _daily_answer_at(index: int):
    answers = st.session_state.get("daily_answers", [])
    return answers[index] if 0 <= index < len(answers) else None


def _daily_widget_keys(index: int) -> tuple[str, str]:
    date_key = st.session_state.daily_date_key
    return (
        f"daily_held_{date_key}_{index}",
        f"daily_dice_pills_{date_key}_{index}",
    )


def _saved_hold_indices(index: int) -> list[int]:
    answer = _daily_answer_at(index)
    if answer is None:
        return []
    dice = st.session_state.daily_challenges[index]["dice"]
    return hold_indices_from_values(dice, answer.get("selected_hold", []))


def _reset_daily_widget_to_saved(index: int):
    """Discard an un-saved UI change when navigating backward."""
    held_key, pills_key = _daily_widget_keys(index)
    if pills_key in st.session_state:
        del st.session_state[pills_key]
    st.session_state[held_key] = _saved_hold_indices(index)


def _save_daily_choice(index: int, selected_hold) -> bool:
    """Save a new answer or revise an existing draft without exposing feedback."""
    challenge = st.session_state.daily_challenges[index]
    dice = challenge["dice"]
    report, solver_record = build_live_report(
        dice,
        challenge["scorecard"],
        selected_hold,
        challenge["roll_number"],
    )
    if solver_record.get("source") != "exact":
        st.error("The exact scorer was unavailable, so this choice was NOT saved. Please try again.")
        return False

    attempt_id = st.session_state.get("daily_attempt_id")
    if not attempt_id:
        st.error("Your saved Daily attempt could not be found, so this choice was NOT saved. Please sign in again.")
        _force_daily_resync()
        return False

    saved_answer = _daily_answer_at(index)
    same_choice = bool(
        saved_answer is not None
        and sorted(int(v) for v in saved_answer.get("selected_hold", []))
        == sorted(int(v) for v in selected_hold)
    )

    try:
        if saved_answer is None:
            load_daily_store().save_answer(
                attempt_id,
                question_number=index + 1,
                puzzle_id=str(challenge.get("challenge_id", "")),
                chosen_hold=selected_hold,
                optimal_hold=_hold_values_from_exact_label(solver_record.get("optimal_hold", "")),
                points_lost=float(solver_record.get("points_lost", 0.0) or 0.0),
                solver_source="exact",
            )
        elif not same_choice:
            load_daily_store().revise_answer(
                attempt_id,
                question_number=index + 1,
                puzzle_id=str(challenge.get("challenge_id", "")),
                chosen_hold=selected_hold,
                optimal_hold=_hold_values_from_exact_label(solver_record.get("optimal_hold", "")),
                points_lost=float(solver_record.get("points_lost", 0.0) or 0.0),
                solver_source="exact",
            )
    except (DuplicateAnswer, OutOfOrderAnswer, AttemptAlreadyComplete, ChallengeMismatch):
        _force_daily_resync()
        if sync_daily_attempt_from_database(force=True):
            st.session_state.daily_flash = "Your Daily was refreshed."
            st.rerun()
        return False
    except Exception as exc:
        detail = str(exc).lower()
        if saved_answer is not None and "locked daily answers cannot be changed" in detail:
            st.error("Back/edit needs the one-time Phase 2E Supabase migration. Your existing saved choice was not changed.")
        else:
            st.error("We couldn't save that change. Please try again.")
        if database_check_enabled():
            st.caption(f"Daily save detail: {type(exc).__name__}: {exc}")
        return False

    rich_answer = _daily_solver_record(challenge, solver_record, selected_hold, report)
    if saved_answer is None:
        st.session_state.daily_answers.append(rich_answer)
    else:
        st.session_state.daily_answers[index] = rich_answer

    held_key, _ = _daily_widget_keys(index)
    st.session_state[held_key] = hold_indices_from_values(dice, selected_hold)
    return True


@st.fragment
def _daily_choice_fragment():
    """Only rerun the dice controls when a player taps a die."""
    challenges = st.session_state.daily_challenges
    answers = st.session_state.daily_answers
    index = int(st.session_state.daily_question_index)
    challenge = challenges[index]
    dice = challenge["dice"]

    st.markdown("<div class='practice-question'>Which dice would you keep? <span class='muted'>Tap to select.</span></div>", unsafe_allow_html=True)

    held_key, pills_key = _daily_widget_keys(index)
    if held_key not in st.session_state:
        st.session_state[held_key] = _saved_hold_indices(index)
    selected_indices = st.pills(
        "Daily dice to hold",
        options=list(range(len(dice))),
        default=st.session_state.get(held_key, []),
        format_func=lambda die_index: unique_dice_label(die_index, dice[die_index]),
        selection_mode="multi",
        key=pills_key,
        label_visibility="collapsed",
    )
    selected_indices = list(selected_indices or [])
    st.session_state[held_key] = sorted(selected_indices)
    selected_hold = selected_hold_from_indices(dice, selected_indices)
    st.markdown(f"<div class='selected-summary'>Your hold: {hold_label(selected_hold)}</div>", unsafe_allow_html=True)

    already_saved = index < len(answers)
    all_ten_saved = len(answers) >= 10
    if all_ten_saved:
        primary_label = "Save changes & return to review"
    elif index == len(challenges) - 1:
        primary_label = "Save & review all 10"
    elif already_saved:
        primary_label = "Save changes & next"
    else:
        primary_label = "Save & next"

    back_col, save_col = st.columns([1, 2])
    with back_col:
        back_clicked = st.button(
            "← Back",
            use_container_width=True,
            disabled=index <= 0,
            key=f"daily_back_{index}",
        )
    with save_col:
        save_clicked = st.button(
            primary_label,
            type="primary",
            use_container_width=True,
            key=f"daily_save_{index}",
        )

    if back_clicked:
        _reset_daily_widget_to_saved(index)
        st.session_state.daily_ready_to_submit = False
        st.session_state.daily_question_index = index - 1
        st.rerun()

    if save_clicked:
        if not _save_daily_choice(index, selected_hold):
            return
        if all_ten_saved or index + 1 >= len(challenges):
            st.session_state.daily_ready_to_submit = True
            st.session_state.daily_question_index = len(challenges) - 1
            st.session_state.daily_flash = "Choice saved. Review your 10 before final submission."
        else:
            st.session_state.daily_ready_to_submit = False
            st.session_state.daily_question_index = index + 1
            st.session_state.daily_flash = f"Answer {index + 1} saved."
        # A save changes the whole Daily flow, so intentionally leave the fragment.
        st.rerun()


def render_daily_question():
    challenges = st.session_state.daily_challenges
    answers = st.session_state.daily_answers
    index = int(st.session_state.daily_question_index)
    index = max(0, min(index, len(challenges) - 1))
    st.session_state.daily_question_index = index

    challenge = challenges[index]
    render_daily_progress(index, len(answers))
    flash = st.session_state.get("daily_flash", "")
    if flash:
        st.markdown(f"<div class='daily-flash'>✓ {flash}</div>", unsafe_allow_html=True)
        st.session_state.daily_flash = ""

    roll_number = int(challenge["roll_number"])
    if roll_number == 1:
        roll_stage_class = "roll-1"
        roll_stage_title = "🔵 ROLL 1 · First roll · 2 rerolls left"
        roll_stage_sub = ""
    else:
        roll_stage_class = "roll-2"
        roll_stage_title = "🟢 ROLL 2 · Second roll · 1 reroll left"
        roll_stage_sub = ""
    st.markdown(
        f"<div class='daily-roll-stage {roll_stage_class}'>"
        f"<div class='daily-roll-stage-title'>{roll_stage_title}</div>"
        f"<div class='daily-roll-stage-sub'>{roll_stage_sub}</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    render_scorecard(challenge["scorecard"])

    _daily_choice_fragment()

    st.markdown(
        "<div class='daily-lock-note'>Your choices stay private and editable until you submit. After that, your result is final.</div>",
        unsafe_allow_html=True,
    )

def render_daily_submission_review():
    """Show all 10 chosen holds without feedback, then let the player final-submit."""
    answers = st.session_state.daily_answers
    if len(answers) < 10:
        st.session_state.daily_ready_to_submit = False
        st.session_state.daily_question_index = len(answers)
        st.rerun()
        return

    render_daily_progress(9, 10)
    st.markdown(
        "<div class='daily-hero'>"
        "<div class='daily-kicker'>Final review</div>"
        "<div class='daily-title'>Check your 10 choices</div>"
        "<div class='daily-rule'><b>No grades, Points Lost, or best answers are shown yet.</b><br>"
        "Edit anything you entered by mistake. Once you submit, your result is final.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    review_cards = []
    for i, answer in enumerate(answers, start=1):
        challenge = answer["challenge"]
        dice_faces = " ".join(DICE_FACE.get(int(die), str(die)) for die in challenge.get("dice", []))
        review_cards.append(
            "<div class='daily-review-choice'>"
            f"<div class='daily-review-choice-top'><span>Q{i}</span><span>Roll {challenge.get('roll_number')}</span></div>"
            f"<div class='daily-review-choice-dice'>{dice_faces}</div>"
            f"<div class='daily-review-choice-hold'>Kept: {hold_label(answer.get('selected_hold', []))}</div>"
            "</div>"
        )
    st.markdown("<div class='daily-review-grid'>" + "".join(review_cards) + "</div>", unsafe_allow_html=True)

    edit_question = st.selectbox(
        "Need to fix one?",
        options=list(range(1, 11)),
        format_func=lambda q: f"Question {q}: {hold_label(answers[q - 1].get('selected_hold', []))}",
        key="daily_review_edit_question",
    )
    edit_col, back_col = st.columns(2)
    with edit_col:
        if st.button("✏️ Edit selected question", use_container_width=True, key="daily_review_edit"):
            st.session_state.daily_ready_to_submit = False
            st.session_state.daily_question_index = int(edit_question) - 1
            st.rerun()
    with back_col:
        if st.button("← Back to Question 10", use_container_width=True, key="daily_review_back"):
            st.session_state.daily_ready_to_submit = False
            st.session_state.daily_question_index = 9
            st.rerun()

    st.warning("Submitting ends today's Daily. After this point, your 10 choices cannot be changed.")
    if st.button("🏁 Submit final Daily Challenge", type="primary", use_container_width=True, key="daily_final_submit"):
        attempt_id = st.session_state.get("daily_attempt_id")
        if not attempt_id:
            st.error("Your Daily couldn't be found. Please sign in again before submitting.")
            _force_daily_resync()
            return
        try:
            load_daily_store().complete_attempt(attempt_id)
            _clear_social_caches()
        except Exception as exc:
            st.error("Your Daily couldn't be submitted yet. Your 10 choices are still saved and editable.")
            if database_check_enabled():
                st.caption(f"Daily finalize detail: {type(exc).__name__}: {exc}")
            return
        st.session_state.daily_completed = True
        st.session_state.daily_ready_to_submit = False
        st.session_state.daily_question_index = 10
        _force_daily_resync()
        st.rerun()


def _leaderboard_frame(board):
    """Dataframe form retained for exports/tests; player UI uses cards below."""
    rows = []
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for item in board:
        rank = int(item["rank"])
        name = item["display_name"] + ("  ← you" if item.get("is_user") else "")
        rows.append({
            "Rank": f"{medals.get(rank, '')} {rank}".strip(),
            "Player": name,
            "Points Lost": f"{item['total_ev_loss']:.2f}",
            "Best Holds": f"{item['exact_count']}/10",
        })
    return pd.DataFrame(rows)


def _open_friend_review(player_id: str):
    st.session_state.friend_review_player_id = str(player_id)


def _close_friend_review():
    st.session_state.friend_review_player_id = None


def render_leaderboard_cards(board, *, allow_review=False):
    """Render a clean, scan-friendly leaderboard. Friend review lives below the standings."""
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    active_player_id = str(st.session_state.get("active_player_id") or "")
    rows = []
    for item in board:
        rank = int(item.get("rank") or 0)
        player_id = str(item.get("player_id") or "")
        display_name = str(item.get("display_name") or "Player")
        is_you = player_id == active_player_id
        you_note = " <span>YOU</span>" if is_you else ""
        row_class = "leaderboard-row you" if is_you else "leaderboard-row"
        rows.append(
            f"<div class='{row_class}'>"
            f"<div class='leaderboard-rank'>{medals.get(rank, '')} {rank}</div>"
            f"<div class='leaderboard-name'>{html.escape(display_name)}{you_note}</div>"
            f"<div class='leaderboard-score'><b>{float(item['total_ev_loss']):.2f}</b>"
            f"Points Lost · {int(item['exact_count'])}/10 best</div>"
            "</div>"
        )
    if rows:
        st.markdown("<div class='leaderboard-list'>" + "".join(rows) + "</div>", unsafe_allow_html=True)
    with st.expander("How rankings work", expanded=False):
        st.caption("Lowest displayed Points Lost ranks first. Same score to the hundredth = a real tie. Tied players share the place, so ranks can go 1, 1, 3. Names are only alphabetized inside a tie.")


def _share_square(points_lost: float) -> str:
    """Convert EV loss into a compact spoiler-free result square.

    The share bands intentionally mirror the exact-mode coaching rubric so the
    visual result never looks harsher than the feedback the player receives.
    """
    loss = max(0.0, float(points_lost or 0.0))
    if loss <= 1e-9:
        return "🟩"
    if loss <= 0.25:
        return "🟨"
    if loss <= 1.50:
        return "🟧"
    return "🟥"


def build_daily_share_text(records, summary, rank=None, completed_count=0, rank_tied=False):
    """Build a compact spoiler-free Daily result suitable for text messages/social sharing."""
    squares = [_share_square(item.get("points_lost", 0.0)) for item in records]
    first_row = "".join(squares[:5])
    second_row = "".join(squares[5:10])
    date_label = _daily_date_label(st.session_state.daily_date_key)
    lines = [
        f"🎲 Yahtzee Coach Daily — {date_label}",
        f"{summary['total_ev_loss']:.2f} Points Lost · {summary['exact_count']}/10 best holds",
        first_row,
        second_row,
        f"🔥 Best-hold streak: {summary['best_exact_streak']}",
    ]
    if rank is not None and int(completed_count or 0) > 0:
        if rank_tied:
            lines.append(f"🏆 Group rank right now: Tied for #{int(rank)} of {int(completed_count)}")
        else:
            lines.append(f"🏆 Group rank right now: #{int(rank)} of {int(completed_count)}")
    lines.extend([
        "🟩 best · 🟨 almost best · 🟧 close · 🟥 miss",
        PUBLIC_APP_URL,
    ])
    return "\n".join(lines)


def render_daily_share_result(records, summary, rank=None, completed_count=0, rank_tied=False):
    """Render compact spoiler-free Daily blocks with native share/copy controls."""
    share_text = build_daily_share_text(records, summary, rank=rank, completed_count=completed_count, rank_tied=rank_tied)
    share_text_js = json.dumps(share_text)
    squares = [_share_square(item.get("points_lost", 0.0)) for item in records]
    first_row = "".join(squares[:5])
    second_row = "".join(squares[5:10])
    share_html = f"""
        <div style="font-family:Arial,sans-serif;border:1px solid #d1d5db;border-radius:16px;padding:15px;background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%);box-shadow:0 2px 10px rgba(0,0,0,0.04);">
          <div style="font-size:12px;text-transform:uppercase;letter-spacing:.06em;font-weight:800;color:#64748b;">Your Daily · Spoiler-free</div>
          <div style="font-size:28px;line-height:1.18;letter-spacing:2px;margin:7px 0 1px 0;">{first_row}</div>
          <div style="font-size:28px;line-height:1.18;letter-spacing:2px;">{second_row}</div>
          <div style="font-size:12px;color:#64748b;margin-top:8px;">🟩 best · 🟨 almost best · 🟧 close · 🟥 miss</div>
          <div style="display:flex;gap:10px;margin-top:12px;">
            <button id="shareDaily" style="flex:1;border:1px solid #166534;background:#166534;color:white;border-radius:10px;padding:10px 12px;font-weight:800;cursor:pointer;">📤 Share result</button>
            <button id="copyDaily" style="flex:1;border:1px solid #cbd5e1;background:white;color:#0f172a;border-radius:10px;padding:10px 12px;font-weight:800;cursor:pointer;">📋 Copy score</button>
          </div>
          <div id="shareDailyStatus" style="min-height:18px;margin-top:7px;font-size:12px;color:#64748b;text-align:center;"></div>
        </div>
        <script>
        (function() {{
          const shareText = {share_text_js};
          const status = document.getElementById('shareDailyStatus');
          async function copyScore() {{
            try {{
              if (navigator.clipboard && navigator.clipboard.writeText) {{
                await navigator.clipboard.writeText(shareText);
              }} else {{
                throw new Error('clipboard unavailable');
              }}
              status.textContent = 'Score copied — paste it into a text or group chat!';
              return true;
            }} catch (err) {{
              try {{
                const area = document.createElement('textarea');
                area.value = shareText;
                area.style.position = 'fixed';
                area.style.opacity = '0';
                document.body.appendChild(area);
                area.focus();
                area.select();
                const copied = document.execCommand('copy');
                document.body.removeChild(area);
                if (copied) {{
                  status.textContent = 'Score copied — paste it into a text or group chat!';
                  return true;
                }}
              }} catch (fallbackErr) {{}}
              status.textContent = 'Copy was blocked. Open Preview shared result below to copy it manually.';
              return false;
            }}
          }}
          document.getElementById('copyDaily').addEventListener('click', copyScore);
          document.getElementById('shareDaily').addEventListener('click', async function() {{
            if (navigator.share) {{
              try {{
                await navigator.share({{text: shareText}});
                status.textContent = 'Share sheet opened with your Daily score.';
                return;
              }} catch (err) {{
                if (err && err.name === 'AbortError') return;
              }}
            }}
            await copyScore();
          }});
        }})();
        </script>
    """
    st.html(share_html, unsafe_allow_javascript=True)
    with st.expander("Preview shared result", expanded=False):
        st.code(share_text, language=None)


def _render_daily_review_body(answer, *, subject_name="You"):
    record = answer["solver_record"]
    challenge = answer["challenge"]
    report = answer["report"]
    loss = float(record.get("points_lost", 0.0) or 0.0)
    grade = record.get("grade", "") or extract_line(report, "Grade:")
    lesson = record.get("lesson", "") or record.get("teaching_takeaway", "") or record.get("lesson_title", "")
    st.caption(
        f"{challenge.get('stage', '')} · Roll {challenge.get('roll_number')} · {challenge.get('skill_tag', '')}"
    )
    dice_faces = " ".join(DICE_FACE.get(int(die), str(die)) for die in challenge.get("dice", []))
    st.markdown(f"<div class='daily-dice-line'>{dice_faces}</div>", unsafe_allow_html=True)
    st.markdown("**Scorecard at the decision**")
    st.markdown("<div class='score-section-title'>Upper</div>", unsafe_allow_html=True)
    st.markdown(score_grid_html(challenge["scorecard"], UPPER_CATEGORIES), unsafe_allow_html=True)
    st.markdown("<div class='score-section-title'>Lower</div>", unsafe_allow_html=True)
    st.markdown(score_grid_html(challenge["scorecard"], LOWER_CATEGORIES, lower=True), unsafe_allow_html=True)
    st.markdown(
        "<div class='review-summary'>"
        f"<div class='review-box'><div class='review-label'>{html.escape(str(subject_name))} kept</div><div class='review-value'>{record.get('user_hold', '—')}</div></div>"
        f"<div class='review-box'><div class='review-label'>Best hold</div><div class='review-value'>{record.get('optimal_hold', '—')}</div></div>"
        f"<div class='review-box'><div class='review-label'>Hold rank</div><div class='review-value'>#{record.get('hold_rank', '—')} of {record.get('legal_hold_count', '—')}</div></div>"
        f"<div class='review-box'><div class='review-label'>Points Lost</div><div class='review-value'>{loss:.2f}</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    simple_why_items = extract_section(report, "Simple why:")
    simple_why = simple_why_items[0] if simple_why_items else record.get("simple_why", "")
    if 0.0 < loss <= 0.25:
        st.markdown(
            f"**🤏 Very close:** Your hold was only {loss:.2f} Points Lost from the exact best hold. "
            "This was a fine distinction, not a bad strategy choice."
        )
    if simple_why:
        st.markdown(f"**💡 Why this wins:** {simple_why}")
    if lesson:
        st.markdown(f"**🧠 Remember:** {lesson}")
    idea = record.get("adjustment", "")
    if idea:
        st.markdown(f"**Try this instead:** {idea}")
    top_holds = extract_section(report, "Top exact holds:")
    if top_holds:
        with st.expander("See the top 3 holds", expanded=False):
            st.markdown("".join(f"<div class='top-hold-line'>{line}</div>" for line in top_holds[:3]), unsafe_allow_html=True)


def _daily_review_item(answer):
    """Compatibility wrapper for a single compact review expander."""
    record = answer["solver_record"]
    challenge = answer["challenge"]
    number = int(challenge.get("daily_number") or 0)
    loss = float(record.get("points_lost", 0.0) or 0.0)
    grade = record.get("grade", "") or extract_line(answer["report"], "Grade:")
    label = f"Q{number} · {grade} · {loss:.2f} points lost"
    with st.expander(label, expanded=False):
        _render_daily_review_body(answer)

def _rebuild_friend_daily_answers(review_payload):
    """Rebuild exact local coaching for a completed friend's immutable DB answers."""
    rows = list(review_payload.get("answers", []))
    challenges = st.session_state.daily_challenges
    if len(rows) != 10:
        raise ChallengeMismatch("That completed Daily does not have all 10 saved answers.")
    rebuilt = []
    for row in sorted(rows, key=lambda item: int(item.get("question_number") or 0)):
        q = int(row.get("question_number") or 0)
        if not 1 <= q <= 10:
            raise ChallengeMismatch("Friend Daily question number is invalid.")
        challenge = challenges[q - 1]
        if str(challenge.get("challenge_id", "")) != str(row.get("puzzle_id", "")):
            raise ChallengeMismatch("Friend Daily answer does not match today's puzzle order.")
        selected_hold = [int(value) for value in row.get("chosen_hold", [])]
        report, solver_record = build_live_report(
            challenge["dice"], challenge["scorecard"], selected_hold, challenge["roll_number"]
        )
        if solver_record.get("source") != "exact":
            raise InvalidOfficialAnswer("Exact strategy is required to review a friend's Daily.")
        rebuilt_loss = float(solver_record.get("points_lost", 0.0) or 0.0)
        if abs(rebuilt_loss - float(row.get("points_lost", 0.0) or 0.0)) > 1e-6:
            raise ChallengeMismatch("Friend Daily score does not match the locked exact policy.")
        rebuilt.append(_daily_solver_record(challenge, solver_record, selected_hold, report))
    return rebuilt


def _render_friend_pick_peek(active_group, board):
    """Optional spoiler-safe peek at a completed friend's ten held-dice choices."""
    if active_group is None:
        return
    active_player_id = str(st.session_state.get("active_player_id") or "")
    friends = [
        item for item in board
        if str(item.get("player_id") or "") != active_player_id
    ]
    if not friends:
        return

    with st.expander("👀 Peek at a Friend's Picks", expanded=False):
        friend_by_id = {str(item.get("player_id")): item for item in friends}
        friend_id = st.selectbox(
            "Finished friend",
            options=list(friend_by_id),
            format_func=lambda player_id: str(friend_by_id[player_id].get("display_name") or "Friend"),
            key="friend_pick_peek_player",
        )
        friend = friend_by_id[str(friend_id)]
        friend_name = str(friend.get("display_name") or "Friend")
        if st.button(
            f"👀 See {friend_name}'s 10 picks",
            use_container_width=True,
            key="friend_pick_peek_button",
        ):
            st.session_state.friend_review_player_id = str(friend_id)

        target_id = str(st.session_state.get("friend_review_player_id") or "")
        if target_id not in friend_by_id:
            return
        target = friend_by_id[target_id]
        target_name = str(target.get("display_name") or "Friend")
        try:
            payload = _cached_group_player_daily_review(
                active_group.group_id,
                st.session_state.daily_set_id,
                active_player_id,
                target_id,
            )
            friend_answers = _rebuild_friend_daily_answers(payload)
        except Exception as exc:
            st.warning("That friend's picks couldn't be loaded right now.")
            if database_check_enabled():
                st.caption(f"Friend picks detail: {type(exc).__name__}: {exc}")
            return

        st.markdown(f"**{html.escape(target_name)}'s 10 picks**")
        for q, answer in enumerate(friend_answers, start=1):
            record = answer["solver_record"]
            selected = record.get("user_hold", "—")
            loss = float(record.get("points_lost", 0.0) or 0.0)
            result = "✅ Best" if loss <= 1e-9 else f"{loss:.2f} lost"
            st.markdown(f"**Q{q}** · {html.escape(str(selected))} · {result}")


def render_daily_results():
    answers = st.session_state.daily_answers
    records = [answer["solver_record"] for answer in answers]
    challenges = st.session_state.daily_challenges
    summary = summarize_attempt(records)

    # Keep group switching available, but put group administration later.
    groups = _load_player_groups()
    if len(groups) > 1:
        render_group_selector(groups, key="daily_results_group_selector")

    try:
        active_group, members, board, stats = _real_group_context()
    except Exception as exc:
        active_group, members, board, stats = None, [], [], []
        st.warning("Your Daily result is safe, but friend standings couldn't be refreshed right now.")
        if database_check_enabled():
            st.caption(f"Leaderboard detail: {type(exc).__name__}: {exc}")
    rank = _user_real_rank(board)
    rank_tied = _rank_is_tied(board, rank)
    story = _story_from_group_stats(stats)
    rank_value = f"T-{rank} of {len(board)}" if rank_tied else (f"#{rank} of {len(board)}" if rank is not None else "—")

    st.markdown(
        "<div class='daily-hero'>"
        "<div class='daily-kicker'>✅ Today's Daily</div>"
        f"<div class='daily-title'>{_daily_date_label(st.session_state.daily_date_key)}</div>"
        "<div class='daily-rule'>Nice work. Here's how your 10 decisions turned out.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='daily-result-grid'>"
        f"<div class='daily-result-box'><div class='daily-result-label'>Points Lost</div><div class='daily-result-value'>{summary['total_ev_loss']:.2f}</div><div class='daily-result-sub'>lower is better</div></div>"
        f"<div class='daily-result-box'><div class='daily-result-label'>Best Holds</div><div class='daily-result-value'>{summary['exact_count']}/10</div></div>"
        f"<div class='daily-result-box'><div class='daily-result-label'>Group Rank</div><div class='daily-result-value'>{rank_value}</div></div>"
        f"<div class='daily-result-box'><div class='daily-result-label'>Best Streak</div><div class='daily-result-value'>🔥 {summary['best_exact_streak']}</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    participation_streak = _participation_streak()
    streak_copy = _daily_streak_copy(participation_streak, completed_today=True)
    if streak_copy:
        st.caption(streak_copy)

    render_daily_share_result(records, summary, rank=rank, completed_count=len(board), rank_tied=rank_tied)

    # Social payoff comes before group administration.
    if active_group is not None:
        completed = len(board)
        total_members = len(members)
        st.markdown(f"### 🏆 {active_group.group_name}")
        if total_members <= 1:
            st.markdown(
                "<div class='daily-rank-banner'><b>You're the only member so far.</b><br>Invite a friend to turn this into a real leaderboard.</div>",
                unsafe_allow_html=True,
            )
        elif completed == 1 and rank == 1:
            waiting = max(0, total_members - completed)
            st.markdown(
                f"<div class='daily-rank-banner'><b>You're the first to finish today!</b><br>Waiting for {waiting} friend{'s' if waiting != 1 else ''}.</div>",
                unsafe_allow_html=True,
            )
        elif rank is not None:
            rank_copy = f"You're tied for #{rank} of {completed} today." if rank_tied else f"You're #{rank} of {completed} today."
            st.markdown(
                f"<div class='daily-rank-banner'><b>{rank_copy}</b><br>Lowest Points Lost leads the group.</div>",
                unsafe_allow_html=True,
            )
        if total_members > 1 and completed < total_members:
            waiting = total_members - completed
            st.caption(f"{completed} of {total_members} finished · waiting for {waiting} more")
        elif total_members > 1 and completed >= total_members:
            st.caption("Everyone's in — final standings for today.")
        if board:
            render_leaderboard_cards(board, allow_review=False)

        toughest = story.get("toughest")
        easiest = story.get("easiest")
        story_cards = []
        if toughest:
            q = toughest["question_number"]
            challenge = challenges[q - 1]
            exact_copy = (
                "Nobody found the best hold."
                if toughest["exact_count"] == 0
                else f"{toughest['exact_count']}/{toughest['players']} found the best hold."
            )
            story_cards.append(
                "<div class='group-story-card'><div class='story-kicker'>😈 Today's Killer</div>"
                f"<div class='story-title'>Q{q} · {challenge.get('scenario_name', '')}</div>"
                f"<div class='story-copy'>{exact_copy} Avg Points Lost: {toughest['avg_loss']:.2f}.</div></div>"
            )
        if easiest:
            q = easiest["question_number"]
            challenge = challenges[q - 1]
            unanimous = easiest["exact_count"] == easiest["players"]
            headline = "🎯 Everyone Nailed It" if unanimous else "🎯 Most Solved"
            exact_copy = (
                f"All {easiest['players']} players found the best hold."
                if unanimous
                else f"{easiest['exact_count']}/{easiest['players']} found the best hold."
            )
            story_cards.append(
                f"<div class='group-story-card'><div class='story-kicker'>{headline}</div>"
                f"<div class='story-title'>Q{q} · {challenge.get('scenario_name', '')}</div>"
                f"<div class='story-copy'>{exact_copy} Avg Points Lost: {easiest['avg_loss']:.2f}.</div></div>"
            )
        if story_cards:
            st.markdown("<div class='group-story-grid'>" + "".join(story_cards) + "</div>", unsafe_allow_html=True)
    else:
        st.markdown("### 🏆 Play with friends")
        st.caption("Create or join a friend group to compare Daily results on a shared leaderboard.")

    st.markdown("### 📝 Your 10 Grades")
    st.caption("Tap any question to open its full coaching.")
    for answer in answers:
        _daily_review_item(answer)

    _render_friend_pick_peek(active_group, board)

    st.caption("🔒 Today's Daily is complete. Come back tomorrow for a new set.")

    st.button(
        "🎯 Go to open Practice",
        type="primary",
        use_container_width=True,
        key="daily_to_practice",
        on_click=_set_app_mode,
        args=("Practice",),
    )

    # Group administration stays below results, insights, personal grades, and optional friend peeks.
    render_friend_group_hub(expanded=active_group is None)

    render_solver_panel(records)


def render_daily_mode():
    if not st.session_state.get("active_player_id"):
        render_player_identity_gate()
        return
    render_player_status_bar()
    if not sync_daily_attempt_from_database():
        return
    if not st.session_state.daily_started:
        if render_yesterday_final_standings_if_needed():
            return
        render_daily_intro()
        return
    if st.session_state.daily_completed:
        render_daily_results()
        return
    if st.session_state.get("daily_ready_to_submit"):
        render_daily_submission_review()
        return
    st.caption("Your Daily progress saves automatically.")
    render_daily_question()


@st.fragment
def _practice_choice_fragment():
    """Keep dice taps local to the puzzle controls instead of rerunning the whole app."""
    challenge = st.session_state.challenge
    round_id = st.session_state.round_id
    dice = challenge["dice"]
    scorecard = challenge["scorecard"]
    roll_number = challenge["roll_number"]
    answer_submitted = st.session_state.report is not None

    held_key = f"held_indices_{round_id}"
    if held_key not in st.session_state:
        st.session_state[held_key] = []
    selected_indices = st.pills(
        "Dice to hold",
        options=list(range(len(dice))),
        default=st.session_state.get(held_key, []),
        format_func=lambda die_index: unique_dice_label(die_index, dice[die_index]),
        selection_mode="multi",
        key=f"dice_pills_{round_id}",
        label_visibility="collapsed",
        disabled=answer_submitted,
    )
    selected_indices = list(selected_indices or [])
    st.session_state[held_key] = sorted(selected_indices)
    selected_hold = selected_hold_from_indices(dice, selected_indices)
    st.markdown(f"<div class='selected-summary'>Your hold: {hold_label(selected_hold)}</div>", unsafe_allow_html=True)

    if not answer_submitted:
        if st.button("Submit hold", type="primary", use_container_width=True, key=f"practice_submit_{round_id}"):
            report, solver_record = build_live_report(dice, scorecard, selected_hold, roll_number)
            if solver_record.get("source") != "exact":
                st.error("Exact strategy is temporarily unavailable. This puzzle was not graded. Please try another puzzle.")
                return
            st.session_state.report = report
            st.session_state.history.append({
                "scenario": challenge.get("scenario_name", ""),
                "roll": roll_number,
                "dice": str(dice),
                "choice": hold_label(selected_hold),
                "optimal": extract_line(report, "Optimal choice:"),
                "grade": extract_line(report, "Grade:"),
            })
            solver_record["scenario"] = challenge.get("scenario_name", "")
            solver_record["bank_version"] = challenge.get("bank_version", "")
            solver_record["skill_tag"] = challenge.get("skill_tag", "")
            solver_record["difficulty"] = challenge.get("difficulty", "")
            solver_record["stage"] = challenge.get("stage", "")
            solver_record["bonus_status"] = challenge.get("bonus_status", "")
            solver_record["challenge_id"] = challenge.get("challenge_id", "")
            solver_record["timestamp_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            before_solver_history = list(st.session_state.solver_history)
            st.session_state.solver_history.append(solver_record)
            st.session_state.new_badges = newly_unlocked_badges(before_solver_history, st.session_state.solver_history)
            st.session_state.scroll_to_result = True
            st.session_state.scroll_to_top = False
            st.rerun()


def render_practice_mode():
    challenge = st.session_state.get("challenge")
    history = st.session_state.history

    st.markdown(
        "<div class='practice-hero'>"
        "<div class='practice-title'>🎯 Practice</div>"
        "<div class='practice-subtitle'>Unlimited practice · instant coaching after every decision</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    if challenge is None:
        st.error("Exact Practice is temporarily unavailable. No heuristic coaching will be substituted.")
        if st.button("Try loading a Practice puzzle again", type="primary", use_container_width=True):
            new_round(scroll_to_top=False)
            st.rerun()
        if solver_debug_enabled() and st.session_state.get("practice_bank_error"):
            st.caption(st.session_state.get("practice_bank_error"))
        return

    # Before showing a Practice puzzle, prove that the audited exact policy can
    # evaluate this exact scorecard/roll. If not, fail closed rather than coach
    # from the legacy heuristic engine.
    try:
        exact_policy = load_exact_policy()
        exact_policy.best_hold(challenge["scorecard"], challenge["dice"], challenge["roll_number"])
    except Exception as exc:
        st.error("Exact strategy is temporarily unavailable. No heuristic coaching will be substituted.")
        if st.button("Try another exact Practice puzzle", type="primary", use_container_width=True):
            new_round(scroll_to_top=False)
            st.rerun()
        if solver_debug_enabled():
            st.caption(f"{type(exc).__name__}: {exc}")
        return

    if st.session_state.get("daily_completed") and len(st.session_state.get("daily_answers", [])) >= 10:
        st.button(
            "🏆 Daily complete · View leaderboard",
            use_container_width=True,
            key="practice_to_daily_results",
            on_click=_set_app_mode,
            args=("Daily Challenge",),
        )

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

    roll_number = challenge["roll_number"]
    scorecard = challenge["scorecard"]
    rolls_remaining = int(challenge.get("rolls_remaining", 3 - roll_number))

    st.markdown(
        f"""
        <div class='practice-puzzle-card'>
            <div class='practice-scenario'>{challenge.get('scenario_name', 'Practice Round')}</div>
            <div class='practice-description'>{challenge.get('scenario_description', '')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    roll_class = "roll-1" if int(roll_number) == 1 else "roll-2"
    roll_label = "First roll" if int(roll_number) == 1 else "Second roll"
    reroll_word = "reroll" if rolls_remaining == 1 else "rerolls"
    st.markdown(
        f"""
        <div class='daily-roll-stage {roll_class}'>
            <div class='daily-roll-stage-title'>🎲 ROLL {roll_number} · {roll_label} · {rolls_remaining} {reroll_word} left</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_scorecard(scorecard)
    st.markdown("<div class='practice-question'>Which dice would you keep? <span class='muted'>Tap to select.</span></div>", unsafe_allow_html=True)
    _practice_choice_fragment()

    if st.session_state.report:
        render_result(st.session_state.report)
        if st.button("Next Practice Puzzle →", type="primary", use_container_width=True):
            new_round(scroll_to_top=True)
            st.rerun()

        with st.expander("📈 See my practice progress", expanded=False):
            render_session_progress(history, st.session_state.solver_history)
            render_new_badges()
            render_session_coach(st.session_state.solver_history)
            render_practice_momentum(st.session_state.solver_history)

    if history:
        with st.expander("Session history", expanded=False):
            st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)
    render_solver_panel(st.session_state.solver_history)

def render_help_feedback_footer():
    """Low-profile beta help and feedback inbox."""
    st.markdown("<div style='height:.55rem'></div>", unsafe_allow_html=True)
    with st.expander("❓ Help & feedback", expanded=False):
        st.caption(APP_PUBLIC_VERSION)
        st.markdown(
            "**Something confusing, broken, or worth adding?** Send a quick note here. "
            "Your current app section and beta version are attached automatically."
        )
        with st.form("beta_feedback_form", clear_on_submit=True):
            feedback_type = st.selectbox(
                "Feedback type",
                ["Something confusing", "Bug / something broke", "Idea / suggestion", "Account / PIN help"],
                key="beta_feedback_type",
            )
            feedback_message = st.text_area(
                "What happened?",
                max_chars=1200,
                placeholder="A sentence or two is plenty.",
                key="beta_feedback_message",
            )
            submitted = st.form_submit_button("Send feedback", use_container_width=True)
        st.caption("Please don't include your PIN or other private information.")
        if submitted:
            try:
                load_daily_store().submit_feedback(
                    player_id=st.session_state.get("active_player_id"),
                    feedback_type=feedback_type,
                    message=feedback_message,
                    app_version=APP_RELEASE,
                    page_mode=str(st.session_state.get("app_mode") or "Unknown"),
                )
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error("Feedback couldn't be sent right now. Please try again later.")
                if database_check_enabled():
                    st.caption(f"Feedback detail: {type(exc).__name__}: {exc}")
            else:
                st.success("Thanks — feedback sent!")

        st.markdown("**Forgot your PIN?**")
        st.write("PIN recovery isn't available during the beta yet. Contact Mike or the person who invited you for help, and only share your display name — never your PIN.")


initialize_state()
initialize_daily_state()
initialize_player_identity_state()
_remember_storage_state = render_remember_storage_bridge()
_restore_remembered_player(_remember_storage_state)
render_yesterday_result_storage_bridge()
if _pending_invite_code():
    st.session_state.app_mode = "Daily Challenge"
if process_pending_group_invite():
    st.rerun()
render_pending_remember_cookie_command()
# Install near the top so dice taps stay visually anchored on mobile.
# Dice taps are fragment-scoped in Phase 2K.5, so the old full-rerun scroll guard is no longer needed.
install_app_shell_metadata()
st.markdown("<div id='app-top-anchor'></div>", unsafe_allow_html=True)
st.markdown("<h1 class='top-title'>🎲 Yahtzee Coach</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Hold Strategy Trainer</div>", unsafe_allow_html=True)

mode = st.radio(
    "Mode",
    options=["Daily Challenge", "Practice", "📲 Add to Home Screen"],
    horizontal=True,
    key="app_mode",
    label_visibility="collapsed",
)
if mode == "📲 Add to Home Screen":
    player_note = "Keep Yahtzee Coach one tap away"
elif mode == "Practice":
    player_note = "Unlimited hold-strategy practice"
elif st.session_state.get("active_player_id"):
    player_note = f"Today's Daily · {st.session_state.get('active_player_name')}"
else:
    player_note = "Today's 10-puzzle Daily Challenge"
st.markdown(f"<div class='mode-note'>{html.escape(player_note)}</div>", unsafe_allow_html=True)

if mode == "Daily Challenge":
    render_daily_mode()
elif mode == "Practice":
    render_practice_mode()
else:
    render_install_mode()

render_help_feedback_footer()
