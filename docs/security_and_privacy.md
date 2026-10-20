# Security and Privacy

## Implemented controls

- Passwords are stored with Werkzeug's salted password hashing, never plaintext.
- JWT access tokens expire after a configurable interval. Disabling an account
  or revoking its sessions changes the server-checked token version; re-enabling
  an account does not restore its old tokens.
- Every transaction, budget, forecast, alert, recommendation, and analysis
  query is restricted to the authenticated user ID.
- SQLAlchemy parameterisation is used instead of string-built SQL.
- Marshmallow validates request bodies before persistence.
- CSV uploads are limited by size, extension, schema, row values, and duplicate
  fingerprints.
- CORS uses `ALLOWED_CORS_ORIGINS`. The current deployment blueprint uses an
  empty list: native Android and the same-origin admin need no cross-origin
  browser access. A future web client must list its exact HTTPS origins. Earlier
  blueprints used `*`; the current parser ignores that blanket value even if a
  host retains it. Verify a live preflight after deployment. CORS does not
  replace authenticated ownership checks or admin CSRF protection.
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
- From API 1.3.5, successful account creation/sign-ins record account ownership,
  UTC time, provider and event kind for administrator support. Failed sign-ins
  and renewals are excluded. This history stores no IP, device fingerprint,
  user-agent, credentials, tokens or financial records. Only the separate admin
  boundary can read it; views are audited. It is included in authorized account
  export and removed with account deletion. No automatic history purge was added.
  Sign-in history does not establish online presence or an active device session.
- Synthetic records must not be described as real Kenyan young-adult spending.
- Forecasts, alerts, and recommendations are stored so the authenticated user
  can view history.
- A deployment owner must choose and schedule the retention interval before
  production use. Users can delete their transactions/budgets. The admin can
  export one account or delete a disabled account and its financial/analysis
  dependencies after reconfirmation. Audit identifiers survive account deletion;
  backups, exported copies and audit retention require separate operator handling.
  There is no self-service full-account erasure flow in the mobile app.

## Financial safety statement

The system provides financial decision support. Forecasts are estimates,
unusual-spending alerts are not fraud findings, and recommendations are not
professional financial advice or guaranteed outcomes.

## Production requirements

- Generate unique secrets of at least 32 random bytes.
- Use TLS at the reverse proxy.
- Rotate database and JWT credentials.
- Restrict database access to the backend. The hosted guide uses PostgreSQL;
  local Compose uses persistent MySQL and is a separate data target.
- Back up and encrypt the database.
- Admin authentication/reconfirmation has database-backed throttling and mobile
  sessions have version-based revocation. Broader API rate limiting and an edge
  access/MFA boundary remain deployment work; these controls are not equivalent.
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
