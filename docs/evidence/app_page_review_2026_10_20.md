# Mobile and admin page review — 20 October 2026

Baseline: deployed app source `b1d11dd2638c013fc0079f50b7ffb30fe072fd40`.
Mobile fixes: `4e32ca7d66b3f20fbe16fd7ad352d44700955a56`, preparing 1.3.5+12.
No model, API contract, framework, SDK or dependency upgrade.

## Reproduced and fixed

- #76: dashboard/analytics summary cards overflowed at 320x640/200% text;
  fixed-height cards and truncated values now size to content. Analytics headers,
  legend and breakdown, registration password rules and recommendation headings
  wrap. Long recommendation detail sheets, empty/error panels and splash content
  scroll in short viewports.
- #77: all three history requests started before their lazy tab views existed,
  leaving unopened-tab connection failures unhandled. Each tab now starts and
  observes its own request when built; retry replaces the loaders for all tabs.
- #78: returning transaction/budget dates after closing their editors called
  setState after disposal. Three regressions reproduced it; mounted checks now
  ignore late date results.

The first page sweep had 10 passes/seven failures, including two unhandled
history errors. The separate date-disposal baseline failed all three cases.
These failures were not counted as passes. Final widget coverage adds 21 cases.

## Page coverage

| Area | Current automated coverage |
|---|---|
| Registration, login, consent | 320x640/200% text and vertical scrolling; existing validation/auth/consent routing tests |
| Onboarding, splash | Narrow large text; short 640x320 landscape splash; existing introduction navigation tests |
| Dashboard | Populated synthetic long amounts, summary/insight cards and scroll; existing periods/empty/partial/stale-error tests |
| Transactions and entry | Long values, form layout; existing validation/edit/repeated-save and CSV upload state tests; date-disposal regression |
| Budgets | Empty-page layout plus existing populated long-amount/editor checks; both date-disposal regressions |
| Analytics | Summary/chart/breakdown scroll, loading/disposal, offline error and explicit retry; existing resolutions/metric selection |
| History | Populated forecasts/alerts/advice, unopened-tab offline errors and cross-tab retry recovery |
| Forecast and spending check | Narrow large text; existing recorded-actual wording and alert review/deleted-entry tests |
| Recommendations | Narrow heading/card and long detail sheet scroll to the final disclaimer |
| Profile, More, navigation | Narrow large text/scroll; existing username/preferences/logout/account-switch/drawer tests; short-landscape main navigation |

This is bounded automated coverage, not proof of every interaction, text length,
device, assistive-technology flow or approved SRS requirement.

## Checks actually run

- Flutter offline suite: **96 passed, one opt-in live-backend test skipped**.
  New page tests use fake repositories/platform boundaries and synthetic data.
- Flutter analyzer: **no issues**, 13.2 seconds after two brace-style infos fixed.
- Backend/recommendation lightweight gate: **173 passed**, two existing Alembic
  path-separator deprecation warnings, 49.21 seconds. SQLite/fake inference fixtures;
  the two real-model suites were explicitly excluded.
- Existing admin JavaScript delayed-response checks: five passed using direct
  Node execution. Node18's file-level `--test` output does not enumerate those
  subtests, so direct execution supplies the recorded count.
- Independent read-only supplied-diff review found no reproducible blockers;
  reviewer ran no tools/tests.

## Native attempt and remaining acceptance

The authorized Samsung SM-G988B/Android13 was connected. A new separate
`com.evagh.capstone.spending_support.acceptance` debug build compiled in42.8
seconds and installed in4.6 seconds. The loopback fixture attested an in-memory
database and loaded the actual retained portable models. Synthetic account,
financial validation and partial-inference requests reached it successfully.

The test **did not complete**: its process was absent and the phone's screen was
off before the new page tour. No completed native pass is claimed. An unlock
request was sent while independent work continued. The expanded suite includes
an eleven-page, app-local200% text tour for a controlled repeat; its native CSV
picker test remains opt-in. Earlier completed native CSV/secure-storage evidence
belongs to its recorded binaries, not this new candidate.

The original app was not uninstalled/reset or its account data inspected. No
system font setting changed. Remaining process-death, actual network-loss,
Google cancellation/recovery, TalkBack and disposable-target rollback checks stay
in #22/#56.

### Completed native repeat after owner unlocked phone

The controlled repeat passed **one native test in40 seconds; one CSV-picker test
was skipped because its explicit opt-in was off**. Build37.1 seconds/install5.5
seconds. Existing actual secure-storage/session/account-isolation, synthetic
financial validation/edit/repeated-save, partial and eligible portable inference
checks passed, followed by the eleven-page tour: dashboard, transactions,
budgets, analytics, history, forecast detail, spending check, recommendations,
profile, More and upload. Each was rendered at app-local200% text and its primary
vertical scroll reached the end without reported rendering exceptions. This
does not establish TalkBack, physical network-loss or process-death coverage.

Acceptance APK SHA-256:
`21392a1882b3311d92049ccc5628e94b552ece29c160879be9c912a832416990`.
It was saved locally as
`mobile/dist/candidates/spendly-acceptance-page-review-1.3.5-12.apk`.
The fixture database remained in memory; the hosted API was not used. The runner
had removed the acceptance package by cleanup (a redundant uninstall reported
DELETE_FAILED_INTERNAL_ERROR); package enumeration confirmed only the original
Spendly package remained. The owned5057 reverse rule and backend process were
removed/stopped. Earlier interrupted attempt remains incomplete, not a pass.

## Additional findings tracked

- #79: startup secure-storage failure can escape restoration without retry UI.
- #80: CSV format/example and bounded rejected-row explanations are missing in-app.
- #81: privacy setup needs clearer administrator access/sign-in-history wording
  and a consistent consent-version decision.
- #82: admin lists need complete loading/failure/retry states and a fresh browser
  review. The browser tool's URL policy blocked local page access in this session;
  source/unit checks do not establish visual browser acceptance.

Admin source review included login, overview, management templates, JavaScript,
CSS, authenticated API controls and existing ownership/CSRF/audit tests. No
hosted admin credentials or real account records were read. Earlier browser and
PostgreSQL evidence remains separate from this review.
