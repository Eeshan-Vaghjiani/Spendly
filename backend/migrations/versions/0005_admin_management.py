"""Administrator audit, durable login throttling, controls and token revocation."""

from alembic import op
import sqlalchemy as sa

revision = "0005_admin_management"
down_revision = "0004_username_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0")
        )
    op.create_table(
        "admin_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(300), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for field in ("action", "target_id", "created_at"):
        op.create_index(f"ix_admin_audit_{field}", "admin_audit", [field])
    op.create_table(
        "admin_login_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for field in ("client_key", "created_at"):
        op.create_index(
            f"ix_admin_login_attempts_{field}", "admin_login_attempts", [field]
        )
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("admin_login_attempts")
    op.drop_table("admin_audit")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("auth_version")
