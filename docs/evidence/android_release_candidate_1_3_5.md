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

The owner approved using a dedicated Google test identity and handling Google's
account-selection/consent UI. Installation over the original app requires the
separate in-place-update approval requested after these identity checks. At this
record, that update and signed-build Google sign-in are pending. Do not uninstall,
reset or clear the original app as a shortcut.

Native lifecycle/process-death, broader assistive/offline coverage and a safe
signed-update/rollback procedure remain tracked in #22/#56. Successful signature
verification is not proof of downgrade/rollback or full release readiness.
