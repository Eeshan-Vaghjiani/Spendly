"""Add unique usernames and account-scoped onboarding state.

Revision ID: 0004_username_onboarding
Revises: 0003_google_identity
"""

from __future__ import annotations

from datetime import datetime, timezone
import re

from alembic import op
import sqlalchemy as sa


revision = "0004_username_onboarding"
down_revision = "0003_google_identity"
branch_labels = None
depends_on = None


def _base_username(display_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", display_name.strip()).strip("_").lower()
    if len(cleaned) < 3:
        cleaned = f"{cleaned}_user".strip("_")
    return (cleaned or "spendly_user")[:30]


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(length=30)))
        batch_op.add_column(sa.Column("username_normalized", sa.String(length=30)))
        batch_op.add_column(sa.Column("onboarding_completed_at", sa.DateTime()))

    connection = op.get_bind()
    users = sa.table(
        "users",
        sa.column("id", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("username", sa.String()),
        sa.column("username_normalized", sa.String()),
        sa.column("onboarding_completed_at", sa.DateTime()),
    )
    used: set[str] = set()
    completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = connection.execute(sa.select(users.c.id, users.c.display_name)).all()
    for user_id, display_name in rows:
        base = _base_username(display_name or "spendly_user")
        candidate = base
        suffix = 1
        while candidate.casefold() in used:
            suffix_text = f"_{suffix}"
            candidate = f"{base[:30 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        used.add(candidate.casefold())
        connection.execute(
            users.update().where(users.c.id == user_id).values(
                username=candidate,
                username_normalized=candidate.casefold(),
                onboarding_completed_at=completed_at,
            )
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("username", existing_type=sa.String(30), nullable=False)
        batch_op.alter_column(
            "username_normalized", existing_type=sa.String(30), nullable=False
        )
        batch_op.create_index(
            "ix_users_username_normalized", ["username_normalized"], unique=True
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_username_normalized")
        batch_op.drop_column("onboarding_completed_at")
        batch_op.drop_column("username_normalized")
        batch_op.drop_column("username")
