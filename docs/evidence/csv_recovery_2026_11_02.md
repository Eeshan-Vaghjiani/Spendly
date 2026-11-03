# Android CSV recovery completed — 2 November 2026

Related: Android acceptance #22. Source base: `main` at `58f1b8b`.
Branch: `test/android-csv-recovery`. The separate sync-feedback change in #111
is not part of this APK or these device results.

## Actual device and data target

- Named disposable AVD: `SpendlySmsFinal_20261023`, `emulator-5564`, Android
  API 36, x86_64, 2048 MiB guest RAM, two cores. No wipe was performed.
- Separate debug package: `com.evagh.capstone.spending_support.acceptance`,
  built from `tool/csv_recovery_main.dart` with SMS capability excluded.
- APK SHA-256:
  `667431414d488170c212c13c31f8a7a38ea6869e49ea620434f9932bd59cc42d`.
- Backend: `backend.scripts.run_csv_recovery_backend`, loopback port 5057,
  fresh in-memory SQLite and one invented account. Real Android secure storage,
  DocumentsUI and the normal app/repository/upload routes were exercised.
- Only a fictional one-row CSV was used. No hosted records, physical phone,
  personal inbox, production signing key or release APK was accessed.

Build and device guards are the same as the
[26 October procedure](csv_recovery_2026_10_26.md). Required Android SDK/NDK
versions were already installed; no SDK installation or upgrade was performed.

## Reproduced runner defect

Initial attempts passed synthetic startup but timed out looking for the visible
"More" tab. A diagnostic UI tree showed that control present and enabled.
`xml.etree.ElementTree.Element` is false in a boolean check when it has no child
elements. The shared wait helper therefore discarded a valid leaf control and
timed out. This was a test-runner defect, not evidence that app navigation failed.

The one-line correction accepts an observed XML element explicitly, preserving
ordinary truthiness for boolean/string predicates. Six added cases cover a leaf
element, missing `None`/`False`/empty string/empty list and timeout behavior.
Before the correction: **1 failed, 6 passed**. After: **7 passed**.

The host initially had low free memory; completed lab-build compiler daemons were
stopped before further attempts. A later attempt still reproduced the same wait
failure, so memory is not presented as the proven cause. The native suite passed
after the runner correction, using the same acceptance APK.

## Completed native scenarios

| Scenario | Observed result |
|---|---|
| Kill background Spendly while the actual file picker is open, then finish selection | A new startup restored the existing account; no unsolicited transaction or upload checkpoint |
| Explicit retry after app death | Fresh successful upload checkpoint: received 1, created 1, duplicates 0, invalid 0; exactly one server transaction |
| Stop the actual DocumentsUI provider while selecting | Spendly's process survived; upload button became usable; explicit retry received 1, created 0, duplicates 1, invalid 0 |
| Reinstall the same acceptance APK in place while authenticated | New startup checkpoint reported restored session; signed-in navigation and the single server transaction remained |

All four native runner checkpoints passed with exit code 0. Fresh backend
startup/upload checkpoints, exact import counts and PID checks were used, not
an old on-screen summary alone. The fixture prohibits an automatic fresh login
after first startup, so that cannot disguise secure-storage session loss.

## Repeatable checks and review

- Focused runner/fixture tests: **7 passed**.
- Backend/recommendation lightweight gate: **223 passed**, six existing Alembic
  deprecation warnings. Uses synthetic SQLite/fake inference; the documented two
  real-model suites were excluded. The native fixture itself loads the existing
  portable artifacts, without retraining or computing predictive-quality metrics.
- Debug acceptance APK build passed. Flutter production sources/dependencies did
  not change in this branch; the separate #111 Flutter results are not claimed
  as a new run for this branch.
- Independent read-only review found no required changes and reran the six
  isolated runner regressions successfully. Its own full pytest collection was
  blocked by a missing dependency; it did not rerun the native scenarios.

## Cleanup and limits

The runner removed the acceptance package, fictional CSV, UI dump and port
reverse. Their absence was checked before the owned emulator was stopped.
The loopback fixture was stopped and port 5057 was no longer listening. No test
service or device process is left running.

The ignored debug acceptance APK remains in
`mobile/build/app/outputs/flutter-apk/app-debug.apk`. A one-off diagnostic runner,
synthetic-only screenshot and fixture log remain in the approved OpenCode temp
directory; they are not production evidence or tracked release artifacts.

This completes the emulator CSV interruption/retry and acceptance-app in-place
reinstall scenarios left open on 26 October. It does not establish recovery
after uninstall/data clear, interrupted installation, rollback, Android backup,
the currently signed production binary or another OEM. Physical Google OAuth,
TalkBack, radio/background behavior, M-PESA sync timing, public distribution and
policy approvals remain separate. No production app change, new release or
deployment is included.
