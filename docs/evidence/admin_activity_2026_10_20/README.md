# Admin sign-in activity and final synthetic acceptance — 20 October 2026

Tracking: [#70](https://github.com/Eeshan-Vaghjiani/Spendly/issues/70).
Source branch: `feature/admin-sign-in-activity`; API 1.3.5. No model changes.

## Behavior

Successful password/Google sign-ins and account creation record time, provider
and event kind. Token renewal, incorrect credentials, invalid/conflicting Google
identity and disabled-account attempts do not create success events. Legacy
accounts have unknown last sign-in and empty history until a new observed success.
The last timestamp cannot move backwards under out-of-order requests.

Admin lists/details show the last observed sign-in; overview cards count distinct
accounts in 7/30 days. Per-user history is paginated and audited. Account export
includes history within the shared 50,000-record bound; deletion removes it while
retaining admin audit. Enabled does not mean online. No individual session/device
tracking, IP, user-agent, token or financial payload is stored in the history.

## Automated checks actually run

- Backend/recommendation gate: **173 passed**, two pre-existing Alembic
  configuration deprecation warnings. Includes 12 new activity tests and an
  existing SQLite 0004-to-head migration/ORM metadata check. Mostly SQLite/fake
  inference; this is not the separate real-model test suite.
- `node --test backend/tests/admin_sign_in_ui.test.cjs`: **5 passed**. Delayed
  account responses/failures, current failure/retry, closing a pending account,
  and legacy empty state; no real browser/network in these unit tests.
- `node --check backend/app/static/admin/manage.js`: passed.
- Flutter analyzer: no issues. Regular Flutter tests: **67 passed, 1 skipped**
  (the opt-in live-backend test). No fresh phone acceptance in this change.

## Actual browser acceptance

Target: `http://127.0.0.1:5058`, disposable in-memory SQLite fixture with the actual
retained portable V6 registry. Runtime-generated local admin password, 25 invented
accounts, 45 invented transactions and 45 sign-in events for synthetic account 01.

Verified overview 7/30-day counts both 1; last-time versus Not recorded displays;
all three history pages (20/20/5 events) and disabled final Next; refresh to page 1;
switch to synthetic account 02 with no history and no stale account-01 rows.
At 360×800, document width equalled client width (345px excluding scrollbar);
tables remain internally horizontally scrollable. Viewport was reset afterward.

The formerly outstanding browser-delete submission in issue #60 was completed
against **synthetic account 02 in this disposable fixture only**: disable, reject
wrong username, clear password after rejection, then exact username/password/reason
confirmation. The account count changed 25→24, detail closed, search returned no
match, audit updated, and unrelated account 01 retained its 45 sign-in events.
This is not a real-user deletion or hosted admin write.

Screenshots contain invented records only:

- [Populated history](sign_in_history.png)
- [Legacy empty history](legacy_history.png)
- [Narrow layout](narrow_history.png)
- [Confirmed synthetic deletion](synthetic_deletion.png)

## Actual PostgreSQL and recovery

Owner-approved disposable PostgreSQL 16.15 (`postgres:16-alpine`, same previously
verified official image) on loopback 55432, tmpfs storage, 384MiB/one CPU.
Upgraded an invented legacy account from 0004 to `0007_sign_in_activity`;
auth_version stayed zero, last sign-in stayed null, ORM/Alembic metadata diff empty.
Registration created an activity record; admin read/export included it. Confirmed
disabled-account deletion removed owned sign-in/review/transaction rows while
preserving the unrelated legacy user and deletion audit.

`pg_dump -Fc` → `pg_restore --exit-on-error` into a second disposable database
passed: restored 0007, one legacy user, one deletion audit and zero deleted-account
sign-in rows. Repeated rehearsal rejected the nonempty source before writes.
No persistent Compose/Neon database was used for these checks.

## Cleanup and limits

Browser logged out. Owned loopback server and PostgreSQL container stopped;
synthetic DB/recovery/backup discarded, generated fixture password removed.
Screenshots and this evidence are intentional artifacts. Docker Desktop and its
official cached image remain. No native OAuth/picker/update, production load,
real-user record access or predictive reevaluation was performed.

Independent read-only review and final deployment status are recorded in the PR.
