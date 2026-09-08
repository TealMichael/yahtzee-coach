CURRENT RELEASE: v43B Phase 2K.14.5. Use REALISM_RELEASE_NOTES.md for current scope and deployment.
The following is retained historical documentation for 2K.14.4 and earlier.

# v43B Phase 2K.14.4 — Daily Decision Balance + Coaching Clarity (revised)

This replacement includes the original balance patch below plus the coaching
revision described in COACHING_REVISION.md. Install this revised package only.
Statements below about unchanged coaching describe the original balance patch;
the revised package additionally changes four presentation functions in exact_mode.py.

Literal baseline: packaged Phase 2K.14.3. Effective date: September 7, 2026,
using the existing shared America/New_York Daily date. Deploy before that date.
If installing later, do not switch mid-day: ask for a new forward-only date.

## Eight-week comparison (September 7–November 1; 560 puzzles per build)

| Selection measure | Baseline | New |
|---|---:|---:|
| Straight-related decisions | 148 (2.64/day) | 88 (1.57/day) |
| Days with at least four straight-related decisions | 9 | 0 |
| Upper-pair-or-more bonus candidates | 100 (1.79/day) | 125 (2.23/day) |
| Candidates with verified subtotal sensitivity | 8 | 51 |
| Repeated exact best holds within a day (extra occurrences) | 80 | 2 |
| Shared straight/bonus best-hold patterns between neighboring days | 52 | 43 |

New straight counts: zero on 6 days, one on 20, two on 22, three on 8.
New bonus-candidate counts: one on 5 days, two on 34, three on 16, four on 1.
These are soft preferences, not fixed quotas or guarantees for every future date.
All 56 new Dailies retain five to seven families and the fixed roll, stage,
difficulty, origin and state-uniqueness constraints. Bank/break reservations
and Joker scheduling are preserved, not replaced with bonus quotas.

## Definitions and limits

Straight-related means Straight Structure label OR the catalog's exact best hold
contains at least three distinct dice fitting an available Small/Large Straight.
It does not mean a straight statistic merely appears in the coach. This is a
screening rule; it can include decisions that reject a straight chase and does
not establish the causal contribution of straights to full-game value.

Bonus candidate means the bonus is unearned but mathematically reachable and
the best hold keeps two to four matching dice for an open upper box. This is
more recognizable than a singleton but does not prove the bonus causes the hold.
Sensitivity is separately verified using packaged model states with the SAME
open-category mask and extra-Yahtzee eligibility but a different upper subtotal.
An alternative within four expected points of best must change its margin
against the held dice by at least 0.50 points. The comparison is within each
state; absolute values across different scorecards are never subtracted as a
bonus decomposition. Only existing supported states are used. Lower filled
scores may differ but do not affect this model's remaining-game choices.

Within-day repetition is penalized by exact best-hold code. A deterministic
date-dependent preference rotates patterns without recursively generating
yesterday. Across-day repetition is measured in the audit, not forcibly banned.
No new causal claims are added to the coach.

## Performance

Local eight-week timing: mean uncached date generation 333ms baseline versus
352ms new. The evidence index takes about 233ms once per server process and is
then cached. Separate fresh-process Daily checks measured 524ms baseline versus
719ms new; same-date cached calls measured 0.15ms versus 0.17ms. These are local
measurements, not promised live Streamlit timings. No database reads were added.

## Preservation and deployment

Thirty dates August 8–September 6 matched baseline puzzle dictionaries exactly.
Historical versions and challenge IDs remain unchanged. Post-boundary challenge
IDs/version identify the new selection algorithm. Shared same-date caching and
copy isolation remain intact. Practice selection is unchanged.

Runtime edits: puzzle_bank.py (guarded Daily-only preferences), daily_challenge.py
(future version boundary), new daily_balance.py (cached selection evidence), and
app.py (release label only). UI/coaching, exact_mode.py, exact_runtime.py, policy,
source catalog/bank, persistence, authentication, SQL, avatars and medals stay
unchanged. No Supabase migration.

Commit: `v43B Phase 2K.14.4 - balance Daily straight and bonus decisions`
