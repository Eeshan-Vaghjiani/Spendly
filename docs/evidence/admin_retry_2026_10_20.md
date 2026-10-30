# Admin loading and retry checks — 20 October 2026

Issue #82 records the source review and remaining visual acceptance. No hosted
credentials/accounts, production records, new migrations or model changes.

## Behavior

Accounts, records and audit clear stale rows and disable paging while loading.
Records clear cached row actions and disable Add until a successful load.
Failures render an explicit message; Search, Refresh records and audit Refresh
retry the relevant view. Request/owner guards ignore stale successes/failures.

Privileged writes complete independently from the following view refresh.
Successful writes close the confirmation dialog, clear its password and report
completion. A later list/audit failure says the action was saved but the view
needs refreshing, instead of offering a second mutation as if the first failed.
Rejected writes keep the dialog open for correction and clear the password.
Authentication, CSRF, current-password reconfirmation and server audit logic are
unchanged. Overview amounts and management headers/pagers can wrap.

## Verification

- Existing five JavaScript history tests passed. Four new list tests first
  failed (loading controls, current failure/retry and stale failure). A separate
  post-write/refresh handler regression also first failed.
- Final direct execution: **12 Node subtests passed**, zero failures/skips.
  `node backend/tests/admin_sign_in_ui.test.cjs` runs the actual management script
  in a synthetic DOM/fetch harness. It is not browser layout/network evidence.
- `node --check backend/app/static/admin/manage.js`: passed.
- Full lightweight Python backend/rule gate after changes: **173 passed**, two
  existing Alembic path-separator deprecation warnings, 29.92 seconds. SQLite and
  fake inference fixtures; real-model suites excluded. No new PostgreSQL rehearsal.
- Independent supplied-diff read-only review found no concrete blockers; reviewer
  ran no tools/tests. Git diff whitespace check passed.

The browser tool URL policy blocked access to the local admin page. No alternate
browser workaround was attempted. New browser/zoom/keyboard/contrast acceptance
remains unchecked in #82; earlier admin browser/database evidence is separate.

Node18.8 reports its test runner as experimental. Direct execution enumerates
the 12 subtests; file-level `node --test` output is not used to infer that count.
