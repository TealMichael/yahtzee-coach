# v43B Phase 2K.14.14 — Zero-Yahtzee Joker Coaching

Baseline: the supplied complete 2K.14.13 project. Presentation only.

## Why this update exists

In the reported Q7 decision, the dice were 1, 5, 5, 5, 5 with only Ones,
Small Straight, Large Straight and Chance open. Fives was filled, Yahtzee
contained zero, and Four of a Kind was also filled. The exact policy correctly
recommends keeping four 5s, ahead of keeping one 5 by 3.510734558 expected
remaining-game points.

An easily missed official rule explains the ranking: a later five-of-a-kind
may be used as a Joker even when the Yahtzee box contains **zero**. There is
no 100-point bonus, but when the matching upper box has already been scored,
the player can score an open Large Straight for 40 or Small Straight for 30.
The official Hasbro clarification is:
https://hasbro-apac-eng.custhelp.com/app/answers/detail/a_id/975/

Keeping four 5s with two rerolls gives an 11/36 (30.6%) chance of completing
five 5s. Keeping just one 5 gives approximately 0.9% for that specific Joker
finish. The ordinary natural-straight probabilities remain separate and valid.

## Changes

- The existing comparison card now names the zero-Yahtzee Joker rule whenever
  the winning hold is four matching dice, its upper category is already
  filled, and at least one straight box remains open.
- Shows the chance to finish the five-of-a-kind with the rerolls left. Where
  both compared holds chase the same face, an existing lower-value evidence
  row is replaced with a compact Joker-odds comparison (e.g., 0.9% vs 30.6%).
- Clarifies that the existing Straight chances row counts ordinary straights,
  **not** Joker scoring. The takeaway and math note make the distinction clear.
- The shared Daily/Practice comparison card remains capped at five rows.
- New regression suite verifies Q7's ranking, margin, odds and grade; Roll 2;
  correct-answer reviews; non-Joker situations; and frozen policy integrity.

## Unchanged

`exact_policy.npz`, the policy integrity fingerprint, all 3,669,120 stored
hold values, best-hold rankings, grades, scoring rules, challenge selection,
past Daily attempts, persistence, authentication, and Supabase integration.
This release needs no SQL migration, new secrets or dependency changes.

## GitHub browser installation

1. Unzip the delivered release ZIP and open `UPLOAD_TO_GITHUB`.
2. In the existing GitHub `yahtzee-coach` repository root, upload **all files
   inside** `UPLOAD_TO_GITHUB`, replacing files with matching names. This
   includes the updated version checks in existing test files.
3. Commit with `v43B Phase 2K.14.14 - explain zero-Yahtzee Joker opportunities`.
4. Allow the existing Streamlit app to redeploy; refresh Daily Review or Practice.

Do not upload the `UPLOAD_TO_GITHUB` folder itself, or nest the
`yahtzee-coach-main` folder in GitHub. The `yahtzee-coach-main` directory in
the ZIP is a cumulative full-project backup. Only `exact_mode.py` and the
release label in `app.py` change runtime behavior; the other changed files
are documentation or test/version checks. Existing score and account data
remain in Supabase and are not contained in this ZIP.
