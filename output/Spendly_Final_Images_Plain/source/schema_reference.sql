-- Documentation only: compiled from the ORM. Do not use instead of Alembic migrations.

-- This file was not executed against a database.

CREATE TABLE admin_audit (
	id VARCHAR(36) NOT NULL, 
	actor VARCHAR(255) NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	target_type VARCHAR(40) NOT NULL, 
	target_id VARCHAR(64) NOT NULL, 
	reason VARCHAR(300) NOT NULL, 
	details JSON NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_admin_audit_action ON admin_audit (action);

CREATE INDEX ix_admin_audit_created_at ON admin_audit (created_at);

CREATE INDEX ix_admin_audit_target_id ON admin_audit (target_id);

CREATE TABLE admin_login_attempts (
	id VARCHAR(36) NOT NULL, 
	client_key VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_admin_login_attempts_client_key ON admin_login_attempts (client_key);

CREATE INDEX ix_admin_login_attempts_created_at ON admin_login_attempts (created_at);

CREATE TABLE model_versions (
	id VARCHAR(36) NOT NULL, 
	component VARCHAR(30) NOT NULL, 
	version VARCHAR(30) NOT NULL, 
	artifact_path VARCHAR(500) NOT NULL, 
	metadata_json JSON NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_model_component_version UNIQUE (component, version)
);

CREATE TABLE system_settings (
	key VARCHAR(64) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255), 
	google_subject VARCHAR(255), 
	display_name VARCHAR(100) NOT NULL, 
	username VARCHAR(30) NOT NULL, 
	username_normalized VARCHAR(30) NOT NULL, 
	monthly_income NUMERIC(14, 2), 
	terms_accepted_at TIMESTAMP WITHOUT TIME ZONE, 
	privacy_accepted_at TIMESTAMP WITHOUT TIME ZONE, 
	consent_version VARCHAR(30), 
	model_training_opt_in BOOLEAN NOT NULL, 
	model_training_consented_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	onboarding_completed_at TIMESTAMP WITHOUT TIME ZONE, 
	is_active BOOLEAN NOT NULL, 
	auth_version INTEGER DEFAULT '0' NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

CREATE INDEX ix_users_email ON users (email);

CREATE UNIQUE INDEX ix_users_google_subject ON users (google_subject);

CREATE UNIQUE INDEX ix_users_username_normalized ON users (username_normalized);

CREATE TABLE analysis_runs (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	forecast_model_version VARCHAR(30) NOT NULL, 
	anomaly_model_version VARCHAR(30) NOT NULL, 
	history_periods INTEGER NOT NULL, 
	generated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_analysis_runs_user_id ON analysis_runs (user_id);

CREATE TABLE budgets (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	period_start DATE NOT NULL, 
	period_end DATE NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	amount NUMERIC(14, 2) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_budget_user_period_category UNIQUE (user_id, period_start, period_end, category), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_budget_user_period ON budgets (user_id, period_start, period_end);

CREATE TABLE transactions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	transaction_timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	amount NUMERIC(14, 2) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	transaction_type VARCHAR(10) NOT NULL, 
	merchant VARCHAR(120), 
	is_recurring BOOLEAN NOT NULL, 
	source VARCHAR(20) NOT NULL, 
	fingerprint VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_transaction_user_fingerprint UNIQUE (user_id, fingerprint), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_transaction_user_timestamp ON transactions (user_id, transaction_timestamp);

CREATE TABLE anomaly_alerts (
	id VARCHAR(36) NOT NULL, 
	analysis_run_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	transaction_id VARCHAR(36), 
	is_unusual_spending BOOLEAN NOT NULL, 
	anomaly_score FLOAT NOT NULL, 
	decision_threshold FLOAT NOT NULL, 
	explanation TEXT NOT NULL, 
	model_version VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(analysis_run_id) REFERENCES analysis_runs (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(transaction_id) REFERENCES transactions (id) ON DELETE SET NULL
);

CREATE INDEX ix_alert_user_created ON anomaly_alerts (user_id, created_at);

CREATE TABLE forecasts (
	id VARCHAR(36) NOT NULL, 
	analysis_run_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	period_start DATE NOT NULL, 
	period_end DATE NOT NULL, 
	predicted_spending NUMERIC(14, 2) NOT NULL, 
	baseline_prediction NUMERIC(14, 2), 
	currency VARCHAR(3) NOT NULL, 
	model_version VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (analysis_run_id), 
	FOREIGN KEY(analysis_run_id) REFERENCES analysis_runs (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_forecast_user_created ON forecasts (user_id, created_at);

CREATE TABLE recommendations (
	id VARCHAR(36) NOT NULL, 
	analysis_run_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	recommendation_code VARCHAR(100) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	message TEXT NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	reason TEXT NOT NULL, 
	supporting_values JSON NOT NULL, 
	suggested_action TEXT NOT NULL, 
	disclaimer TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(analysis_run_id) REFERENCES analysis_runs (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_recommendation_user_created ON recommendations (user_id, created_at);
