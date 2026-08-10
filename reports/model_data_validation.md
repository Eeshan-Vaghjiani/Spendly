# Model Data Validation

Overall status: **PASSED**

Checks passed: **43/43**

Final model training is permitted only when this report passes.

## Validation checks

| Check | Result | Details |
|---|---:|---|
| Required files exist | PASS | All 11 required files are present. |
| Feature schema | PASS | Metadata defines 20 unique ordered features. |
| Target definition | PASS | Total expense outflow in the next 1 weekly period(s) for the same user |
| Look-back and horizon | PASS | Look-back=8; forecast horizon=1. |
| LSTM train arrays | PASS | All required arrays are present in the train partition. |
| LSTM train shapes | PASS | X=(3600, 8, 20); y=(3600,). |
| LSTM train missing/non-finite values | PASS | No missing or infinite numeric values. |
| LSTM train future target | PASS | Every target period occurs strictly after its input window. |
| LSTM train duplicate user-periods | PASS | No duplicate user/target-period records. |
| LSTM train within-user chronology | PASS | Target periods are ordered within every user. |
| LSTM validation arrays | PASS | All required arrays are present in the validation partition. |
| LSTM validation shapes | PASS | X=(900, 8, 20); y=(900,). |
| LSTM validation missing/non-finite values | PASS | No missing or infinite numeric values. |
| LSTM validation future target | PASS | Every target period occurs strictly after its input window. |
| LSTM validation duplicate user-periods | PASS | No duplicate user/target-period records. |
| LSTM validation within-user chronology | PASS | Target periods are ordered within every user. |
| LSTM test arrays | PASS | All required arrays are present in the test partition. |
| LSTM test shapes | PASS | X=(900, 8, 20); y=(900,). |
| LSTM test missing/non-finite values | PASS | No missing or infinite numeric values. |
| LSTM test future target | PASS | Every target period occurs strictly after its input window. |
| LSTM test duplicate user-periods | PASS | No duplicate user/target-period records. |
| LSTM test within-user chronology | PASS | Target periods are ordered within every user. |
| Chronological split separation | PASS | Train ends 2024-05-13, validation spans 2024-05-20 to 2024-06-03, and test begins 2024-06-10. |
| Training-only scaler metadata | PASS | Feature and target min-max scalers are marked training-only with valid parameters. |
| Stored target scaling | PASS | Every scaled target matches the training-fitted target scaler. |
| Linear Regression train schema | PASS | 3,600 rows and 160 ordered lag features. |
| Linear Regression train missing/non-finite values | PASS | No missing or infinite feature/target values. |
| Linear Regression train duplicate user-periods | PASS | No duplicate user/target-period records. |
| LSTM/Linear Regression train target consistency | PASS | User, input date, target date, and raw target match exactly. |
| Linear Regression validation schema | PASS | 900 rows and 160 ordered lag features. |
| Linear Regression validation missing/non-finite values | PASS | No missing or infinite feature/target values. |
| Linear Regression validation duplicate user-periods | PASS | No duplicate user/target-period records. |
| LSTM/Linear Regression validation target consistency | PASS | User, input date, target date, and raw target match exactly. |
| Linear Regression test schema | PASS | 900 rows and 160 ordered lag features. |
| Linear Regression test missing/non-finite values | PASS | No missing or infinite feature/target values. |
| Linear Regression test duplicate user-periods | PASS | No duplicate user/target-period records. |
| LSTM/Linear Regression test target consistency | PASS | User, input date, target date, and raw target match exactly. |
| Forecasting user coverage | PASS | All partitions contain all 300 users. |
| Isolation Forest feature schema | PASS | Both partitions contain the expected 10 features. |
| Isolation Forest missing/non-finite values | PASS | No missing or infinite model features. |
| Isolation Forest label leakage | PASS | Anomaly labels are absent from the training feature table. |
| Isolation Forest chronological separation | PASS | Train ends 2024-05-06 07:05:47; test begins 2024-05-06 07:11:43. |
| Isolation Forest label compatibility | PASS | All 17,588 test rows have aligned evaluation labels; 235 are positive. |

## Validated model contract

- Look-back window: 8
- Forecast horizon: 1
- Target: Total expense outflow in the next 1 weekly period(s) for the same user
- Ordered feature count: 20
- User coverage: {'train': 300, 'validation': 300, 'test': 300}
- LSTM shapes: {'train': [3600, 8, 20], 'validation': [900, 8, 20], 'test': [900, 8, 20]}
- Chronological ranges: {'train': ['2024-02-26T00:00:00', '2024-05-13T00:00:00'], 'validation': ['2024-05-20T00:00:00', '2024-06-03T00:00:00'], 'test': ['2024-06-10T00:00:00', '2024-06-24T00:00:00']}
- Isolation Forest rows: {'train': 41239, 'test': 17588, 'positive_labels': 235}

## Leakage decision

No critical leakage or schema problem was detected.

Synthetic data are used for controlled development only and are not evidence of real Kenyan young-adult spending behaviour.
