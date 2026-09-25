# Spendly

Spendly is a Flutter and Flask personal-finance decision-support application.
It tracks income, expenses and budgets; presents cash-flow analytics; and runs
versioned forecasting and unusual-spending models. Financial data is stored in
PostgreSQL and remains isolated by authenticated user.

## Repository layout

- `mobile/` — Flutter Android client.
- `backend/` — Flask API, migrations and administrator dashboard.
- `artifacts/models/` — versioned production model artifacts.
- `model_research/` — forecasting experiments, Kaggle notebooks, and research results.
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
