"""Store explicit transaction-scoped spending-alert review decisions."""
from alembic import op
import sqlalchemy as sa

revision = "0006_alert_reviews"
down_revision = "0005_admin_management"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("alert_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False))
    op.create_index("ix_alert_review_owner_transaction", "alert_reviews", ["user_id", "transaction_id"], unique=True)


def downgrade():
    op.drop_index("ix_alert_review_owner_transaction", table_name="alert_reviews")
    op.drop_table("alert_reviews")
