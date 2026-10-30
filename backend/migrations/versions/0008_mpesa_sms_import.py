"""Optional SMS consent, durable source identities and non-destructive reversals."""
from alembic import op
import sqlalchemy as sa

revision = "0008_mpesa_sms_import"
down_revision = "0007_sign_in_activity"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users", sa.Column("mpesa_sms_import_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("mpesa_sms_consented_at", sa.DateTime()))
    op.add_column("users", sa.Column("mpesa_sms_consent_version", sa.String(30)))
    op.add_column("transactions", sa.Column("is_reversed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("mpesa_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_reference", sa.String(10), nullable=False),
        sa.Column("original_reference", sa.String(10)),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("principal_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("fee_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("transaction_timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "external_reference", name="uq_mpesa_owner_reference"))
    op.create_index("ix_mpesa_original", "mpesa_events", ["user_id", "original_reference"])
    op.create_table("mpesa_components",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("mpesa_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id", ondelete="SET NULL")),
        sa.Column("component", sa.String(10), nullable=False),
        sa.UniqueConstraint("event_id", "component", name="uq_mpesa_event_component"))


def downgrade():
    op.drop_table("mpesa_components")
    op.drop_index("ix_mpesa_original", table_name="mpesa_events")
    op.drop_table("mpesa_events")
    op.drop_column("transactions", "is_reversed")
    for field in ("mpesa_sms_consent_version", "mpesa_sms_consented_at", "mpesa_sms_import_enabled"):
        op.drop_column("users", field)
