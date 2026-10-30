# Spendly

Spendly is a Flutter and Flask personal-finance decision-support application.
It tracks income, expenses and budgets; presents cash-flow analytics; and runs
versioned forecasting and unusual-spending models. Financial data is stored in
PostgreSQL and remains isolated by authenticated user.

## Repository layout

Submission documentation: [report draft](docs/submission_report.md),
[requirements and evidence matrix](docs/submission_evidence.md), and
[Wasaa testing decision](docs/wasaa_testing_and_model_decision.md).
Historical evidence distinguishes its tested source/binary from the deployed
release. Current work goes through reviewed PRs to `main`; deployment remains a
separate owner-approved action. See [the branch workflow](docs/git_workflow.md).

- `mobile/` — Flutter Android client.
- `backend/` — Flask API, migrations and administrator dashboard.
- `artifacts/models/` — versioned production model artifacts.
- `model_research/` — forecasting experiments, Kaggle notebooks, and research results.
- `render.yaml` — Render Blueprint for the live lightweight deployment.

## Local verification

```powershell
python -m pytest backend/tests services/recommendation_engine/tests --ignore=backend/tests/test_model_inference.py --ignore=backend/tests/test_vertical_slice_real.py -q
```

From `mobile/`, after resolving the locked dependencies if necessary:

```powershell
flutter analyze --no-pub
flutter test --no-pub
```

## Live deployment

The existing private service uses the deployment branch, not this source merge.
`render.yaml` is intentionally unchanged here and is not proof of parity with
the hosted service (including its optional SMS capability). Do not deploy or
enable flags without separate approval. For an approved deployment, provide a pooled Neon `DATABASE_URL`,
administrator credentials and `GOOGLE_WEB_CLIENT_ID`, then build the tester APK
against the resulting HTTPS API URL. Secrets, keystores and generated APKs are
excluded from Git.

See [the live deployment guide](docs/live_deployment_and_tester_apk.md) and
[Google Sign-In setup](docs/google_sign_in_setup.md) for the remaining console
configuration.

## Current account and dashboard behavior

The private 1.4.1 release includes an audited administrator management console at
`/admin/manage`: account access control, token revocation, financial record
corrections, per-account exports/deletion, insight pause/resume and an audit
trail. See [admin capabilities and rollout](docs/admin_management.md).
Its source also includes the separately consented M-PESA SMS importer and
migrations through 0008. A source merge does not apply those migrations or enable
SMS in a normal APK; see [the exact capability and consent contract](docs/mpesa_sms_import.md).

- Login and registration expose the same working **Continue with Google** flow.
- Each account has a unique, case-insensitive username (3–30 ASCII letters,
  numbers or underscores) that can be edited from Profile.
- New accounts complete or skip four account-scoped welcome screens once;
  Profile can replay them without resetting completion.
- Dashboard headline values come from authenticated server aggregates. The
  default is the current Nairobi calendar month; choices are Monday-based current
  week, current month, rolling three months through today, current year, and all
  time. Empty periods are shown separately from API failures and lifetime data.

For a separately approved deployment, existing databases must be upgraded before
starting the matching code. Rehearse on a disposable target first:

```powershell
python -m flask --app backend.run:app db upgrade --directory backend/migrations
```

The frozen V2 research artifacts are not production-compatible yet. See the
[V2 integration readiness review](docs/model_integration_readiness_v2.md).
