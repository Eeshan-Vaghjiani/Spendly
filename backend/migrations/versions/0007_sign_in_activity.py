"""Record successful user authentication without request/device metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0007_sign_in_activity"
down_revision = "0006_alert_reviews"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable: an existing account has no observed sign-in until its next login.
    op.add_column("users", sa.Column("last_signed_in_at", sa.DateTime(), nullable=True))
    op.create_index("ix_users_last_signed_in_at", "users", ["last_signed_in_at"])
    op.create_table(
        "sign_in_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("event", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sign_in_owner_time", "sign_in_events", ["user_id", "created_at", "id"])


def downgrade():
    op.drop_index("ix_sign_in_owner_time", table_name="sign_in_events")
    op.drop_table("sign_in_events")
    op.drop_index("ix_users_last_signed_in_at", table_name="users")
    op.drop_column("users", "last_signed_in_at")
