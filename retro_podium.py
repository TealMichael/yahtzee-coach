from __future__ import annotations

"""Phase 2K.14.9 personal retro medal moment.

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


def _podium_names_html(board: Iterable[Mapping]) -> str:
    rows = [dict(row) for row in board]
    medals = {1: ("🥇", "GOLD"), 2: ("🥈", "SILVER"), 3: ("🥉", "BRONZE")}
    columns: list[str] = []
    for rank in (1, 2, 3):
        names = [str(row.get("display_name") or "Player") for row in rows if _rank(row) == rank]
        full_name = " / ".join(names) if names else "—"
        visible_name = full_name if len(full_name) <= 28 else full_name[:25].rstrip() + "…"
        emoji, label = medals[rank]
        columns.append(
            f"<div class='podium-name-cell' title='{escape(full_name)}'>"
            f"<span>{emoji}</span><small>{label}</small><b>{escape(visible_name)}</b></div>"
        )
    return (
        "<div class='yesterday-podium-names'>"
        "<div class='podium-names-title'>YESTERDAY'S PODIUM</div>"
        "<div class='podium-names-row'>" + "".join(columns) + "</div></div>"
    )


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
    podium_names = _podium_names_html(rows) if rows else ""
    totals = _medal_totals_html(medal_totals, group_name)
    has_medal = "has-medal" if medal_rank else "no-medal-award"
    mine = _viewer_row(rows, active_player_id)
    if mine and not medal_rank:
        exact = mine.get("exact_count")
        if isinstance(exact, int) and 0 <= exact <= 10:
            subhead = f"You found {exact} best {'hold' if exact == 1 else 'holds'} yesterday."
    confetti = "".join(
        f"<i style='--x:{7 + n * 7}%;--d:{(n % 4) * .09}s;--c:{('#ffd369', '#64dbcb', '#ff89b6')[n % 3]}'></i>"
        for n in range(13)
    ) if medal_rank == 1 else ""
    date = escape(date_label)
    player = escape(active_player_name or "Player")
    headline = escape(headline)
    subhead = escape(subhead)

    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    *{{box-sizing:border-box}}html,body{{margin:0;padding:0;background:transparent;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}}
    .moment{{position:relative;height:560px;overflow:hidden;border:1px solid #475378;border-radius:22px;background:radial-gradient(ellipse at 50% 30%,#354779 0,#182443 48%,#10192e 100%);color:#fff4d7;cursor:pointer;isolation:isolate}}
    .moment:before,.moment:after{{content:'';position:absolute;top:-70px;width:50%;height:440px;background:linear-gradient(#ffdc8530,transparent);clip-path:polygon(44% 0,56% 0,100% 100%,0 100%);pointer-events:none;z-index:-1}}
    .moment:before{{left:0;transform:rotate(20deg)}}.moment:after{{right:0;transform:rotate(-20deg)}}
    .skip{{position:absolute;z-index:20;right:12px;top:12px;border:1px solid #8e9bb8;border-radius:20px;background:#17233d;color:#fff4d7;font:700 10px ui-monospace;padding:7px 10px;cursor:pointer}}.skip:focus-visible{{outline:3px solid #ffd369;outline-offset:3px}}
    .top{{position:relative;text-align:center;padding:18px 16px 0}}.date{{font-size:9px;letter-spacing:.12em;color:#c0cce4;margin-right:54px;margin-left:54px;min-height:12px}}
    .welcome{{font-size:12px;color:#e2eafa;margin:16px 0 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .headline{{font-size:clamp(18px,4.8vw,26px);line-height:1.12;font-weight:1000;color:#ffda85;letter-spacing:-.03em;margin:0 auto;max-width:500px;text-shadow:0 3px 0 #080f22}}
    .sub{{font:500 11px/1.4 ui-monospace;color:#d4dff3;margin:8px auto 0;max-width:440px;min-height:30px}}
    .scene{{position:absolute;left:6%;right:6%;top:148px;height:164px;display:grid;grid-template-columns:minmax(0,1fr) 64px minmax(0,1fr);align-items:end;border-bottom:2px solid #d5b873;background:radial-gradient(ellipse at bottom,#f8d98b25,transparent 70%)}}
    .person{{text-align:center;min-width:0;opacity:0;animation:enter .35s ease-out .2s both}}.player-person{{animation-delay:.45s}}.sprite{{height:133px;display:flex;align-items:flex-end;justify-content:center}}.sprite svg{{width:130px;max-width:100%;height:auto;max-height:140px;image-rendering:pixelated;filter:drop-shadow(0 6px 3px #0005)}}
    .name{{display:inline-block;max-width:100%;margin:5px 0 8px;font-size:9px;font-weight:800;color:#edf2ff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .medal-space{{position:relative;height:140px;display:flex;flex-direction:column;align-items:center;justify-content:center;opacity:0;animation:enter .4s ease-out 2.2s both}}.handoff-medal{{position:relative;width:54px;height:76px;animation:lift .6s ease-in-out 2.6s both}}
    .ribbon{{position:absolute;top:0;width:17px;height:34px;background:#4785db;clip-path:polygon(0 0,100% 0,75% 100%,25% 100%)}}.r1{{left:10px}}.r2{{right:10px;background:#eaf0ff;border-left:4px solid #e5627b}}
    .coin{{position:absolute;left:5px;top:29px;width:44px;height:44px;border:3px solid #fff2af;background:var(--medal);color:#182443;display:grid;place-items:center;font-weight:1000;font-size:18px;border-radius:50%;box-shadow:inset 0 0 0 3px #0002,0 0 24px #ffd36940}}
    .shine{{position:absolute;right:-12px;top:31px;color:#fff4c5;font-size:25px;opacity:0;animation:flash .6s ease-out 2.8s}}.medal-word{{margin-top:5px;font-size:8px;font-weight:800;color:#d9e4fa}}.quiet-star{{font-size:32px;color:#ffda85}}
    .has-medal .player-person{{animation:enter .35s ease-out .45s both,lift .6s ease-in-out 2.6s}}
    .yesterday-podium-names{{position:absolute;left:5%;right:5%;top:327px;color:#fff4d7}}.podium-names-title{{text-align:center;font-size:8px;letter-spacing:.16em;color:#b9c9e8;margin-bottom:8px}}.podium-names-row{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;text-align:center;align-items:end}}
    .podium-name-cell{{min-width:0;border:1px solid #ffffff20;border-radius:10px 10px 3px 3px;padding:9px 3px;background:linear-gradient(#ffffff15,#ffffff05);opacity:0;animation:enter .35s ease-out both}}.podium-name-cell:nth-child(1){{animation-delay:1.9s;border-color:#ffda8570;background:linear-gradient(#ffcf6530,#ffcf6508)}}.podium-name-cell:nth-child(2){{animation-delay:1.45s}}.podium-name-cell:nth-child(3){{animation-delay:1s}}.podium-name-cell span{{font-size:23px;display:block;line-height:1.2}}.podium-name-cell small{{display:block;font-size:7px;letter-spacing:.08em;margin:3px 0;color:#d1ddf3}}.podium-name-cell b{{display:block;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .medal-totals{{position:absolute;left:5%;right:5%;bottom:49px;border-top:1px solid #ffffff20;padding-top:9px;opacity:0;animation:enter .35s ease-out 3s both}}.medal-total-title{{text-align:center;font-size:8px;color:#b9c9e8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:8px}}.medal-total-row{{display:grid;grid-template-columns:repeat(3,1fr);text-align:center}}.medal-total-row>div{{display:flex;gap:5px;align-items:center;justify-content:center}}.medal-total-row span{{font-size:16px}}.medal-total-row small{{font-size:7px;color:#c7d5ed}}.medal-total-row b{{font-size:16px;color:#fff4d7}}
    .tap{{position:absolute;left:10px;right:10px;bottom:16px;text-align:center;font-size:10px;color:#ffda85;opacity:0;animation:enter .3s ease-out 3.5s both}}
    .confetti{{position:absolute;inset:0;pointer-events:none;overflow:hidden}}.confetti i{{position:absolute;left:var(--x);top:25%;width:5px;height:9px;background:var(--c);opacity:0;animation:confetti .8s ease-out calc(2.6s + var(--d)) both}}
    @keyframes enter{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:none}}}}@keyframes lift{{50%{{transform:translateY(-10px)}}}}@keyframes flash{{50%{{opacity:1;transform:scale(1.3)}}100%{{opacity:0;transform:scale(1.6)}}}}@keyframes confetti{{15%{{opacity:1}}100%{{opacity:0;transform:translateY(230px) rotate(210deg)}}}}
    .moment.skip-now *{{animation:none!important}}.moment.skip-now .person,.moment.skip-now .medal-space,.moment.skip-now .podium-name-cell,.moment.skip-now .medal-totals,.moment.skip-now .tap{{opacity:1!important;transform:none!important}}.moment.skip-now .skip{{display:none}}.moment.skip-now .confetti{{display:none}}
    @media(max-width:350px){{.headline{{font-size:18px}}.sub{{font-size:10px}}.scene{{left:3%;right:3%;grid-template-columns:minmax(0,1fr) 54px minmax(0,1fr)}}.medal-total-row small{{display:none}}.podium-name-cell b{{font-size:9px}}}}
    @media(prefers-reduced-motion:reduce){{.moment *{{animation:none!important}}.person,.medal-space,.podium-name-cell,.medal-totals,.tap{{opacity:1!important;transform:none!important}}.confetti,.skip{{display:none}}}}
    </style></head><body>
      <div class='moment {has_medal}' id='moment' role='group' aria-label='Yesterday medal moment'>
        <button class='skip' id='skip' type='button'>SKIP ›</button>
        <div class='top'><div class='date'>🏆 {date}</div><div class='welcome'>Welcome back, {player}.</div><div class='headline'>{headline}</div><div class='sub'>{subhead}</div></div>
        <div class='scene'>
          <div class='person mike-person'><div class='sprite'>{mike_svg}</div><div class='name'>PIXEL MIKE</div></div>
          {medal}
          <div class='person player-person'><div class='sprite'>{player_svg}</div><div class='name'>{player}</div></div>
        </div>
        <div class='confetti' aria-hidden='true'>{confetti}</div>
        {podium_names}
        {totals}
        <div class='tap'>New day. Ten new decisions.</div>
      </div>
      <script>(function(){{const root=document.getElementById('moment'),skip=document.getElementById('skip');function finish(){{root.classList.add('skip-now')}}setTimeout(finish,4000);document.addEventListener('keydown',e=>{{if(e.key==='Escape')finish()}});skip.addEventListener('click',e=>{{e.stopPropagation();finish()}});root.addEventListener('click',e=>{{if(!e.target.closest('#skip'))finish()}})}})();</script>
    </body></html>"""


# Compatibility alias for older source-level tests/imports during this handoff.
def podium_ceremony_html(board: Iterable[Mapping], **kwargs) -> str:
    kwargs.setdefault("avatar_config", {})
    kwargs.setdefault("medal_totals", {})
    return personal_medal_moment_html(board, **kwargs)
