"""Reported same-category tradeoff and honest shared-card language."""
from pathlib import Path
import ast
from hashlib import sha256
from exact_mode import CATEGORY_LABELS, ExactPolicyTable, build_exact_report, _generic_comparison_rows

def main():
    tree = ast.parse(Path(__file__).with_name('exact_mode.py').read_text())
    allowed = {'_comparison_topic','_generic_comparison_rows','_low_pair_open_board_card','_build_comparison_card','_endgame_straight_math_detail'}
    tree.body = [node for node in tree.body if not isinstance(node, ast.FunctionDef) or node.name not in allowed]
    assert sha256(ast.dump(tree).encode()).hexdigest() == 'e436e6dacf52af319ec3a6aaf37536cbc3f2e2d0711675344b3c8e6294b9ab75'
    policy = ExactPolicyTable(Path(__file__).with_name('exact_policy.npz'))
    scorecard = dict.fromkeys(CATEGORY_LABELS)
    scorecard.update(ones=0, twos=4, threes=6)
    ranked = policy.analyze(scorecard, [1,2,2,5,6], 2)
    assert ranked[0]['hold'] == [5,6] and ranked[1]['hold'] == [5]
    assert ranked[0]['strategy_value'] - ranked[1]['strategy_value'] == 0.400543212890625
    for hold in ([5], [5,6]):
        card = build_exact_report(policy, dice=[1,2,2,5,6], scorecard=scorecard, user_hold=hold, roll_number=2)[1]['comparison_card']
        assert len(card['rows']) <= 5
        assert 'deeper scorecard sequencing' not in card['summary']
        assert 'wins through' not in card['summary']
    card = build_exact_report(policy, dice=[1,2,2,5,6], scorecard=scorecard, user_hold=[5], roll_number=2)[1]['comparison_card']
    rows = {r['label']:r for r in card['rows']}
    for label, left, right, advantage in [
        ('Fives','8.33 pts','7.50 pts','left'),
        ('Sixes','4.00 pts','9.00 pts','right'),
        ('Chance total','19.00','21.50','right')]:
        r=rows[label]
        assert (r['left_value'],r['right_value'],r['advantage']) == (left,right,advantage)
    assert 'Straight chances' in rows and 'Straight payoff' not in rows
    assert 'sixes and Chance value' in card['summary']
    assert 'upper-bonus pace' not in card['summary']
    for roll in (1,2):
        forward = _generic_comparison_rows(scorecard,[5],[5,6],roll_number=roll)
        reverse = _generic_comparison_rows(scorecard,[5,6],[5],roll_number=roll)
        for a,b in zip(forward,reverse):
            assert a['label']==b['label']
            assert a['left_value']==b['right_value'] and a['right_value']==b['left_value']
    print('PASS reported ranking, exact gap, same-box evidence, Chance, compactness, symmetric evidence and honest language')

if __name__ == '__main__':
    main()
