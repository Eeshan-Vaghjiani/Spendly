# Mobile amounts and native CSV acceptance — 20 October 2026

Tracking: #22 / #56. Branch: `fix/mobile-large-text`. No model or API changes.

## Fix

At 320 logical pixels, long KES amounts overflowed budget and transaction rows
even at normal text size. At 200% text size the same rows and over-budget badge
overflowed further. Budget usage/totals and transaction category/amount now stack
and wrap; badge text wraps within its available width. Full amounts and editing
actions remain available. No monetary calculations or storage behavior changed.

Four regression tests reproduced the original rendering failures, then passed
at 320x640 with text scales 1.0 and 2.0. They also open the editors, verify the
original numeric values and scroll to reachable Save controls.

## Automated checks

- `flutter analyze --no-pub`: no issues.
- `flutter test --no-pub --reporter expanded`: **71 passed, 1 skipped**. The skip
  is the opt-in live-backend test. These tests use fake repositories/mocked I/O.
- Touched Dart format and Git diff checks passed.

## Actual Android execution

Target: owner-authorized Samsung SM-G988B, Android 13. Separate package
`com.evagh.capstone.spending_support.acceptance`, label Spendly Acceptance,
version 1.3.4+9. The existing in-memory loopback backend loaded the retained
portable V6 artifacts; no hosted service or persistent database was used.

**Two native tests passed in 54 seconds**, after a 25.4-second debug build and
5.1-second install:

1. Existing real secure-storage/session/account-isolation, HTTP, partial/eligible
   portable inference, financial form validation and repeated-save/edit checks.
2. Actual Android CSV chooser cancellation, mixed import, duplicate re-import,
   bad-header rejection, recovery and 200% budget layout/editor checks.

The second test uses the real file-picker plugin and HTTP repository. Two
invented CSV fixtures were copied into a dedicated test folder. A host-side
driver operated only the native picker and selected the named synthetic results.
The search field is excluded from file-result selection. Earlier interrupted
attempts are not counted as passes; the final complete run passed both tests.

| Operation | Observed/asserted result |
|---|---|
| Cancel picker | Zero transactions; button enabled again; no summary |
| Import four mixed rows | 2 created, 1 duplicate, 1 invalid; 2 stored records |
| Import the same file again | 0 created, 3 duplicates, 1 invalid; still 2 records |
| Choose bad-header file | Missing-columns error; no stale summary; still 2 records |
| Choose valid file after error | 0 created, 3 duplicates; still 2 records |
| Budget at app-local 200% text scale | Full KES 1,500,000.00 / KES 1,250,000.00 amounts render without exceptions; edit opens with original amount |

The text scale was overridden inside the test app; system font settings were not
changed. Native fixture dates are June 2026, outside the tested budget day of
20 October 2026. This is not a test of every screen or assistive technology.

Acceptance APK SHA-256:
`d4af75dd7cca13582203d2a860b1b9536fd30a59f709f73147f6e329b6baeefe`.
It is distinct from earlier acceptance binaries and the production-package
candidate. The unchanged 1.3.4+9 production candidate does not contain this patch.

## Repeat procedure

Use the existing disposable backend and package guards in
[the native acceptance procedure](../release_1_3_4.md). Copy only the two
synthetic files in `mobile/integration_test/fixtures/` into a dedicated device
folder. From `mobile/`, with the authorized device and port forwarding prepared:

```powershell
flutter test integration_test/native_acceptance_test.dart -d DEVICE_SERIAL --no-pub --dart-define=SPENDLY_ACCEPTANCE_BUILD=true --dart-define=NATIVE_PICKER_ACCEPTANCE=true --dart-define=API_BASE_URL=http://127.0.0.1:5057/api/v1 --dart-define=ACCEPTANCE_API_BASE_URL=http://127.0.0.1:5057/api/v1
```

The picker test is skipped unless explicitly enabled. For its printed phases,
cancel once, then choose the mixed fixture twice, the invalid fixture once and
the mixed fixture again. Keep the phone unlocked and unused by other activity
during the controlled run. Choosing a file through a mocked channel does not
reproduce this evidence.

## Cleanup and remaining scope

The runner removed the separate acceptance package; package inspection confirmed
the original Spendly package remained. Only the two copied synthetic files and
their empty test folder were removed. The owned USB reverse rule was removed,
and the owned local backend stopped, discarding its in-memory database. SDK,
phone settings, original app storage and model artifacts were unchanged.

Real Google OAuth still needs a designated test identity/configuration. Native
leave-screen/process-death and broader accessibility/offline recovery, plus
same-certificate production-package update/rollback, remain in #22/#56. This run
does not certify those flows or authorize tester distribution.
