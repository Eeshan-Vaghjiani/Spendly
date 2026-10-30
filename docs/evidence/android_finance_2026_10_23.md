# Android finance acceptance — 23 October 2026

Issue #97 was found while extending the final-release checks in #22/#56.
The first emulator run failed with an unhandled transaction-list `ApiException`
during a deliberately refused connection. Four focused regressions reproduced
the same failure timing in budgets, transactions, analytics and dashboard.

The loaders now observe their newly assigned futures immediately with `ignore()`.
They retain the original futures: `FutureBuilder` still receives and displays the
error with its retry control. This closes the gap before the next render frame
subscribes; it does not retry writes or replace a failure with successful data.
All four focused regressions failed before their respective fixes and passed
afterward. Independent read-only review found no issues in the four-screen fix.

## Target and scope

- Disposable AVD `SpendlySmsFinal_20261023`, `emulator-5564`, Android API36.
- Separate debug-only `com.evagh.capstone.spending_support.acceptance` package.
  The build guard now recognises the new `finance_acceptance_test.dart` target.
- Loopback port5057, `backend.scripts.run_acceptance_backend`, in-memory SQLite.
  No Compose or persistent database was started. The backend loads the retained
  portable model artifacts; these finance tests do not evaluate predictive quality.
- A new invented `@example.invalid` account; no personal device, inbox, Google
  account or hosted financial record was accessed. URL, package and disposable
  target attestation precede secure-storage mutation, including cleanup.
- The test's HTTP client switches requests to a just-closed ephemeral port on the
  emulator for a real native socket refusal, then reconnects to the real local API.
  No HTTP response or repository result is mocked in this native suite. This is
  controlled endpoint failure, not physical Wi-Fi/mobile-data loss or a timeout
  after a server might have committed a write.

## Checks

- Budget empty state, create, edit the same record, delete cancellation, confirmed
  synthetic deletion and return to empty state.
- Failed budget refresh removes stale values; reconnect/Retry restores them.
- Failed budget save preserves its draft and performs one write attempt. The
  test checks actual server state before explicitly resubmitting, then verifies
  exactly one resulting budget.
- Transaction delete cancellation, failed refresh/clear/retry and confirmed
  synthetic deletion, checked against server record counts.
- All five analytics resolutions: selected chip plus real API query resolution;
  socket failure, retry and preserved Yearly selection.
- Dashboard failed refresh and successful reconnect/refresh.

## Reproduction

Use only the designated disposable emulator and the in-memory acceptance backend.
With that target running, from `mobile/`:

```powershell
flutter test integration_test/finance_acceptance_test.dart -d emulator-5564 --no-pub --dart-define=SPENDLY_ACCEPTANCE_BUILD=true --dart-define=API_BASE_URL=http://127.0.0.1:5057/api/v1 --dart-define=ACCEPTANCE_API_BASE_URL=http://127.0.0.1:5057/api/v1
```

Port5057 must be reversed explicitly with ADB for this loopback URL. The suite
refuses the original application package and any unapproved API URL. It does not
configure Google OAuth, enable SMS capability or use the CSV picker.

## Results and remaining limits

Final native run: **one test passed**, no skips, 29 seconds of test execution
(31 seconds including test teardown), after a 32.4-second debug build. All four
named finance markers passed. Analyzer: no issues (28.7 seconds). The four focused
refresh regressions passed after failing before the fixes. The initial native
failure and earlier three-screen passing run remain separately recorded in local
logs; the final run includes all four corrected screens.

Complete offline Flutter suite: **179 passed**, one intentional live-service skip,
35 seconds. No backend/model source changed, so backend, PostgreSQL, SMS and the older native
OAuth/storage/CSV suites were not rerun. The complete offline Flutter result is
recorded above. Its fake repositories remain distinct from the real
socket/local API execution above.

Cleanup removed the owned port reverse and stopped the owned emulator/backend.
The acceptance package was already absent after Flutter's test cleanup. In-memory
records disappeared with the backend. The generated debug APK and local logs
remain development artifacts, not the released tester APK.

Physical-device OEM behavior, radio-network changes, TalkBack, Google cancellation,
CSV/provider interruption, disposable rollback and manual browser zoom remain
separately tracked. No production deployment or replacement signed APK is included.
