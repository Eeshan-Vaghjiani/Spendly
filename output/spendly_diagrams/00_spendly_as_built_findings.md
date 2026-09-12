# Spendly As-Built Analysis and Diagram Decisions

## System understanding

Spendly is a Flutter Android personal-finance decision-support client backed by a Flask REST API and PostgreSQL. Authenticated users record income and expense transactions manually or import them from CSV, manage dated category or total budgets, view cash-flow summaries, and explicitly refresh analytical insights. Each successful analysis stores an analysis run, a next-seven-day total-spending forecast, any unusual-spending alerts, and up to three rule-based recommendations.

The full local runtime loads both the trained LSTM and Multiple Linear Regression artifacts and combines their predictions using 35% LSTM and 65% Linear Regression. The deployed Render free-tier service is intentionally configured as the lightweight runtime and currently reports Multiple Linear Regression as its live forecasting model. Both runtimes use the versioned Isolation Forest for unusual-spending detection. Detected anomalies are review prompts, not fraud findings.

## Confirmed actors

- **Registered User** - uses the Flutter application and owns all personal financial records.
- **Administrator** - uses a separate environment-credential-protected, read-only web dashboard.
- **Google Identity Provider** - external supporting actor for optional Google sign-in.

There is no persisted administrator account or role. Administrator authentication is based on `ADMIN_USERNAME` and `ADMIN_PASSWORD` environment configuration and a protected Flask session.

## Actor and permission matrix

| Function | Registered User | Administrator | Google Identity Provider |
|---|:---:|:---:|:---:|
| Register with email/password and required consent | Yes | No | No |
| Sign in with email/password | Yes | No | No |
| Sign in with Google | Yes | No | Verifies identity token |
| Manage optional model-training consent | Yes | No | No |
| Add, review, edit, and delete own transactions | Yes | No | No |
| Import own transactions from CSV | Yes | No | No |
| Create, review, edit, and delete own budgets | Yes | No | No |
| View own cash-flow analytics | Yes | No | No |
| Generate/refresh own analytical insights | Yes | No | No |
| View own forecast, alerts, recommendations, and stored history | Yes | No | No |
| Sign out of mobile session | Yes | No | No |
| Authenticate to administrator console | No | Yes | No |
| View/refresh operational overview, users, cash flow, model health, forecasts, alerts | No | Yes, read-only | No |
| Create/edit/delete users or financial records in admin console | No | No | No |
| Sign out of administrator session | No | Yes | No |

## Feature inventory

| Classification | Verified functions/data |
|---|---|
| User interaction | Registration, password/Google sign-in, required consent, optional model-training consent, transaction CRUD, CSV import, budget CRUD, dashboard, cash-flow analytics, insight refresh, forecast/alert/recommendation detail, stored insight history, sign-out |
| Administrator interaction | Environment-credential sign-in, read-only dashboard refresh, system metrics, recent users and consent status, aggregate cash flow, model health, recent forecasts, recent unusual alerts, sign-out |
| Internal application processing | JWT and consent enforcement, user scoping, input validation, category normalization, duplicate fingerprinting, CSV row summaries, database retrieval and persistence |
| ML/analytical processing | Weekly feature preparation, total-spending forecast, transaction/behavioural anomaly features, Isolation Forest scoring, deterministic recommendation rules |
| Persistent data | users, transactions, budgets, analysis_runs, forecasts, anomaly_alerts, recommendations, model_versions |
| Derived/temporary data | Cash-flow series and summaries, category totals/changes, recurring-expense totals, data-readiness percentage, recommendation context, CSV validation summary |

## Documentation versus implementation

