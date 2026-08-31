# Spendly

Spendly is a Flutter and Flask personal-finance decision-support application.
It tracks income, expenses and budgets; presents cash-flow analytics; and runs
versioned forecasting and unusual-spending models. Financial data is stored in
PostgreSQL and remains isolated by authenticated user.

## Repository layout

- `mobile/` — Flutter Android client.
- `backend/` — Flask API, migrations and administrator dashboard.
- `artifacts/models/` — versioned production model artifacts.
- `university_trial_colab/` — combined CSV and notebook learning exercise.
- `render.yaml` — Render Blueprint for the live lightweight deployment.

## Local verification

```powershell
python -m pytest backend\tests services\recommendation_engine\tests -q
cd mobile
flutter analyze
flutter test
```

## Live deployment

Deploy the Blueprint in `render.yaml`, provide a pooled Neon `DATABASE_URL`,
administrator credentials and `GOOGLE_WEB_CLIENT_ID`, then build the tester APK
against the resulting HTTPS API URL. Secrets, keystores and generated APKs are
excluded from Git.

See [the live deployment guide](docs/live_deployment_and_tester_apk.md) and
[Google Sign-In setup](docs/google_sign_in_setup.md) for the remaining console
configuration.

## Current account and dashboard behavior

Release 1.2.0 adds an audited administrator management console at
`/admin/manage`: account access control, token revocation, financial record
corrections, per-account exports/deletion, insight pause/resume and an audit
trail. See [admin capabilities and rollout](docs/admin_management.md).
Deploy migrations through 0005 before distributing the updated tester APK.

- Login and registration expose the same working **Continue with Google** flow.
- Each account has a unique, case-insensitive username (3–30 ASCII letters,
  numbers or underscores) that can be edited from Profile.
- New accounts complete or skip four account-scoped welcome screens once;
  Profile can replay them without resetting completion.
- Dashboard headline values come from authenticated server aggregates. The
  default is the current UTC calendar month; choices are Monday-based current
  week, current month, rolling three months through today, current year, and all
  time. Empty periods are shown separately from API failures and lifetime data.

Existing databases must be upgraded before starting the new code:

```powershell
python -m flask --app backend.run:app db upgrade --directory backend/migrations
```

The frozen V2 research artifacts are not production-compatible yet. See the
[V2 integration readiness review](docs/model_integration_readiness_v2.md).
