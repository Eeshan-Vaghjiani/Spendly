"""Create initial application tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("monthly_income", sa.Numeric(14, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_table(
        "model_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("component", sa.String(length=30), nullable=False),
        sa.Column("version", sa.String(length=30), nullable=False),
        sa.Column("artifact_path", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "component", "version", name="uq_model_component_version"
        ),
    )
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "forecast_model_version", sa.String(length=30), nullable=False
        ),
        sa.Column(
            "anomaly_model_version", sa.String(length=30), nullable=False
        ),
        sa.Column("history_periods", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_runs_user_id", "analysis_runs", ["user_id"], unique=False
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("transaction_timestamp", sa.DateTime(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("transaction_type", sa.String(length=10), nullable=False),
        sa.Column("merchant", sa.String(length=120), nullable=True),
        sa.Column("is_recurring", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "fingerprint",
            name="uq_transaction_user_fingerprint",
        ),
    )
    op.create_index(
        "ix_transaction_user_timestamp",
        "transactions",
        ["user_id", "transaction_timestamp"],
        unique=False,
    )
    op.create_table(
        "budgets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "period_start",
            "period_end",
            "category",
            name="uq_budget_user_period_category",
        ),
    )
    op.create_index(
        "ix_budget_user_period",
        "budgets",
        ["user_id", "period_start", "period_end"],
        unique=False,
    )
    op.create_table(
        "forecasts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("predicted_spending", sa.Numeric(14, 2), nullable=False),
        sa.Column("baseline_prediction", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("model_version", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id"),
    )
    op.create_index(
        "ix_forecast_user_created",
        "forecasts",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "anomaly_alerts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("transaction_id", sa.String(length=36), nullable=True),
        sa.Column("is_unusual_spending", sa.Boolean(), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=False),
        sa.Column("decision_threshold", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_alert_user_created",
        "anomaly_alerts",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "recommendation_code", sa.String(length=100), nullable=False
        ),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("supporting_values", sa.JSON(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommendation_user_created",
        "recommendations",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recommendation_user_created", table_name="recommendations"
    )
    op.drop_table("recommendations")
    op.drop_index("ix_alert_user_created", table_name="anomaly_alerts")
    op.drop_table("anomaly_alerts")
    op.drop_index("ix_forecast_user_created", table_name="forecasts")
    op.drop_table("forecasts")
    op.drop_index("ix_budget_user_period", table_name="budgets")
    op.drop_table("budgets")
    op.drop_index(
        "ix_transaction_user_timestamp", table_name="transactions"
    )
    op.drop_table("transactions")
    op.drop_index("ix_analysis_runs_user_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_table("model_versions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
