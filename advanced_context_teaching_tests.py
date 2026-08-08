from pathlib import Path
import numpy as np

from exact_mode import ExactPolicyTable, build_exact_report
from puzzle_bank import scorecard_for_state_index

ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / 'exact_policy.npz')
BANK = np.load(ROOT / 'puzzle_bank.npz', allow_pickle=False)


def find_state(*, bonus=None, yahtzee=None, max_open=None, chance_open=None):
    for i in range(len(BANK['state_keys'])):
        if bonus is not None and str(BANK['bonus_status'][i]) != bonus:
            continue
        if yahtzee is not None and str(BANK['yahtzee_status'][i]) != yahtzee:
            continue
        if max_open is not None and int(BANK['open_count'][i]) > max_open:
            continue
        card = scorecard_for_state_index(i)
        if chance_open is not None and (card['chance'] is None) != chance_open:
            continue
        return i, card
    raise AssertionError('No matching puzzle-bank context found')


def report_for(index, card, roll_number=2):
    dice = tuple(int(x) for x in POLICY.rolls[(index * 37 + 11) % 252])
    best, _ = POLICY.best_hold(card, dice, roll_number)
    report, meta = build_exact_report(POLICY, dice=dice, scorecard=card, user_hold=best, roll_number=roll_number)
    return report, meta


def main():
    i, card = find_state(bonus='Earned')
    report, _ = report_for(i, card)
    assert 'upper bonus is already secured' in report
    print('PASS bonus-secured teaching')

    i, card = find_state(bonus='Dead')
    report, _ = report_for(i, card)
    assert 'upper bonus is mathematically out of reach' in report
    print('PASS bonus-dead teaching')

    i, card = find_state(yahtzee='Live 50')
    report, _ = report_for(i, card)
    assert 'another Yahtzee can carry the 100-point bonus' in report
    print('PASS extra-Yahtzee/Joker context teaching')

    i, card = find_state(max_open=2)
    report, _ = report_for(i, card)
    assert 'True endgame:' in report
    assert 'Generic opening rules matter much less now' in report
    print('PASS true-endgame teaching')

    i, card = find_state(max_open=3, chance_open=True)
    report, _ = report_for(i, card)
    assert 'Chance is one of very few remaining escape valves' in report
    print('PASS Chance-timing context teaching')

    print('ALL ADVANCED SCORECARD-CONTEXT TEACHING TESTS PASSED')

if __name__ == '__main__':
    main()
