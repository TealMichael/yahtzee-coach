"""Weekly screens. Accept only public store responses, never private dice pools.

All mutations use the revision shown by the clicked widget, a stable request ID,
and the server-authorized store. A failed save keeps that exact request for retry.
No solver, advice, or friend-review endpoint is used during official play.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
import html
import json
from uuid import NAMESPACE_URL, uuid4, uuid5
from zoneinfo import ZoneInfo

import streamlit as st

from weekly_game import (
    CATEGORIES, CATEGORY_LABELS, GameComplete, GameExpired, InvalidAction,
    StaleState, WeeklyGameError, current_week_id, score_totals, scoring_options,
)
from weekly_store import WeeklyAuthRequired, WeeklyGameNotFound, WeeklyStoreError

FACES = ("⚀", "⚁", "⚂", "⚃", "⚄", "⚅")


def clear_weekly_state():
    """Clear private UI state on logout/account switch, not the saved game."""
    for key in list(st.session_state):
        if str(key).startswith("weekly_"):
            del st.session_state[key]


def week_label(week_id):
    first = date.fromisoformat(week_id)
    last = first + timedelta(days=6)
    return f"{first:%b} {first.day} – {last:%b} {last.day}, {last.year}"


def held_positions(dice, held):
    """Choose canonical physical copies when a saved hand contains duplicates."""
    remaining = Counter(held)
    indices = []
    for i, face in enumerate(dice):
        if remaining[face]:
            indices.append(i)
            remaining[face] -= 1
    return indices


def action_request(game, action):
    """A duplicate event from the same rendered revision is the same request."""
    payload = json.dumps([game["game_id"], game["revision"], action], sort_keys=True, separators=(",", ":"))
    return {"operation": "act", "game_id": game["game_id"], "week_id": game["week_id"],
            "expected_revision": game["revision"], "request_id": str(uuid5(NAMESPACE_URL, payload)),
            "action": action}


def _queue(scope, request):
    key = f"{scope}_pending"
    if not st.session_state.get(key):
        st.session_state[key] = request


def _queue_start(scope, week_id, operation, expected_replay_id=None):
    _queue(scope, {"operation": operation, "week_id": week_id,
                   "request_id": str(uuid4()), "expected_replay_id": expected_replay_id})


def _send_pending(store, scope):
    key = f"{scope}_pending"
    pending = st.session_state.get(key)
    if not pending:
        return True
    try:
        if pending["operation"] == "act":
            store.act(pending["game_id"], expected_revision=pending["expected_revision"],
                      request_id=pending["request_id"], action=pending["action"])
            # Animate only a successfully saved reroll or the newly dealt hand.
            # This marker is private UI state: no extra RNG, requests, or dice data.
            if pending["action"]["kind"] in ("reroll", "score"):
                st.session_state[f"{scope}_animate_roll"] = (
                    pending["game_id"], pending["expected_revision"] + 1)
        elif pending["operation"] == "start":
            store.start_official(pending["week_id"], request_id=pending["request_id"])
        else:
            store.start_replay(pending["week_id"], expected_replay_id=pending["expected_replay_id"],
                               request_id=pending["request_id"])
        st.session_state.pop(key, None)
        return True
    except WeeklyAuthRequired:
        st.session_state.pop(key, None)
        raise
    except (StaleState, GameExpired, GameComplete, WeeklyGameNotFound, InvalidAction) as exc:
        st.session_state.pop(key, None)
        st.warning(str(exc))
        return True  # Display the current saved state, without replaying the action.
    except (WeeklyStoreError, WeeklyGameError):
        st.warning("The save wasn't confirmed. Your game may already be saved. Retry the same action or reload the saved game.")
        st.button("Retry save", key=f"{scope}_retry", use_container_width=True)
        if st.button("Reload saved game", key=f"{scope}_discard", use_container_width=True):
            st.session_state.pop(key, None)
            st.rerun()
        return False


def _scorecard(state):
    """Read-only, always-visible scorecard; only saved values, never hints."""
    scores = dict(zip(CATEGORIES, state["scores"]))
    bonus_count = sum(r["yahtzee_bonus"] for r in state["rounds"]) // 100
    totals = score_totals(scores, bonus_count)
    filled = sum(v is not None for v in scores.values())
    rows = []
    for i, category in enumerate(CATEGORIES):
        if i == 0:
            rows.append("<tr class='weekly-score-section'><th colspan='2'>Upper section</th></tr>")
        elif i == 6:
            rows.append("<tr class='weekly-score-section'><th colspan='2'>Lower section</th></tr>")
        value = scores[category]
        row_class = "weekly-score-filled" if value is not None else "weekly-score-open"
        score = "—" if value is None else str(value)  # Important: a saved zero is visible.
        rows.append(f"<tr class='{row_class}'><td>{CATEGORY_LABELS[category]}</td>"
                    f"<td>{score}</td></tr>")
    st.markdown(
        "<div class='weekly-scorecard-panel'>"
        f"<div class='weekly-scorecard-heading'><span>Scorecard</span><small>{filled}/13 filled</small></div>"
        "<table class='weekly-scorecard' aria-label='Your saved weekly scores'>"
        "<thead><tr><th>Category</th><th>Saved score</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        f"<div class='weekly-score-detail'><span>Upper section</span><b>{totals['upper']}/63</b></div>"
        f"<div class='weekly-score-detail'><span>Upper bonus</span><b>+{totals['upper_bonus']}</b></div>"
        f"<div class='weekly-score-detail'><span>Extra Yahtzees</span><b>+{totals['yahtzee_bonus']}</b></div>"
        f"<div class='weekly-score-total'><span>Total score</span><strong>{totals['total']}</strong></div>"
        "</div>", unsafe_allow_html=True)


def _roll_animation_css(indices):
    """Visual-only dice shake/faces; final values already came from saved state."""
    if not indices:
        return ""
    selectors = [
        f'.st-key-weekly_dice [data-testid="stHorizontalBlock"] > '
        f'[data-testid="stColumn"]:nth-child({i + 1}) '
        '[data-testid="stButton"] > button'
        for i in indices
    ]
    rules = []
    for pos, selector in enumerate(selectors):
        delay = pos * 55
        rules.append(f"{selector}{{animation:weekly-die-bounce .58s {delay}ms ease-out both!important;"
                     "position:relative!important;overflow:hidden!important}}")
        rules.append(f"{selector}::after{{content:'⚀';position:absolute;inset:0;z-index:1;"
                     "display:flex;align-items:center;justify-content:center;"
                     "border-radius:inherit;background:#f8fafc;color:#142344;"
                     "font-size:clamp(2.75rem,11vw,3.5rem);font-weight:500;"
                     f"animation:weekly-face-shuffle .58s {delay}ms steps(1,end) both!important;}}")
    return "<style>" + "".join(rules) + "</style>"


def _review(state, prefix):
    with st.expander("Review your rounds", expanded=False):
        st.caption("Your saved rolls and scores. No future dice or strategy grades are shown.")
        for number, rnd in enumerate(state["rounds"], 1):
            st.markdown(f"**Round {number} · {CATEGORY_LABELS[rnd['category']]} · {rnd['points']} points**")
            for roll_number, roll in enumerate(rnd["rolls"], 1):
                dice_text = " · ".join(str(v) for v in roll["dice"])
                hold_text = ", ".join(str(v) for v in roll["held_before"]) or "none"
                st.write(f"Roll {roll_number}: {dice_text}" + (f" — kept {hold_text}" if roll_number > 1 else ""))
            if rnd["yahtzee_bonus"]:
                st.caption("Extra Yahtzee bonus: +100")


def _friends(groups):
    st.markdown("#### Friends this week")
    if not groups:
        st.caption("Join or create a friend group from Daily Challenge to play alongside friends.")
    for group in groups:
        st.markdown(f"**{html.escape(group['group_name'])}**")
        count = group["completed_friends"]
        st.caption(f"{count} {'friend has' if count == 1 else 'friends have'} finished.")
        if not group["unlocked"]:
            st.caption("Scores and ranks unlock after your official game is finished.")
        else:
            rows = "".join(f"<tr><td>{row['rank']}</td><td>{html.escape(row['display_name'])}</td><td>{row['score']}</td></tr>"
                           for row in group["standings"])
            st.markdown("<table class='weekly-scorecard'><thead><tr><th>Rank</th><th>Player</th><th>Score</th></tr></thead>"
                        f"<tbody>{rows}</tbody></table>", unsafe_allow_html=True)
            st.caption("Official scores only. Equal scores share a rank.")


def _play(game, scope):
    state = game["state"]
    dice = state["rolls"][-1]["dice"]
    roll_number, rounds_done = len(state["rolls"]), len(state["rounds"])
    selected = held_positions(dice, state["held"])
    prefix = f"{scope}_{game['game_id']}_{game['revision']}"

    # Mobile-only summary stays in view while scrolling a full, readable scorecard.
    # On desktop the scorecard is alongside the play controls.
    game_type = "Official" if state["mode"] == "official" else "Practice replay"
    with st.container(key="weekly_mobile_summary"):
        st.markdown(
            f"<div class='weekly-summary-line'><span>{game_type} · Round {rounds_done + 1}/13 "
            f"· Roll {roll_number}/3</span><strong>{game['total_score']} pts</strong></div>",
            unsafe_allow_html=True)

    animate_indices = []
    animation_marker = st.session_state.pop(f"{scope}_animate_roll", None)
    if animation_marker == (game["game_id"], game["revision"]):
        # On a saved reroll, exclude the dice that were held before that roll.
        # On a newly scored round, animate the five already-saved first-roll dice.
        held_before = state["rolls"][-1]["held_before"] if roll_number > 1 else []
        held_copy_indices = set(held_positions(dice, held_before))
        animate_indices = [i for i in range(5) if i not in held_copy_indices]

    with st.container(key="weekly_play_layout"):
        play_col, card_col = st.columns([1.07, 0.93], gap="medium")
        with play_col:
            st.markdown(f"### Round {rounds_done + 1} of 13 · Roll {roll_number} of 3")
            st.progress(rounds_done / 13, text=f"{rounds_done} rounds saved · {game['total_score']} points")
            st.caption("Tap dice to hold or release them." if roll_number < 3 else
                       "Final roll. Choose a scoring category.")
            with st.container(key="weekly_dice"):
                # The same physical-die buttons and symbols as the Daily player.
                # The existing server-authenticated multiset hold actions are unchanged.
                cols = st.columns(5, gap="small")
                for i, face in enumerate(dice):
                    held = list(selected)
                    if i in held:
                        held.remove(i)
                    else:
                        held.append(i)
                    action = {"kind": "hold", "held": sorted(dice[j] for j in held)}
                    cols[i].button(FACES[face - 1], type="primary" if i in selected else "secondary",
                                   key=f"{prefix}_die_{i}", disabled=roll_number >= 3,
                                   use_container_width=True,
                                   help=f"Die {i + 1}: {face}. {'Held; tap to release.' if i in selected else 'Tap to hold.'}",
                                   on_click=_queue, args=(scope, action_request(game, action)))
            if animate_indices:
                st.markdown(_roll_animation_css(animate_indices), unsafe_allow_html=True)
            if roll_number < 3:
                st.caption("Held: " + (", ".join(str(v) for v in state["held"]) or "none"))
                st.button("Roll remaining dice", type="primary", use_container_width=True,
                          key=f"{prefix}_roll", disabled=len(selected) == 5,
                          on_click=_queue, args=(scope, action_request(game, {"kind": "reroll"})))
                if len(selected) == 5:
                    st.caption("Release a die to roll again, or score this hand.")
            scores = dict(zip(CATEGORIES, state["scores"]))
            options = scoring_options(dice, scores)
            by_category = {o.category: o for o in options}
            if len(options) < sum(v is None for v in scores.values()):
                st.caption("The Joker rule limits where this Yahtzee can be scored.")
            chosen = st.selectbox("Scoring category", options=list(by_category), index=None,
                                  placeholder="Choose an unused category", key=f"{prefix}_category",
                                  format_func=lambda c: f"{CATEGORY_LABELS[c]} — {by_category[c].points} points")
            if chosen:
                opt = by_category[chosen]
                st.caption(f"Score {opt.points} in {CATEGORY_LABELS[chosen]}" +
                           (f" plus a {opt.yahtzee_bonus}-point Yahtzee bonus." if opt.yahtzee_bonus else ".") +
                           " This choice is permanent.")
            st.button("Score this round", disabled=chosen is None, type="primary", use_container_width=True,
                      key=f"{prefix}_score", on_click=_queue,
                      args=(scope, action_request(game, {"kind": "score", "category": chosen})))
            st.caption("Saved after every action. You can leave Weekly and return to this game.")
        with card_col:
            _scorecard(state)  # Not an expander. Always visible during play.


def render_weekly(store, player_id):
    """store is actor-scoped; all data is freshly authorized on each rerun."""
    st.markdown("""<style>
    /* Weekly v44.0.2 — consistent with Daily dice; only Weekly controls are scoped. */
    .weekly-scorecard-panel{background:#fbf8f3;border:1px solid #ddd5c9;border-radius:16px;
        padding:.78rem .8rem .8rem;box-shadow:0 3px 12px #14234410;color:#142344}
    .weekly-scorecard-heading{display:flex;justify-content:space-between;align-items:center;
        font-size:1.16rem;font-weight:900;color:#142344;margin-bottom:.55rem}
    .weekly-scorecard-heading small{font-weight:750;font-size:.76rem;color:#667187}
    .weekly-scorecard{width:100%;border-collapse:collapse;font-size:.85rem;table-layout:auto}
    .weekly-scorecard td,.weekly-scorecard th{padding:.32rem .35rem;border-bottom:1px solid #dce0e9;
        text-align:left;overflow-wrap:anywhere}
    .weekly-scorecard td:last-child,.weekly-scorecard th:last-child{text-align:right;white-space:nowrap}
    .weekly-scorecard thead th{font-size:.75rem;color:#59667c}
    .weekly-score-section th{background:#e9edf4;color:#142344;font-size:.76rem;
        text-transform:uppercase;letter-spacing:.06em;padding:.36rem .4rem}
    .weekly-score-filled td{font-weight:750;color:#142344}
    .weekly-score-open td{color:#737d90}
    .weekly-score-detail{display:flex;justify-content:space-between;padding:.32rem .36rem;
        gap:.5rem;font-size:.8rem;color:#536078}
    .weekly-score-detail b{color:#142344}
    .weekly-score-total{display:flex;justify-content:space-between;align-items:center;
        background:#142344;border-radius:10px;padding:.58rem .75rem;margin-top:.38rem;
        color:#fff;font-size:.93rem;font-weight:800}
    .weekly-score-total strong{font-size:1.2rem;color:#fff}
    .st-key-weekly_mobile_summary{display:none!important}
    .st-key-weekly_play_layout [data-testid="stHorizontalBlock"]{align-items:flex-start}
    .st-key-weekly_dice [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;
        gap:clamp(.2rem,.55vw,.42rem)!important;justify-content:space-between!important}
    .st-key-weekly_dice [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important}
    .st-key-weekly_dice div[data-testid="stButton"]>button{
        width:100%!important;min-width:0!important;max-width:68px!important;
        aspect-ratio:1!important;height:auto!important;min-height:0!important;
        padding:0!important;margin:0 auto!important;display:flex!important;align-items:center!important;
        justify-content:center!important;border-radius:15px!important;box-shadow:0 4px 0 #c7c9cc,
        0 7px 14px #00000026!important;background:#f8fafc!important;
        border:2px solid #d1d5db!important;color:#111827!important}
    .st-key-weekly_dice div[data-testid="stButton"]>button p{
        font-size:clamp(2rem,4.2vw,3.5rem)!important;line-height:1!important;
        margin:0!important;padding:0!important;font-weight:500!important;
        font-family:-apple-system,BlinkMacSystemFont,"Segoe UI Symbol","Apple Color Emoji",
        "Noto Color Emoji",sans-serif!important;color:#111827!important}
    .st-key-weekly_dice div[data-testid="stButton"]>button[kind="primary"]{
        background:#ff4b4b!important;border-color:#ff4b4b!important;
        box-shadow:0 4px 0 #b91c1c,0 7px 14px #ff4b4b40!important}
    .st-key-weekly_dice div[data-testid="stButton"]>button[kind="primary"] p{color:#fff!important}
    .st-key-weekly_dice div[data-testid="stButton"]>button:disabled{opacity:1!important;cursor:default!important}
    .st-key-weekly_dice div[data-testid="stButton"]>button:not(:disabled):active{
        transform:translateY(3px)!important;box-shadow:0 1px 0 #c7c9cc,0 3px 8px #00000030!important}
    @keyframes weekly-die-bounce{
        0%{transform:translateY(-7px) rotate(-10deg) scale(.93)}
        20%{transform:translateY(2px) rotate(12deg) scale(1.05)}
        43%{transform:translateY(-4px) rotate(-8deg)}
        69%{transform:translateY(1px) rotate(5deg)}
        88%{transform:translateY(-2px) rotate(-2deg)}
        100%{transform:translateY(0) rotate(0) scale(1)}
    }
    @keyframes weekly-face-shuffle{
        0%{content:'⚀';opacity:1} 18%{content:'⚄';opacity:1}
        36%{content:'⚂';opacity:1} 54%{content:'⚅';opacity:1}
        72%{content:'⚁';opacity:1} 88%{content:'⚃';opacity:1}
        100%{content:'';opacity:0}
    }
    @media(max-width:767px){
        .st-key-weekly_mobile_summary{display:block!important;position:sticky!important;
            top:3.1rem;z-index:45;background:#f8f3ea;border:1px solid #dfd4c5;
            border-radius:11px;padding:.42rem .72rem;margin:.35rem 0 .65rem;
            box-shadow:0 2px 8px #1423441a}
        .weekly-summary-line{display:flex;justify-content:space-between;align-items:center;
            gap:.5rem;white-space:nowrap;font-size:clamp(.73rem,2.6vw,.88rem);color:#142344}
        .weekly-summary-line strong{font-size:.98rem;color:#b82e42}
        .st-key-weekly_play_layout [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important}
        .st-key-weekly_play_layout [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{
            flex:0 0 100%!important;width:100%!important;min-width:0!important}
        .st-key-weekly_dice [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important}
        .st-key-weekly_dice [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{
            flex:1 1 0!important;width:auto!important;min-width:0!important}
        .st-key-weekly_dice div[data-testid="stButton"]>button p{font-size:clamp(2.6rem,10vw,3.3rem)!important}
        .weekly-scorecard-panel{margin-top:.4rem}
    }
    @media(max-width:380px){
        .st-key-weekly_dice [data-testid="stHorizontalBlock"]{gap:.2rem!important}
        .st-key-weekly_dice div[data-testid="stButton"]>button{border-radius:13px!important}
        .st-key-weekly_dice div[data-testid="stButton"]>button p{font-size:clamp(2.4rem,10vw,3rem)!important}
    }
    @media(prefers-reduced-motion:reduce){
        .st-key-weekly_dice button{animation:none!important}
        .st-key-weekly_dice button::after{animation:none!important;opacity:0!important;content:none!important}
    }
    </style>""", unsafe_allow_html=True)
    st.markdown("## Weekly Yahtzee")
    scope = f"weekly_{player_id}"
    try:
        if not _send_pending(store, scope):
            return
        current = current_week_id()
        history = store.history(limit=52)
        older = st.session_state.get(f"{scope}_older", [])
        weeks = sorted({current, *(row["week_id"] for row in history), *older}, reverse=True)
        selected_key = f"{scope}_week"
        if st.session_state.get(selected_key) not in weeks:
            st.session_state[selected_key] = current
        week_id = st.selectbox("Challenge week", weeks, key=selected_key,
                               format_func=lambda w: week_label(w) + (" · This week" if w == current else ""))
        if len(history) == 52 or older:
            if st.button("Load older weeks", key=f"{scope}_history"):
                page = store.history(before_week=weeks[-1], limit=52)
                st.session_state[f"{scope}_older"] = sorted(set(older + [r["week_id"] for r in page]))
                if page:
                    st.rerun()
                st.caption("No earlier Weekly games.")
        dashboard = store.dashboard(week_id)
        now = datetime.fromisoformat(dashboard["server_now"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(dashboard["ends_at"].replace("Z", "+00:00"))
        start = datetime.fromisoformat(dashboard["starts_at"].replace("Z", "+00:00"))
        is_open = start <= now < end
        official, replay = dashboard["official"], dashboard["replay"]
        st.caption(f"Closes Monday, {end.astimezone(ZoneInfo('America/New_York')):%b %d} at 12:00 a.m. Eastern. Unfinished games receive no official score.")
        if official is None:
            st.write("One official game. Thirteen rounds. The same hidden dice opportunities for everyone, with your choices deciding the score.")
            st.caption("No coaching during your official game. After finishing, see friend standings and replay this week's dice for practice.")
            st.button("Start Official Game", disabled=not is_open, type="primary", use_container_width=True,
                      key=f"{scope}_start_{week_id}", on_click=_queue_start, args=(scope, week_id, "start"))
            if not is_open:
                st.info("This week is closed.")
        elif official["completed_at"] is None:
            if is_open:
                st.caption("Official game · one attempt")
                _play(official, scope)
            else:
                st.info("This official game expired unfinished. No score was entered in the standings.")
                _scorecard(official["state"])
                _review(official["state"], scope)
        else:
            st.success(f"Official Score (locked): {official['total_score']}")
            _scorecard(official["state"])
            _review(official["state"], scope)
            summary = dashboard["replay_summary"]
            if summary:
                st.caption(f"Best replay: {summary['best_score']} · Latest replay: {summary['latest_score']} · {summary['completed_count']} completed")
            if replay and replay["completed_at"] is None:
                st.info("Practice — does not affect standings")
                _play(replay, scope)
            else:
                if replay:
                    st.info(f"Practice complete: {replay['total_score']} points. Your official score is unchanged.")
                    _review(replay["state"], scope + "_replay")
                st.button("Replay This Week's Dice", use_container_width=True, key=f"{scope}_replay_{week_id}",
                          on_click=_queue_start, args=(scope, week_id, "replay", replay["game_id"] if replay else None))
        _friends(dashboard["groups"])
        st.button("Refresh saved game", key=f"{scope}_refresh", use_container_width=True)
    except WeeklyAuthRequired:
        clear_weekly_state()
        st.warning("Your sign-in expired. Sign out and sign in again to continue your saved Weekly game.")
    except (WeeklyStoreError, WeeklyGameError):
        st.error("Weekly couldn't load right now. Your saved game is unchanged. Please try again.")
        st.button("Try Weekly again", key=f"{scope}_load_retry", use_container_width=True)
