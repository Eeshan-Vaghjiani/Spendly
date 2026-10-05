# Spend-advisor

Standalone Flask HTTP service for a reviewed **synthetic** Wasaa snapshot.
This implementation uses approved budget gaps as a transparent retrospective
baseline. It does not call, train or claim predictions from either ML model.

## Contract

- `GET /health`: service identity and synthetic baseline status.
- `POST /recommendations` with `{userId, month, year}`.
- Response: `{items:[{type, reason, savingKes, targetId}]}`, at most three items.
- Unknown household/period:404; invalid request:422; invalid service key:401.

`userId` maps to `user_profile_id`; `targetId` is the existing budget_category_id.
Savings are exact Decimal differences between recorded actual spending and an
approved allocation, restricted to Entertainment, Groceries, Transport and Airtime
and Data. Rent, medical, school fees, savings and household help are not treated
as automatically reducible expenses. Pending allocations do not produce advice.

The reason explicitly describes returning to the approved allocation in a
comparable period **if feasible**. It is not a guaranteed/realized saving or a
forecast. The historical month is selected for retrospective review; the snapshot
has no budget approval timestamp, so this service must not be represented as a
causal prospective evaluation of advice. A future advice workflow needs inputs
known at its actual decision date.

## Run locally

Use an isolated Python environment with this folder's requirements, Flask tests
via `python -m pytest services/spend_advisor/test_contract.py -q`.

Set runtime environment variables (do not commit their values):

- `SPEND_ADVISOR_SNAPSHOT`: local directory containing snapshot.json and the
  verified budget_categories.csv.
- `SPEND_ADVISOR_API_KEY`: random private ASCII service key, at least32 characters.

Run `python -m services.spend_advisor.app` on loopback8000. On an approved Linux
host, use `gunicorn 'services.spend_advisor.app:create_app()' --bind 0.0.0.0:8000`.
No process is launched by importing the factory, and requests never mutate source
records. The snapshot must be provisioned separately; it is not committed.

POST calls require `Authorization: Bearer <service key>`. This is a proposed
server-to-server contract addition and must be configured with the platform.
The platform must authorize each household before forwarding userId. This key
is not a mobile-user token and must never be shipped to clients. Tests establish
household data selection, not authorization inside the external platform.

## Handoff

Spendly hosts its own source and review PRs. There is no required PR to the Wasaa
platform repository. Configure the approved service URL through
`SPEND_ADVISOR_SERVICE_URL`, plus the agreed service credential transport.

Remaining work: confirm this baseline's saving/target semantics, service auth,
prospective budget availability, persistent recommendation exposure/feedback and
acceptance denominator (#31), and approved deployment with HTTP smoke (#32).
This service does not invent acceptance rates. No hosted deployment or persistent
database migration is performed by this change.
