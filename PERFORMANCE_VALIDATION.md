# v43B Phase 2K.14.8 — Validation

14 protected gameplay/account/model artifacts match 2K.14.7 byte-for-byte:

exact_policy.npz, exact_runtime.py, yahtzee_engine.py, coaching_math.py, daily_store.py, puzzle_bank.py, daily_challenge.py, daily_balance.py, player_avatar.py, retro_podium.py, requirements.txt, puzzle_bank.npz, challenge_catalog.npz, puzzle_bank_contexts.csv

Local benchmark, 280 full reports across 14 Daily sets (best and reroll-everything holds):

{
  "reports": 280,
  "baseline_seconds": 0.34133549800003493,
  "patched_seconds": 0.22304514400002518,
  "warm_baseline_seconds": 0.054639128999951936,
  "warm_patched_seconds": 0.05566917700002705,
  "outputs_identical": true
}

Only the diagnostic lookup_ms field is excluded from report equality. All report text and other metadata match. These timings measure local report calculations, not total app startup or live database latency.

Packaged-release gate: run all 73 standalone suites from a fresh extraction of the complete ZIP, including the new performance/history regression. The handoff contains the actual final pass count.
