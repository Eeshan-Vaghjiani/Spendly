# Wasaa snapshot and model compatibility

**Status, 20 October 2026:** the frozen transfer evaluation is complete and its
saved outputs have been re-audited. This document preserves the initial data
review and explains the adopted mapping decisions. See the
[final testing decision](../docs/wasaa_testing_and_model_decision.md) and
[fresh verification record](evidence/wasaa_transfer/verification_2026_10_20.json).
The owner confirmed dataset evaluation and reporting only; a separate advisor
deployment/platform integration is not required.

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

## Input limitations and adopted mapping decisions

The snapshot has no independent anomaly labels and no merchant column. Description
and payment source are not established merchant identities. Fabricating a merchant
would change the retained IF's features and duplicate matching. An explicit
missing-merchant sensitivity test could be reported separately, but is not a full
input-equivalent validation. Precision/recall/F1 cannot be computed against budget
overruns as if those were anomaly ground truth.

Category vocabulary: Airtime and Data, Entertainment, Groceries, Household Help,
Medical, Rent, Savings, School Fees, Transport, Utilities. The locked experiment
used Groceries->Food, Medical->Healthcare and School Fees->Education, together
with unchanged Entertainment, Rent, Transport and Utilities. Savings, Household
Help and Airtime and Data were excluded only from the explicitly restricted
mapped-category scenario (84.21% of evaluated amount).

The retained total LSTM was also evaluated on all outflows and consumption
excluding Savings. Missing merchants used the retained empty-string fallback;
complete internal weeks were assumed and partial boundary weeks excluded. These
are declared sensitivity scenarios, not proof of fully equivalent R3 inputs.
Models/scalers/thresholds remained frozen. Full results are in
[WASAA_TRANSFER_RESULTS.md](WASAA_TRANSFER_RESULTS.md).

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

Dataset review #29 and transfer testing #30 are complete. The 20 October
recheck found the same input identities, reconciliation and saved metrics.
Document the negative/limited transfer finding in #11; no separate HTTP service
or feedback rollout is needed for the owner's dataset-only requirement.
