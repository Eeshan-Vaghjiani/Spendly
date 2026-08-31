# Spendly administrator management — release 1.2.0

The existing environment-configured administrator is the highest-privilege
**application** operator. This is a separate browser-only security boundary,
not a role that a normal mobile user can request or assign to themselves.
No administrator password, token or elevated client mode is included in the APK.

Open `/admin/login`, then **Manage system** (`/admin/manage`). Existing admin
credentials remain in use. Do not share this account with testers.

## Capabilities

| Area | Administrator capability | Safeguard |
| --- | --- | --- |
| Accounts | Search, filter, paginate and inspect any account | No password hashes or Google subject identifiers in responses |
| Profile | Correct display names and unique usernames | Email, identity, consent and protected fields are immutable here |
| Access | Disable/enable accounts; revoke all sessions | Disabling or changing active status increments a server-checked token version; old tokens cannot work again after reactivation |
| Financial records | Add, edit and delete transactions and budgets for a selected user | Existing validation and duplicate checks; explicit user/record ownership; KES only |
| Insights | Review forecasts, unusual-spending alerts and recommendations | Read-only historical outputs; not proof of fraud or guaranteed predictions |
| Operations | Pause/resume new analysis requests globally | Persisted switch; no artifact or threshold changes; normal financial CRUD and stored history remain available |
| Data export | Download one account's JSON, including all five financial/output record types | Password reconfirmation and reason; excludes credentials; fails explicitly above 50,000 records |
| Deletion | Permanently delete a disabled account and its financial/analysis records | Exact username confirmation, current admin password and reason; no app undo |
| Accountability | Read paginated admin audit records | No edit/delete audit endpoint; changes and their audit records commit together |

Corrections do not rewrite old analyses. They remain historical snapshots until
the user requests fresh analysis. The pause switch prevents requests that start
after it is enabled; work already running may complete. The switch is **not** V2
shadow mode or a model deployment mechanism. Frozen V2 integration remains at
the [readiness-review stage](model_integration_readiness_v2.md).

## Authentication and security

- Admin browser sessions expire after 30 minutes idle or 8 hours total.
- Rotating the configured admin username/password invalidates existing admin
  sessions through a keyed credential stamp. No password is stored in cookies.
- Cookies are HttpOnly and SameSite=Strict. Set `SESSION_COOKIE_SECURE=true` for
  HTTPS production (included in `render.yaml`; defaults true in Render).
- Every privileged write **and export** requires the admin session,
  `X-CSRF-Token`, a 5–300 character reason and the current administrator password.
  The password is cleared from the form after submission/close.
- HTTP Basic remains supported for read-only diagnostic requests. It cannot
  perform management writes. Ordinary user JWTs never grant admin access.
- Database-backed throttling blocks further checks after 10 recorded failures per
  server-observed peer address in 15 minutes, across form/Basic/reconfirmation
  paths. Expired attempt rows are pruned on the next checked authentication.
  Forwarded headers are not trusted. Behind a shared proxy, peers may share
  this limit: add an edge rate limit and configure trusted proxy handling before
  a broader rollout. This is not a complete distributed brute-force defence.
- Responses use `no-store`, `nosniff`, `X-Frame-Options: DENY` and no-referrer.
- Audit entries contain actor, UTC time, action, opaque target, reason, and
  limited metadata (field names/counts), not credential or financial snapshots.
  Administrators must not type secrets into reasons. The audit trail survives
  account deletion; apply an explicit retention policy for these identifiers.
- The app cannot edit its audit trail, but a database owner can. It is not a
  cryptographically tamper-proof or independently backed-up audit system.

Keep the console behind HTTPS and, for real financial data, an additional
identity-aware access/MFA boundary. This release keeps the existing single
administrator credential setup; it does not implement multi-admin identities,
MFA, password reset, database restoration or host/root-shell access.

## API contract

Prefix: `/api/v1/admin`. All responses use the existing success/error envelope,
except the authenticated JSON export attachment. Lists accept `page` and
`per_page` (default 20, maximum 100).

