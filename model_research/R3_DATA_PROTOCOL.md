# R3 dataset expansion: declared generation and usage contract

## Goal

Produce a substantially larger **separate** synthetic dataset, not change existing
models or overwrite the original CSV. Quantity alone does not guarantee learning or
real-world generalization. R3's assumptions are hypothetical simulations, not
empirically estimated Kenyan population parameters. No model metrics tune generation.

Default: **1,000 users × 156 weeks** (three years of complete observation per user):
600 training, 100 validation, 100 threshold-calibration, 100 untouched test users and
100 untouched shifted-test users. Amounts KES; explicit Africa/Nairobi offsets;
one CSV per cohort, not a mixed train/test file. A create-only output directory and
SHA256 manifest preserve identity. Default durable path `datasets/spendly_synthetic_r3/`
is ignored by git; source, tests, protocol and aggregate development QA are versioned.
CSV + ZIP companion files allow Colab upload without repository imports.

## New behaviour versus R2 (all declared before generation)

- Three profiles (salaried, irregular/gig income, student/support income) with varying
  levels/rates, pay schedules, category preferences and weekday routines. Profile
  truth is in a separate diagnostic table, never required as model input.
- Persistent but bounded weekly spending state (AR coefficient varies by user),
  individual trends and seasonal amplitudes. Not an exact four-week sinusoid.
- Payday effects follow the user's actual simulated calendar, with late/missed pay
  more likely for irregular earners; higher activity after an observed payment.
- Weekly habits with skipped occurrences and amount noise, grocery/transport/leisure
  preferences, intermittent sparse users, heterogeneous monthly bill due dates.
- Utilities have 8–22% lognormal noise; rent modest noise and occasional legitimate
  permanent changes; subscriptions may change supplier/price. No perfectly constant
  bill amounts by default. Payments can move ±days under shift.
- Random transaction counts and amounts, user-specific idiosyncratic noise, genuine
  zero days and benign night activity. Expected non-bill spend is calculated before
  draws; residual error against this conditional expectation is audited separately
  from bills, so deterministic bill timing cannot masquerade as random variation.
- Benign duplicate purchases, outings/bursts and large expenses remain normal labels.
  Anomaly labels indicate injected scenarios only and are not inferred from magnitude.
- Injected amount shocks, bursts, duplicates, recurring deviations and split events
  across the full history after eight weeks, with user-level prevalence heterogeneity.
  Shifted tests change noise, routines, pay delays and anomaly prevalence. Do not add
  model-perfect thresholds, unique anomalous merchant names or label-derived features.

Separate per-user RNG streams for profiles, ordinary expenses, bills, income,
lookalikes and injected events. Adding users does not alter existing users; disabling
injection leaves benign rows identical. Seeds are reproducibility controls, not tuned
for high scores: train 306173, validation 417239, calibration 528307, test 639373,
shifted test 740419. User IDs are globally unique across seed/cohort, never features.

## Label/coverage contract and leakage boundaries

Every transaction has explicit `is_anomaly=0/1` and nullable shared `event_id`/
`anomaly_type`. Unknown labels must not be synthesized for arbitrary external CSVs.
All covered days are observed, including zero spend; each user has constant
`observation_start` and exclusive `observation_end`. Use chronological completed
Monday–Monday weeks; do not shuffle sequences between train/validation/test.

Training CSV contains income and expense rows; existing V5 loader filters expenses.
Income remains available for future feature work only when earlier than forecast
origin. Profiles, expected-spend diagnostic series, scenario family and event IDs
must never enter model feature matrices. Event IDs may purge split boundaries and
score events, not help prediction.

Validation/calibration/test users have no overlap with training users. Use training
users' earlier weeks for inner early stopping and final refit. Select parameters on
validation; choose thresholds on the separate calibration cohort; freeze before
opening test files. Existing V5's single-file workflow must **not** silently combine
these CSVs, or describe a within-train split as R3 external validation.

The test ZIPs are labelled HOLDOUT_DO_NOT_TUNE. They are generated and hashed but
not used for model scoring or generation-acceptance changes. The manifest does not
claim cryptographic sealing or guarantee a human has never opened a file. Any viewed
holdout becomes development evidence if used to change the method.

## Quality audits, without manufacturing success

For train/validation/calibration: record per-category/type counts, users, timestamps,
missing/duplicate records, zero-day fraction, explicit label prevalence, per-family
support, normal lookalike counts, per-profile coverage, bill amount variability,
realized payday/weekend/seasonal factors, and random ordinary-spend residual versus
the conditional generator expectation. Feature effects audited on generated draws
with known internal multipliers used only for diagnostics; they are not claims of
real-world effect sizes. Print observations and violations; do not automatically
regenerate or adjust parameters until an arbitrary score is achieved.

Run correctness tests on disposable small seeds, not the held-out population.
No test transactions/user-level diagnostic rows are logged. Test exports receive
schema/ownership/coverage checks inside generation only; no holdout quality leaderboard.

## Bounded model sensitivity check

After generation, use deterministic development subsets only: train 16 vs 48 users,
validate on the first 16 validation users; all chosen independently of labels.
Use first 104 covered weeks; training targets end before week 80, validation targets
weeks 80–103. Same 16-unit LSTM/MAE and unchanged weekly recurrence features; 60-epoch
cap. Compare to recurring median/mean, last week and seasonal lag-4 on identical rows.
This is a sample-size diagnostic, not training on all 600 users or a full grid search.

Check Isolation Forest sensitivity independently (current excess view, 128 samples,
200 trees): fit on training users before week 80, fix 0.5% labelled-negative FPR
threshold on 16 calibration users' weeks 64–79, then evaluate 16 validation users'
weeks 80–103. Preserve label support and TP/FP/FN. No two-forest deployment or changes
to default app configuration. Higher volume can change rankings/precision, so old
thresholds and old performance claims cannot be carried across datasets.
