from pathlib import Path

ROOT = Path(__file__).parent

def run():
    app = (ROOT / 'app.py').read_text(encoding='utf-8')
    fragment_start = app.index('def _practice_choice_fragment():')
    start = app.index('def render_practice_mode():')
    end = app.index('def render_help_feedback_footer():', start)
    practice = app[fragment_start:end]
    checks = [
        ('Practice has a clean player-facing header', '🎯 Practice' in practice and 'Unlimited practice · instant coaching after every decision' in practice),
        ('Daily crossover is compact', '🏆 Daily complete · View leaderboard' in practice and "daily-rank-banner" not in practice),
        ('Session dashboard no longer leads the puzzle', practice.find('render_session_progress') > practice.find('render_result')),
        ('Scenario remains visible before the decision', 'practice-scenario' in practice and 'practice-description' in practice),
        ('Practice uses the same strong Roll 1/Roll 2 cue', 'daily-roll-stage' in practice and 'roll_label = "First roll"' in practice and 'reroll_word' in practice and 'remaining' in practice),
        ('Scorecard remains above dice decision', practice.find('render_scorecard(scorecard)') < practice.find('Which dice would you keep?')),
        ('Dice instructions are simplified', 'Tap the dice you want to keep. Leave all five unselected to reroll everything.' in practice),
        ('Primary answer action remains Submit hold', 'Submit hold' in practice),
        ('Coach result remains immediate after submit', 'render_result(st.session_state.report)' in practice),
        ('Next puzzle is the primary post-coaching action', 'Next Practice Puzzle →' in practice and practice.find('Next Practice Puzzle →') < practice.find('See my practice progress')),
        ('Practice progress is collapsed', 'with st.expander("📈 See my practice progress", expanded=False)' in practice),
        ('Badges and session coach moved into secondary progress', practice.find('render_new_badges()') > practice.find('See my practice progress') and practice.find('render_session_coach') > practice.find('See my practice progress')),
        ('Session history stays collapsed at bottom', 'with st.expander("Session history", expanded=False)' in practice),
        ('Exact solver diagnostics remain available only through existing debug panel', 'render_solver_panel(st.session_state.solver_history)' in practice),
        ('Practice navigation hotfix remains callback-based', 'on_click=_set_app_mode' in practice and 'args=("Daily Challenge",)' in practice),
    ]
    failed=[]
    for name, ok in checks:
        print(('PASS' if ok else 'FAIL'), name)
        if not ok: failed.append(name)
    if failed:
        raise SystemExit(f'{len(failed)} failed: {failed}')
    print(f'{len(checks)} PASS / 0 FAIL')

if __name__ == '__main__':
    run()