| Method | Path | Inputs / result |
| --- | --- | --- |
| GET | `/users` | `q` literal name/email/username search; `status=all/active/disabled` |
| GET | `/users/{id}` | Account metadata, counts and lifetime income/expenses; audited access |
| PATCH | `/users/{id}` | Any of `display_name`, `username`, `is_active`; rejects protected/unknown fields |
| POST | `/users/{id}/revoke-sessions` | Invalidates all previously issued tokens |
| DELETE | `/users/{id}` | `confirm_username`; account must already be disabled |
| GET | `/users/{id}/records/{kind}` | `transactions`, `budgets`, `forecasts`, `alerts`, `recommendations`; audited access |
| POST | `/users/{id}/records/{kind}` | `record` object; only transactions/budgets |
| PUT | `/users/{id}/records/{kind}/{record_id}` | Complete validated `record` object; only transactions/budgets |
| DELETE | `/users/{id}/records/{kind}/{record_id}` | `confirm_id` equal to record ID; only transactions/budgets |
| POST | `/users/{id}/export` | Complete bounded per-account JSON export; audited |
| GET | `/audit` | Paginated audit; optional `target_id` exact filter |
| GET | `/settings` | Analysis enablement and loaded model/runtime metadata |
| PUT | `/settings` | Boolean `analysis_enabled` |

Every non-GET call includes `reason` and `admin_password` alongside the listed
inputs, with the CSRF header from the authenticated admin page. Never put them
in a URL, save them in an example request collection, or log request bodies.
An admin cannot change which user owns a record by adding a `user_id` field.

Error cases include 401 admin session/credentials required, 403 CSRF/session/
reauthentication failure, 404 target not found, 409 uniqueness conflict, 413
oversized export, 422 invalid input or missing confirmation, and 429 throttling.
The normal `/analysis/run` returns 503 `ANALYSIS_PAUSED` when paused.

## Migration and rollout

1. Take a recoverable database backup outside the application.
2. Deploy **all** application changes, including migrations 0004 and 0005.
   Render startup applies migrations via `backend/start.sh`. For local use:
   `python -m flask --app backend.run:app db upgrade --directory backend/migrations`.
3. Verify `/api/v1/health` reports `api_release: 1.2.0` and capability
   `admin_management`, not merely `healthy` from an older deployment.
4. Sign in over HTTPS; verify a non-production test account before using any
   support operations on real accounts. Confirm a normal mobile login cannot
   access admin endpoints.
5. Only then distribute the replacement APK. See the
   [APK/deployment guide](live_deployment_and_tester_apk.md).

Migration 0005 adds a default-zero user token version, audit and login-attempt
tables, and system settings. Existing mobile tokens (without a version claim)
remain valid as version zero until the administrator revokes them. A schema
rehearsal also aligns ORM email-index metadata with migration 0001; the existing
database unique email constraint is preserved without rebuilding that index.

For rollback, pause insights if needed and prefer a forward fix. Do not casually
downgrade 0005: it removes the audit trail and token revocation state. Old server
code does not enforce those revocations or the analysis pause flag. Coordinate
token invalidation and backups before any server rollback. Keeping an old APK
does not itself provide a safe Android downgrade (Android normally rejects a
lower versionCode).

## Verification

Run `python -m pytest backend/tests services/recommendation_engine/tests -q`.
Focused tests cover privilege separation, CSRF, reconfirmation, protected
fields, search/pagination, token revocation, record ownership and validation,
atomic audit/financial rollback, deletion dependency cleanup, export safety,
analysis pausing, session expiry, credential rotation, throttling, and the
upgrade of an existing account to the exact ORM schema.

Browser QA uses `python scripts/preview_admin_dashboard.py` with disposable
local data. Check sign-in, search, account details, profile edit, record form,
confirmation/error handling, audit display and narrow-screen scrolling. No
real user's records are needed for that verification.

Verified locally on 2026-08-31: **106 backend/recommendation tests passed**
(27 dependency/configuration deprecation warnings), Flutter analysis reported
no issues, and **20 Flutter tests passed with one live-API test skipped** because
`LIVE_API_BASE_URL` was not provided. The migration rehearsal preserved an
existing account and matched ORM metadata. Browser checks verified sign-in,
search, account details, a profile change, incorrect-password rejection, a
successful budget correction, audit feedback and a 390-pixel layout; there
were no browser console errors. A narrow-layout summary overflow was corrected
during that review. YAML parsing, JavaScript syntax and `git diff --check` passed.

The replacement APK is version 1.2.0 (code 4), SHA-256
`361859e54a7d1e3f133f27d70f8d2909830a10f3d9951c0f8f7fb755a4f0531a`.
Both its signature/package compatibility and its embedded live URL/public
Google client ID were checked against the previous tester APK. The previous
APK was retained in `mobile/dist` as a timestamped backup. No frozen model
artifact was changed. No production deployment, physical-device update or
real Google OAuth flow was performed in this verification.
