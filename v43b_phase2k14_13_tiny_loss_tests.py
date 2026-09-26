"""Q5 rounding regression: presentation only, never scoring tolerance."""
from pathlib import Path
import ast
from exact_mode import CATEGORIES, ExactPolicyTable, build_exact_report
from loss_display import format_points_loss

ROOT = Path(__file__).resolve().parent

def main():
    for value, expected in [(0, '0.00'), (.003757476806640625, '<0.01'),
                            (.0049, '<0.01'), (.0051, '0.01'), (.01, '0.01'), (.06, '0.06')]:
        assert format_points_loss(value) == expected
    sc = dict.fromkeys(CATEGORIES)
    sc.update(twos=0, fives=10, sixes=24, three_of_a_kind=18, four_of_a_kind=7,
              full_house=25, small_straight=30, chance=26)
    policy = ExactPolicyTable(ROOT/'exact_policy.npz')
    report, record = build_exact_report(policy, dice=[1,4,5,5,5], scorecard=sc, user_hold=[4], roll_number=2)
    assert record['points_lost'] == .003757476806640625
    assert record['grade'] == 'A' and record['hold_rank'] == 2
    assert record['comparison_card']['edge'] == '<0.01'
    assert 'excellent choice' in record['comparison_card']['summary']
    assert '0.00 expected pts' not in report
    assert 'Expected game points lost: 0.003757' in report
    from daily_challenge import is_exact_record, best_exact_streak
    assert not is_exact_record(record)
    assert best_exact_streak([{'points_lost':0}, record, {'points_lost':0}]) == 1
    # Run the unchanged share-color logic with only its required globals.
    module = ast.parse((ROOT/'app.py').read_text())
    square = next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='_share_square')
    scope = {}
    exec(compile(ast.Module(body=[square],type_ignores=[]), 'app.py', 'exec'),scope)
    assert scope['_share_square'](record['points_lost']) == '🟨'
    _, optimal = build_exact_report(policy, dice=[1,4,5,5,5], scorecard=sc, user_hold=[1,4,5], roll_number=2)
    assert optimal['grade'] == 'A+' and optimal['points_lost'] == 0
    from streamlit.testing.v1 import AppTest
    source = (ROOT/'qa_winner_first_app.py').read_text()
    source = source.replace('ROOT = Path(__file__).resolve().parent', f'ROOT = Path({str(ROOT)!r})')
    source = source.replace('"_render_daily_review_body",', '"_render_daily_review_body", "_daily_review_item",')
    source = source.replace('report, record = build_exact_report(', f'scorecard = {sc!r}\nreport, record = build_exact_report(')
    source = source.replace('dice=[1, 1, 4, 5, 6], scorecard=scorecard, user_hold=[1, 1], roll_number=1',
                            'dice=[1,4,5,5,5], scorecard=scorecard, user_hold=[4], roll_number=2')
    source = source.replace('_render_daily_review_body(answer)', 'answer["challenge"]["daily_number"] = 5\n_daily_review_item(answer)')
    at = AppTest.from_string(source, default_timeout=30).run()
    assert not at.exception
    assert at.expander[0].label == 'Q5 · A · <0.01 points lost'
    markup = '\n'.join(str(x.value) for x in at.markdown)
    assert '<strong>&lt;0.01</strong>' in markup
    assert '+&lt;0.01' not in markup and '<strong>+0.00</strong>' not in markup
    assert 'excellent choice' in markup and 'See full hold rankings' in markup
    print('PASS Q5 label, shared card, rankings, report, boundaries; grade, yellow square and streak unchanged')

if __name__ == '__main__':
    main()
