# Account session recovery — 20 October 2026

Issues: #85 (late account responses), #79 (startup storage failures).

## Behavior

Account operations carry a generation. Logout, a new sign-in and disposal make
old completions ineligible to change authentication state. The API layer also
checks the storage generation before sending authenticated requests, accepting
responses and committing credentials. A late renewal failure cannot clear a newer
session. Already accepted server writes are not cancelled by these client guards.

Production secure-storage wrappers share one ordered queue. A token and cached
profile are saved together in `signed_in_session_v2`. A complete legacy pair is
readable and migrated on a successful renewal/sign-in/profile update. Sign-out
writes an authoritative signed-out record before best-effort legacy-key cleanup.
Malformed versioned records never fall back to obsolete credentials. A failed
authoritative write reports failure; it is not presented as a successful logout.

Google sign-out is coalesced across wrappers. A stuck provider cleanup releases
local logout and email sign-in after five seconds, while Google sign-in remains
blocked until that original cleanup settles. Startup storage errors show a safe
retry page without silently deleting stored credentials or exposing diagnostics.

## Verification

- Full offline Flutter suite: **137 passed, one opt-in live test skipped**.
- Flutter analyzer: **no issues**, 101.6 seconds on the final style correction.
- New focused tests cover late success/failure after logout, account switching
  and disposal; token/profile consistency; legacy migration; failed writes and
  obsolete-key cleanup; shared wrappers; delayed Google identity/cleanup; and
  retry after an actual simulated storage-read exception.
- Offline storage/HTTP/Google tests use synthetic fakes. They do not establish
  native plugin behavior or actual Google OAuth success.
- Independent read-only review of supplied implementation found no concrete
  blockers; final native evidence is still pending. The reviewer ran no tools.

The guarded native suite now exercises real secure-storage migration and holds
a real local HTTP consent response until after synthetic account switching. Its
current result must be recorded before this release blocker is closed.

## Release limits

Build metadata advances to 1.3.5+13. No signed +13 artifact or installation is
claimed by this source change. The previously installed candidate remains +12.
No backend, API schema, model, training or SDK/dependency change is included.

The new format is authoritative for this and later compatible builds. An older
APK does not understand its signed-out record; downgrade compatibility is not
certified. Keep rollback procedures and broader process-death/offline/accessibility
acceptance tracked separately. No personal account storage was inspected.
