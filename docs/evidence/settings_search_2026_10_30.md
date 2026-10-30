# Settings search and installation follow-up — 30 October 2026

Issue: [#107](https://github.com/Eeshan-Vaghjiani/Spendly/issues/107).
Related: sync investigation [#105](https://github.com/Eeshan-Vaghjiani/Spendly/issues/105),
new installation report [#108](https://github.com/Eeshan-Vaghjiani/Spendly/issues/108),
roadmap [#33](https://github.com/Eeshan-Vaghjiani/Spendly/issues/33).

## Scope and source

Prepared on `feat/searchable-settings`, initially based on staging `5c33d42`,
in a separate worktree. Baseline PR #109 reconciles that app into main before
this focused feature PR. The older, dirty deployment checkout and its unrelated
work were not overwritten. The owner subsequently authorized commits and PRs
to main; the linked issue/PR records integration status. No APK signing or
deployment occurred. The delivered private release remains 1.4.1+15.

- Profile/settings now has local case-insensitive search, aliases, clear-search
  and no-results states, grouped into Account, Imports and sync, Privacy and
  permissions, and About and help.
- Search results retain existing destinations and stable widget keys. Search
  does not index account values, send search text, enable SMS, request permission
  or change optional training consent. Existing username/logout failure handling
  remains in place.
- Transactions has a direct M-PESA sync-settings shortcut and refreshes its
  list on return. It does not initiate sync or bypass disclosure.
- Existing M-PESA status/history/manual-sync/error controls are reused, not
  replaced. No scheduler, native permission or import/API behavior changed.
- The installation guide now distinguishes unknown-source permission, scan
  prompts, sensitive-permission sideload blocks, harmful-app classifications
  and package/update errors. It describes reviewed distribution or a separately
  approved permission-free build, not disabling Play Protect.

## Verification actually run

- `flutter test --no-pub --reporter failures-only`: **187 passed, one skipped**.
  The skip is the opt-in live-backend test; no live backend URL was supplied.
- `flutter analyze --no-pub`: **no issues found**, rerun after the final full
  test suite on the complete changed mobile sources/tests.
- Eight new fake-repository/native-platform widget tests cover aliases, direct
  SMS/privacy navigation, preserved active import state, no personal-value search,
  training-choice persistence, transaction refresh on return, and 320-pixel/
  200%-text layout with simulated keyboard insets. Existing logout, introduction
  and privacy tests were adjusted for the new layout/scrollable search field.
- Independent read-only review of the scoped files reported no concrete findings.
  That review did not independently verify the exact base diff or run tests.
- Dart MCP test/analyzer attempts timed out and are not counted as passes. After
  checking no prior Flutter command remained active, terminal commands supplied
  the completed gates above. Intermediate test-navigation failures were corrected
  before the final full-suite pass.

## Remaining boundaries

No actual Android keyboard, TalkBack, personal phone, OAuth, SMS inbox, native
background delivery, backend/database or model checks were run for this UI-only
change. Fake status tests do not establish automatic-sync performance or solve
the owner's #105 report. No Play Protect block was reproduced or appealed.

#108 remains blocked on the exact affected-device warning and received APK
identity. Do not assume the previous #102 installation problem has recurred or
that removing SMS permissions guarantees acceptance. Close #107 only with its
reviewed source integration; native/release acceptance remains separately in
#22. Source integration and widget tests are not delivery to existing users.

The feature worktree and normal dependency/build caches remain. No server,
emulator, database, application listener or background import job was launched.
