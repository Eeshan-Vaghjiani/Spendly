# Spendly - final diagrams and wireframes

Prepared for Eeshan's mobile personal-finance project, 31 August 2026.

This pack documents the Spendly **v1.2.0 implementation** on branch `agent/spendly-live-deployment`, baseline commit `b0a0f8550d6673bb04d7b18a27a0e734893c1dfb`. It is not a redesign of the friend's medical web application. Those attachments supplied layout references only.

## Open first

- `Spendly_Final_Diagrams.pdf`: all seven figures, with selectable vector text.
- `Pack_Overview.png`: quick visual index.
- `png/`: high-resolution images for inserting into a report.
- `svg/`: editable vector versions for scaling, recolouring or rearranging in a vector editor.
- `Database_Data_Dictionary.md`: every column, nullability, key, unique constraint and index.
- `source/`: reproducible generators, schema metadata and documentation-only PostgreSQL DDL.

## Figure list

| Figure | Filename stem | Purpose |
| --- | --- | --- |
| 1 | 01_Database_Schema | All 11 application tables, 97 columns and 10 foreign-key relationships |
| 2 | 02_System_Architecture | Flutter mobile client, browser admin, Flask services, models, PostgreSQL and Google sign-in |
| 3 | 03_Sequence_Generate_Insights | Authenticated analysis request through feature preparation, inference, guidance and storage |
| 4 | 04_Wireframe_Mobile_Dashboard | Financial overview and entry points to the app's insights |
| 5 | 05_Wireframe_Mobile_Add_Transaction | The main financial data-entry flow |
| 6 | 06_Wireframe_Mobile_Forecast_Results | Estimated spending, history readiness and limitations |
| 7 | 07_Wireframe_Web_Admin_Management | Privileged account management, records, system switch and audit |

The four wireframes are Dashboard, Add Transaction, Forecast Results and Admin Management. Dashboard shows two scroll positions of the **same** screen. The first three are phone layouts. Admin is deliberately browser-based because the implemented administration interface is a web console, even though the end-user product is mobile.

Wireframes explain structure and behaviour; they are not pixel-perfect screenshots. Spacing is condensed for report readability. Every amount, count, example transaction, date and account shown is illustrative. No real account data was read to populate these wireframes.

## Implementation facts preserved

### Data and relationships

- Live persistence uses PostgreSQL; the table/column definitions were exported directly from `backend/app/models/entities.py` without connecting to a database.
- IDs are UUID strings stored in `VARCHAR(36)`. Amounts are `NUMERIC(14,2)`. Timestamp values use UTC in application code and are stored without a database timezone.
- `users` owns transactions, budgets, analysis runs, forecasts, anomaly alerts and recommendations. All ten foreign keys are documented.
- `forecasts.analysis_run_id` is unique: an analysis run has zero or one forecast at database level. Successful runs normally create one.
- `anomaly_alerts.transaction_id` is nullable and uses `ON DELETE SET NULL`. Other ownership/run foreign keys use `ON DELETE CASCADE`.
- Model-version strings on result rows are not foreign keys into `model_versions`.
- `admin_audit.target_id` is intentionally not a foreign key. Accountability can survive deletion of an account or record.
- Admin credentials are configured outside `users`; there is no invented database admin-role field.
- Operational `alembic_version` bookkeeping is not an application entity and is excluded.
- Categories are text fields, and recurring payments are tagged transactions. No category, recurring-schedule, feedback or shadow-model tables have been invented.

### Deployed models versus research

- `render.yaml` selects `MODEL_RUNTIME=lightweight`, forecast model `v1`, and anomaly model `v1`.
- The lightweight runtime uses multiple linear regression when at least eight history weeks are available. Before that it uses a personal weekly-average baseline.
- `ModelRegistry.forecast()` returns the same linear prediction under both legacy result keys when no LSTM is loaded; the service's weighted expression therefore reduces to the linear prediction in this runtime.
- Isolation Forest flags unusual expense patterns; the recommendation engine applies rules. Both execute inside the Flask backend, not on the phone and not in separately deployed ML microservices.
- Model files are loaded from the backend container filesystem. The database keeps version metadata and analysis results, not the serialized estimator objects.
- Optional full-runtime LSTM support and the frozen V2 research candidates are **not** shown as active components of this deployment.
- Data readiness is not statistical confidence or accuracy. The forecast wireframe intentionally illustrates the four-week baseline state. A completed-week comparison is separate from out-of-sample model evaluation.
- Existing app copy after eight weeks can still describe a model blend. These diagrams document the actual lightweight execution path, not that legacy wording. This documentation task did not change application text or model behaviour.

### Admin boundary

The admin wireframe includes account search, enable/disable, profile correction, session revocation, private export, guarded deletion, record inspection/correction, a switch for new analysis requests, and audit review. Creating records applies to transactions and budgets; permissions vary for other record types. It does not imply unrestricted database access, model retraining, live threshold editing, or the ability to override protected consent/authentication identities.

## Source map

Paths below are relative to the repository root.

| Area | Checked implementation |
| --- | --- |
| Schema | `backend/app/models/entities.py` |
| Deployment | `render.yaml`, `backend/Dockerfile.lightweight` |
| Model runtime | `backend/app/services/model_registry.py` |
| Features and analysis | `backend/app/services/feature_preparation.py`, `backend/app/services/analysis.py` |
| Rules | `services/recommendation_engine.py` |
| Analysis API and identity checks | `backend/app/routes/analysis.py`, `backend/app/security/current_user.py` |
| Google sign-in | `backend/app/security/google_identity.py`, `mobile/lib/data/services/google_identity_service.dart` |
| Admin | `backend/app/templates/admin/manage.html`, `backend/app/static/admin/manage.js`, `backend/app/routes/admin_management.py` |
| Mobile navigation | `mobile/lib/presentation/screens/home_shell.dart` |
| Wireframes | `dashboard_screen.dart`, `transaction_entry_screen.dart`, `forecast_detail_screen.dart` within `mobile/lib/presentation/screens/` |

## Rebuild

1. With the repository's Python environment, run `python output/Spendly_Final_Diagrams_v1_2/source/export_schema.py` from the repository root. This requires the app's SQLAlchemy dependencies but does not connect to the database.
2. With Python containing `reportlab`, `Pillow` and `pypdf`, and Poppler's `pdftoppm` on PATH, run `python output/Spendly_Final_Diagrams_v1_2/source/build_pack.py`.
3. Run `python output/Spendly_Final_Diagrams_v1_2/source/verify_pack.py` with the same document environment.
4. Inspect all seven rendered images after any layout edit. The PDF is the source of the PNG render, so image review also verifies PDF layout.
5. Run `python output/Spendly_Final_Diagrams_v1_2/source/package_pack.py` to update the distributable ZIP after verification.

The builder uses Arial fonts from the standard Windows font directory. For another operating system, change only the two font paths. Exporting SQL is documentation, not a migration: **do not execute `schema_reference.sql` against an existing database**.

## Scope

Only this new documentation folder and its ZIP were created. Application code, database data, deployed services, model artifacts, APKs and existing diagram folders were not changed for this request.
