# Offline now-versus-later evidence

This is analysis source, NOT the app's ranking engine. The app never executes it.
The original `exact_policy.npz` is not rewritten. `build_evidence.py` writes only
`continuation_evidence.npz`, and only after matching every supported hold value
to the existing policy within 0.00002 points.

## Scope

67 existing policy states: Full House, both straights and Chance closed; no
already-scored 50-point Yahtzee at the starting decision. Remaining categories
are a subset of the six upper boxes, Three of a Kind, Four of a Kind, and Yahtzee.
The solver includes subsequent Yahtzee bonuses and mandatory Joker placement
after Yahtzee is filled (including zero), plus the 35-point upper bonus.
It is intentionally not a complete replacement for the production solver.

Each plan records total expected remaining points, expected points this turn,
probability of scoring zero this turn, and probability of choosing Ones.
The scoring box is selected after seeing the final roll. With two rerolls,
the next hold is also chosen optimally. These are NOT category-committed plans.
Newly earned upper bonuses count in this turn's points; previously earned
bonuses are excluded, matching the production remaining-score convention.
Tied terminal scoring choices use the deterministic tuple order in the builder;
the split describes one optimal continuation rather than all possible tie paths.

## Reproduce

From this directory, with C++17, Python and NumPy installed:

```bash
g++ -O3 -std=c++17 solver.cpp -o solver
./solver
OPENBLAS_NUM_THREADS=1 python build_evidence.py
```

`states.txt` is the explicit audited set of production state keys. The C++ tool
writes `terminal_choices.csv`; the Python tool enumerates weighted dice outcomes
and validates 585,312 legal hold values over both roll stages before exporting.
The largest observed error is below 0.000008 points (the policy stores float32).
All 33,768 state/dice/roll recommendations agree within the validation tolerance.

The final Python app uses the frozen, approximately 178 KB evidence file with a
one-entry load cache. Unsupported positions, nonmatching gaps and decisions
without a verified now-versus-later tradeoff retain their existing explanations.
The coaching helper never supplies a ranking, grade, recommendation or Points Lost.

`coverage_examples.json` records an audit of best-versus-runner-up comparisons:
1,283 Roll 1 and 1,265 Roll 2 positions receive the new explanation. This is a
count of possible positions, not a promised number of Daily questions.
