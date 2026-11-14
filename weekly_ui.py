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
    scores = dict(zip(CATEGORIES, state["scores"]))
    bonus_count = sum(r["yahtzee_bonus"] for r in state["rounds"]) // 100
    totals = score_totals(scores, bonus_count)
    rows = "".join(f"<tr><td>{CATEGORY_LABELS[c]}</td><td>{'—' if scores[c] is None else scores[c]}</td></tr>" for c in CATEGORIES)
    st.markdown("<table class='weekly-scorecard'><thead><tr><th>Category</th><th>Saved score</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>", unsafe_allow_html=True)
    st.caption(f"Upper subtotal: {totals['upper']}/63 · Upper bonus: +{totals['upper_bonus']} · Extra Yahtzees: +{totals['yahtzee_bonus']}")
    st.markdown(f"**Total: {totals['total']}**")


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
    st.markdown(f"### Round {rounds_done + 1} of 13 · Roll {roll_number} of 3")
    st.progress(rounds_done / 13, text=f"{rounds_done} rounds saved · {game['total_score']} points")
    st.caption("Tap dice to hold or release them." if roll_number < 3 else "Final roll. Choose a scoring category.")
    with st.container(key="weekly_dice"):
        cols = st.columns(5, gap="small")
        for i, face in enumerate(dice):
            held = list(selected)
            if i in held:
                held.remove(i)
            else:
                held.append(i)
            action = {"kind": "hold", "held": sorted(dice[j] for j in held)}
            cols[i].button(FACES[face - 1], type="primary" if i in selected else "secondary",
                           key=f"{prefix}_die_{i}", disabled=roll_number >= 3, use_container_width=True,
                           help=f"Die {i + 1}: {face}. {'Held; tap to release.' if i in selected else 'Tap to hold.'}",
                           on_click=_queue, args=(scope, action_request(game, action)))
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
    with st.expander("Your scorecard", expanded=False):
        _scorecard(state)


def render_weekly(store, player_id):
    """store is actor-scoped; all data is freshly authorized on each rerun."""
    st.markdown("""<style>
    .weekly-scorecard{width:100%;border-collapse:collapse;font-size:.95rem;table-layout:auto}
    .weekly-scorecard td,.weekly-scorecard th{padding:.4rem .5rem;border-bottom:1px solid #d9dce5;text-align:left;overflow-wrap:anywhere}
    .weekly-scorecard td:last-child,.weekly-scorecard th:last-child{text-align:right;white-space:nowrap}
    .st-key-weekly_dice [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:.4rem!important}
    .st-key-weekly_dice [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important}
    .st-key-weekly_dice button{min-height:52px!important;padding:.1rem!important;min-width:0!important}
    .st-key-weekly_dice button p{font-size:2rem!important;line-height:1.2!important}
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
            with st.expander("Official scorecard"):
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
