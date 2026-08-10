"""Store required service consent and optional model-training consent.

Revision ID: 0002_user_consent
Revises: 0001_initial
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_user_consent"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("privacy_accepted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("consent_version", sa.String(length=30), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "model_training_opt_in",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column("model_training_consented_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "model_training_consented_at")
    op.drop_column("users", "model_training_opt_in")
    op.drop_column("users", "consent_version")
    op.drop_column("users", "privacy_accepted_at")
    op.drop_column("users", "terms_accepted_at")
