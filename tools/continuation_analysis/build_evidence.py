import csv,json,math,hashlib
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];p=dict(np.load(root/'exact_policy.npz'));rows=defaultdict(lambda:defaultdict(list))
for row in csv.DictReader(open('terminal_choices.csv')):
 rows[int(row['state'])][tuple(map(int,row['dice']))].append((float(row['total_value']),int(row['score_now']),int(row['category'])))
rolls=[tuple(map(int,r)) for r in p['rolls']];codes=p['hold_codes'];si={int(k):i for i,k in enumerate(p['state_keys'])}
def enc(r):return sum(r.count(f)<<(3*(f-1)) for f in range(1,7))
for key,term in rows.items():
 already_earned=35 if ((key>>13)&63)==63 else 0
 err=max(abs(max(term[r])[0]-already_earned-float(p['roll2_hold_values'][si[key],i,list(codes[i]).index(enc(r))])) for i,r in enumerate(rolls))
 assert err<0.00002,(key,err)
print('states',len(rows))
holds=sorted({int(c) for row in codes for c in row if c>=0});hi={c:i for i,c in enumerate(holds)}
hold_dice=[tuple(f for f in range(1,7) for _ in range((c>>(3*(f-1)))&7)) for c in holds]
W=np.zeros((len(holds),252))
for h,held in enumerate(hold_dice):
 hc=Counter(held);n=5-len(held)
 for j,r in enumerate(rolls):
  rc=Counter(r)
  if any(hc[f]>rc[f] for f in hc):continue
  counts=[rc[f]-hc[f] for f in range(1,7)]
  W[h,j]=math.factorial(n)/math.prod(math.factorial(c) for c in counts)/6**n
assert np.max(abs(W.sum(axis=1)-1))<1e-12
keys=sorted(rows);allstats=[];audit=[]
for key in keys:
 upper=(key>>13)&63;term=rows[key];termstats=[]
 for r in rolls:
  total,score,cat=max(term[r]);total-=35 if upper==63 else 0
  now=score+(35 if cat<6 and upper<63<=upper+score else 0)
  termstats.append([total,now,float(now==0),float(cat==0)])
 stats2=W@np.array(termstats)
 selected=[]
 for i,r in enumerate(rolls):
  hs=[hi[int(c)] for c in codes[i] if c>=0];h=max(hs,key=lambda h:stats2[h,0]);selected.append(stats2[h])
 stats1=W@np.array(selected)
 maxerr=0;best_mismatches=0
 for stage,stats in [(1,stats1),(2,stats2)]:
  for i,r in enumerate(rolls):
   hs=[hi[int(c)] for c in codes[i] if c>=0];source=p[f'roll{stage}_hold_values'][si[key],i,:len(hs)]
   maxerr=max(maxerr,float(np.max(abs(source-stats[hs,0]))))
   selected_h=int(np.argmax(stats[hs,0]))
   if float(max(source)-source[selected_h])>2e-5:best_mismatches+=1
 assert maxerr<2e-5,(key,maxerr)
 assert best_mismatches==0
 allstats.append([stats1,stats2]);audit.append({'state':key,'max_value_error':maxerr,'best_mismatches':best_mismatches})
np.savez_compressed(root/'continuation_evidence.npz',state_keys=np.array(keys),hold_codes=np.array(holds),stats=np.array(allstats),policy_sha256=np.array([hashlib.sha256((root/'exact_policy.npz').read_bytes()).hexdigest()]))
Path('evidence_audit.json').write_text(json.dumps({'states':len(keys),'legal_hold_values_checked':len(keys)*2*4368,'max_error':max(x['max_value_error'] for x in audit),'results':audit},indent=2))
print('VALIDATED',len(keys)*2*4368,'values; max error',max(x['max_value_error'] for x in audit),'asset bytes',(root/'continuation_evidence.npz').stat().st_size)
