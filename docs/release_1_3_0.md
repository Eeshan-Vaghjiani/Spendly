# Spendly 1.3.0 release checklist

## Implemented
- Dashboard hamburger opens a left quick-access drawer for existing tabs.
- Spending alerts include the linked transaction and descriptive prior-category context.
- Open/edit transaction from alert; explicit intentional review with stale-version rejection.
- Confirmed unchanged spending stays in totals but suppresses repeated review prompts;
  recommendations can suggest planning for confirmed expenses.
- Account-scoped analysis state ignores delayed results from a previous account.
- Selected LSTM/forest run from numeric arrays without TensorFlow or linear regression.
  Synthetic export parity:268 forecast windows max difference KES.000152;
  869 forest scores match within1.2e-16. This is inference parity, not an accuracy gain.
- Selected forecast is current Nairobi Monday–Sunday using only pre-Monday history;
  explicit complete-history confirmation required. It is not rolling next7days.

## Deployment
Release branch: agent/spendly-live-deployment. Migration0006_alert_reviews is
additive and required before distributing the new client. SELECTED_MODEL_ROOT
points to /app/artifacts/candidates/selected_v6. The Docker image sets this default;
Render configuration also declares it. Numeric artifact hashes/parity metadata
travel with the selected bundle; original V1 artifacts are preserved.

The user approved release push/auto-deploy and the additive migration. Verify
/api/v1/health api_release1.3.0 and inference_runtime portable_lstm after deployment.
No TensorFlow dependency is installed by the lightweight image. Free hosting still
has sleep/resource limits; no uptime or production-scale guarantee is made.

## Checks and remaining coverage
- Flutter analyzer passed;38 tests passed,1 live-backend suite skipped (it writes data).
- Release-worktree backend/recommendation suite passed110 tests with2 existing
  Alembic warnings, including actual portable inference through the API. Local
  additional untracked adapter suites are not included in that release count.
- Release APK1.3.0+5 built and signature/package matched prior tester installation.
- Samsung SM-G988B update installed successfully without clearing app data;
  installed signing identity matches the previous tester release. Real-account
  screens were not inspected. Synthetic runtime navigation remains pending.
- Native Google login, production-like DB concurrency/cascades, Linux resource behavior
  and live rollout are separate checks. Do not describe widget tests as device coverage.

APK destination: mobile/dist/spendly-1.3.0-5.apk (ignored); keep previous APK backup.
Do not distribute until matching backend health is verified. Historical research
files and unrelated local edits are excluded from this release changeset.
