# Model Card: LSTM Spending Forecaster v1

## Purpose

Forecast the same user's total expense outflow one weekly period ahead. The
LSTM is the project's main forecasting model. Multiple Linear Regression is a
baseline comparison only.

## Data

- Source: `synthetic_kenyan_young_adult_finance`
- Users: 300 simulated users aged 18–35
- Currency: KES
- History: approximately 180 simulated days
- Sequences: 5,400
- Split: 3,600 train, 900 validation, 900 test
- Synthetic records used: yes

These simulations are not evidence of actual spending behaviour among Kenyan
young adults.

## Inputs and target

- Aggregation: weekly
- Look-back: 8 weekly periods
- Horizon: 1 weekly period
- Features: 20 spending, category, count, amount, income, recurring-expense,
  budget, previous-period, rolling-average, and growth features
- Target: next-period total expense outflow for the same user

Feature and target min-max parameters were fitted on training data only.
Partitions are chronological and test data were not used for model selection.

## Training

- TensorFlow/Keras 2.16.2
- Architecture: one 32-unit LSTM, a 16-unit dense layer, and one output
- Dropout: 0 (not added without evidence that it was needed)
- Optimizer: Adam
- Validation-loss checkpointing
- Early stopping with best-weight restoration
- Epochs completed: 10
- Device: CPU

## Test metrics

| Model | MAE (KES) | RMSE (KES) | MAPE | R-squared |
|---|---:|---:|---:|---:|
| LSTM | 5,156.72 | 6,854.62 | 301.90% | 0.1081 |
| Linear Regression | 3,895.09 | 6,416.56 | 192.80% | 0.2185 |
| Moving average (4) | 5,344.96 | 7,968.44 | 303.27% | -0.2052 |
| Previous-period naive | 6,798.63 | 10,136.90 | 247.59% | -0.9505 |

MAPE excludes one zero-actual test row. The LSTM did not outperform Linear
Regression, so this experiment does not justify a superiority claim.

## Expected and inappropriate uses

Expected: controlled prototype forecasts and model-integration testing.

Inappropriate: guaranteed financial outcomes, credit decisions, population
claims, or autonomous high-impact financial actions.

## Artefacts

`artifacts/models/forecasting/v1/`

## Limitations

- Synthetic-only training and evaluation.
- Short history and only three unique test target dates.
- High MAPE due to small actual values and heterogeneous simulated users.
- Real-user drift and category differences have not been evaluated.
