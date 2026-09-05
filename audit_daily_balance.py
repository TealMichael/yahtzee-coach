"""Reproducible baseline/patched eight-week selection audit; no DB access."""
from collections import Counter
from datetime import date, timedelta
from time import perf_counter
import json
from pathlib import Path

from daily_balance import decision_evidence
from puzzle_bank import _data, _generate_phase2k9_daily_challenge_set


def audit():
    start = perf_counter()
    straight, bonus, sensitive, codes = decision_evidence()
    evidence_ms = (perf_counter() - start) * 1000
    data = _data()
    index = {(int(r['state_index']), int(r['roll_id']), int(r['roll_number'])): i for i, r in enumerate(data['rows'])}
    rolls = {tuple(int(x) for x in r): i for i, r in enumerate(data['rolls'])}
    output = {'evidence_cold_ms': round(evidence_ms, 2)}
    for balanced in (False, True):
        counts = Counter(); hist = Counter(); bonus_hist = Counter(); families = Counter(); daily = []; previous = set(); generation = []
        for offset in range(56):
            key = (date(2026, 9, 7) + timedelta(days=offset)).isoformat()
            started = perf_counter()
            puzzles = _generate_phase2k9_daily_challenge_set(key, decision_balance=balanced)
            generation.append((perf_counter() - started) * 1000)
            ids = [index[(c['bank_state_index'], rolls[tuple(c['dice'])], c['roll_number'])] for c in puzzles]
            s, b, verified = (sum(flags[i] for i in ids) for flags in (straight, bonus, sensitive))
            patterns = Counter(codes[i] for i in ids)
            active = {codes[i] for i in ids if straight[i] or bonus[i]}
            counts.update(straight=s, bonus=b, sensitive=verified, repeated_holds=sum(n-1 for n in patterns.values()), consecutive_patterns=len(active & previous))
            previous = active
            hist[s] += 1; bonus_hist[b] += 1
            families.update(c['skill_tag'] for c in puzzles)
            assert Counter(c['roll_number'] for c in puzzles) == {1: 5, 2: 5}
            assert Counter(c['stage'] for c in puzzles) == {'Opening':2,'Midgame':3,'Late Game':3,'True Endgame':2}
            assert Counter(c['difficulty'] for c in puzzles) == {'Hard':2,'Medium':3,'Clear':2,'Punishing':2,'Knife-edge':1}
            assert Counter(c['scorecard_origin'] for c in puzzles) == {'Simulated Game':9,'Curated Edge Case':1}
            assert len(set(c['bank_state_index'] for c in puzzles)) == 10
            daily.append({'date':key,'straight':s,'bonus':b,'sensitive':verified,'families':len(set(c['skill_tag'] for c in puzzles))})
        output['patched' if balanced else 'baseline'] = {'totals':dict(counts),'straight_per_day':dict(sorted(hist.items())), 'bonus_per_day':dict(sorted(bonus_hist.items())), 'families':dict(families),'mean_generation_ms':round(sum(generation)/56,2),'max_generation_ms':round(max(generation),2),'days':daily}
    return output


if __name__ == '__main__':
    result = audit()
    Path('DAILY_BALANCE_AUDIT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: {a:b for a,b in v.items() if a != 'days'} if isinstance(v,dict) else v for k,v in result.items()}, indent=2))
