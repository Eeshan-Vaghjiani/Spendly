# Wasaa snapshot and model compatibility

The two authorized synthetic exports were retrieved successfully over HTTPS.
Credentials and tokens were held at runtime and are not included in this report,
source or snapshot metadata. No upstream financial records were created/changed.

| Table | Rows | Households |
|---|---:|---:|
| spending_records | 293,448 | 500 |
| budget_categories | 80,013 | 500 |

Spending dates:2025-04-01 06:02 UTC through2026-09-28 21:58 UTC. Source timestamps
exist; complete observed weeks still require a declared coverage policy. Do not
treat the final partial week/month as complete because a budget row exists.

No duplicate spending IDs, duplicate category-period rows, missing budget links,
household/category mismatches or UTC month/year mismatches were found. Per-budget
spending sums exactly reconcile to actual_kes.26,460 category-months (33.0696%)
exceed allocated_kes.64,163 budgets are APPROVED and15,850 PENDING.

Hashes, columns and missing counts are in wasaa_snapshot_review.json. Raw exports
remain local under datasets/wasaa_snapshot, never committed. Float summation was
used for aggregate reconciliation; service monetary arithmetic uses Decimal.

## Mapping decisions needed before scoring

The snapshot has no independent anomaly labels and no merchant column. Description
and payment source are not established merchant identities. Fabricating a merchant
would change the retained IF's features and duplicate matching. An explicit
missing-merchant sensitivity test could be reported separately, but is not a full
input-equivalent validation. Precision/recall/F1 cannot be computed against budget
overruns as if those were anomaly ground truth.

Category vocabulary: Airtime and Data, Entertainment, Groceries, Household Help,
Medical, Rent, Savings, School Fees, Transport, Utilities. Possible mappings
Groceries->Food, Medical->Healthcare, School Fees->Education require confirmation.
Savings may be a transfer rather than consumption. Household Help and Airtime and
Data have no direct frozen-category output. They cannot simply be dropped or mapped
to Shopping/Subscriptions without changing the evaluated question.

The retained total LSTM can aggregate totals only after deciding which records
represent expenses and whether category/merchant-dependent recurring features are
supported. The category LSTM additionally needs a complete explicit category map.
Both models remain frozen; no inference scores have been inspected on this data.

## Service baseline supported now

The records support retrospective approved-budget review: identify optional
categories above allocation, state the observed gap, and propose reviewing a
comparable future period if that limit is feasible. Existing budget_category_id
provides a traceable targetId. This is rule-based planning evidence, not an ML
forecast, realized saving or measured recommendation acceptance.

The snapshot lacks approval timestamps and recommendation feedback. Prospective
backtesting must not assume the stored allocation was known before spending.
Acceptance-rate evidence needs issued/shown/accepted events and a defined
denominator. Those are separate from the33% over-budget statistic.

## Next

Resolve category/expense/merchant/coverage semantics in #29, then lock supported
model tests in #30. Complete feedback #31 and service handoff #32. Source and PRs
remain in Spendly; platform integration is over HTTP, not a platform repository PR.
