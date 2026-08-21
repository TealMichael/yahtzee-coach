from __future__ import annotations

"""Phase 2K.11.1 personal retro medal moment.

This is intentionally icing-only: Pixel Mike + the signed-in player's saved
sprite + one medal handoff on a clean light card.  No game math, puzzle, Daily,
or ranking logic lives here.
"""

from html import escape
from typing import Iterable, Mapping

from player_avatar import avatar_svg, normalize_avatar_config

_MEDAL = {
    1: ("GOLD", "#f6c944", "🥇"),
    2: ("SILVER", "#cbd5e1", "🥈"),
    3: ("BRONZE", "#c97834", "🥉"),
}


def _rank(row: Mapping) -> int:
    try:
        return int(row.get("rank") or 0)
    except Exception:
        return 0


def _viewer_row(board: Iterable[Mapping], player_id: str) -> dict | None:
    target = str(player_id or "")
    for row in board:
        if str(row.get("player_id") or "") == target:
            return dict(row)
    return None


def _rank_tied(board: Iterable[Mapping], rank: int) -> bool:
    return sum(1 for row in board if _rank(row) == int(rank)) > 1


def medal_moment_copy(board: Iterable[Mapping], player_id: str) -> tuple[str, str, int | None]:
    rows = [dict(row) for row in board]
    mine = _viewer_row(rows, player_id)
    if mine is None:
        winner = next((row for row in rows if _rank(row) == 1), None)
        if winner:
            return "YESTERDAY'S RESULTS ARE IN", f"{winner.get('display_name', 'A friend')} took gold. Your fresh 10 is ready.", None
        return "NEW DAY. NEW 10.", "Yesterday is in the books. Today's Daily is ready.", None

    rank = _rank(mine)
    tied = _rank_tied(rows, rank)
    if rank == 1:
        return ("TIED FOR GOLD!" if tied else "YOU WON YESTERDAY!", "Can you defend the title?", 1)
    if rank == 2:
        return ("TIED FOR SILVER!" if tied else "YOU TOOK SILVER!", "One step from gold. Can you climb today?", 2)
    if rank == 3:
        return ("TIED FOR BRONZE!" if tied else "YOU MADE THE PODIUM!", "Can you move up today?", 3)
    prefix = "Tied for" if tied else "You finished"
    return f"{prefix} #{rank} YESTERDAY", "New day. New 10.", None


def _pixel_mike() -> str:
    mike = {
        "hair": "curly",
        "outfit": "pink_tee",
        "skin": "light",
        "accessory": "none",
        "shoes": "white",
    }
    return avatar_svg(mike, width=170, pose="give", title="Pixel Mike")


def _medal_html(rank: int | None) -> str:
    if rank not in _MEDAL:
        return "<div class='medal-space no-medal'><div class='quiet-star'>★</div><div class='medal-word'>FRESH START</div></div>"
    label, color, emoji = _MEDAL[rank]
    return (
        f"<div class='medal-space'><div class='handoff-medal' style='--medal:{color}' aria-label='{label} medal'>"
        "<div class='ribbon r1'></div><div class='ribbon r2'></div>"
        f"<div class='coin'>{rank}</div><div class='shine'>✦</div></div><div class='medal-word'>{emoji} {label}</div></div>"
    )


def _medal_totals_html(totals: Mapping | None, group_name: str) -> str:
    values = dict(totals or {})
    gold = int(values.get("gold") or 0)
    silver = int(values.get("silver") or 0)
    bronze = int(values.get("bronze") or 0)
    group = f" · {escape(group_name)}" if group_name else ""
    return f"""
    <div class='medal-totals'>
      <div class='medal-total-title'>ALL-TIME MEDALS{group}</div>
      <div class='medal-total-row'>
        <div><span>🥇</span><small>GOLD</small><b>{gold}</b></div>
        <div><span>🥈</span><small>SILVER</small><b>{silver}</b></div>
        <div><span>🥉</span><small>BRONZE</small><b>{bronze}</b></div>
      </div>
    </div>"""


