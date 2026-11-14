# Yahtzee Coach v44.0 — installation guide

**Ready to install.** Local Chromium checks passed for Weekly play/replays and
the full Daily journey at phone and desktop widths. Physical iPhone and your
live hosting remain post-install checks. Nothing has been uploaded to GitHub
or run in your production Supabase project.

This updates the supplied **v43B Phase 2K.14.14** app. Keep your existing
accounts, friend groups, Streamlit app, Supabase project, and secrets.

## What is in the browser package

- `UPLOAD_TO_GITHUB/`: all changed and new project files, including tests and notes.
- `RUN_THIS_ONCE_IN_SUPABASE_v44_0.sql`: the complete database upgrade.
- This guide and `VALIDATION_v44_0.md`.

The full-project ZIP is a separate complete source copy for backup and future
work. Use the smaller browser package for your usual update workflow.

## 1. Run the database upgrade first

1. Unzip the browser package on your Mac.
2. Open the Supabase project used by **Yahtzee Coach**. Open **SQL Editor**.
3. Start a new query. Open `RUN_THIS_ONCE_IN_SUPABASE_v44_0.sql`, copy its entire
   contents, paste into that query, and run it.
4. Continue only after the SQL succeeds. If it reports an error, retain the
   error and do not upload the app yet.

Run the combined v44 file only. Do not run `SUPABASE_SCHEMA.sql`, `v43b_schema.sql`,
old classroom scripts, or the two component migrations separately. The combined
file already includes both components. It is safe to rerun and does not erase
history. The old app can still use its ten-puzzle day before activation.

## 2. Upload the app files in GitHub

1. Open your existing Yahtzee Coach repository and its deployed branch.
2. In the root where `app.py` lives, choose **Add file → Upload files**.
3. Open `UPLOAD_TO_GITHUB` on your Mac. Select **all files inside it** and drag
   those files into GitHub. Upload their contents, not the enclosing folder or ZIP.
4. Confirm `app.py`, `weekly_game.py`, `weekly_store.py`, `weekly_ui.py`, and the
   other files are at the repository root. Keep the existing unchanged files.
5. Use this commit message and commit the upload:

   `v44.0 - add saved Weekly games and versioned six-puzzle Daily`

Streamlit should update from the repository. If the old version remains visible,
use **Reboot app** in your Streamlit workspace. In the app's Help area, check for
**Yahtzee Coach · v44.0**. No new secret or production dependency is needed.

## 3. Activate Daily Six

Sign in and open **Daily Challenge once after the update**. The server records
the next midnight Eastern as the six-puzzle start. Everyone shares that date.

For example, opening the updated Daily on November 13 schedules the change for
November 14 at 12:00 a.m. Eastern. Until then, that day's ten questions remain.
Migration reruns, server restarts, and later sign-ins cannot move the date.
Any already-registered ten-puzzle date retains its original questions and ID.

Optional read-only confirmation in SQL Editor:

```sql
select six_effective_date, activated_at
from public.yc_daily_format_config;
```

A null date means no updated Daily page has activated it yet. Do not change
this row manually or try to force a mid-day switch.

## 4. Check the installed app on your phone

Confirm the v44.0 label, sign-in, and navigation among Daily, Weekly, Practice,
and My Player. Verify your existing history and friend group are present.
The first updated Daily visit schedules the next midnight Eastern; the current
day keeps its registered question count. No account reset is needed.

For an additional full-game test, use synthetic players in a separate test
Supabase project and deployment:

1. Sign in with remembering off, then on. Visit Daily, Weekly, Practice, and My Player.
2. In Weekly, start, hold dice, reroll, score, refresh, leave, and return.
   Confirm the saved state resumes and all five dice fit in portrait.
3. Finish 13 rounds. Confirm the official score locks, friend standings reveal,
   and a replay does not replace that score. Check the 13-category scorecard.
4. Sign out, sign in as the other test player, and confirm no prior player's
   game or friend scores appear before completion.
5. Check Daily's final review, edit/back controls, submission, sharing, friend
   review, and yesterday's awards. After the boundary, each new Daily has six.

The provided `qa_daily_app.py` and `qa_weekly_app.py` are developer-only local
fixtures, not deployment entrypoints. Keep the deployed entrypoint `app.py`.
Do not use your real official game for experimental testing: it cannot restart.

## If something goes wrong

Keep the saved tables and game rows. Do not reset accounts, delete attempts,
rerun an old schema, or change the launch date to troubleshoot. Before the
six-puzzle boundary, the previous app can still read its existing ten-puzzle day.
After the boundary, old code cannot create new ten-puzzle days; use a forward
fix instead of restoring old code alone.

## Reference documentation

- [GitHub browser file uploads](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)
- [Supabase SQL Editor](https://supabase.com/features/sql-editor)
- [Streamlit app updates](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
- [Streamlit reboot](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/reboot-your-app)
