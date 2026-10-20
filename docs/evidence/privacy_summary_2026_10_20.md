# Privacy summary — 20 October 2026

Issue #81. Setup and Profile now share a factual privacy summary covering
authorized support access to account/financial records and the audited record
views, exports and successful changes. Successful registration/sign-in times and
methods are explained without claiming online presence or device/location tracking.

Profile opens the summary as a read-only page. Opening it does not accept terms,
save training choices, change timestamps or call the consent endpoint. The setup
checkboxes remain required and future model-improvement permission stays optional.
The current app does not automatically train on user records.

The summary revision is 20 October 2026. Stored backend policy version remains
`2026-08-02`: this clarifies existing behavior and does not re-date old acceptance
or certify a newly approved policy. Owner/institution review of terms, retention
and future version/re-consent requirements remains open under #81.

Verification: **147 offline Flutter tests passed, one opt-in live test skipped**;
analyzer clear (15.4 seconds). Five new widget tests cover setup/read-only copy,
normal/200% text at 320x640, full scrolling, unchanged required-consent gating and
Profile navigation with zero consent submissions. Existing registration,
onboarding and account-switching regressions remain in the full gate.

Independent supplied-code review found no blockers after narrowing the audit
wording to implemented coverage; the reviewer ran no tools or tests. No backend,
consent API, stored-policy/version, dependency or model change is included.

## Final native check

Clean app source: `e62bd57940155247b2c83d5a77c7cc82dd14be91`. On the authorized
Samsung SM-G988B / Android 13, **one native test passed in 44 seconds; one opt-in
picker test skipped**. All 12 primary pages scrolled fully at app-local 200% text,
including the read-only privacy page and expanded CSV format/example. Actual
secure-storage legacy migration and the delayed real HTTP consent-response/account
switch scenario passed again. The backend was attested in-memory SQLite using
retained portable inference; no personal or hosted financial data was used.

Build: 35.5 seconds; install: 6.3 seconds. Separate acceptance APK SHA-256:
`2a214565847d287a8a4a3b8daf8515ec61a19ca97c657ef26b5dc52b98200198`.
Retained locally as `mobile/dist/candidates/spendly-acceptance-final-1.3.5-13.apk`.
The runner removed that separate package; owned reverse/backend processes were
removed/stopped, and package enumeration showed the original app retained.

This does not establish native Google OAuth, picker/process-death, TalkBack,
physical-network-loss or original-package migration/rollback behavior. The new
read-only page is not an institutional policy approval. These boundaries remain
separate from the passing synthetic acceptance and offline widget/API fakes.
