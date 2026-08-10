# Forecasting Model Comparison

Training date (UTC): 2026-07-25T15:30:24.782009+00:00

Evaluation uses the same 900 chronologically held-out weekly targets for the LSTM, Multiple Linear Regression, previous-period naive forecast, and four-period moving average.

| Model | MAE (KES) | RMSE (KES) | MAPE (%) | R-squared | Train seconds | Inference seconds |
|---|---:|---:|---:|---:|---:|---:|
| linear_regression | 3895.086 | 6416.555 | 192.801 | 0.2185 | 0.224 | 0.008343 |
| lstm | 5156.716 | 6854.624 | 301.901 | 0.1081 | 12.574 | 0.905553 |
| moving_average_4 | 5344.964 | 7968.435 | 303.271 | -0.2052 | 0.000 | 0.002831 |
| naive_previous_period | 6798.629 | 10136.904 | 247.594 | -0.9505 | 0.000 | 0.000325 |

## Result

The LSTM did not achieve the lowest test MAE. It remains the main project model, but this controlled experiment does not justify claiming that its complexity improved forecast accuracy.

The LSTM ran for 10 epoch(s); its best checkpoint was selected using validation loss and test data were not used for model selection.

MAPE excludes actual values equal to zero. The metrics table records the number of non-zero rows included.

## Limitations

- All training and evaluation records are synthetic controlled data.
- Metrics do not establish performance for real Kenyan young adults.
- The quick dataset covers approximately 180 days, limiting seasonal evaluation.
- Multiple records share the same three weekly test dates across users, so uncertainty across longer calendar periods is not measured.
