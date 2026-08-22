from pathlib import Path

APP = Path(__file__).with_name('app.py').read_text()

checks = [
    ('mobile breakpoint 640', '@media (max-width:640px)' in APP),
    ('small-mobile breakpoint 390', '@media (max-width:390px)' in APP),
    ('result hero exists', "class='result-hero'" in APP),
    ('hold comparison exists', "class='hold-compare'" in APP),
    ('three-step coach exists', "class='coach-three'" in APP),
    ('key lesson exists', "class='lesson-card-v41'" in APP),
    ('details collapsed', 'with st.expander("Strategy details", expanded=False)' in APP),
    ('hold rank visible', "class='rank-chip'" in APP and '🏆 Hold rank:' in APP),
    ('session progress rail exists', "class='progress-rail'" in APP),
    ('mobile hold cards stack', '.hold-compare { grid-template-columns:1fr;' in APP),
    ('mobile coach steps stack', '.coach-three { grid-template-columns:1fr;' in APP),
    ('independent dice buttons preserved', '_render_independent_dice_picker(' in APP and 'toggle_die_index(' in APP),
    ('duplicate dice positions are keyed independently', 'key=f"{key_prefix}_die_{die_index}"' in APP),
    ('dice scroll guard preserved', 'install_dice_scroll_guard()' in APP),
]

failed = []
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
    if not ok:
        failed.append(name)

if failed:
    raise SystemExit(f"{len(failed)} UI polish checks failed: {', '.join(failed)}")
print(f"\n{len(checks)} PASS / 0 FAIL")
