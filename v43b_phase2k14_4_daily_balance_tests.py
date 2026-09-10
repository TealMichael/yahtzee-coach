"""Forward-only decision balance, exact policy, and eight-week regressions."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

from audit_daily_balance import audit
from daily_challenge import daily_challenges, daily_challenge_version
from puzzle_bank import _bank_break_day_plan

ROOT = Path(__file__).resolve().parent


def main():
    for day, expected in {
        '2026-08-28': 'c48bc2b0a59d6fba736d12e86a710f2811715d68823c332896f15c9e2663b719',
        '2026-09-01': 'd40cc985e4eabd95be535c3f721fb24d55b3687feec25341320e62671f03c64e',
        '2026-09-05': 'a05826a3151c275e7b584eb2b847fb6a663c4701e0c5c4d3cc4539e9bccbd80c',
        '2026-09-06': '26db12691d54b4c9e48c19faeba2820cfbc037241dbb200f530987f8f3c26f4b',
    }.items():
        assert sha256(json.dumps(daily_challenges(day), sort_keys=True).encode()).hexdigest() == expected
    assert daily_challenge_version('2026-09-06') == '43B-bank42.6-2K12'
    assert daily_challenge_version('2026-09-07') == '43B-bank42.6-2K14-4'
    for file, expected in {
        'exact_mode.py':'b0d5395973a1b6918f298f21a951eac8c5f6e9d82a7b140749720811983524b5',
        'exact_policy.npz':'cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b',
        'daily_spotlight.py':'119c516ee9c82118b462619d63d00b87c93bd02883af34e7629e9aa929d4f274',
    }.items():
        assert sha256((ROOT/file).read_bytes()).hexdigest() == expected
    print('PASS forward-only Sep7 boundary, historical fingerprints and frozen policy/coaching')
    result = audit()
    old, new = result['baseline'], result['patched']
    assert new['totals']['straight'] < old['totals']['straight']
    assert max(new['straight_per_day']) <= 3
    assert 1.7 <= new['totals']['bonus']/56 <= 2.5
    assert new['totals']['sensitive'] > old['totals']['sensitive']
    assert new['totals']['repeated_holds'] < old['totals']['repeated_holds']
    assert new['totals']['consecutive_patterns'] < old['totals']['consecutive_patterns']
    assert all(5 <= day['families'] <= 7 for day in new['days'])
    outcomes = Counter()
    for day in new['days']:
        puzzles = daily_challenges(day['date'])
        assert puzzles == daily_challenges(day['date'])
        specials = [c for c in puzzles if c.get('puzzle_theme') == 'Bank It or Break It']
        assert len(specials) <= 1
        assert bool(specials) == bool(_bank_break_day_plan(day['date']))
        if specials:
            outcomes[specials[0]['bank_break_outcome']] += 1
    assert abs(outcomes['BANK']-outcomes['BREAK']) <= 2
    print('PASS 56 days: hard composition, family variety, bank/break schedule, determinism')
    print('PASS straight/bonus/repetition balance:', old['totals'], '->', new['totals'])


if __name__ == '__main__':
    main()
