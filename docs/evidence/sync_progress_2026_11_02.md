# Manual M-PESA sync status feedback — 2 November 2026

Source base: `main` at `58f1b8b`, branch `fix/mpesa-sync-progress`.
Related: sync reliability #105, Android acceptance #22, roadmap #33.
This is a source change, not a new APK or hosted release.

## Reproduced problem and bounded fix

While `MpesaController.sync()` awaited the native worker, settings retained its
pre-sync pending count and summary until the complete sync returned. A synthetic
regression reproduced this: the native fixture had 12 pending records after one
second, but the controller still showed zero.

During a manual sync, the controller now requests a local native status snapshot
once per second, without overlapping reads or starting another sync. Android
already dispatches status on its control executor separately from the sync worker.
Status reads local importer state, not the SMS inbox or network. Counts reflect
the latest native checkpoint; they are not a per-message progress percentage.

Settings explains that navigation need not wait for sync, and that Android can
pause background work. The summary is labelled "Latest import summary" because
it can now show partial batch results. No new scheduler, server polling, automatic
re-enable, mutation retry, permission request or model analysis was added.

Generation/account/session/disposal checks fence late snapshots. Refresh, off,
completion and disposal cancel the timer; identity/session changes stop it at
the next tick. Snapshot failure does not cancel native work or replace its final
result. Navigating away disposes the observer, not the existing native worker.

## Checks actually run

| Check | Result | Coverage |
|---|---|---|
| Pre-fix stale-count regression | 1 failed as expected: expected 12, actual 0 | Fake platform, no device/network |
| Final focused M-PESA tests | 21 passed | Controller/widget fixtures |
| Final complete Flutter suite | 196 passed, 1 intentional live-backend skip, 0 failed | Includes 21 M-PESA consent/progress tests |
| `flutter analyze --no-pub` | No issues | Flutter source/static analysis |
| Backend/recommendation lightweight gate | 217 passed, 6 Alembic deprecation warnings | Synthetic SQLite/fake inference; real-model suites excluded |
| Admin JavaScript tests | 18 passed | Node fixtures, not browser zoom or screen-reader interaction |
| Independent read-only review | No required changes | Reviewed diff, callers, auth hooks and native dispatch/lifecycle; did not independently rerun tests |

Nine added cases cover snapshot publication/duplicate-sync prevention, overlap and
late completion, transient snapshot failure, off/account switch/disposal/refresh/
session-refresh fences, and a 320-pixel-wide 200% text layout with navigation.

The final full Flutter run used `--no-pub --concurrency=1`; its saved JSON reporter
ends with `success: true`. Dependency resolution left the checked-in dependency
files unchanged.

## Still open

- #105 is **not resolved** by progress feedback. No affected-phone bottleneck,
  before/after import throughput, cold/warm service timing, automatic delivery or
  native recovery measurement was obtained. Native/server timeouts and batching
  are unchanged; no speed improvement is claimed.
- Reopening settings during already-running native work obtains the existing
  initial snapshot but does not start continuous observation automatically.
- `flutter devices --machine` found Windows/Chrome/Edge only, no Android device.
  No emulator was launched and no personal inbox, OAuth account or native storage
  was accessed. No JVM/native suite or live backend test was run this pass.
- #108 needs the exact affected-device warning, Android/device details, received
  APK hash/source and a retest. #22 still needs its separately listed native checks;
  #82 needs actual browser zoom and assistive technology. #81 and #11 still need
  owner/institution inputs. Wasaa and optional model/hosting work were left aside.

No running service, persistent database, deployed server or APK was changed.
Local build/cache files and synthetic test reporters remain in the isolated
worktree/temp directory. No test service or device process was left running.