| Feature | Documentation | Implementation | Final diagram decision |
|---|---|---|---|
| Administrator | Not established as a principal actor | Separate environment-credential, session-protected, read-only admin dashboard | Include Administrator only with verified sign-in, dashboard viewing/refresh, and sign-out |
| Transaction import | Structured file upload proposed | UTF-8 CSV import with required headers, per-row validation, duplicate suppression, and summary; upload file itself is not stored | Include CSV import and validation; no uploaded-file entity |
| Categorisation | Expense categorisation proposed | User supplies category; backend normalizes aliases and stores a string on each transaction | Do not create Category or CategoryMapping tables/classes |
| Seven-day history gate | Initial analytics after at least seven consecutive days proposed | Analysis requires at least one transaction; fewer than eight weekly periods use a rolling personal baseline and an insufficient-history recommendation | Show no-data rejection and the implemented eight-period readiness branch, not a coded seven-day gate |
| Forecast target | Next-week category-level expenditure proposed | One next-seven-day **total-spending** forecast is persisted per analysis run | Model a total forecast, not per-category forecast rows |
| Forecasting model | LSTM described as principal model | Full runtime blends LSTM 35% and Linear Regression 65%; live Render runtime uses Linear Regression only | Show both runtime paths and identify the live path explicitly |
| Forecast persistence | Proposed forecast storage | `forecasts` table; exactly one forecast is created for every successful analysis run | Include Forecast and AnalysisRun with a 0..1 database cardinality from run to forecast |
| Anomaly meaning | Unusual spending requiring review | Isolation Forest stores only threshold-crossing alerts and never labels fraud | Use “unusual spending” consistently |
| Alert persistence | Proposed | `anomaly_alerts` rows persisted only for unusual results; optional transaction FK | Include persisted alerts with nullable transaction reference |
| Recommendation persistence | Proposed | Up to three deterministic results stored per run; below eight periods only the insufficient-history recommendation is returned | Include RecommendationRecord owned through AnalysisRun/User |
| Recurring expenses | Identification proposed | Boolean `transactions.is_recurring`; current/previous weekly recurring totals are derived | No RecurringExpense table |
| Categories | Principal entity implied by old diagrams | No category table; transaction and budget category are strings | Exclude Category entity/table |
| Budgets | Budget definition proposed | User-owned dated budgets, unique per user + period + category; category may be `total` | Include Budget with actual uniqueness constraint |
| Cash-flow analytics | Spending trend analysis proposed | Derived daily/weekly/monthly/quarterly/yearly income, expense, net, balance, savings rate and budgeted total | Include user-visible analytics; no analytics table |
| Profile management | Possible generic feature | Profile screen is informational; only model-training consent is editable | Do not claim profile editing |
| Logout | Not central in proposal | Mobile token/Google session sign-out and admin CSRF-protected sign-out implemented | Include sign-out for both human actors |
| Feedback | Research evaluation discussed | No feedback screen, endpoint, model, or table | Exclude feedback |
| Report/export | Not verified | No export endpoint or mobile export feature | Exclude report/export |
| Admin mutations | Questions to investigate | No create/edit/delete/activate routes in admin console | Exclude all admin management use cases |
| Model metadata | Proposed analytical components | `model_versions` exists, but run/result version fields are strings without foreign keys | Show standalone model_versions table and no invented relationship |
| M-PESA/bank connection | Explicitly out of scope | Mobile privacy text confirms manual/CSV data only | Exclude all bank, M-PESA, payment and transfer actors/use cases |

## Cross-diagram consistency rules applied

- Every persisted class in the ERD comes from the SQLAlchemy models and migrations.
- The Class Diagram adds actual Flutter abstractions and backend services, so it is not a duplicate of the ERD.
- The Sequence and Activity diagrams distinguish no-history, provisional baseline, full-runtime forecasting, and live lightweight forecasting.
- All result persistence flows through `analysis_runs`; forecasts, alerts, and recommendations are never shown as free-floating generated data.
- No diagram includes a Category, Feedback, UploadedFile, RecurringExpense, DashboardView, SystemAdmin, payment, bank, or M-PESA table/class/use case.

## Implementation evidence map

| Concern | Primary implementation evidence |
|---|---|
| Persistent schema and constraints | `backend/app/models/entities.py`; `backend/migrations/versions/0001_initial.py`; consent and Google migrations `0002_user_consent.py`, `0003_google_identity.py` |
| Authentication, consent, and user scoping | `backend/app/routes/auth.py`; `backend/app/security/current_user.py`; `backend/app/security/google_identity.py` |
| Transaction CRUD and CSV import | `backend/app/routes/transactions.py`; `backend/app/services/transactions.py`; `backend/app/schemas/requests.py` |
| Budgets and analytics | `backend/app/routes/budgets.py`; `backend/app/routes/analytics.py`; `backend/app/repositories/financial.py` |
| Forecast, anomaly, recommendations, and persistence | `backend/app/routes/analysis.py`; `backend/app/services/analysis.py`; `backend/app/services/feature_preparation.py`; `backend/app/services/model_registry.py` |
| Read-only administrator surface | `backend/app/routes/admin.py`; `backend/app/templates/admin/login.html`; `backend/app/templates/admin/dashboard.html` |
| Live lightweight deployment | `render.yaml`; `backend/Dockerfile.lightweight`; live `/api/v1/health` and `/api/v1/model-info` responses |
| Flutter application boundary and user screens | `mobile/lib/domain/repositories/spending_repository.dart`; `mobile/lib/data/repositories/api_spending_repository.dart`; `mobile/lib/presentation/screens/` |
