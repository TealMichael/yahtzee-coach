"""Narrow upper-zero filter, exceptions, historical identity, future Daily mix."""
from datetime import date, timedelta
from hashlib import sha256
import json
from puzzle_bank import _implausible_upper_zero, _data, _realistic_state_mask
from daily_challenge import daily_challenges, daily_challenge_version
from v43b_phase2k12_scorecard_realism_tests import _assert_locked_composition

def main():
    for face in range(6):
        row = [-1]*13
        row[face] = 0
        assert _implausible_upper_zero(row, 'Simulated Game') == (face >= 2)
        assert not _implausible_upper_zero(row, 'Curated Edge Case')
        for chance in (0, 12):
            row[12] = chance
            assert not _implausible_upper_zero(row, 'Simulated Game')
    for upper, blocked in [
        ([0,4,0,-1,-1,-1],True), # Under pressure, but reachable
        ([0,0,0,0,-1,-1],False), # Maximum 55: Dead
        ([3,10,0,20,30,-1],False), # Already 63: Earned
        ([3,10,0,20,-1,-1],True),
    ]:
        assert _implausible_upper_zero(upper+[-1]*7,'Simulated Game') == blocked
    data=_data()
    flags=[i for i,r in enumerate(data['scorecards']) if _implausible_upper_zero(r,str(data['origin'][i]))]
    assert len(flags)==4
    assert not any(_realistic_state_mask()[i] for i in flags)
    for day, expected in {
        '2026-08-22':'2ff789df6f41b4c7f077b32e6e7354efc789802d5fccb741edb53ceb39346389',
        '2026-09-07':'b0501b8cd18e3874b2052f67226157d62bf8bf98609c7e152e4856b6b3696939',
        '2026-09-08':'83bc6d084d9afb866b4a9c86197b6a0ac10febe78a40811e13ff9ace9bb91e38',
    }.items():
        assert sha256(json.dumps(daily_challenges(day),sort_keys=True).encode()).hexdigest()==expected
    assert daily_challenge_version('2026-09-08')=='43B-bank42.6-2K14-4'
    assert daily_challenge_version('2026-09-09')=='43B-bank42.6-2K14-5'
    for offset in range(60):
        day=(date(2026,9,9)+timedelta(days=offset)).isoformat()
        puzzles=daily_challenges(day)
        _assert_locked_composition(puzzles)
        for p in puzzles:
            i=p['bank_state_index']
            assert not _implausible_upper_zero(data['scorecards'][i],str(data['origin'][i]))
    print('PASS 4 filtered contexts; low-face/Dead/Earned/used-Chance/curated exceptions; historical identity; 600 future puzzles and hard mix')

if __name__=='__main__': main()
