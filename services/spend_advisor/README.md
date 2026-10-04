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
- `SPEND_ADVISOR_FEEDBACK_DB`: SQLite file in an existing writable directory.
  Startup creates the local tables. Provision persistent hosting storage separately.

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
prospective budget availability, feedback transport/denominator (#31), and approved
deployment with HTTP smoke (#32). No hosted database was created or migrated.

## Persistent feedback (proposed companion contract)

The required `/recommendations` response remains unchanged. All companion calls
use the same private server-to-server authorization and household scope:

- POST `/recommendations/offers` with `{userId,month,year}` returns
  `{offers:[{offerId,revision,item}]}`. Obtain/display this version before feedback.
- POST `/recommendations/feedback` with
  `{userId,month,year,offerId,expectedRevision,action}`. Actions: `shown`, `accepted`,
  `declined`. Decisions increment revision; stale retries return409 instead of
  overwriting a later decision. Refresh offers before a deliberate change.
- POST `/recommendations/metrics` with `{userId,month,year}` returns delivered,
  shown, responded and accepted counts plus rates and their definitions.

`acceptRate` is accepted unique offer versions divided by all unique delivered
versions in the requested **budget period**, including unanswered and superseded
offers. `shownAcceptRate` uses explicitly acknowledged shown versions. An API
response prepared by the service is delivery, not proof of receipt or viewing.
A decision implies a view; a recommendation request alone does not. Rates are
null for empty denominators. Changed offers do not inherit earlier decisions;
identical retries and unrelated snapshot changes do not inflate the denominator.

SQLite transactions serialize updates; data survives process restart. Snapshot
identity is recorded separately from content identity; workers with a superseded
snapshot are rejected. Deploy a single snapshot version per service and replace
workers together: an old process restarting can otherwise activate its old source.
Historical `active` counts reflect the most recent response for each period, not
eager reconciliation of every household after a snapshot replacement. Feedback
always checks the current source's recommendations before accepting a decision.

The external platform still must authorize the household. These endpoints and
definitions require agreement before integration. Fixture decisions test accounting;
they are not measured human acceptance or realized savings. No real acceptance
rate has been claimed. Retention/access policy for stored identifiers and reasons
must be set before use beyond synthetic staging.
