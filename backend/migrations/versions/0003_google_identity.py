"""Add Google identity support.

Revision ID: 0003_google_identity
Revises: 0002_user_consent
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_google_identity"
down_revision = "0002_user_consent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            nullable=True,
        )
        batch_op.add_column(sa.Column("google_subject", sa.String(255)))
        batch_op.create_index(
            "ix_users_google_subject",
            ["google_subject"],
            unique=True,
        )


def downgrade() -> None:
    op.execute(
        "UPDATE users SET password_hash = 'disabled-google-only-account' "
        "WHERE password_hash IS NULL"
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_google_subject")
        batch_op.drop_column("google_subject")
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            nullable=False,
        )
