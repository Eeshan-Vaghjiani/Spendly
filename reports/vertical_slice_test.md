# Thin Vertical Slice Test

Execution date: 2026-07-25

Status: **PASSED**

## Executed path

1. Started a real Flask process on `http://127.0.0.1:5051`.
2. Applied migration `0001_initial` to a clean temporary SQLite database.
3. Loaded the saved TensorFlow LSTM, Linear Regression, scaler, Isolation
   Forest, and anomaly preprocessor once during Flask startup.
4. Used the Flutter `ApiClient` and `ApiSpendingRepository` over live HTTP.
5. Registered a development user and received a JWT.
6. Submitted eight weekly expense and income records.
7. Created a next-period budget.
8. Called `POST /api/v1/analysis/run`.
9. Received and parsed:
   - one next-period LSTM forecast;
   - an unusual-spending result;
   - at least one transparent recommendation.
10. Verified the corresponding Flutter typed models.
11. Separately verified through widget tests that the dashboard renders the
    forecast, alert state, and recommendation count.

## Commands actually executed

```powershell
python -m flask --app backend.run:app db upgrade --directory backend/migrations
flutter test test\live_backend_test.dart --dart-define=LIVE_API_BASE_URL=http://127.0.0.1:5051/api/v1
flutter test
```

## Test result

- Live Flutter-to-Flask test: **1 passed**
- Flutter unit/widget suite: **4 passed**
- Flask real-model vertical test: **1 passed**

## Docker and MySQL verification

The same Flutter live integration test was then executed against the Docker
backend at `http://127.0.0.1:5000/api/v1`. Both the Flask and MySQL containers
reported healthy. Migration `0001_initial` was present in MySQL, and the live
test passed using the saved models. Two executions persisted the following
development-test records in MySQL:

- 2 users
- 32 transactions
- 2 budgets
- 2 analysis runs
- 2 forecasts
- 14 unusual-spending alert records
- 8 recommendation records

Command:

```powershell
flutter test test\live_backend_test.dart --dart-define=LIVE_API_BASE_URL=http://127.0.0.1:5000/api/v1
```

## Scope limitation

The isolated repeatable integration fixture uses SQLite, while the additional
live execution above verifies the target MySQL environment. No live M-Pesa or
banking integration is present.
