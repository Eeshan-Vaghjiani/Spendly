# Android 1.3.4 acceptance candidate

API 1.3.4 is deployed from the existing release branch through PRs #62–68.
The Android candidate is 1.3.4+9. The signed 1.3.3+8 tester APK remains a
separate historical artifact; its hash must not be relabelled.

Latest evidence: the [20 October native extension](evidence/android_2026_10_20.md)
passed actual form/repeated-save/edit checks. A separate production-package
[release candidate](evidence/android_release_candidate_2026_10_20.md) now builds
and matches the prior tester signing certificate. Final Google/picker/signed-update
acceptance remains open; these three APK hashes identify different artifacts.

## Device evidence — 19 October 2026

The owner authorized a separate synthetic test app on their Samsung SM-G988B
(Android 13). USB debugging was approved on the phone. The existing Spendly
package was present, and the acceptance package was initially absent.

The integration suite passed **1 native test**, containing checks for:

- A separate package, explicit loopback target and disposable database marker.
- Synthetic registration/consent/onboarding, real native secure token storage,
  session renewal, logout/token removal and a second account without stale data.
- Real HTTP transaction and budget creation, KES 125.50 totals, rejection of
  fractional-cent amounts, and the actual budget screen.
- Unavailable forecasts retaining recommendations and a visible explanation.
- Eight controlled completed weeks producing a finite, nonnegative forecast
  through the retained portable LSTM, with the correct Nairobi week.

The backend used in-memory SQLite and actual checked-in portable inference,
not the test suite's fake model registry. Google identity was synthetic.
These checks do not establish native Google OAuth, native file-picker behavior,
all UI CRUD/offline paths, PostgreSQL migration compatibility or signed update
installation/rollback. Those remain tracked in #22 and #60.

The first run stopped before data access because USB forwarding was missing.
The next exposed connection recycling that destroyed the fixture's in-memory
schema after five minutes. The fixture now disables recycling and serves serial
requests through one connection. A cross-thread registration regression passes.
The subsequent device run completed successfully in ten seconds after launch.

Verified APK identity after that successful run:

- Package: `com.evagh.capstone.spending_support.acceptance`
- Label: `Spendly Acceptance`; version: `1.3.4`; versionCode: `9`
- SHA-256: `d401ec92b0dae63b841d45892bb59fda21817a5c8507cc1e49820f8eb5367912`
- Local output: `mobile/build/app/outputs/flutter-apk/app-debug.apk`
- Source: the issue-22 PR commit, based on release `238978e54f185e99529d9d7ba3b8604b71af2908`.

The backend retained manifest format `spendly-portable-v6-v1`, forecast
`v6_reference_lstm`, and anomaly model `single_excess128` (300 trees,
128 samples, threshold 0.6451359189730762). Weights SHA-256:
`6fcf6b12c5c0c00ad5057c126e2054588858b5b5bba10d6f10417ea6bf146538`.
No training, model promotion or personal financial data was involved.

## Repeat the separate acceptance run

`--dart-define=SPENDLY_ACCEPTANCE_BUILD=true` selects a debug-only package
with independent storage. It does not read release signing properties.
Gradle rejects the named integration target without that flag, and rejects
release tasks when the flag is enabled. The suite checks the actual package
and backend marker before clearing its own secure storage.

Start the disposable backend from the repository root with the prepared Python
environment:

```powershell
python -m backend.scripts.run_acceptance_backend
```

The fixture always uses in-memory SQLite, ignores persistent database settings,
loads retained portable models and binds only 127.0.0.1:5057. It has no configured
admin or Google identity. Stop the owned process after testing; records disappear.

After the owner authorizes the chosen device, forward only this port and run
from `mobile/`. Check the forwarding rule again after a USB reconnect:

```powershell
adb -s DEVICE_SERIAL reverse tcp:5057 tcp:5057
adb -s DEVICE_SERIAL reverse --list
flutter test integration_test/native_acceptance_test.dart -d DEVICE_SERIAL --no-pub --dart-define=SPENDLY_ACCEPTANCE_BUILD=true --dart-define=API_BASE_URL=http://127.0.0.1:5057/api/v1 --dart-define=ACCEPTANCE_API_BASE_URL=http://127.0.0.1:5057/api/v1
adb -s DEVICE_SERIAL reverse --remove tcp:5057
```

Inspect the built APK package before manual installation. Preserve the existing
Spendly package and signing identity. No SDK installation, licence acceptance,
phone reset or production account was needed for this run.

## Final validation and cleanup

- Backend/rules gate: **153 passed**, no failures; two existing Alembic
  configuration deprecation warnings. Most fixtures use SQLite/fake inference;
  the acceptance fixture and native run load the actual portable models.
- Flutter offline gate: **67 passed**, **1 opt-in live test skipped**, no failures.
- `flutter analyze --no-pub`: no issues. Touched Dart format check: unchanged.
- Direct Gradle configuration check: the integration target without the explicit
  acceptance flag fails with the expected guard message before building.
- The local acceptance backend was stopped and its synthetic database discarded.
  The phone later disconnected, so final package inspection/removal was unavailable.
  The separate acceptance app may remain installed; no command reset, uninstalled
  or updated the original Spendly package. USB reverse forwarding ends with the
  device connection. No production endpoint was used.
