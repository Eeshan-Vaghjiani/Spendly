# Current Project Status

Project: **Personal Spending Behavior Forecasting Using LSTM Neural Networks
with Isolation Forest and Rule-Based Financial Decision Support**

Status date: 2026-07-25

## 1. What is complete

- A deterministic synthetic financial dataset for controlled development.
- Explicit user ages from 18 to 35 in the synthetic user table.
- KES transaction, budget, and controlled anomaly-label tables.
- Weekly spending aggregation and feature engineering.
- Chronological train, validation, and test partitions.
- Training-only min-max scaling for the LSTM inputs and target.
- Model-ready files for the LSTM, Multiple Linear Regression baseline, and
  Isolation Forest.
- Six basic rule-engine smoke cases.
- Lightweight execution-path smoke tests for all three models and the rules.

The earlier repository cleanup intentionally removed the previous raw datasets,
audit reports, obsolete trained models, and stale pipeline reports. Therefore,
`reports/training_readiness.md` and `reports/dataset_audit.md` are not present.
The current status is reconstructed from the retained source tables, model
metadata, scripts, and `reports/smoke_test_results.json`.

## 2. Files ready for training

### LSTM

- `data/model_ready/lstm_train.npz`
- `data/model_ready/lstm_validation.npz`
- `data/model_ready/lstm_test.npz`
- `data/model_ready/lstm_metadata.json`

### Multiple Linear Regression baseline

- `data/model_ready/linear_regression_train.parquet`
- `data/model_ready/linear_regression_validation.parquet`
- `data/model_ready/linear_regression_test.parquet`

### Isolation Forest

- `data/model_ready/isolation_forest_train.parquet`
- `data/model_ready/isolation_forest_test.parquet`
- `data/model_ready/isolation_forest_labels.parquet`

### Rule-engine cases

- `data/model_ready/recommendation_test_cases.csv`

## 3. Selected aggregation period

Weekly.

## 4. LSTM look-back window

Eight weekly periods.

## 5. Forecast horizon

One weekly period ahead.

## 6. Selected LSTM features

1. `total_spending`
2. `category_airtime_and_data`
3. `category_education`
4. `category_entertainment`
5. `category_food`
6. `category_healthcare`
7. `category_irregular_expenses`
8. `category_rent`
9. `category_savings`
10. `category_subscriptions`
11. `category_transport`
12. `category_utilities`
13. `transaction_count`
14. `average_transaction_amount`
15. `income`
16. `recurring_expenses`
17. `budget_difference`
18. `previous_period_spending`
19. `rolling_average_4`
20. `spending_growth_rate`

The Linear Regression baseline contains the same 20 features flattened across
the same eight historical periods, producing 160 ordered lag columns.

## 7. Target variable

The same user's total expense outflow in the next weekly period:
`target_total_spending`.

## 8. Users and sequences

- Synthetic users: 300
- User age range: 18–35
- Synthetic transactions: 60,572
- LSTM sequences: 5,400
- Training sequences: 3,600
- Validation sequences: 900
- Test sequences: 900
- LSTM input shape: `(sequences, 8, 20)`

## 9. Data classification

All data currently retained under `data/synthetic/` and `data/model_ready/` are
synthetic controlled-development records. No real, public, or anonymised source
records remain in the cleaned workspace. Synthetic data must not be described
as observed spending behaviour among Kenyan young adults.

## 10. Missing prototype components

- Independent model-data validation report.
- Final TensorFlow/Keras LSTM training and evaluation.
- Final Multiple Linear Regression and simple forecasting baselines.
- Final Isolation Forest training, threshold selection, and evaluation.
- Versioned saved model artefacts.
- Modular recommendation engine and comprehensive tests.
- Versioned OpenAPI contract.
- Flask backend, authentication, database models, migrations, and tests.
- MySQL development environment and seed data.
- Thin end-to-end integration slice.
- Flutter mobile application and Flutter tests.
- CSV upload contract and validation.
- Docker development environment.
- Security, privacy, model-card, architecture, API, and mobile documentation.
- Final system-test and readiness reports.

Final training may begin only after `scripts/validate_model_data.py` reports no
critical schema, chronology, scaler, target-consistency, or leakage failures.
