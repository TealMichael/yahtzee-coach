"""Weekly screens. Accept only public store responses, never private dice pools.

All mutations use the revision shown by the clicked widget, a stable request ID,
and the server-authorized store. A failed save keeps that exact request for retry.
No solver, advice, or friend-review endpoint is used during official play.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from hashlib import sha256
import random
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


def _replace_cached_game(scope, game):
    """Use the authenticated mutation result; avoid an extra dashboard read."""
    entry = st.session_state.get(f"{scope}_dashboard_cache")
    if entry and entry["week_id"] == game["week_id"]:
        entry["data"]["official" if game["mode"] == "official" else "replay"] = game
        if game.get("completed_at"):
            # Completion changes the server-side friends reveal policy.
            st.session_state.pop(f"{scope}_dashboard_cache", None)


def _send_pending(store, scope):
    """Save only actual game actions; retries keep the identical IDs/revisions."""
    key = f"{scope}_pending"
    pending = st.session_state.get(key)
    if not pending:
        return True
    try:
        if pending["operation"] == "roll_chain":
            # Save the final held multiset and then the roll, not each die tap.
            # Each operation has its own deterministic idempotency key.
            requests = pending["requests"]
            while pending["step"] < len(requests):
                request = requests[pending["step"]]
                game = store.act(request["game_id"], expected_revision=request["expected_revision"],
                                 request_id=request["request_id"], action=request["action"])
                _replace_cached_game(scope, game)
                pending["step"] += 1
            visual = _new_visual_roll(game, scope, pending["display_before"], pending["held_positions"])
            visual_key = (game["game_id"], len(game["state"]["rounds"]) + 1, len(game["state"]["rolls"]))
            st.session_state[f"{scope}_visual_rolls"][visual_key] = visual
            st.session_state.setdefault(f"{scope}_visual_held", {})[visual_key] = list(pending["held_positions"])
            st.session_state[f"{scope}_animate_roll"] = (
                game["game_id"], game["revision"], tuple(i for i in range(5)
                                                    if i not in pending["held_positions"]))
        elif pending["operation"] == "act":
            game = store.act(pending["game_id"], expected_revision=pending["expected_revision"],
                             request_id=pending["request_id"], action=pending["action"])
            _replace_cached_game(scope, game)
            if pending["action"].get("kind") == "score" and not game.get("completed_at"):
                # Return to the next round after the authoritative save succeeds.
                st.session_state[f"{scope}_scroll_after_score"] = True
        elif pending["operation"] == "start":
            game = store.start_official(pending["week_id"], request_id=pending["request_id"])
            _replace_cached_game(scope, game)
        else:
            game = store.start_replay(pending["week_id"], expected_replay_id=pending["expected_replay_id"],
                                      request_id=pending["request_id"])
            _replace_cached_game(scope, game)
        st.session_state.pop(key, None)
        return True
    except WeeklyAuthRequired:
        st.session_state.pop(key, None)
        raise
    except (StaleState, GameExpired, GameComplete, WeeklyGameNotFound, InvalidAction) as exc:
        st.session_state.pop(key, None)
        st.session_state.pop(f"{scope}_dashboard_cache", None)
        st.warning(str(exc))
        return True  # Refetch authoritative saved state instead of guessing.
    except (WeeklyStoreError, WeeklyGameError):
        st.warning("The save wasn't confirmed. Your game may already be saved. Retry the same action or reload the saved game.")
        st.button("Retry save", key=f"{scope}_retry", use_container_width=True)
        if st.button("Reload saved game", key=f"{scope}_discard", use_container_width=True):
            st.session_state.pop(key, None)
            st.session_state.pop(f"{scope}_dashboard_cache", None)
            st.rerun()
        return False


def _deterministically_mixed(values, game_id, round_number, roll_number):
    """Mix visible *saved* faces; this has no access to future dice pools."""
    faces = list(values)
    seed = int.from_bytes(sha256(f"weekly-visual-v1|{game_id}|{round_number}|{roll_number}".encode()).digest(), "big")
    random.Random(seed).shuffle(faces)
    return faces


def _new_visual_roll(game, scope, previous, held_indices):
    """Keep each tapped die at its original screen position after a saved roll."""
    state = game["state"]
    current = state["rolls"][-1]
    held_indices = set(held_indices)
    held = [previous[i] for i in range(5) if i in held_indices]
    leftovers = list((Counter(current["dice"]) - Counter(held)).elements())
    if len(leftovers) != 5 - len(held_indices):
        raise WeeklyGameError("Saved rolled dice don't match the held dice.")
    new_faces = iter(_deterministically_mixed(leftovers, game["game_id"], len(state["rounds"]) + 1,
                                              len(state["rolls"])))
    return [previous[i] if i in held_indices else next(new_faces) for i in range(5)]


def _visual_dice(game, scope):
    """Project sorted backend rolls into stable physical positions for the UI.

    Existing v44 states are untouched. On reconnect, duplicate held faces have
    no stored physical identity; reconstruct a deterministic, valid layout.
    """
    state = game["state"]
    round_number = len(state["rounds"]) + 1
    rolls = state["rolls"]
    positions = st.session_state.setdefault(f"{scope}_visual_rolls", {})
    current_key = (game["game_id"], round_number, len(rolls))
    cached = positions.get(current_key)
    if cached is not None and Counter(cached) == Counter(rolls[-1]["dice"]):
        return list(cached)
    first_key = (game["game_id"], round_number, 1)
    displayed = positions.get(first_key)
    if displayed is None or Counter(displayed) != Counter(rolls[0]["dice"]):
        displayed = _deterministically_mixed(rolls[0]["dice"], game["game_id"], round_number, 1)
        positions[first_key] = displayed
    for number, roll in enumerate(rolls[1:], 2):
        key = (game["game_id"], round_number, number)
        existing = positions.get(key)
        if existing is not None and Counter(existing) == Counter(roll["dice"]):
            displayed = existing
            continue
        previously_held = held_positions(displayed, roll["held_before"])
        displayed = _new_visual_roll(
            {"game_id":game["game_id"],"state":{"rolls":rolls[:number],"rounds":state["rounds"]}},
            scope, displayed, previously_held)
        positions[key] = displayed
    # Restrict memory to the active and immediately preceding round.
    if len(positions) > 9:
        keep = {k:v for k,v in positions.items() if k[0] == game["game_id"] and k[1] >= round_number - 1}
        st.session_state[f"{scope}_visual_rolls"] = keep
    return list(displayed)


def _dice_pill_options(dice):
    # Exactly the Daily picker: Unicode faces plus invisible unique position IDs.
    return [FACES[int(face) - 1] + ("\u200b" * (i + 1)) for i, face in enumerate(dice)]


def _selected_die_indices(dice, selected):
    identifiers = {label:i for i, label in enumerate(_dice_pill_options(dice))}
    return sorted(identifiers[label] for label in (selected or []) if label in identifiers)


def _queue_roll(scope, game, displayed, pill_key):
    selected = _selected_die_indices(displayed, st.session_state.get(pill_key, []))
    if len(selected) == 5:
        return
    hold = sorted(displayed[i] for i in selected)
    state = game["state"]
    requests = []
    if hold != state["held"]:
        requests.append(action_request(game, {"kind":"hold", "held":hold}))
    following = dict(game, revision=game["revision"] + len(requests))
    requests.append(action_request(following, {"kind":"reroll"}))
    _queue(scope, {"operation":"roll_chain", "requests":requests, "step":0,
                   "game_id":game["game_id"], "held_positions":selected,
                   "display_before":list(displayed)})


def _reveal_first_roll(scope, game):
    state = game["state"]
    st.session_state[f"{scope}_revealed_round"] = (game["game_id"],len(state["rounds"]) + 1)
    st.session_state[f"{scope}_animate_roll"] = (game["game_id"], game["revision"], (0,1,2,3,4))


def _choose_category(key, category):
    st.session_state[key] = category


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
    """Shake only saved, newly rolled dice using the very same Daily pill faces."""
    if not indices:
        return ""
    css = []
    for pos, index in enumerate(indices):
        delay = pos * 45
        css.append(
            f'.st-key-weekly_dice div[role="group"] > button:nth-child({index + 1})'
            f'{{animation:weekly-die-bounce .52s {delay}ms ease-out both!important;'
            'position:relative!important;overflow:hidden!important}}'
        )
        css.append(
            f'.st-key-weekly_dice div[role="group"] > button:nth-child({index + 1})::after'
            "{content:'⚀';position:absolute;inset:0;z-index:1;"
            'display:flex;align-items:center;justify-content:center;'
            'border-radius:inherit;background:#f8fafc;color:#142344;'
            'font-size:3.3rem;font-weight:500;'
            f'animation:weekly-face-shuffle .52s {delay}ms steps(1,end) both!important;}}'
        )
    return '<style>' + ''.join(css) + '</style>'


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


# Use exactly the short category labels shown on the Daily Challenge scorecard.
# The actual scoring eligibility and point previews still come exclusively from
# weekly_game.scoring_options (including Joker/forced-category rules).
WEEKLY_DAILY_LABELS = (
    "1s", "2s", "3s", "4s", "5s", "6s", "3K", "4K", "FH", "SS", "LS", "YTZ", "CH",
)


def _scorecard_tile_label(category, index, scores, options, revealed):
    """Daily-style short label + saved score or preview; never predict hidden rolls."""
    short = WEEKLY_DAILY_LABELS[index]
    value = scores[category]
    if value is not None:
        return f"{short}  \n**{value}**", False, "filled"
    if revealed and category in options:
        return f"{short}  \n**+{options[category].points}**", True, "available"
    # Daily's green OPEN text signifies unused categories, not an offered
    # score. A game still requires Roll 1 before any box can be selected.
    return f"{short}  \n**OPEN**", False, "open"


def _render_weekly_tile_section(section, categories, indices, *, prefix, choice_key,
                                options, scores, revealed, scope, game, current):
    """Compact 3-across Upper and 4-across Lower layout from Daily's phone UI.

    All score buttons are normal Streamlit widgets. Their callbacks only set a
    local selected category, and the actual DB mutation is a separate Confirm.
    The Confirm appears immediately after the selected tile's *row*, preventing
    another 13-row scroll without risking a one-tap irreversible score.
    """
    count = 3 if section == "upper" else 4
    with st.container(key=f"weekly_score_grid_{section}"):
        st.markdown(f"<div class='weekly-score-section-heading'>{section.title()} section</div>",
                    unsafe_allow_html=True)
        for row_start in range(0, len(categories), count):
            row_cats = categories[row_start:row_start+count]
            with st.container(key=f"weekly_score_grid_{section}_row_{row_start // count}"):
                columns = st.columns(count, gap="small")
                for col_index, category in enumerate(row_cats):
                    index = indices[row_start + col_index]
                    label, enabled, status = _scorecard_tile_label(category, index, scores, options, revealed)
                    with columns[col_index]:
                        # Every offered category stays tappable, including +0. Emphasize
                        # positive opportunities visually, never change eligibility.
                        tone = ("gain" if options[category].points > 0 else "zero") if enabled else "saved"
                        with st.container(key=f"weekly_score_tile_{index}_{status}_{tone}"):
                            st.button(label, key=f"{prefix}_category_{category}",
                                      type="primary" if current == category else "secondary",
                                      disabled=not enabled, use_container_width=True,
                                      on_click=_choose_category, args=(choice_key, category),
                                      help=("Select the category to preview a permanent score"
                                            if enabled else "Already scored or roll first"))
                if current in row_cats:
                    category = current
                    option = options[category]
                    bonus = f" + {option.yahtzee_bonus} bonus" if option.yahtzee_bonus else ""
                    with st.container(key="weekly_selected_score_action"):
                        st.button(f"Confirm {option.points} points in {CATEGORY_LABELS[category]}{bonus}",
                                  type="primary", use_container_width=True, key=f"{prefix}_confirm_score",
                                  on_click=_queue,
                                  args=(scope, action_request(game, {"kind":"score", "category":category})))
                        st.caption("Only Confirm saves this score permanently.")


def _scorecard_picker(game, scope, dice, revealed, prefix):
    """Daily-style, compact, tappable 13-category scorecard for Weekly."""
    state = game["state"]
    scores = dict(zip(CATEGORIES, state["scores"]))
    bonus_count = sum(r["yahtzee_bonus"] for r in state["rounds"]) // 100
    totals = score_totals(scores, bonus_count)
    options = {o.category:o for o in scoring_options(dice, scores)} if revealed else {}
    choice_key = f"{scope}_{game['game_id']}_{len(state['rounds']) + 1}_category_choice"
    current = st.session_state.get(choice_key)
    if current not in options:
        current = None
        st.session_state.pop(choice_key, None)
    with st.container(key="weekly_scorecard_interactive"):
        st.markdown(
            f"<div class='weekly-scorecard-heading'><span>Scorecard</span>"
            f"<small>{sum(v is not None for v in scores.values())}/13 filled "
            f"· Upper {totals['upper']}/63</small></div>",
            unsafe_allow_html=True)
        _render_weekly_tile_section("upper", CATEGORIES[:6], range(6), prefix=prefix,
                                    choice_key=choice_key, options=options, scores=scores,
                                    revealed=revealed, scope=scope, game=game, current=current)
        _render_weekly_tile_section("lower", CATEGORIES[6:], range(6,13), prefix=prefix,
                                    choice_key=choice_key, options=options, scores=scores,
                                    revealed=revealed, scope=scope, game=game, current=current)
        if not revealed:
            st.caption("Roll to see your scoring choices.")
        elif len(options) < sum(v is None for v in scores.values()):
            st.caption("Joker rule: only eligible categories can be chosen.")
        st.markdown(
            f"<div class='weekly-score-detail'><span>Upper section</span><b>{totals['upper']}/63</b></div>"
            f"<div class='weekly-score-detail'><span>Upper bonus</span><b>+{totals['upper_bonus']}</b></div>"
            f"<div class='weekly-score-detail'><span>Extra Yahtzees</span><b>+{totals['yahtzee_bonus']}</b></div>"
            f"<div class='weekly-score-total'><span>Total score</span><strong>{totals['total']}</strong></div>",
            unsafe_allow_html=True)


def _play(game, scope):
    state = game["state"]
    dice = _visual_dice(game, scope)  # Physical screen positions; never sorted after each roll.
    roll_number, rounds_done = len(state["rolls"]), len(state["rounds"])
    prefix = f"{scope}_{game['game_id']}_{game['revision']}"
    revealed = (roll_number > 1 or st.session_state.get(f"{scope}_revealed_round") ==
                (game["game_id"], rounds_done + 1))

    game_type = "Official" if state["mode"] == "official" else "Practice replay"
    with st.container(key="weekly_mobile_summary"):
        st.markdown(
            f"<div class='weekly-summary-line'><span>{game_type} · Round {rounds_done + 1}/13 "
            f"· {'Ready for roll 1' if not revealed else f'Roll {roll_number}/3'}</span>"
            f"<strong>{game['total_score']} pts</strong></div>", unsafe_allow_html=True)

    animate_indices = []
    marker = st.session_state.pop(f"{scope}_animate_roll", None)
    if marker and len(marker) == 3 and marker[:2] == (game["game_id"], game["revision"]):
        animate_indices = list(marker[2])

    with st.container(key="weekly_play_layout"):
        play_col, card_col = st.columns([1.07, 0.93], gap="medium")
        with play_col:
            phase = "Ready to roll" if not revealed else f"Roll {roll_number} of 3"
            st.markdown(
                f"<div class='weekly-play-head'><strong>Round {rounds_done + 1} of 13</strong>"
                f"<span>{phase}</span><b>{game['total_score']} pts</b></div>",
                unsafe_allow_html=True)
            st.progress(rounds_done / 13)
            if not revealed:
                st.caption("Tap Roll Dice to start.")
                with st.container(key="weekly_unrevealed_dice"):
                    st.markdown('<div class="weekly-five-unrolled">' + '<div>?</div>'*5 + '</div>',
                                unsafe_allow_html=True)
                st.button("🎲 Roll Dice · 1 of 3", type="primary", use_container_width=True,
                          key=f"{prefix}_first_roll", on_click=_reveal_first_roll, args=(scope, game))
            else:
                st.caption("Tap dice to hold." if roll_number < 3 else
                           "Choose a scoring category below.")
                with st.container(key="weekly_dice"):
                    # Same st.pills widget, symbols and unique invisible position IDs as Daily.
                    options = _dice_pill_options(dice)
                    selected_positions = held_positions(dice, state["held"]) if roll_number < 3 else []
                    visual_key = (game["game_id"], rounds_done + 1, roll_number)
                    exact_indices = st.session_state.get(f"{scope}_visual_held", {}).get(visual_key)
                    if exact_indices is not None and Counter(dice[i] for i in exact_indices) == Counter(state["held"]):
                        selected_positions = list(exact_indices)
                    pill_key = f"{prefix}_pills_v2"
                    if pill_key not in st.session_state:
                        st.session_state[pill_key] = [options[i] for i in selected_positions]
                    chosen = st.pills("Dice to hold", options=options, selection_mode="multi", key=pill_key,
                                      label_visibility="collapsed", disabled=roll_number >= 3)
                if animate_indices:
                    st.markdown(_roll_animation_css(animate_indices), unsafe_allow_html=True)
                held_indices = _selected_die_indices(dice, chosen)
                if roll_number < 3:
                    st.caption(f"Holding {len(held_indices)} of 5 dice")
                    st.button(f"🎲 Roll Dice · {roll_number + 1} of 3", type="primary",
                              use_container_width=True, key=f"{prefix}_roll",
                              disabled=len(held_indices) == 5,
                              on_click=_queue_roll, args=(scope, game, dice, pill_key))
                    if len(held_indices) == 5:
                        st.caption("Release a die to reroll, or score this hand.")
                else:
                    # Same control footprint as the prior Roll button: no mobile
                    # scorecard jump as soon as the third roll finishes.
                    st.caption("All three rolls completed")
                    st.markdown('<div class="weekly-final-roll-banner" role="status">✓ Final roll — choose a score</div>',
                                unsafe_allow_html=True)
                # Game actions are still saved server-side; local selection needs no explanation.
        with card_col:
            _scorecard_picker(game, scope, dice, revealed, prefix)
    _mobile_summary_visibility_watcher(
        st.session_state.pop(f"{scope}_scroll_after_score", False),
        animate_indices=animate_indices,
        animation_token=f"{game['game_id']}:{game['revision']}:{rounds_done}:{roll_number}",
    )


def _mobile_summary_visibility_watcher(scroll_after_score=False, *, animate_indices=(), animation_token=None):
    """Mobile-only scroll affordance; DOM observer never touches game or DB state.

    Streamlit renders this 0-height component after the play controls. No network,
    session state, or click interception. If a browser disallows parent access,
    the full in-flow round header continues to provide the same information.
    """
    components = getattr(st, "components", None)
    if components is None or not hasattr(components, "v1"):
        return  # Also keeps the isolated test shim fully offline.
    scroll_command = "true" if scroll_after_score else "false"
    roll_positions = json.dumps(list(animate_indices))
    roll_token = json.dumps(str(animation_token or ""))
    components.v1.html(r"""
    <script>
    (() => {
      try {
        const win = window.parent, doc = win.document;
        if (typeof win.__ycWeeklyMiniCleanup === 'function') win.__ycWeeklyMiniCleanup();
        const bar = doc.querySelector('.st-key-weekly_mobile_summary');
        const dice = doc.querySelector('.st-key-weekly_dice') ||
                     doc.querySelector('.st-key-weekly_unrevealed_dice');
        if (!bar || !dice) return;
        const update = () => {
          const edge = dice.getBoundingClientRect().bottom;
          const mobile = win.matchMedia('(max-width:767px)').matches;
          bar.classList.toggle('yc-mini-active', mobile && edge < 120);
        };
        win.addEventListener('scroll', update, {passive:true});
        win.addEventListener('resize', update, {passive:true});
        const obs = new MutationObserver(update);
        obs.observe(dice, {childList:true,subtree:true});
        win.__ycWeeklyMiniCleanup = () => {
          win.removeEventListener('scroll', update);
          win.removeEventListener('resize', update);
          obs.disconnect();
        };
        update();
        // Saved-roll celebration is cosmetic. A new revision has a new token,
        // and repeating a Streamlit rerun must not replay the animation.
        const rollPositions = ROLL_POSITIONS;
        const rollToken = ROLL_TOKEN;
        const pills = doc.querySelectorAll('.st-key-weekly_dice div[role="group"] > button');
        if (rollPositions.length && rollToken && pills.length === 5 &&
            win.__ycWeeklyLastAnimated !== rollToken) {
          win.__ycWeeklyLastAnimated = rollToken;
          if (!win.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            win.requestAnimationFrame(() => {
              rollPositions.forEach((index, order) => {
                const die = pills[index];
                if (!die) return;
                die.style.setProperty('animation', 'none', 'important');
                void die.offsetWidth; // Make WebKit/iPhone Chrome restart the keyframe.
                die.style.setProperty('animation',
                  `weekly-die-bounce .52s ${order * 45}ms ease-out both`, 'important');
                die.addEventListener('animationend', () => {
                  die.style.removeProperty('animation');
                }, {once:true});
              });
            });
          }
        }
        if (SCROLL_AFTER_SCORE) {
          win.requestAnimationFrame(() => win.requestAnimationFrame(() => {
            const head = doc.querySelector('.weekly-play-head');
            if (head) head.scrollIntoView({behavior:'smooth', block:'start'});
          }));
        }
      } catch (_) { /* Full round header remains visible without the mini bar. */ }
    })();
    </script>""".replace("SCROLL_AFTER_SCORE", scroll_command)
               .replace("ROLL_POSITIONS", roll_positions)
               .replace("ROLL_TOKEN", roll_token), height=0, scrolling=False)


@st.fragment
def render_weekly(store, player_id):
    """store is actor-scoped; all data is freshly authorized on each rerun."""
    st.markdown("""<style>
    /* Weekly v44.0.3 — exact Daily st.pills dice, tappable rows, stable layout. */
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
        0%{transform:translateY(-10px) rotate(-11deg) scale(.93)}
        20%{transform:translateY(3px) rotate(13deg) scale(1.04)}
        43%{transform:translateY(-7px) rotate(-9deg)}
        69%{transform:translateY(2px) rotate(6deg)}
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
        .st-key-weekly_mobile_summary{display:none!important;position:fixed!important;
            top:6.1rem;left:50%;transform:translateX(-50%);z-index:45;
            width:min(calc(100vw - 1.15rem),750px);max-width:750px;
            background:#f8f3ea;border:1px solid #dfd4c5;
            border-radius:11px;padding:.3rem .6rem;margin:0!important;
            box-shadow:0 2px 8px #1423441a}
        .st-key-weekly_mobile_summary.yc-mini-active{display:block!important}
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

    /* Native st.pills in Weekly deliberately inherit the SAME face styling as Daily
       in app.py. Do not shrink or substitute button glyphs. */
    .st-key-weekly_dice div[data-testid="stButtonGroup"],
    .st-key-weekly_dice div[data-testid="stPills"]{width:100%!important}
    .st-key-weekly_dice div[role="group"]{justify-content:center!important;gap:.32rem!important;flex-wrap:nowrap!important}
    .st-key-weekly_dice div[role="group"]>button{flex-shrink:0!important}
    .weekly-five-unrolled{display:flex;gap:.42rem;justify-content:center;margin:.5rem 0 .85rem}
    .weekly-five-unrolled>div{width:clamp(54px,16vw,68px);height:clamp(54px,16vw,68px);
        display:flex;align-items:center;justify-content:center;border:2px solid #d1d5db;
        border-radius:15px;background:#f8fafc;box-shadow:0 4px 0 #c7c9cc,0 7px 14px #00000026;
        color:#a7b0bf;font-size:2.3rem;font-weight:800}
    .st-key-weekly_scorecard_interactive{background:#fbf8f3;border:1px solid #ddd5c9;
        border-radius:16px;padding:.78rem .8rem .8rem;box-shadow:0 3px 12px #14234410}
    .weekly-score-section-heading{font-weight:900;letter-spacing:.06em;text-transform:uppercase;
        color:#142344;background:#e9edf4;border-radius:5px;padding:.36rem .42rem;
        font-size:.76rem;margin:.4rem 0 .2rem}
    div[class*="st-key-weekly_score_row_"]{border-bottom:1px solid #dce0e9;margin:0!important;padding:0!important}
    div[class*="st-key-weekly_score_row_"] div[data-testid="stHorizontalBlock"]{
        align-items:center!important;gap:.15rem!important;flex-wrap:nowrap!important}
    div[class*="st-key-weekly_score_row_"] div[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:first-child{
        width:78%!important;min-width:0!important;flex:0 0 78%!important}
    div[class*="st-key-weekly_score_row_"] div[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child{
        width:21%!important;min-width:0!important;flex:0 0 21%!important}
    div[class*="st-key-weekly_score_row_"] div[data-testid="stButton"]>button{
        justify-content:flex-start!important;border:0!important;background:transparent!important;
        color:#142344!important;box-shadow:none!important;min-height:1.65rem!important;
        height:1.65rem!important;width:100%!important;padding:.15rem .28rem!important;
        border-radius:4px!important;font-size:.82rem!important;text-align:left!important}
    div[class*="st-key-weekly_score_row_"] div[data-testid="stButton"]>button p{
        font-size:.82rem!important;color:inherit!important;line-height:1.2!important}
    div[class*="st-key-weekly_score_row_"] div[data-testid="stButton"]>button:not(:disabled):hover{
        background:#f8dce1!important;color:#922237!important}
    div[class*="st-key-weekly_score_row_"] div[data-testid="stButton"]>button[kind="primary"]{
        background:#b82e42!important;color:#fff!important}
    div[class*="st-key-weekly_score_row_"] div[data-testid="stButton"]>button:disabled{
        color:#7c8595!important;opacity:1!important}
    .weekly-score-row-value{font-weight:800;color:#142344;font-size:.82rem;
        white-space:nowrap;text-align:right;padding:.25rem .35rem}
    @media(max-width:767px){
        /* Override the mobile play-column stacking for the scorecard's own rows. */
        div[class*="st-key-weekly_score_row_"] div[data-testid="stHorizontalBlock"]{
            flex-wrap:nowrap!important}
        div[class*="st-key-weekly_score_row_"] div[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:first-child{
            flex:0 0 78%!important;width:78%!important}
        div[class*="st-key-weekly_score_row_"] div[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child{
            flex:0 0 21%!important;width:21%!important}
    }

    /* v44.0.4: compact reading and touch targets; unchanged game semantics. */
    .weekly-page-title{font-size:clamp(1.3rem,2.6vw,1.6rem);font-weight:900;
        line-height:1.13;color:#142344;letter-spacing:-.03em;margin:.05rem 0 .25rem}
    .weekly-play-head{display:flex;gap:.4rem;align-items:center;flex-wrap:wrap;
        color:#142344;margin:0 0 .15rem;line-height:1.2}
    .weekly-play-head strong{font-weight:900;font-size:1.13rem}
    .weekly-play-head span{color:#627087;font-size:.85rem;flex:1;white-space:nowrap}
    .weekly-play-head b{color:#b82e42;font-size:.97rem;white-space:nowrap}
    .st-key-weekly_selected_score_action{padding:.3rem .35rem .4rem;
        background:#fff2f3;border:1px solid #e9b3bd;border-radius:9px;margin:.12rem 0 .28rem}
    .st-key-weekly_selected_score_action [data-testid="stVerticalBlock"]{gap:.13rem!important}
    .st-key-weekly_selected_score_action div[data-testid="stButton"]>button{
        min-height:2.45rem!important;height:auto!important;border-radius:8px!important;
        background:#b82e42!important;color:#fff!important}
    .st-key-weekly_selected_score_action div[data-testid="stButton"]>button p{
        color:#fff!important;font-weight:800!important;font-size:.84rem!important}
    .st-key-weekly_selected_score_action [data-testid="stCaptionContainer"] p{font-size:.73rem!important}
    div[class*="st-key-weekly_score_row_"] [data-testid="stVerticalBlock"]{
        gap:0!important;row-gap:0!important}
    div[class*="st-key-weekly_score_row_"] [data-testid="stHorizontalBlock"]{
        gap:.1rem!important;align-items:center!important;min-height:2.7rem!important}
    div[class*="st-key-weekly_score_row_"] div[data-testid="stButton"]>button{
        min-height:2.65rem!important;height:2.65rem!important;
        font-size:.87rem!important;line-height:1.2!important;cursor:pointer}
    div[class*="st-key-weekly_score_row_"] div[data-testid="stButton"]>button p{
        font-size:.87rem!important}
    div[class*="st-key-weekly_score_row_"] .weekly-score-row-value{
        font-size:.9rem!important;padding:.4rem .2rem!important}
    @media(max-width:767px){
        .weekly-page-title{font-size:1.35rem;margin:0 0 .12rem}
        .weekly-play-head{margin:0 0 .1rem}
        .weekly-play-head strong{font-size:1.08rem}
        .weekly-play-head span{font-size:.77rem}
        .st-key-weekly_play_layout [data-testid="stVerticalBlock"]{gap:.45rem!important}
        .st-key-weekly_scorecard_interactive{padding:.58rem .52rem .68rem!important}
        .weekly-scorecard-heading{font-size:1.03rem;margin-bottom:.25rem}
        .weekly-score-section-heading{padding:.27rem .4rem;margin:.26rem 0 .1rem}
        div[class*="st-key-weekly_score_row_"] div[data-testid="stHorizontalBlock"]{
            min-height:2.72rem!important;margin:0!important}
        .st-key-weekly_scorecard_interactive [data-testid="stCaptionContainer"] p{
            font-size:.76rem!important;line-height:1.24!important}
    }
    /* v44.0.5 — Daily's compact 3+4 scorecard language, as tappable native controls. */
    .weekly-score-section-heading{background:transparent!important;letter-spacing:0!important;
      text-transform:none!important;font-size:.85rem!important;margin:.3rem 0 .18rem!important;
      padding:.1rem 0!important;color:#172746!important}
    .st-key-weekly_scorecard_interactive{background:#fff!important;
      border:1px solid #e0e2e6!important;padding:.7rem .65rem!important}
    div[class*="st-key-weekly_score_grid_"] [data-testid="stHorizontalBlock"]{
      flex-direction:row!important;flex-wrap:nowrap!important;align-items:stretch!important;
      gap:.26rem!important;width:100%!important}
    div[class*="st-key-weekly_score_grid_"] [data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{
      flex:1 1 0!important;width:0!important;min-width:0!important;max-width:none!important}
    div[class*="st-key-weekly_score_tile_"] [data-testid="stButton"]>button{
      background:rgba(255,255,255,.92)!important;color:#142344!important;
      border:1px solid #dadde2!important;border-radius:12px!important;
      min-height:3.55rem!important;height:3.55rem!important;padding:.22rem .07rem!important;
      width:100%!important;box-shadow:none!important;align-items:center!important;
      justify-content:center!important;white-space:normal!important}
    div[class*="st-key-weekly_score_tile_"] [data-testid="stButton"]>button p{
      color:#69758b!important;font-size:.72rem!important;line-height:1.16!important;
      text-align:center!important;margin:0!important}
    div[class*="st-key-weekly_score_tile_"] [data-testid="stButton"]>button p strong{
      font-size:1.05rem!important;font-weight:900!important;color:#142344!important}
    div[class*="st-key-weekly_score_tile_"][class*="_open"] [data-testid="stButton"]>button p strong{
      color:#16803b!important}
    div[class*="st-key-weekly_score_tile_"][class*="_filled"] [data-testid="stButton"]>button{
      background:#f5f6f8!important}
    div[class*="st-key-weekly_score_tile_"] [data-testid="stButton"]>button:disabled{
      cursor:default!important;opacity:1!important}
    div[class*="st-key-weekly_score_tile_"] [data-testid="stButton"]>button:not(:disabled):hover{
      background:#eef4ff!important;border-color:#709ce0!important}
    div[class*="st-key-weekly_score_tile_"] [data-testid="stButton"]>button[kind="primary"]{
      background:#fff2f4!important;border:2px solid #b82e42!important;
      box-shadow:0 0 0 1px #b82e4240!important}
    div[class*="st-key-weekly_score_grid_"] [data-testid="stVerticalBlock"]{
      gap:.2rem!important}
    .st-key-weekly_selected_score_action{margin:.2rem 0 .36rem!important}
    .weekly-scorecard-heading{margin:0 0 .22rem!important}
    @media(max-width:767px){
      /* Higher specificity than the old outer play-layout mobile column stack. */
      .st-key-weekly_play_layout div[class*="st-key-weekly_score_grid_"] [data-testid="stHorizontalBlock"]{
        flex-wrap:nowrap!important;flex-direction:row!important;gap:.21rem!important}
      .st-key-weekly_play_layout div[class*="st-key-weekly_score_grid_"] [data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{
        flex:1 1 0!important;width:0!important;min-width:0!important}
      .st-key-weekly_scorecard_interactive{padding:.62rem .52rem!important}
      div[class*="st-key-weekly_score_tile_"] [data-testid="stButton"]>button{
        min-height:3.2rem!important;height:3.2rem!important;border-radius:11px!important}
      div[class*="st-key-weekly_score_tile_"] [data-testid="stButton"]>button p{
        font-size:.67rem!important}
      div[class*="st-key-weekly_score_tile_"] [data-testid="stButton"]>button p strong{
        font-size:.98rem!important}
    }
    /* v44.0.6: keep the action slot in place on roll three and improve score contrast. */
    .weekly-final-roll-banner{display:flex;align-items:center;justify-content:center;
      min-height:2.75rem;margin:0;padding:.4rem .6rem;border-radius:12px;
      background:#ecf6ef;border:1px solid #a9d7b7;color:#166534;
      font-weight:850;font-size:.9rem;text-align:center}
    div[class*="st-key-weekly_score_tile_"][class*="_available_gain"]
      [data-testid="stButton"]>button p strong{color:#16733c!important}
    div[class*="st-key-weekly_score_tile_"][class*="_available_zero"]
      [data-testid="stButton"]>button p strong{color:#69758b!important}
    @media(prefers-reduced-motion:reduce){
      .st-key-weekly_dice div[role="group"]>button{animation:none!important}
      .st-key-weekly_dice div[role="group"]>button::after{animation:none!important;content:none!important}
    }
    </style>""", unsafe_allow_html=True)
    st.markdown("<div class='weekly-page-title'>Weekly Yahtzee</div>", unsafe_allow_html=True)
    # Never reuse a cached dashboard for a different signed-in device session.
    scope = f"weekly_{player_id}_{store._actor.session_id}"
    try:
        if not _send_pending(store, scope):
            return
        current = current_week_id()
        history_key = f"{scope}_history_cache"
        if history_key not in st.session_state:
            st.session_state[history_key] = store.history(limit=52)
        history = st.session_state[history_key]
        older = st.session_state.get(f"{scope}_older", [])
        weeks = sorted({current, *(row["week_id"] for row in history), *older}, reverse=True)
        selected_key = f"{scope}_week"
        if st.session_state.get(selected_key) not in weeks:
            st.session_state[selected_key] = current
        week_id = st.selectbox("Challenge week", weeks, key=selected_key,
                               label_visibility="collapsed",
                               format_func=lambda w: week_label(w) + (" · This week" if w == current else ""))
        if len(history) == 52 or older:
            if st.button("Load older weeks", key=f"{scope}_history"):
                page = store.history(before_week=weeks[-1], limit=52)
                st.session_state[f"{scope}_older"] = sorted(set(older + [r["week_id"] for r in page]))
                if page:
                    st.rerun()
                st.caption("No earlier Weekly games.")
        cache_key = f"{scope}_dashboard_cache"
        entry = st.session_state.get(cache_key)
        if not entry or entry["week_id"] != week_id:
            entry = {"week_id": week_id, "data": store.dashboard(week_id)}
            st.session_state[cache_key] = entry
        dashboard = entry["data"]
        # Fresh local time prevents a cached dashboard keeping an expired week open.
        now = datetime.now(ZoneInfo('America/New_York'))
        end = datetime.fromisoformat(dashboard["ends_at"].replace("Z", "+00:00"))
        start = datetime.fromisoformat(dashboard["starts_at"].replace("Z", "+00:00"))
        is_open = start <= now < end
        official, replay = dashboard["official"], dashboard["replay"]
        st.caption(f"Closes {end.astimezone(ZoneInfo('America/New_York')):%b %d}, midnight Eastern · Finish all 13 rounds to count.")
        if official is None:
            st.write("One official game. Thirteen rounds. The same hidden dice opportunities for everyone, with your choices deciding the score.")
            st.caption("No coaching during your official game. After finishing, see friend standings and replay this week's dice for practice.")
            st.button("Start Official Game", disabled=not is_open, type="primary", use_container_width=True,
                      key=f"{scope}_start_{week_id}", on_click=_queue_start, args=(scope, week_id, "start"))
            if not is_open:
                st.info("This week is closed.")
        elif official["completed_at"] is None:
            if is_open:
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
        if st.button("Refresh saved game and friend standings", key=f"{scope}_refresh", use_container_width=True):
            st.session_state.pop(cache_key, None)
            st.session_state.pop(history_key, None)
            st.rerun()
    except WeeklyAuthRequired:
        clear_weekly_state()
        st.warning("Your sign-in expired. Sign out and sign in again to continue your saved Weekly game.")
    except (WeeklyStoreError, WeeklyGameError):
        st.error("Weekly couldn't load right now. Your saved game is unchanged. Please try again.")
        st.button("Try Weekly again", key=f"{scope}_load_retry", use_container_width=True)
