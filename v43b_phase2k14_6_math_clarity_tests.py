"""Independent immediate-score enumeration and Full House explanation coverage."""
from pathlib import Path
from itertools import product
from fractions import Fraction
from collections import Counter
from exact_mode import ExactPolicyTable, CATEGORIES, build_exact_report, _turn_plan_stats
from coaching_math import immediate_points, explain_full_house, bonus_explanation

def main():
    scorecard=dict.fromkeys(CATEGORIES)
    scorecard.update(ones=1,twos=8,three_of_a_kind=7,four_of_a_kind=6,chance=22)
    opens=tuple(k for k,v in scorecard.items() if v is None)
    # Independent scoring implementation: this screenshot has no live Joker.
    for hold,expected in [((1,1,5,5),Fraction(15)),((5,5),Fraction(1607,108))]:
        scores=[]
        for reroll in product(range(1,7),repeat=5-len(hold)):
            dice=hold+reroll; counts=Counter(dice); faces=set(dice)
            fh=sorted(counts.values())==[2,3]
            ss=any(set(range(start,start+4))<=faces for start in (1,2,3))
            ls=len(faces)==5 and max(faces)-min(faces)==4
            scores.append(max([face*counts[face] for face in (3,4,5,6)]+[25*fh,30*ss,40*ls,50*(len(faces)==1)]))
        assert Fraction(sum(scores),len(scores))==expected
        assert abs(immediate_points(hold,opens)-float(expected))<1e-10
    policy=ExactPolicyTable(Path(__file__).with_name('exact_policy.npz'))
    for hold in ([1,1,5,5],[5,5]):
        meta=build_exact_report(policy,dice=[1,1,5,5,6],scorecard=scorecard,user_hold=hold,roll_number=2)[1]
        card=meta['comparison_card'];summary=card['summary'];detail=card['math_detail']
        for text in ['33.3%','9.3%','16.7%','42.1%','exactly 63','1.78','reverses']:
            assert text in summary,(text,summary)
        for text in ['2/6','20/216','15.00','14.88','only one box','not the chance of earning']:
            assert text in detail,(text,detail)
        assert len(summary)<650
        assert len(card['rows'])<=5
    ranked=policy.analyze(scorecard,[1,1,5,5,6],2)
    assert ranked[0]['strategy_value']==141.605712890625
    assert ranked[1]['strategy_value']==139.82115173339844
    for roll in (1,2):
        for winner in ('left','right'):
            result=explain_full_house(scorecard,(1,1,5,5,5),(5,5,5),roll,winner,2.0)
            assert 'made Full House worth 25' in result[0]
            assert 'no reroll needed' in result[2]
            if roll==1:
                assert 'by Roll 3' in result[0] and 'new hold after Roll 2' in result[2]
                assert 'Best immediate raw score' not in result[2]
    assert explain_full_house(dict(scorecard,full_house=25),(1,1,5,5),(5,5),2,'right',1) is None
    assert explain_full_house(dict(scorecard,yahtzee=50),(1,1,5,5),(5,5),2,'right',1) is None
    closed=explain_full_house(dict(scorecard,fives=10),(1,1,5,5),(5,5),2,'right',.03)
    assert 'effectively tied' in closed[0] and closed[1]=='' and 'Fives is closed' in closed[2]
    assert 'unreachable' in bonus_explanation(dict(scorecard,threes=0,fours=0,fives=0))
    assert 'already earned' in bonus_explanation(dict(scorecard,threes=15,fours=20,fives=25))
    from streamlit.testing.v1 import AppTest
    root=Path(__file__).resolve().parent
    source=(root/'qa_winner_first_app.py').read_text()
    source=source.replace('ROOT = Path(__file__).resolve().parent', f'ROOT = Path({str(root)!r})')
    source=source.replace('report, record = build_exact_report(', "scorecard.update(ones=1, twos=8, three_of_a_kind=7, four_of_a_kind=6, chance=22)\nreport, record = build_exact_report(")
    source=source.replace('dice=[1, 1, 4, 5, 6], scorecard=scorecard, user_hold=[1, 1], roll_number=1', 'dice=[1, 1, 5, 5, 6], scorecard=scorecard, user_hold=[1, 1, 5, 5], roll_number=2')
    at=AppTest.from_string(source,default_timeout=30).run()
    assert not at.exception
    visible=' '.join(str(x.value) for x in at.markdown)
    assert 'Full House chase' not in visible or 'Keeping both pairs' in visible
    for text in ['Keeping both pairs','15.00','14.88','See full hold rankings','exactly 63']:
        assert text in visible,text
    print('PASS independent immediate math, exact ranking, both user outcomes, bank/chase, roll horizons, closed boxes, Joker preservation, near ties and bonus states')

if __name__=='__main__':main()
