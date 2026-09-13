"""Personal celebration content and entry-point regression."""
from pathlib import Path
from retro_podium import personal_medal_moment_html


def render(board, player='me'):
    return personal_medal_moment_html(board, active_player_id=player,
        active_player_name='Mike <T>', group_name='Friends & Family',
        date_label='Yesterday', avatar_config={}, medal_totals={'gold':4})


def run():
    for rank in (1, 2, 3, 4):
        doc=render([{'player_id':'me','display_name':'Mike <T>','rank':rank,'exact_count':7}])
        assert 'Welcome back, Mike &lt;T&gt;.' in doc
        assert "<i style=" in doc if rank == 1 else "<i style=" not in doc
        assert 'setTimeout(finish,4000)' in doc
        assert "e.key==='Escape'" in doc
        assert 'prefers-reduced-motion' in doc
        assert '<audio' not in doc and 'https://' not in doc
        if rank == 4: assert 'You found 7 best holds yesterday.' in doc
    doc=render([{'player_id':'me','display_name':'Mike','rank':4,'exact_count':1}])
    assert '1 best hold yesterday' in doc
    missing=render([{'player_id':'a','display_name':'Jenny','rank':1}])
    assert 'Your fresh 10 is ready.' in missing and '<i style=' not in missing
    empty=render([])
    assert 'NEW DAY. NEW 10.' in empty
    assert "<div class='yesterday-podium-names'>" not in empty
    tied=render([{'player_id':'me','display_name':'Mike','rank':1},
        {'player_id':'b','display_name':'Jenny','rank':1},
        {'player_id':'c','display_name':'Paul','rank':3}])
    assert 'TIED FOR GOLD!' in tied and 'Mike / Jenny' in tied
    assert "title='—'" in tied
    app=(Path(__file__).parent/'app.py').read_text()
    section=app.split('def render_yesterday_final_standings_if_needed()')[1].split('def render_daily_intro()')[0]
    assert section.index('key="yesterday_final_start_today"') < section.index('components.html(ceremony')
    assert section.count('key="yesterday_final_start_today"') == 1
    assert 'if len(members) > 1:' in section
    assert 'mark_yesterday_ceremony_seen_now(today)' in section
    print('PASS personal outcomes, safety, tie podium, no media, skip, motion and immediate Play entry')

if __name__ == '__main__': run()
