"""Verified now/later arithmetic, safe coverage, and unchanged shared card UI."""
from pathlib import Path
import hashlib
import ast
import numpy as np
from exact_mode import CATEGORIES, ExactPolicyTable, build_exact_report, _generic_comparison_rows
from continuation_coaching import _evidence, explain_continuation

ROOT=Path(__file__).resolve().parent

def main():
    # Updating the explanation-file fingerprint must never mask a solver change.
    tree=ast.parse((ROOT/'exact_mode.py').read_text())
    solver=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ExactPolicyTable')
    assert hashlib.sha256(ast.dump(solver).encode()).hexdigest()=='b1b9aadeb17076afafb1d27be602446c34d6c2abb75f44f68f47937d32ea5027'
    policy=ExactPolicyTable(ROOT/'exact_policy.npz')
    states,holds,stats=_evidence()
    assert len(states)==67
    with np.load(ROOT/'continuation_evidence.npz',allow_pickle=False) as d:
        assert str(d['policy_sha256'][0])==hashlib.sha256((ROOT/'exact_policy.npz').read_bytes()).hexdigest()
    checked=0
    for key,si in states.items():
        pi=int(np.searchsorted(policy.state_keys,key)); assert int(policy.state_keys[pi])==key
        for ri,codes in enumerate(policy.hold_codes):
            hs=[holds[int(c)] for c in codes if c>=0]
            for stage,source in [(0,policy.roll1_values),(1,policy.roll2_values)]:
                assert np.max(abs(stats[si,stage,hs,0]-source[pi,ri,:len(hs)]))<0.00002
                chosen=int(np.argmax(stats[si,stage,hs,0]))
                assert max(source[pi,ri,:len(hs)])-source[pi,ri,chosen]<0.00002
                checked+=len(hs)
    assert checked==585312
    sc=dict.fromkeys(CATEGORIES);sc.update(full_house=25,small_straight=30,large_straight=40,chance=16)
    for hold in ([6],[1]):
        report,meta=build_exact_report(policy,dice=[1,2,3,5,6],scorecard=sc,user_hold=hold,roll_number=2)
        card=meta['comparison_card'];summary=card['summary']
        assert 'weak finish' in summary and 'Ones' in summary and 'later' in summary
        assert 'effectively tied' in summary and not card['takeaway']
        assert card['rows']==_generic_comparison_rows(sc,hold,[1] if hold==[6] else [2],roll_number=2)
        assert summary in report
        assert len(summary)<450
        if hold==[6]:
            assert all(x in summary for x in ['2.55','2.61','0.06'])
            assert meta['points_lost']==0.06000518798828125
            assert all(x in card['math_detail'] for x in ['3.162','5.708','115.236','112.630'])
    # Additional exact tradeoffs, not screenshot-specific hold matching.
    low_triple=explain_continuation(255,(5,5),(1,1,1),2,'right',
        float(stats[states[255],1,holds[3],0]-stats[states[255],1,holds[2<<(3*4)],0]))
    assert low_triple and '5.29' in low_triple[0] and '5.51' in low_triple[0]
    assert explain_continuation(2303,(6,),(1,),2,'right',0.8) is None
    assert explain_continuation(8191,(6,),(1,),2,'right',0.06) is None
    assert explain_continuation(2303|(1<<19),(6,),(1,),2,'right',0.06) is None
    assert explain_continuation(2303,(6,),(1,),3,'right',0.06) is None
    assert explain_continuation(2303,(1,),(1,),2,'right',0) is None
    # Existing shared renderer and Daily disclosure stay in use.
    from streamlit.testing.v1 import AppTest
    source=(ROOT/'qa_winner_first_app.py').read_text().replace('ROOT = Path(__file__).resolve().parent',f'ROOT = Path({str(ROOT)!r})')
    source=source.replace('report, record = build_exact_report(', 'scorecard.update(full_house=25,small_straight=30,large_straight=40,chance=16)\nreport, record = build_exact_report(')
    source=source.replace('dice=[1, 1, 4, 5, 6], scorecard=scorecard, user_hold=[1, 1], roll_number=1','dice=[1,2,3,5,6], scorecard=scorecard, user_hold=[6], roll_number=2')
    at=AppTest.from_string(source,default_timeout=30).run();assert not at.exception
    visible=' '.join(str(x.value) for x in at.markdown)
    assert 'weak finish' in visible and 'See full hold rankings' in visible
    print('PASS 585312 hold values, 67 states, correct and nonoptimal coaching, original table rows, bounds, and Daily renderer')

if __name__=='__main__': main()
