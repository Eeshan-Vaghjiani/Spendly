# Spendly v1.2.0 - complete data dictionary

Generated from SQLAlchemy metadata. No database connection or mutation was performed.

11 application tables. The Alembic migration bookkeeping table is not included.

UUID identifiers are stored as VARCHAR(36), not as the native PostgreSQL UUID type. Timestamps are stored without a timezone; application code uses UTC. Defaults and API validation are defined in the application, not inferred from this diagram.

## admin_audit

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| id | VARCHAR(36) | PK | No |  |
| actor | VARCHAR(255) |  | No |  |
| action | VARCHAR(80) |  | No |  |
| target_type | VARCHAR(40) |  | No |  |
| target_id | VARCHAR(64) |  | No |  |
| reason | VARCHAR(300) |  | No |  |
| details | JSON |  | No |  |
| created_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |

- Index `ix_admin_audit_action`: (action)
- Index `ix_admin_audit_created_at`: (created_at)
- Index `ix_admin_audit_target_id`: (target_id)

## admin_login_attempts

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| id | VARCHAR(36) | PK | No |  |
| client_key | VARCHAR(64) |  | No |  |
| created_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |

- Index `ix_admin_login_attempts_client_key`: (client_key)
- Index `ix_admin_login_attempts_created_at`: (created_at)

## model_versions

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| id | VARCHAR(36) | PK | No |  |
| component | VARCHAR(30) |  | No |  |
| version | VARCHAR(30) |  | No |  |
| artifact_path | VARCHAR(500) |  | No |  |
| metadata_json | JSON |  | No |  |
| is_active | BOOLEAN |  | No |  |
| created_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |

- Unique: (component, version)

## system_settings

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| key | VARCHAR(64) | PK | No |  |
| enabled | BOOLEAN |  | No |  |


## users

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| id | VARCHAR(36) | PK | No |  |
| email | VARCHAR(255) | UQ | No |  |
| password_hash | VARCHAR(255) |  | Yes |  |
| google_subject | VARCHAR(255) | UQ | Yes |  |
| display_name | VARCHAR(100) |  | No |  |
| username | VARCHAR(30) |  | No |  |
| username_normalized | VARCHAR(30) | UQ | No |  |
| monthly_income | NUMERIC(14, 2) |  | Yes |  |
| terms_accepted_at | TIMESTAMP WITHOUT TIME ZONE |  | Yes |  |
| privacy_accepted_at | TIMESTAMP WITHOUT TIME ZONE |  | Yes |  |
| consent_version | VARCHAR(30) |  | Yes |  |
| model_training_opt_in | BOOLEAN |  | No |  |
| model_training_consented_at | TIMESTAMP WITHOUT TIME ZONE |  | Yes |  |
| created_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |
| onboarding_completed_at | TIMESTAMP WITHOUT TIME ZONE |  | Yes |  |
| is_active | BOOLEAN |  | No |  |
| auth_version | INTEGER |  | No |  |

- Unique: (email)
- Unique: (username_normalized)
- Unique: (google_subject)
- Index `ix_users_email`: (email)
- Index `ix_users_google_subject`: (google_subject); unique
- Index `ix_users_username_normalized`: (username_normalized); unique

## analysis_runs

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| id | VARCHAR(36) | PK | No |  |
| user_id | VARCHAR(36) | FK | No | users.id / CASCADE |
| status | VARCHAR(20) |  | No |  |
| forecast_model_version | VARCHAR(30) |  | No |  |
| anomaly_model_version | VARCHAR(30) |  | No |  |
| history_periods | INTEGER |  | No |  |
| generated_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |

- Index `ix_analysis_runs_user_id`: (user_id)

## budgets

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| id | VARCHAR(36) | PK | No |  |
| user_id | VARCHAR(36) | FK | No | users.id / CASCADE |
| period_start | DATE |  | No |  |
| period_end | DATE |  | No |  |
| category | VARCHAR(80) |  | No |  |
| amount | NUMERIC(14, 2) |  | No |  |
| currency | VARCHAR(3) |  | No |  |
| created_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |
| updated_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |

