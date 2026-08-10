# Complete System Test Results

Execution date: **2026-07-25**

Overall status: **PASSED for the local controlled-development prototype**

## Executed checks

| Area | Executed command or check | Result |
|---|---|---|
| Model-ready data | `python scripts\validate_model_data.py` | **43/43 checks passed** |
| Python system suite | `python -m pytest -q` | **42 passed**, 19 non-failing dependency deprecation warnings |
| Flutter static analysis | `flutter analyze` | **No issues found** |
| Flutter full suite with live API | `flutter test --dart-define=LIVE_API_BASE_URL=http://127.0.0.1:5000/api/v1` | **5 passed** |
| Live Flutter slice after final Docker rebuild | `flutter test test\live_backend_test.dart --dart-define=LIVE_API_BASE_URL=http://127.0.0.1:5000/api/v1` | **1 passed** |
| Python syntax | `python -m compileall -q backend services scripts` | **Passed** |
| OpenAPI contract | Parsed `docs/openapi.yaml` and inspected examples | OpenAPI 3.0.3, **15 paths, 17 operations, 0 missing request/response examples** |
| Docker configuration | `docker compose config --quiet` | **Passed** |
| Docker runtime | `docker compose ps` | Flask and MySQL both **healthy** |
| Backend health | `GET /api/v1/health` | Database connected; forecasting and anomaly models loaded |
| MySQL migration | Inspected `alembic_version` | **0001_initial** |

## Required integration workflow coverage

1. Registration and login: passed backend authentication tests; the live
   Flutter test registered and authenticated a user.
2. Manual transaction entry: passed API tests and live Flutter-to-MySQL test.
3. CSV upload: passed header, row-validation, duplicate, partial-success, and
   error-summary API tests.
4. Budget creation: passed API tests and live Flutter-to-MySQL test.
5. Analysis execution: passed fake-model and real-saved-model API tests, plus
   the live Flutter test.
6. Forecast response: received, parsed, rendered in widget tests, and stored.
7. Unusual-spending response: received, parsed, rendered, and stored.
8. Recommendation response: received, parsed, rendered, and stored.
9. Stored history: forecast, alert, and recommendation history endpoints
   passed; the Flutter history screen consumes all three resources.
10. Insufficient history: passed typed API error test.
11. User isolation: passed tests preventing one user from accessing another
    user's financial records.
12. Retention: dry-run and explicit-apply behaviours passed.

## Target MySQL evidence

After two controlled live Flutter executions, the Docker MySQL database
contained:

| Entity | Stored rows |
|---|---:|
| Users | 2 |
| Transactions | 32 |
| Budgets | 2 |
| Analysis runs | 2 |
| Forecasts | 2 |
| Anomaly alerts | 14 |
| Recommendations | 8 |

These are development-test records, not real user data.

## Test warnings

The Python suite emitted 19 dependency deprecation warnings from pandas,
Matplotlib/pyparsing, Keras, and NumPy interoperability. They did not cause test
failures. They should be revisited during a future dependency upgrade.

## What these results do not prove

- They do not establish accuracy on real Kenyan young-adult spending.
- They do not constitute production security, scale, or public deployment
  certification.
- They do not test a live bank or M-Pesa integration because none is present.
