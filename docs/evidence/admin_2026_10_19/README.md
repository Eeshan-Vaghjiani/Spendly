# Synthetic admin acceptance — 19 October 2026

Source: `codex/issue-59-admin-model-evidence`, based on release commit
`31f2403563b122dd9d9d2db14cde60eeea6e7636`; final PR records the candidate commit.
The backend release reports 1.3.4. The local fixture deliberately provides no
hosted source revision, so the browser correctly displays Source Unavailable.

Target: loopback Flask server, SQLite in memory, actual checked-in portable V6
bundle, one invented account at example.invalid. No production database, real
account, real financial record, OAuth provider or persistent migration was used.
The owned fixture server is stopped after testing; its in-memory records disappear.

Browser checks passed:

- Admin login and logout; protected pages and invalid CSRF/session/password rules
  also have isolated Flask coverage.
- Overview empty record states, actual matched model disclosures and source links.
- 360×800 layout: document width345px within viewport360px; long hashes wrap.
- Keyboard Enter opens model disclosure with visible focus; refresh works.
- Stopped loopback server: refresh shows network error and retry remains enabled.
  Restarted fixture: refresh clears error and restores data.
- Management search with no match and recovery to the invented account.
- Added KES125.50 synthetic expense after reason/password reconfirmation; account
  totals, record row and transactions.post audit entry appeared.
- Disabled and re-enabled the invented account; controls reflected each state.
- Paused and resumed local insights; controls and audit trail updated.
- Final-source management view reports portable_lstm, correcting the former
  configured-runtime label. Updated evidence wording is visible.

Screenshots are synthetic acceptance evidence, not production screenshots or
mockups. The narrow screenshot shows the keyboard-focused model disclosure;
the overview and management screenshots show their respective local views.

Automated checks:152 backend/rules tests passed before the final shared-runtime
label adjustment; the focused admin/model/analytics gate then passed62 tests.
The final PR validation comment records the complete post-commit gate. Two Alembic
configuration deprecation warnings remain. Latest Flutter change gate:67 passed,
one live-backend test skipped, analyzer clear. This admin-only slice changes no
Dart sources.

Remaining acceptance: compatible PostgreSQL/MySQL upgrade/recovery rehearsal
(Docker engine unavailable), actual Android installation/OAuth/secure storage,
browser export/delete confirmation and larger multi-page datasets. Export/delete,
CSRF, expiry, stale sessions, ownership and account revocation have synthetic
backend coverage; those tests do not substitute for the omitted browser/device/DB
checks. No destructive browser acceptance was performed.
