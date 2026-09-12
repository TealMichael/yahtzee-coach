# v43B Phase 2K.14.7 — Persistent Login + Admin PIN Reset

Literal baseline: the complete working v43B Phase 2K.14.6 ZIP.

## What changed

- New and returning players see **Keep me logged in** (same checkbox placement and default).
- Remembered tokens now have no scheduled database expiration. Browser localStorage keeps the token; the secure first-party cookie is refreshed when restored. Browser cleanup, private browsing, or clearing site data can still remove login information.
- The migration preserves currently valid, unrevoked remembered logins. It does not revive expired or revoked tokens; those players sign in once again.
- Mike's configured account has **My Player → Admin: Reset a PIN**. Select the player, enter Mike's current PIN, and press Reset this player's PIN. The app displays a randomly generated six-digit PIN for Mike to tell the player privately. Keep any leading zeros.
- Reset changes the PIN hash and revokes the player's remembered-device tokens together in one database transaction. Other account data stays attached to the same player ID.
- Forgot your PIN now directs players to Mike. No email service or recovery registration.
- Only the configured admin can list reset targets or request resets through the app. A current admin PIN is required every time. The database reset function is restricted to the trusted server role.

## Install in this order

1. Extract the browser-upload ZIP. Open **UPLOAD_TO_GITHUB/RUN_THIS_ONCE_IN_SUPABASE_Phase2K14_7.sql**. Copy its entire contents into your **Yahtzee Supabase project's SQL Editor** and run it once.
2. The query at the bottom returns display names and player IDs. Find your existing Mike account by its exact display name; copy its player_id. Do not create a replacement account.
3. In your Yahtzee Streamlit app's settings, add this at the top level of **Secrets**, alongside SUPABASE_URL and SUPABASE_SECRET_KEY. Preserve the existing secrets:

   ```toml
   YAHTZEE_ADMIN_PLAYER_ID = "paste-your-existing-player-id-here"
   ```

   If your secrets contain any `[section]` headers, put this line above the first section so it remains a top-level setting. This ID identifies the permitted admin; it is not your PIN.
4. In GitHub's browser, open the repository folder containing app.py. Choose **Add file → Upload files**. Upload the files INSIDE the extracted UPLOAD_TO_GITHUB folder, preserving filenames. Do not upload the ZIP or create a nested UPLOAD_TO_GITHUB folder. Do not delete any other repository files.
5. Commit with the versioned message below. Let Streamlit restart, then sign into your existing Mike account and open **My Player → Admin: Reset a PIN**.

The changed-files package is for an existing 2K.14.6 installation. The full package is also supplied for a complete copy.

## Using reset

- Choose the friend's display name carefully; the underlying target is their unique player ID.
- Enter YOUR current PIN, not the friend's PIN.
- Tell the displayed new PIN privately. It disappears on the next page rerun; it is not stored in plaintext in the database or included in feedback/log messages.
- Have the friend sign out if they still have an open app, then choose Returning Player and use their existing name plus the new PIN. An already open Streamlit session is not forcibly closed by this update; remembered-token revocation applies to subsequent restoration.
- Mike may also reset his own PIN if he knows his current PIN. If Mike forgets it, the Supabase-owner recovery process is still required. An admin ID setting alone does not bypass the PIN check.

## Unchanged

Only three runtime files changed: app.py, daily_store.py, supabase_daily_store.py. One SQL migration and one new regression suite were added. Existing regression files update release-label, approved login-copy, and changed-auth-file fingerprints only.

The comparison table, Why it wins, Takeaway, all coaching mathematics, exact solver/policy, rankings, Points Lost, grades, Daily generation and date boundaries, Practice puzzles, dice controls, avatars, medals, leaderboards, and existing saved results are unchanged. No email dependency and no requirements.txt change.

Exact-policy SHA-256:
`cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b`

## Verification

See LOGIN_RESET_TEST_RESULTS.md for the final packaged-copy test result and scope audit.

The checks cover persistent-token creation/restoration decades later, explicit legacy expiry, tamper/revocation, unauthorized listing/reset rejection, wrong admin PIN, leading-zero PIN generation, hash-only RPC payloads, and the Streamlit reset form including selected-player targeting and clearing the displayed PIN on rerun.

Live Supabase execution and physical iPhone storage retention are not claimed: this environment tests the backend using controlled clients and the UI with Streamlit AppTest. The supplied migration must be run in your own project before use.

## GitHub commit

```text
v43B Phase 2K.14.7 - keep players logged in and add admin PIN reset
```