- Unique: (user_id, period_start, period_end, category)
- Index `ix_budget_user_period`: (user_id, period_start, period_end)

## transactions

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| id | VARCHAR(36) | PK | No |  |
| user_id | VARCHAR(36) | FK | No | users.id / CASCADE |
| transaction_timestamp | TIMESTAMP WITHOUT TIME ZONE |  | No |  |
| amount | NUMERIC(14, 2) |  | No |  |
| currency | VARCHAR(3) |  | No |  |
| category | VARCHAR(80) |  | No |  |
| transaction_type | VARCHAR(10) |  | No |  |
| merchant | VARCHAR(120) |  | Yes |  |
| is_recurring | BOOLEAN |  | No |  |
| source | VARCHAR(20) |  | No |  |
| fingerprint | VARCHAR(64) |  | No |  |
| created_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |

- Unique: (user_id, fingerprint)
- Index `ix_transaction_user_timestamp`: (user_id, transaction_timestamp)

## anomaly_alerts

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| id | VARCHAR(36) | PK | No |  |
| analysis_run_id | VARCHAR(36) | FK | No | analysis_runs.id / CASCADE |
| user_id | VARCHAR(36) | FK | No | users.id / CASCADE |
| transaction_id | VARCHAR(36) | FK | Yes | transactions.id / SET NULL |
| is_unusual_spending | BOOLEAN |  | No |  |
| anomaly_score | FLOAT |  | No |  |
| decision_threshold | FLOAT |  | No |  |
| explanation | TEXT |  | No |  |
| model_version | VARCHAR(30) |  | No |  |
| created_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |

- Index `ix_alert_user_created`: (user_id, created_at)

## forecasts

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| id | VARCHAR(36) | PK | No |  |
| analysis_run_id | VARCHAR(36) | FK, UQ | No | analysis_runs.id / CASCADE |
| user_id | VARCHAR(36) | FK | No | users.id / CASCADE |
| period_start | DATE |  | No |  |
| period_end | DATE |  | No |  |
| predicted_spending | NUMERIC(14, 2) |  | No |  |
| baseline_prediction | NUMERIC(14, 2) |  | Yes |  |
| currency | VARCHAR(3) |  | No |  |
| model_version | VARCHAR(30) |  | No |  |
| created_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |

- Unique: (analysis_run_id)
- Index `ix_forecast_user_created`: (user_id, created_at)

## recommendations

| Column | PostgreSQL type | Key | Nullable | Reference / delete action |
| --- | --- | --- | --- | --- |
| id | VARCHAR(36) | PK | No |  |
| analysis_run_id | VARCHAR(36) | FK | No | analysis_runs.id / CASCADE |
| user_id | VARCHAR(36) | FK | No | users.id / CASCADE |
| recommendation_code | VARCHAR(100) |  | No |  |
| title | VARCHAR(160) |  | No |  |
| message | TEXT |  | No |  |
| severity | VARCHAR(20) |  | No |  |
| reason | TEXT |  | No |  |
| supporting_values | JSON |  | No |  |
| suggested_action | TEXT |  | No |  |
| disclaimer | TEXT |  | No |  |
| created_at | TIMESTAMP WITHOUT TIME ZONE |  | No |  |

- Index `ix_recommendation_user_created`: (user_id, created_at)

## Important implementation boundaries

- Admin credentials are configured outside the users table. There is no database admin role column.
- Model version strings on results are not foreign keys to model_versions.
- admin_audit.target_id is deliberately not a foreign key, so an audit record can survive deletion of its target.
- system_settings currently stores the analysis_enabled switch.
- categories and recurring flags are transaction attributes, not separate category or schedule tables.
- A run can have zero or one forecast at database level; a successfully completed analysis normally creates one.
