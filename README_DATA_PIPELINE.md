# Model Data

Project: **Personal Spending Behavior Forecasting Using LSTM Neural Networks
with Isolation Forest and Rule-Based Financial Decision Support**

This folder now contains only the generated young-adult dataset, model-ready
training inputs, and the files needed to inspect or reproduce them.

## Important facts

- The retained dataset is synthetic and represents 300 simulated users aged
  18–35.
- The currency is KES and spending is aggregated weekly for forecasting.
- Synthetic data support controlled model development; they are not evidence of
  the real spending behaviour of Kenyan young adults.
- The data are cleaned, split chronologically, and ready for training.
- Feature and target scaling was fitted on the training partition only.
- No final models have been trained. The saved smoke-test result only confirms
  that all four code paths execute successfully.

## Files to use

### LSTM forecasting model

- `data/model_ready/lstm_train.npz`
- `data/model_ready/lstm_validation.npz`
- `data/model_ready/lstm_test.npz`
- `data/model_ready/lstm_metadata.json`

The arrays have shapes `(3600, 8, 20)`, `(900, 8, 20)`, and `(900, 8, 20)`.
The target is the same user's total spending in the next weekly period.

### Multiple Linear Regression baseline

- `data/model_ready/linear_regression_train.parquet`
- `data/model_ready/linear_regression_validation.parquet`
- `data/model_ready/linear_regression_test.parquet`

This is a baseline comparison model and uses the same target dates as the LSTM.

### Isolation Forest unusual-spending model

- `data/model_ready/isolation_forest_train.parquet`
- `data/model_ready/isolation_forest_test.parquet`
- `data/model_ready/isolation_forest_labels.parquet`

Fit the model without the labels. Use the separate label file only for
controlled evaluation. This component detects unusual spending, not fraud.

### Rule-based financial decision support

- `data/model_ready/recommendation_test_cases.csv`
- Rules and their smoke test are in `scripts/smoke_test_models.py`.

### Synthetic source data

The four Parquet files in `data/synthetic/` are the source used to create the
model-ready files. They are retained so features and splits can be rebuilt:

- `users.parquet`
- `transactions.parquet`
- `budgets.parquet`
- `anomaly_labels.parquet`

## Reproduce or verify

Install the required packages:

```powershell
python -m pip install -r requirements.txt
```

Rebuild the model-ready files from the retained synthetic source:

```powershell
python scripts/prepare_model_data.py --mode quick
```

Run lightweight checks for the LSTM, Linear Regression, Isolation Forest, and
rule engine:

```powershell
python scripts/smoke_test_models.py --mode quick
```

The smoke tests are sanity checks only; they do not save final trained models or
provide final performance results.
