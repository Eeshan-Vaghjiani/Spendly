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
  blockers. The reviewer ran no tools.

The guarded native suite passed **one test in 41 seconds, one picker test
explicitly skipped** on Samsung SM-G988B / Android 13. Real secure-storage legacy
migration and a real local HTTP consent response held until after synthetic
account switching both passed. All 11 primary pages scrolled at 200% text without
framework exceptions. Build took 45.3 seconds; installation took 4.6 seconds.
The backend used in-memory SQLite and retained portable inference, not fake HTTP.
Actual native Google OAuth, process death and the picker were not exercised.

The tested snapshot was `cec929f5433ccef01640178c8355e9f6cc121028`, plus the
in-progress CSV help/error-display presentation change for #80. That file's
SHA-256 was `f0168fbc855d7d5a7cae94f0c217ebca8e9dbc4b492f03a458c6991a7870b1ae`.
It did not alter the account/storage implementation under test. The test APK is
retained locally as `mobile/dist/candidates/spendly-acceptance-session-1.3.5-13.apk`,
SHA-256 `e6ee0d8986dd0055ec6935ab3c3fc5ea97d0b6a99484a299843c0103b5d040d1`.
This is a separate acceptance binary, not the signed original package.

The acceptance package was removed by the test runner. The owned ADB reverse and
backend processes were removed/stopped. Package metadata verified the original
installation remained 1.3.5+12; its account contents were not read.

## Release limits

Build metadata advances to 1.3.5+13. No signed +13 artifact or installation is
claimed by this source change. The previously installed candidate remains +12.
No backend, API schema, model, training or SDK/dependency change is included.

The new format is authoritative for this and later compatible builds. An older
APK does not understand its signed-out record; downgrade compatibility is not
certified. Keep rollback procedures and broader process-death/offline/accessibility
acceptance tracked separately. No personal account storage was inspected.
