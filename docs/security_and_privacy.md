# Security and Privacy

## Implemented controls

- Passwords are stored with Werkzeug's salted password hashing, never plaintext.
- JWT access tokens expire after a configurable interval.
- Every transaction, budget, forecast, alert, recommendation, and analysis
  query is restricted to the authenticated user ID.
- SQLAlchemy parameterisation is used instead of string-built SQL.
- Marshmallow validates request bodies before persistence.
- CSV uploads are limited by size, extension, schema, row values, and duplicate
  fingerprints.
- CORS accepts only explicitly configured origins.
- Secret keys and database credentials are read from environment variables.
- Unexpected errors return a generic response; financial request bodies are not
  written to application logs.
- Model artefacts are loaded at application startup and are never retrained
  during an API request.
- Registration records required service/privacy acceptance with a versioned
  timestamp. Existing accounts without this record are restricted until the
  setup is completed.
- Permission to use future de-identified data for model improvement is a
  separate optional choice and does not control access to the app.
- Retention is configurable with `DATA_RETENTION_DAYS`. It is disabled at `0`,
  supports a dry run, and requires an explicit `--apply` maintenance command.

## Privacy scope

- There is no live M-Pesa, banking, or account-aggregation integration.
- Users voluntarily enter or upload their own transaction records.
- Synthetic records are used only for controlled model development.
- The current app does not automatically add user records to a training set.
- Synthetic records must not be described as real Kenyan young-adult spending.
- Forecasts, alerts, and recommendations are stored so the authenticated user
  can view history.
- A deployment owner must choose and schedule the retention interval before
  production use. The prototype supports transaction deletion and timed record
  purging, but not full account erasure.

## Financial safety statement

The system provides financial decision support. Forecasts are estimates,
unusual-spending alerts are not fraud findings, and recommendations are not
professional financial advice or guaranteed outcomes.

## Production requirements

- Generate unique secrets of at least 32 random bytes.
- Use TLS at the reverse proxy.
- Rotate database and JWT credentials.
- Restrict MySQL and the backend to private networks where possible.
- Back up and encrypt the database.
- Add rate limiting and token revocation before public deployment.
- Review retention, consent, access, correction, and deletion obligations under
  applicable privacy law.

## Retention operation

Preview eligible records without changing data:

```bash
docker compose exec backend python -m flask --app backend.run:app purge-retained-data
```

Commit the configured deletion:

```bash
docker compose exec backend python -m flask --app backend.run:app purge-retained-data --apply
```
