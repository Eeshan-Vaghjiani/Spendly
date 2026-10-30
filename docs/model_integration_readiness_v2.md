# Frozen V2 model integration readiness

Status: **readiness review complete; production integration blocked**. The frozen
files were not retrained, edited, copied into `artifacts/models`, or loaded by the
application. Spendly continues to run its existing V1 inference path and fallback.

## Evidence and immutable files

The development archive is
`university_trial_colab/spendly_development_v2_output.zip`. Its SHA-256 values
were recalculated directly from the ZIP entries and match the locked final-seed
manifest:

| Frozen entry | Model/version | SHA-256 |
| --- | --- | --- |
| `frozen_v2_forecast.joblib` | `hist_absolute_ratio_leaf31` | `4a9114d07686efa069f2b57d40f8c56d49d6b2f5e3e7afa8bb5f4a0c00381afb` |
| `frozen_v2_anomaly_scaler.joblib` | RobustScaler V2 | `0fe26c5292e15436d0dee2a285a5408b571d56ae017d3a07e63d2ef30d087cac` |
| `frozen_v2_isolation_forest.joblib` | `if_4096` | `545eca46ecd82d2fd0fa903e11ec67bb99ff2266971d5423d9cc888632e85582` |
| `v2_feature_schema.json` | V2 contract (partial; see blockers) | `66f2664c2f516a8e848da5c167e6b5325ec7712c74dec995a61574545680c5d2` |

The untouched final-seed result reports forecast WAPE 29.852856%, R² 0.675197,
and anomaly precision/recall/F1 of 0.812261/0.807619/0.809933. Those are
synthetic external-test results, not accuracy guarantees for real Spendly users.

## Forecast contract

The estimator accepts one ordered 169-element numeric row and predicts a
dimensionless next-week spending/monthly-income ratio. Production postprocessing
would multiply the prediction by that same user's monthly income and clamp the
KES result at zero. The horizon is the next full Monday–Sunday week and the
lookback is eight complete Monday–Sunday weeks.

Ordering reconstructed from the frozen notebook is:

1. 128 weekly values: eight oldest-to-newest rows, each containing total,
   non-recurring and recurring spending (KES), transaction count, average amount
   (KES), then 11 KES category totals in this order: Airtime and Data, Education,
   Entertainment, Food, Healthcare, Irregular Expenses, Rent, Savings,
   Subscriptions, Transport, Utilities.
2. 17 context values: monthly income (KES), age (years), income day (1–31), three
   one-hot employment flags (`student`, `employed`, `self_employed`), days in the
   target week within three days before payday, month sine/cosine, ISO-week
   sine/cosine, four-week total mean/median/standard deviation, four-week
   non-recurring mean/median, and the inferred recurring-plus-discretionary
   baseline (KES).
3. 24 past-only recurring-schedule values: for Rent, Utilities, Subscriptions,
   then Savings, six values each—due-in-target-week flag, expected amount/monthly
   income, schedule confidence, capped days-since-last normalized by 90, and
   sine/cosine of expected day of month.

Zero-filled weeks are part of the training construction. The exported JSON does
not name the 41 context positions or define forecast missing-value handling; the
notebook is currently the only source for them. That is not a sufficient
production schema.

## Anomaly contract

The hybrid scores expense transactions only, in deterministic
user/timestamp/transaction-ID order. Its 29 ordered float features are listed in
`v2_feature_schema.json`. They consist of log KES amount; amount/income and
past-only user/category/recurring ratios; one-hour, one-day, seven-day and
same-day past counts/sums; time gaps in hours or minutes; 0/1 recurring, weekend,
night and known-recurring-category flags; hour sine/cosine; merchant-cluster
counts/ratios; and historical night proportion. All medians, means, counts and
schedule evidence must exclude the transaction being scored and all future data.

Missing anomaly values use the 29 exported training medians before the frozen
RobustScaler. Rule score and Isolation Forest percentile are combined as:

```text
hybrid = rule_score + 0.25 * percentile(isolation_score, reference_scores)
alert  = hybrid >= 2.24128264710533
```

Rules also need raw category, merchant, amount, timestamp, monthly income,
past-user count and known recurring categories. Alerts are review prompts—not
fraud findings—and may never modify a transaction automatically.

## Blocking incompatibilities

1. The running forecast path supplies an 8×20 V1 tensor (and 160-value linear
   row), not the V2 169-value row. The anomaly path supplies 10 V1 features, not
   29 plus the rule context.
2. Spendly currently stores nullable monthly income but not age, employment
   status or income day. The V2 notebook requires all four profile attributes.
   Inventing defaults would silently change the frozen model's meaning.
3. The anomaly percentile reference distribution is not packaged. The final
   notebook reconstructs it from original training plus 2025 development
   features. A scalar threshold, scaler and Isolation Forest cannot reproduce
   the verified hybrid score without that immutable reference array.
4. The JSON omits the names/order and missing-value policy for 41 forecast
   context features. The notebook reveals the order, but a deployable contract
   must travel with the artifacts and be checksum-locked.
5. The forecast joblib was serialized with scikit-learn 1.6.1 and its compiled
   `_loss` module. The backend currently permits scikit-learn 1.7.x. A clean,
   pinned runtime compatibility test is required before loading untrusted pickle
   formats in a service process.
6. The V1 registry assumes LSTM/linear dictionaries and a simple Isolation
   Forest API. V2 needs separate adapters and cannot be a file replacement.

## Required shadow-mode design

Once the blockers are resolved, use an independent V2 adapter behind two
default-off server flags, `V2_FORECAST_SHADOW_ENABLED` and
`V2_ANOMALY_SHADOW_ENABLED`. Shadow failures must be caught and recorded without
affecting the V1 result, dashboard response, budgets, balances, transactions or
recommendations.

Store no raw feature vector. Store user ownership, run ID, component/model/schema
versions and checksums, generated time, input-window start/end, target horizon,
numeric output/score, status (`completed`, `insufficient_data`, `timeout`,
`error`, `matched`), a safe error code, and later actual outcome. Match forecast
actuals by user and the exact half-open target week. Calculate cohort and rolling
WAPE only after the week closes and data completeness is known. For anomalies,
accept explicit user feedback and monitor precision, recall and F1 overall plus
duplicate, split-transaction and frequency-burst recall. Deduplicate alerts by a
stable user/event fingerprint.

Apply a strict timeout/circuit breaker and retain V1/personal-history fallback.
Disabling either flag must require no migration or artifact deletion. Only the
owning user may read shadow records; operational logs should contain IDs,
versions, timing and error codes, not merchants, amounts or feature vectors.

## Gate before any code integration

- Package a complete ordered forecast schema and immutable anomaly reference
  score array, each with a checksum.
- Decide how the missing profile inputs are collected, consented, validated and
  deleted; then rerun a frozen contract test using those exact app semantics.
- Pin and reproduce the training serializer runtime in an isolated inference
  image, then test load, shape, output, timeout and corrupted-artifact behavior.
- Create golden feature fixtures from the notebook and require byte/float-tolerant
  parity with the production feature builder.
- Add shadow tables, ownership tests, flags, dashboards, actual matching and
  rollback exercises before showing any V2 output to users.

Until every gate passes, V2 remains **eligible for integration review**, not
production-ready.
