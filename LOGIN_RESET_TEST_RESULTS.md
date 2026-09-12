# v43B Phase 2K.14.7 — Release verification

Release gate: run all 72 standalone regression suites from the freshly extracted final ZIP. See the release handoff for the observed pass count.

14/14 protected artifacts match 2K.14.6 byte-for-byte: exact_policy.npz, exact_mode.py, coaching_math.py, exact_runtime.py, yahtzee_engine.py, puzzle_bank.py, daily_challenge.py, daily_balance.py, player_avatar.py, retro_podium.py, requirements.txt, puzzle_bank.npz, challenge_catalog.npz, puzzle_bank_contexts.csv.

Only app.py, daily_store.py, and supabase_daily_store.py changed at runtime. No coaching renderer, dice-control function, CSS, strategy, score, or puzzle-generation change.

New tests exercise the persistent credential lifecycle, unauthorized reset and listing rejection, current-PIN verification, leading-zero PIN generation, secret hashing, selected-player form targeting, and one-rerun PIN display. SQL permissions and transaction structure are inspected; no live database reset is claimed.

The packaged runner writes per-suite logs and a summary when run with:

```text
python run_release_tests.py --logs ../test_logs --workers 4
```
