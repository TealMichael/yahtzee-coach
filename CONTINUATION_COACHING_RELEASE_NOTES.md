# v43B Phase 2K.14.12 — Points Now vs. Value Later

Literal source of truth: the complete 2K.14.11 Perfect Ten release. This is a
coaching explanation update, not a strategy or layout update.

## What changed

The coach can now explain a verified tradeoff that the category-by-category
table could not explain on its own: one hold earns more this turn, while the
other leaves a more valuable scorecard for subsequent turns.

For the reported keep 6 versus keep 1 position, the visible explanation reads:

> The 1 gives a weak finish a useful home in Ones, leaving the higher upper
> boxes for better turns. Keeping 6 earns about 2.55 more points this turn, but
> keeping 1 leaves about 2.61 more expected points for later. That leaves a
> 0.06-point edge. These choices are effectively tied.

The values come from optimal scoring after seeing the final dice, not from
assuming the player must score Sixes or Ones. The detailed text records the
separate current-turn and future-turn averages and explains the distinction
from the individual scoring paths already shown in the table.

## Similar decisions audited

- Low triples versus higher pairs.
- Keeping a pair/triple versus also keeping an extra high die.
- Close upper-box choices where a weak turn has a less costly scoring home.
- Both Roll 1 and Roll 2; both correct answers and nonoptimal answers.

The evidence covers 67 existing scorecard states with Full House, both
straights and Chance already closed, without a previously scored 50-point
Yahtzee at the starting decision. It checks 585,312 legal hold values.
An audit of best-versus-runner-up comparisons identified 2,548 applicable
positions: 1,283 after Roll 1 and 1,265 after Roll 2. These are possible
positions, not a change to the Daily mix or a promised frequency.

This is not universal coverage. The new wording appears only when the
verified current-turn disadvantage is outweighed by the future-turn gain and
the reconstructed gap matches the production policy. Other positions retain
their existing coaching, including the specialized Full House explanations.

## Existing UI and gameplay preserved

- Same comparison table, numbers, colors, headings and responsive CSS.
- Same Daily question expander; no extra click to read the improved explanation.
- Same shared card in Daily, Practice and friend reviews.
- Same full-hold-ranking disclosure and dynamic ranking data.
- Same solver, policy, best holds, Points Lost, grades and tie tolerances.
- Same Daily puzzles, puzzle balance, saved answers and challenge IDs.
- Same login, PIN recovery, persistence, leaderboards, medals, avatars,
  welcome ceremony, Perfect Ten celebration and friend-group cache hotfix.
- No requirements change, SQL migration, secrets change or account reset.

## Exact runtime scope

| File | Change |
|---|---|
| app.py | Release label only |
| exact_mode.py | Small hook that replaces explanation text for verified comparisons |
| continuation_coaching.py | New prose-only helper; never ranks or grades holds |
| continuation_evidence.npz | New approximately 178 KB precomputed explanation evidence |

No analysis runs during gameplay. The small evidence file is loaded once per
process and reused. The production exact policy is unchanged.

The other changed files are release documentation, one new regression suite,
existing test version/hash guards, and reproducible offline analysis source
under tools/continuation_analysis. The previously missing original solver is
not claimed to have been recovered; this is the independently validated
explanation analysis, now preserved with the project.

## Validation

- 77/77 source regression suites passed with Streamlit 1.52.2.
- 585,312 evidence values checked against the existing policy; maximum
  absolute difference 0.000007590 points.
- 33,768 supported state/dice/roll recommendations agree within the
  0.00002-point validation tolerance. This tolerance is only for the offline
  comparison; it does not change app rankings or tie rules.
- Screenshot example tested for both keep 6 and correct keep 1; comparison
  table rows are unchanged. The existing Daily renderer shows the new text.
- Shared Practice/Daily rendering and Spotlight open/select/reveal/close
  interaction regressions pass.
- Scope audit proves app.py differs only in version, and exact_mode.py only
  in the new explanation hook. All other pre-existing runtime files match
  2K.14.11 byte-for-byte. An AST fingerprint additionally protects the exact
  policy reader/ranking class independently of explanation-file hashes.
- On Streamlit 1.64.0, 76/77 suites passed; the remaining existing test accesses
  a removed AppTest session-state attribute. The same test passes under the
  established 1.52.2 environment. No app dependency or behavior was changed
  to address a test-only compatibility issue.
- Fresh browser visual inspection was unavailable because the browser
  download timed out. Layout/CSS are unchanged and automated shared-renderer
  checks pass; physical iPhone/Safari testing was not performed here.

Exact-policy SHA-256:
`cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b`

## GitHub browser installation

Use BROWSER_UPLOAD_CHANGED_FILES when upgrading from 2K.14.11. Extract it,
open UPLOAD_TO_GITHUB, and upload its contents into your existing repository
root, preserving the tools subfolder. Replace matching files. Do not upload
the ZIP itself or add a nested UPLOAD_TO_GITHUB folder.

The FULL_CURRENT_APP ZIP is the complete cumulative backup. The changed-file
overlay is checked against it before delivery. Refresh the app after deployment
so existing reviews are rebuilt with the updated coaching. Do not replay or
reset the Daily.

No Supabase step is required.

## GitHub commit message

```text
v43B Phase 2K.14.12 - explain points now versus scorecard value later
```
