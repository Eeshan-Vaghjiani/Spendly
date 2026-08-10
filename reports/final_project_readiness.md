# Final Project Readiness

Project: **Personal Spending Behavior Forecasting Using LSTM Neural Networks
with Isolation Forest and Rule-Based Financial Decision Support**

Assessment date: **2026-07-25**

Prototype status: **Complete and runnable for controlled local development**

## Direct answers

### 1. Is the LSTM trained?

Yes. TensorFlow/Keras trained the version `v1` LSTM using eight weekly periods
to forecast the next week's total spending. Early stopping and validation-loss
checkpointing selected the saved `.keras` model.

### 2. Does it outperform the naive and Linear Regression baselines?

It outperformed the previous-period naive forecast and the four-period moving
average on MAE and RMSE. It **did not outperform Multiple Linear Regression**.
The LSTM remains the capstone's main forecasting model as required, but no
accuracy-superiority claim is justified.

### 3. What are the LSTM metrics?

On the same 900 chronologically held-out weekly targets:

| Metric | LSTM |
|---|---:|
| MAE | **KES 5,156.7162** |
| RMSE | **KES 6,854.6237** |
| MAPE | **301.9006%** |
| R-squared | **0.1081** |

For comparison, Linear Regression achieved MAE KES 3,895.0861 and RMSE
KES 6,416.5552. MAPE is unstable here because many actual spending values are
small; zero actual values were excluded safely.

### 4. Is Isolation Forest trained and evaluated?

Yes. Version `v1` was trained without anomaly labels as inputs. Contamination
and the decision threshold were selected on an earlier chronological
validation slice and evaluated on the later labelled controlled-test slice.
It identifies unusual spending behaviour, not fraud.

### 5. What are the Isolation Forest metrics?

On 13,877 held-out rows with 182 controlled anomaly labels:

| Metric | Result |
|---|---:|
| Precision | **0.1634** |
| Recall | **0.1374** |
| F1-score | **0.1493** |
| False-positive rate | **0.0093** |
| True positives | **25** |
| Total alerts | **153** |

The low recall and F1 must be reported as a limitation.

### 6. Does every recommendation rule pass its tests?

Yes. All **25 recommendation-engine tests** pass, including individual rules,
boundaries, missing values, insufficient history, conflict handling, priority,
and duplicate suppression.

### 7. Can Flask load all model artefacts?

Yes. Tests loaded the saved LSTM, Linear Regression, forecasting scaler,
Isolation Forest, and anomaly preprocessor and produced finite inference
outputs. The Docker backend health endpoint reports both model components
loaded. Artefacts are loaded at application startup, not retrained per request.

### 8. Can Flutter call the Flask API?

Yes. The live Flutter API integration test passed against
`http://127.0.0.1:5000/api/v1` after the final Docker rebuild.

### 9. Can a user add or upload transactions?

Yes. Manual entry passed the live Flutter-to-Flask-to-MySQL test. CSV upload
passed backend tests for valid rows, invalid rows, headers, duplicates, and
explicit upload summaries. A template and guide are included.

### 10. Can the user receive a forecast?

Yes. The live workflow returned an LSTM next-period forecast, Flutter parsed
it, and MySQL stored it.

### 11. Can the user receive an unusual-spending alert?

Yes. The live workflow returned unusual-spending results with scores,
thresholds, explanations, and the non-fraud interpretation.

### 12. Can the user receive a recommendation?

Yes. The live workflow returned transparent rule-based recommendations with
reasons, supporting values, suggested actions, severity, and a financial
decision-support disclaimer.

### 13. Are results stored in MySQL?

Yes. Docker MySQL is healthy and migration `0001_initial` is applied. The
controlled live runs stored users, transactions, budgets, analysis runs,
forecasts, alerts, and recommendations. The current development-test counts
are documented in `reports/system_test_results.md`.

### 14. Do backend tests pass?

Yes. The complete Python suite reports **42 passed**. This includes backend
API/database/authentication/upload/error tests, real-model inference,
real-model vertical integration, retention behaviour, and the 25 rule tests.

### 15. Do Flutter tests pass?

Yes. `flutter analyze` reports no issues and the full suite reports **5
passed**, including the live backend integration test.

### 16. What limitations remain?

- All retained training and evaluation data are synthetic controlled records.
- The synthetic users are ages **18–35**, so the designed target population is
  young adults, but the results are **not evidence of real Kenyan young-adult
  spending behaviour**.
- Linear Regression currently outperforms the LSTM on MAE and RMSE.
- LSTM MAPE is high and the test covers only three unique target weeks.
- Isolation Forest has low precision, recall, and F1 on controlled anomalies.
- Anomaly explanations are heuristic context, not causal feature attribution.
- There is no live M-Pesa, banking, or account-aggregation integration.
- A public deployment still needs TLS, rate limiting, token revocation,
  password reset, account erasure, monitoring, backups, and secret rotation.
- Flutter is scaffolded for Android; iOS was not built or tested.

### 17. What exact commands run the prototype?

From the project root:

```powershell
Copy-Item .env.example .env
# Replace every placeholder in .env with strong, distinct local secrets.
python scripts\run_training_pipeline.py --mode quick
docker compose up --build -d
Invoke-RestMethod http://localhost:5000/api/v1/health
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

The saved `v1` model artefacts already exist, so the training command may be
skipped when simply running the current prototype.

Run all checks:

```powershell
cd "D:\ICS\YEAR 4\sem1\IS\model related"
python scripts\validate_model_data.py
python -m pytest -q
docker compose config --quiet
cd mobile
flutter analyze
flutter test --dart-define=LIVE_API_BASE_URL=http://127.0.0.1:5000/api/v1
```

## Selected datasets

All selected records are synthetic and separated under `data/synthetic/`.
Training uses the validated versioned inputs under `data/model_ready/`:

- LSTM: `lstm_train.npz`, `lstm_validation.npz`, `lstm_test.npz`
- Linear Regression: chronological train, validation, and test Parquet files
- Isolation Forest: train/test Parquet files plus evaluation-only labels
- Recommendation engine: controlled CSV rule cases

The prepared data contain 300 synthetic users ages 18–35, 60,572
transactions, and 5,400 LSTM sequences.

## Saved model artefacts

Forecasting:

- `artifacts/models/forecasting/v1/lstm.keras`
- `artifacts/models/forecasting/v1/linear_regression.joblib`
- `artifacts/models/forecasting/v1/scaler.joblib`
- `artifacts/models/forecasting/v1/feature_schema.json`
- `artifacts/models/forecasting/v1/model_metadata.json`
- `artifacts/models/forecasting/v1/training_history.json`

Unusual-spending detection:

- `artifacts/models/anomaly/v1/isolation_forest.joblib`
- `artifacts/models/anomaly/v1/preprocessor.joblib`
- `artifacts/models/anomaly/v1/feature_schema.json`
- `artifacts/models/anomaly/v1/model_metadata.json`

## Key locations

- Backend URL: `http://localhost:5000/api/v1`
- API contract: `docs/openapi.yaml`
- Flutter project: `mobile/`
- Migration directory: `backend/migrations/`
- Full test evidence: `reports/system_test_results.md`
- Command summary: `PROJECT_COMMANDS.md`

Manual migration verification command:

```powershell
docker compose exec backend python -m flask --app backend.run:app db upgrade --directory backend/migrations
```
