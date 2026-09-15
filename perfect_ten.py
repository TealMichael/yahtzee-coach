"""Presentation only; eligibility comes from the existing Daily summary."""
from html import escape
import json
from player_avatar import avatar_svg, normalize_avatar_config


def is_perfect_ten(summary):
    return summary.get('questions') == 10 and summary.get('exact_count') == 10 and summary.get('perfect') is True


def perfect_ten_html(*, player_id, challenge_id, player_name, avatar_config):
    sprite = avatar_svg(normalize_avatar_config(avatar_config), width=90, pose='receive', title=player_name or 'Player')
    # JSON is a script literal, never executable player text. Escape script terminators.
    key = json.dumps('yc_perfect_ten_v1:' + json.dumps([str(player_id), str(challenge_id)])).replace('<', '\\u003c')
    return """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;background:transparent;font-family:system-ui,sans-serif}
.card{position:relative;overflow:hidden;min-height:180px;padding:22px 18px;border:2px solid #c69b36;border-radius:20px;background:linear-gradient(125deg,#fff9e6,#ffefbb);color:#30260e;display:flex;gap:14px;align-items:center}
.avatar{flex:0 0 80px}.avatar svg{width:80px;height:auto;image-rendering:pixelated}.copy{min-width:0}.eyebrow{font-size:10px;letter-spacing:.12em;font-weight:800;color:#765a14}h2{font-size:clamp(23px,6vw,32px);margin:4px 0;line-height:1.1}p{font-size:13px;line-height:1.4;margin:6px 0 0}.name{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.spark{position:absolute;inset:0;pointer-events:none}.spark i{position:absolute;left:var(--x);top:-12px;width:6px;height:10px;background:var(--c);opacity:0}.celebrate .spark i{animation:fall 1.3s ease-out var(--d) both}.celebrate .avatar{animation:lift .5s ease-out .15s 2}
@keyframes fall{10%{opacity:1}100%{opacity:0;transform:translateY(190px) rotate(240deg)}}@keyframes lift{50%{transform:translateY(-6px)}}
@media(prefers-reduced-motion:reduce){.celebrate *{animation:none!important}.spark{display:none}}
@media(max-width:350px){.card{padding:18px 12px;gap:10px}.avatar{flex-basis:62px}.avatar svg{width:62px}p{font-size:12px}}
</style></head><body><section class="card" aria-label="Perfect Ten"><div class="avatar">""" + sprite + """</div><div class="copy"><div class="eyebrow">DAILY ACHIEVEMENT</div><h2>PERFECT TEN!</h2><div class="name">""" + escape(player_name or 'Player') + """</div><p>Ten decisions. You found every best hold.</p></div><div class="spark" aria-hidden="true">""" + ''.join(
        f'<i style="--x:{4+i*8}%;--d:{i%3*.08}s;--c:{("#d3a02b", "#237e5d", "#cc655e")[i%3]}"></i>' for i in range(12)
    ) + """</div></section><script>(()=>{const key=""" + key + """;let first=false;try{first=localStorage.getItem(key)!=='seen';localStorage.setItem(key,'seen')}catch(e){first=false;/* Keep a static badge when durable seen-state is unavailable. */}const card=document.querySelector('.card');if(first&&!matchMedia('(prefers-reduced-motion: reduce)').matches){card.classList.add('celebrate');setTimeout(()=>card.classList.remove('celebrate'),1700)}card.addEventListener('click',()=>card.classList.remove('celebrate'));})();</script></body></html>"""
