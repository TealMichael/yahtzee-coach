import ast
from pathlib import Path
from types import SimpleNamespace
from perfect_ten import is_perfect_ten, perfect_ten_html
from retro_podium import personal_medal_moment_html
from daily_challenge import summarize_attempt


def run():
    yes={'questions':10,'exact_count':10,'perfect':True}
    assert is_perfect_ten(yes)
    for no in ({'questions':9,'exact_count':9,'perfect':True},
        {'questions':10,'exact_count':9,'perfect':False,'total_ev_loss':0.00001},
        {'questions':0,'exact_count':0,'perfect':True},{}):assert not is_perfect_ten(no)
    doc=perfect_ten_html(player_id='p',challenge_id='today</script>',player_name='<Mike & Jenny>',avatar_config={})
    assert '&lt;Mike &amp; Jenny&gt;' in doc and 'today</script>' not in doc
    assert 'localStorage.getItem' in doc and '1700' in doc and 'prefers-reduced-motion' in doc
    assert '<audio' not in doc and '<img' not in doc
    for rank in (1,2,3,4):
        doc=personal_medal_moment_html([{'player_id':'p','display_name':'Mike','rank':rank,'exact_count':10}],active_player_id='p',active_player_name='Mike',group_name='Friends',date_label='Yesterday',avatar_config={},medal_totals={})
        assert 'Yesterday, you played a perfect ten.' in doc
    tree=ast.parse((Path(__file__).parent/'app.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('build_daily_share_text','render_leaderboard_cards')]
    import html
    rendered=[]
    class Expander:
        def __enter__(self):return self
        def __exit__(self,*args):pass
    env={'st':SimpleNamespace(session_state=type('State',(dict,),{'__getattr__':dict.__getitem__})(daily_date_key='today',active_player_id='p'),markdown=lambda text,**kw:rendered.append(text),expander=lambda *a,**k:Expander(),caption=lambda *a:None),'html':html,'is_perfect_ten':is_perfect_ten,'_daily_date_label':lambda x:x,'_share_square':lambda x:'🟩','PUBLIC_APP_URL':'https://example.com'}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'app.py','exec'),env)
    summary={**yes,'total_ev_loss':0.0,'best_exact_streak':10}
    assert 'PERFECT TEN' in env['build_daily_share_text']([{}]*10,summary)
    assert 'PERFECT TEN' not in env['build_daily_share_text']([{}]*10,{**summary,'exact_count':9,'perfect':False})
    env['render_leaderboard_cards']([{'rank':1,'player_id':'p','display_name':'<Mike>','total_ev_loss':0,'exact_count':10},{'rank':1,'player_id':'q','display_name':'Other','total_ev_loss':0.00001,'exact_count':9}])
    assert rendered[0].count('🏅 Perfect Ten')==1 and '&lt;Mike&gt;' in rendered[0]
    print('PASS eligibility, rounded near miss, partial attempts, share/standings, ceremony tiers and safe HTML')

if __name__=='__main__':run()
