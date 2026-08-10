# API Guide

The complete machine-readable contract is `docs/openapi.yaml`.

Local base URL:

```text
http://localhost:5000/api/v1
```

## Authentication

Register or log in, then send the JWT:

```http
Authorization: Bearer <access_token>
```

Tokens expire after the configured interval. Resources are always filtered by
the authenticated user.

## Main workflow

1. `POST /auth/register` or `POST /auth/login`
2. `POST /transactions` or `POST /transactions/upload`
3. `POST /budgets`
4. `POST /analysis/run`
5. Read `/analysis/latest`, `/forecasts`, `/alerts`, and `/recommendations`

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
