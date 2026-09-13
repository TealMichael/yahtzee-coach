# v43B Phase 2K.14.10 — Friend Group Cache Hotfix

## Problem
Friend groups failed to display with UnserializableReturnValueError in _cached_player_groups. Results were still visible, but Group Rank was blank and the warning appeared twice. The diagnostic identifies an app cache serialization failure; it does not indicate deleted group membership or Daily data.

A regression reproduces that exact Streamlit error using GroupRecord instances retained across a module reload. This demonstrates a compatible cause; the production process's underlying pickle exception was not provided, so the precise reload history is not confirmed.

## Small targeted fix
- Cache plain dictionaries and an ISO timestamp rather than application-defined GroupRecord instances.
- Reconstruct the same GroupRecord interface after reading the cache.
- Preserve every group field, group order, per-player keys, 60-second cache lifetime, and cache clearing after social writes.
- Reuse the already-loaded group list on the completed-results page. A failed group load now generates one group warning instead of two.
- Real database errors still surface and can be retried; they are not cached as an empty successful result.

## Scope
Literal baseline: the delivered 2K.14.9 full-app ZIP. Only app.py changes at runtime. The new ceremony, saved avatars, medal rules, strategy, Points Lost, Daily puzzles, coaching tables, login/PIN behavior, Supabase store, data files, and requirements remain byte-for-byte unchanged. There is no database migration or new secret.

Version-only assertions in historical tests advance to 2K.14.10; a new regression exercises the real Streamlit cache serializer, stale-class failure, field preservation, cache hits and isolation, invalidation, empty groups, database failure retries, and results-page group-list reuse.

## Installation using the GitHub browser
1. Download and extract the BROWSER_UPLOAD_CHANGED_FILES ZIP.
2. Open UPLOAD_TO_GITHUB and upload its contents to the existing repository root using Add file → Upload files. Do not upload the ZIP itself or add a nested UPLOAD_TO_GITHUB folder.
3. Commit the files together. The changed-files package is intended for a repository already on 2K.14.9; the full ZIP is the complete release backup.
4. Allow the app to redeploy, then reload Jonas's page. Confirm the group standings return and the warnings disappear. Open the normal app URL without ?dbcheck=1 afterward.

No account reset, group rejoin, Daily replay, or Supabase SQL is required. If the warning remains, capture the new Group load detail so we can identify any separate error.

## Commit message
v43B Phase 2K.14.10 - fix friend group cache serialization
