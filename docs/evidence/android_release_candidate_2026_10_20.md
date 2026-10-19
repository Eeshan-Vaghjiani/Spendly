# Production-package candidate — 20 October 2026

A versioned **1.3.4+9 candidate** was compiled and verified. It has not been
published as the final tester release or installed over the owner's Spendly app.

- App source: `c0ebc778251125d5ae5e1f38ff70bb0dac610793` (based on merged PR #68).
- Flutter 3.41.4 / Dart 3.11.1; existing Android SDK 36 / JDK 21; no upgrades.
- Package `com.evagh.capstone.spending_support`, label Spendly, versionCode 9.
- APK SHA-256: `32217bb2bad669414b4ecc2e4193b6a22c7b6fa634197f6ce4e077604ab9d240`.
- Verified certificate SHA-256:
  `1586c2bea26d90ab930a322d8442100ac23e0a09c0eca9e643727326958a5000`.
  It matches the recorded previous 1.3.3+8 tester certificate.
- Android backup and cleartext traffic are disabled in the release manifest.
- ARM64 compiled binary contains the expected public HTTPS API URL and Google
  Web client ID from the previous tester configuration.
- Local output: `mobile/dist/candidates/spendly-1.3.4-9.apk`, with companion
  `spendly-1.3.4-9-manifest.json`. Earlier tester artifacts were not overwritten.

The API at `https://spendly-api-t1d0.onrender.com/api/v1` reported healthy,
release 1.3.4, portable_lstm, models loaded and database connected after Render
7185552356 deployed merge `8ade8ee98d8c1809d02daa037d31227fb5f5f99b`.
A public read-only untrusted-origin preflight had no allow-origin header after
the CORS fix. No hosted account or financial records were written.

The first release command used `--no-pub` after an integration-test build and
failed because the generated registrant still referenced the dev-only native
test plugin. The regular release command regenerated Flutter's platform tooling,
excluded that plugin and succeeded (53.3 seconds). No generated Java was edited,
project cleanup, dependency upgrade or SDK patch was needed. When switching from
native tests to release, allow Flutter to regenerate its platform tooling.
The existing release helper already does so; its backend requirement is now 1.3.4.
Its PowerShell syntax check passed. Kotlin's generated local cache is ignored.

Before final distribution (#22/#56), verify a designated Google test account,
actual CSV chooser/cancellation/import and remaining device accessibility/offline
flows; then test the signed update on an approved disposable installation.
The earlier separate-package native tests do not prove this production-package
Google flow or update/rollback. Existing reports record actual native secure
storage, HTTP, form/repeated-save/edit and portable-inference checks.

Retained model identity/weights remain unchanged. The candidate manifest records
portable_lstm and weights SHA-256
`6fcf6b12c5c0c00ad5057c126e2054588858b5b5bba10d6f10417ea6bf146538`.
It must not be confused with either acceptance APK hash or historical tester APK.
