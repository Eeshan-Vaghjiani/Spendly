# API Guide

The mobile API's machine-readable contract is `docs/openapi.yaml`.
The separate privileged admin contract and safeguards are documented in
[Administrator management](admin_management.md).

Local base URL:

```text
http://localhost:5000/api/v1
```

## Authentication

Register or log in, then send the JWT:

```http
Authorization: Bearer <access_token>
```

Tokens expire after the configured interval. The server also checks each token's
account version: admin session revocation or account-status changes invalidate
older tokens, even after reactivation. Resources are always filtered by the
authenticated user. Admin endpoints do not accept these tokens.

## Main workflow

1. `POST /auth/register`, `/auth/login`, or `/auth/google`
2. `PUT /auth/onboarding` after a new user finishes or skips the introduction
3. `PUT /auth/profile` to change only the authenticated user's username
4. `POST /transactions` or `POST /transactions/upload`
5. `POST /budgets`
6. Read `/analytics/dashboard?period=monthly` for headline aggregates
7. `POST /analysis/run`, then read `/analysis/latest`, `/forecasts`, `/alerts`,
   and `/recommendations`

Dashboard periods are `weekly` (UTC Monday through today), `monthly` (first of
the UTC month through today), `last_3_months` (rolling three months through
today), `yearly` (January 1 through today), and `all_time` (no date filter).
Bounded ranges use a half-open `[start, next-day)` query.

The analysis endpoint aggregates weekly history, validates the eight-period
look-back, runs LSTM inference, calculates the internal Linear Regression
comparison, evaluates recent transactions with Isolation Forest, executes
transparent rules, and stores the results.

## Errors

All errors use:

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_HISTORY",
    "message": "More transaction history is required before a forecast can be produced."
  }
}
```

Common statuses are 401 authentication, 404 user-owned resource not found, 409
duplicate/conflict, 413 upload too large, and 422 validation or insufficient
history.

## Safety

Do not describe unusual-spending output as fraud. Recommendations are automated
decision support rather than professional financial advice.
