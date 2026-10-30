# Admin browser review — 23 October 2026

Issue #82. Reviewed staging UI from PR #94 plus the focus correction in this
change, using the in-app Chromium browser and the explicitly disposable local
admin backend on loopback port 5058. No hosted account or personal record was
accessed. The fixture uses in-memory SQLite, 25 invented accounts, 45 transactions
and one initial budget. Its deliberately large expense total is KES10,005,521.99.
Model runtime loads the saved portable artifacts; no new predictive-quality
evaluation or training was performed.

## Actual browser checks

- Login at 320px: invalid credentials show an error; valid fixture credentials
  reach the overview. No horizontal document overflow.
- Overview: four main metrics, expandable totals including large positive and
  negative amounts, activity table and saved evaluation evidence remain available.
  No outer or panel overflow at 320px.
- Management: tested 320x700, 640x450 and 1280x900 viewports. Tables scroll within
  their containers; the outer document does not overflow. Account summary amounts
  wrap. Search, unmatched search and second account-list page work.
- Selected account: transaction/sign-in pagination reaches page two of three.
  Empty forecast list shows a clear message and disables record creation.
- Transaction and budget dialogs scroll at narrow/short dimensions. Tab traversal
  reaches all transaction fields, reason, password, Confirm and Cancel. Focused
  actions scroll into view. Escape/Cancel close without a write; Escape restores
  focus to Add record. Background controls are inert while the modal is open.
- Invalid confirmation password keeps the populated budget form open, shows an
  error and clears the password. Correct confirmation saves one synthetic KES500
  transport budget and refreshes the records. The audit contains `budgets.post`
  with the synthetic support reason.
- Keyboard issue found/fixed: Close account previously left focus on the body.
  It now returns to the invoking Manage button. If Search replaced that button,
  focus returns to Search. Both paths were checked in the real browser.

## Repeatable checks

- `node --test backend/tests/admin_sign_in_ui.test.cjs backend/tests/admin_dashboard_ui.test.cjs`:
  **18 passed**, including connected/detached opener regressions.
- Lightweight backend/rule gate: **216 passed**, six existing Alembic deprecation
  warnings. SQLite and fake inference fixtures; the two real-model suites were
  explicitly excluded using the repository's documented command.
- Independent read-only review of the complete production diff: no findings.

No mobile code changed in this follow-up, so Flutter/native suites were not
repeated. Their previous PR #94 results remain separately dated evidence.

## Limits and cleanup

Responsive viewport checks are not an actual browser zoom test. The browser tool
does not expose zoom, so #82 retains that manual item. Screen-reader/TalkBack,
physical Android, OAuth cancellation, native network loss and rollback are not
established by these browser checks. No irreversible deletion, private export,
global system switch or hosted mutation was performed. The temporary browser tab
and owned fixture server are closed after review; the in-memory records disappear
with the server. No release/deployment or replacement APK is included.