def personal_medal_moment_html(
    board: Iterable[Mapping],
    *,
    active_player_id: str,
    active_player_name: str,
    group_name: str,
    date_label: str,
    avatar_config: Mapping | None,
    medal_totals: Mapping | None,
) -> str:
    """Return one compact, silent, skippable next-day personal result moment."""
    rows = [dict(row) for row in board]
    headline, subhead, medal_rank = medal_moment_copy(rows, active_player_id)
    player_pose = "receive" if medal_rank else "idle"
    player_svg = avatar_svg(
        normalize_avatar_config(avatar_config),
        width=170,
        pose=player_pose,
        title=active_player_name or "Player",
    )
    mike_svg = _pixel_mike()
    medal = _medal_html(medal_rank)
    totals = _medal_totals_html(medal_totals, group_name)
    has_medal = "has-medal" if medal_rank else "no-medal-award"
    date = escape(date_label)
    player = escape(active_player_name or "Player")
    headline = escape(headline)
    subhead = escape(subhead)

    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    *{{box-sizing:border-box}}html,body{{margin:0;padding:0;background:transparent;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}}
    .moment{{position:relative;height:510px;overflow:hidden;border:3px solid #172033;border-radius:20px;background:#fff9ea;color:#172033;box-shadow:0 8px 0 #d9d2c3;image-rendering:pixelated;cursor:pointer;user-select:none}}
    .moment:before{{content:'✦';position:absolute;left:7%;top:48px;color:#72a8d2;font-size:18px;text-shadow:330px 34px 0 #efad22,270px -28px 0 #72a8d2,40px 110px 0 #efad22;opacity:.9}}
    .skip{{position:absolute;z-index:20;right:12px;top:11px;border:2px solid #172033;background:#fffdf7;color:#172033;font:1000 10px ui-monospace;padding:6px 8px;box-shadow:2px 2px 0 #9aa6b6}}
    .top{{position:relative;z-index:3;text-align:center;padding:19px 54px 0}}
    .date{{font-size:8px;font-weight:1000;letter-spacing:.15em;color:#708096;text-transform:uppercase}}
    .headline{{margin:8px auto 0;max-width:420px;font-size:25px;line-height:1.02;font-weight:1000;color:#ffc62f;text-shadow:3px 0 #172033,-3px 0 #172033,0 3px #172033,0 -3px #172033,3px 3px #d86e16;letter-spacing:.02em}}
    .sub{{margin-top:9px;font:900 12px/1.2 ui-monospace;color:#172033}}
    .scene{{position:absolute;left:4%;right:4%;top:118px;height:230px;display:grid;grid-template-columns:1fr 74px 1fr;align-items:end;z-index:4}}
    .person{{text-align:center;position:relative;opacity:0;transform:translateY(10px);animation:enter .28s steps(4,end) .15s forwards}}
    .player-person{{animation-delay:.48s}}
    .sprite{{height:174px;display:flex;align-items:flex-end;justify-content:center}}
    .name{{display:inline-block;margin-top:-6px;background:#172033;color:#fff9ea;border:2px solid #172033;padding:4px 9px;font-size:9px;font-weight:1000;box-shadow:2px 2px 0 #9aa6b6;max-width:150px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .medal-space{{position:relative;height:154px;display:flex;flex-direction:column;justify-content:center;align-items:center;opacity:0;animation:medalIn .45s steps(5,end) .95s forwards}}
    .no-medal-award .medal-space{{animation-delay:.70s}}.quiet-star{{font-size:30px;color:#d0d7df;text-shadow:2px 2px 0 #172033}}
    .handoff-medal{{position:relative;width:54px;height:76px;transform:translateX(-52px)}}
    .ribbon{{position:absolute;top:0;width:17px;height:34px;background:#2f6eb3;clip-path:polygon(0 0,100% 0,75% 100%,25% 100%)}}.r1{{left:10px}}.r2{{right:10px;background:#f8fafc;border-left:4px solid #d63a42}}
    .coin{{position:absolute;left:5px;top:29px;width:44px;height:44px;border:4px solid #172033;background:var(--medal);display:grid;place-items:center;font-weight:1000;font-size:18px;border-radius:50%;box-shadow:inset 0 0 0 3px rgba(255,255,255,.30),3px 3px 0 #d69b1b}}
    .shine{{position:absolute;right:-12px;top:31px;color:#f6b816;font-size:25px;opacity:0;animation:flash .34s steps(3,end) 1.28s forwards}}
    .medal-word{{margin-top:4px;font-size:9px;font-weight:1000;color:#526078}}
    .has-medal .player-person{{animation:enter .28s steps(4,end) .48s forwards,bounce .38s steps(3,end) 1.32s 2}}
    .medal-totals{{position:absolute;z-index:5;left:8%;right:8%;bottom:52px;border:3px solid #172033;border-radius:12px;background:#18223a;color:#fff9ea;box-shadow:4px 4px 0 #98a4b4;padding:8px 10px 9px;opacity:0;transform:translateY(10px);animation:enter .24s steps(4,end) 1.62s forwards}}
    .medal-total-title{{text-align:center;font-size:9px;font-weight:1000;letter-spacing:.08em;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .medal-total-row{{display:grid;grid-template-columns:repeat(3,1fr);text-align:center;gap:5px}}
    .medal-total-row>div{{border-right:1px dashed #536078}}.medal-total-row>div:last-child{{border-right:0}}
    .medal-total-row span{{font-size:20px;display:block;line-height:1}}.medal-total-row small{{display:block;font-size:7px;font-weight:1000;margin-top:2px}}.medal-total-row b{{display:block;font-size:19px;margin-top:1px}}
    .medal-total-row>div:nth-child(1) small{{color:#ffd23f}}.medal-total-row>div:nth-child(2) small{{color:#e5e7eb}}.medal-total-row>div:nth-child(3) small{{color:#e28a3e}}
    .tap{{position:absolute;z-index:5;left:0;right:0;bottom:15px;text-align:center;font-size:8px;font-weight:1000;color:#708096;opacity:0;animation:enter .18s steps(2,end) 1.92s forwards}}
    @keyframes enter{{to{{opacity:1;transform:none}}}}@keyframes medalIn{{0%{{opacity:0;transform:translateX(-30px)}}35%{{opacity:1}}100%{{opacity:1;transform:none}}}}@keyframes flash{{0%{{opacity:0;transform:scale(.4)}}55%{{opacity:1;transform:scale(1.25)}}100%{{opacity:0;transform:scale(1.75)}}}}@keyframes bounce{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-7px)}}}}
    .moment.skip-now *{{animation:none!important}}.moment.skip-now .person,.moment.skip-now .medal-space,.moment.skip-now .medal-totals,.moment.skip-now .tap{{opacity:1!important;transform:none!important}}.moment.skip-now .handoff-medal{{transform:none!important}}.moment.skip-now .skip{{display:none}}
    @media(max-width:420px){{.moment{{height:495px}}.headline{{font-size:21px}}.scene{{top:116px;grid-template-columns:1fr 58px 1fr}}.sprite svg{{width:142px}}.medal-totals{{left:5%;right:5%}}}}
    @media(prefers-reduced-motion:reduce){{.moment *{{animation-duration:.01s!important;animation-delay:0s!important}}.person,.medal-space,.medal-totals,.tap{{opacity:1!important;transform:none!important}}.handoff-medal{{transform:none!important}}}}
    </style></head><body>
      <div class='moment {has_medal}' id='moment' role='group' aria-label='Yesterday medal moment'>
        <button class='skip' id='skip' type='button'>SKIP ›</button>
        <div class='top'><div class='date'>🏆 {date}</div><div class='headline'>{headline}</div><div class='sub'>{subhead}</div></div>
        <div class='scene'>
          <div class='person mike-person'><div class='sprite'>{mike_svg}</div><div class='name'>PIXEL MIKE</div></div>
          {medal}
          <div class='person player-person'><div class='sprite'>{player_svg}</div><div class='name'>{player}</div></div>
        </div>
        {totals}
        <div class='tap'>TAP TO FINISH · PLAY TODAY'S 10 BELOW</div>
      </div>
      <script>(function(){{const root=document.getElementById('moment'),skip=document.getElementById('skip');function finish(){{root.classList.add('skip-now')}}skip.addEventListener('click',e=>{{e.stopPropagation();finish()}});root.addEventListener('click',e=>{{if(!e.target.closest('#skip'))finish()}})}})();</script>
    </body></html>"""


# Compatibility alias for older source-level tests/imports during this handoff.
def podium_ceremony_html(board: Iterable[Mapping], **kwargs) -> str:
    kwargs.setdefault("avatar_config", {})
    kwargs.setdefault("medal_totals", {})
    return personal_medal_moment_html(board, **kwargs)
