# Android 1.3.5 candidate — 20 October 2026

A signed **1.3.5+10 candidate** includes the financial-amount layout fix. It is
local and unpublished. This document records packaging verification, not complete
native or production acceptance.

| Identity | Verified value |
|---|---|
| App source | `d9e45a5d5347fd269ac32f99ab59163ddd85c0fa` |
| Package | `com.evagh.capstone.spending_support` |
| Version | 1.3.5+10 |
| APK SHA-256 | `424ccff7f4edf7a96764e20170202b18f7f9bcd4da3722b3ba58e4c4d3dfe572` |
| Certificate SHA-256 | `1586c2bea26d90ab930a322d8442100ac23e0a09c0eca9e643727326958a5000` |
| Local candidate | `mobile/dist/candidates/spendly-1.3.5-10.apk` |
| Companion metadata | `mobile/dist/candidates/spendly-1.3.5-10-manifest.json` |

The existing release helper built it in 154.2 seconds using the current locked
dependencies, Flutter 3.41.4/Dart 3.11.1 and existing Android SDK/JDK. No SDK or
dependency upgrade was performed. The old versioned APKs remain preserved.

Package and certificate match the phone's actual installed **1.3.2+7** APK, which
was copied to an ignored local binary backup before any proposed update. That
backup contains the APK only; no user data or secure-storage values were exported.

The expected public HTTPS API and Web OAuth client ID were found in the compiled
ARM64 binary. Manifest inspection verified backup and cleartext traffic disabled.
The minimum compatible backend remains API1.3.4 or later. A public read-only retry
returned healthy API1.3.5, database connected, both retained models loaded and
portable_lstm; an initial 25-second request timed out before the successful retry.
No hosted financial records were read or written for packaging verification.

## Testing boundary

[Layout/native CSV evidence](mobile_large_text_2026_10_20.md) records 71 offline
tests passed/one opt-in live skipped, analyzer clear and two passing physical
Android tests. The native binary was a separate 1.3.4+9 acceptance package at
the UI-fix snapshot `4c2bf69`, before the metadata-only version increment.
It is not relabelled as testing of this signed production-package binary.

The owner separately approved the in-place update over the original app. Android
installation succeeded with the same certificate, and installed package metadata
verified 1.3.5+10. No uninstall or data-clear command was used; existing financial
data was not inspected to certify its contents.

The owner handled logout, dedicated Google test-account selection and consent,
then confirmed reaching the dashboard on the signed build. This is owner-observed
native success, not an automated token/account inspection. Google cancellation,
failure recovery and other identities were not inferred from that observation.
The owner subsequently requested a more visible Google button; its visual fix
is a separate build-number increment, with no Google authentication logic change.

Native lifecycle/process-death, broader assistive/offline coverage and a safe
signed-update/rollback procedure remain tracked in #22/#56. Successful signature
verification is not proof of downgrade/rollback or full release readiness.

## Google button follow-up

Build 1.3.5+11 replaces the generic Material glyph with Google's unmodified
multicolour G on both login and registration. The shared button has a white fill,
dark label, visible grey border and flexible height. No authentication, API or
model logic changed. The asset source and hash are recorded alongside the PNG.

Four new widget tests cover 320x640 at normal/200% text, contrast, labelled tap
targets, callback and disabled/busy behavior. The complete offline suite passed
**75 tests, with one opt-in live test skipped**; analyzer found no issues (54.5
seconds), and touched-file formatting/diff checks passed. Independent read-only
review found no blockers and ran no tools/tests. These checks do not repeat the
owner's native Google account-selection/consent test on the new binary.

### Signed 1.3.5+11 artifact

| Identity | Verified value |
|---|---|
| App source | `4f81cca8c3c40ee363f2009161a3ccc9cda61994` |
| Version | 1.3.5+11 |
| APK SHA-256 | `962dbdd4416929e24447c05441be63cec8d5d7c193d148c59907cc777c9217ec` |
| Certificate | Same SHA-256 as +10 above |
| Local candidate | `mobile/dist/candidates/spendly-1.3.5-11.apk` |

Release compilation succeeded in 113.5 seconds, without dependency/SDK upgrades.
The compiled ARM64 API/client settings and bundled official PNG hash matched;
backup and cleartext remain disabled. The existing certificate identifies an
Android Debug signer: this is a local educational/tester build, with no new
Play signing setup or public distribution claimed. Earlier versioned artifacts
and the APK-only pre-update backup remain local.

The approved same-certificate in-place update from +10 to +11 succeeded, and
installed metadata verified versionCode11/versionName1.3.5. No uninstall or
data-clear command was used. The owner's Google dashboard confirmation remains
specific to +10; no repeat OAuth, account-picker screenshot or personal-data
inspection was performed on +11. Lifecycle/offline/rollback gaps remain open.
