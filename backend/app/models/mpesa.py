"""Minimal immutable source identities; never SMS bodies, balances or contacts."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .entities import new_uuid, utc_now


class MpesaEvent(db.Model):
    __tablename__ = "mpesa_events"
    __table_args__ = (
        UniqueConstraint("user_id", "external_reference", name="uq_mpesa_owner_reference"),
        Index("ix_mpesa_original", "user_id", "original_reference"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(10), nullable=False)
    original_reference: Mapped[str | None] = mapped_column(String(10))
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    transaction_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    def to_dict(self):
        return {name: getattr(self, name) for name in (
            "id", "external_reference", "original_reference", "kind", "parser_version", "status", "direction"
        )} | {"principal_amount": str(self.principal_amount), "fee_amount": str(self.fee_amount),
             "transaction_timestamp": self.transaction_timestamp.isoformat() + "Z",
             "created_at": self.created_at.isoformat() + "Z"}


class MpesaComponent(db.Model):
    __tablename__ = "mpesa_components"
    __table_args__ = (UniqueConstraint("event_id", "component", name="uq_mpesa_event_component"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(ForeignKey("mpesa_events.id", ondelete="CASCADE"), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"))
    component: Mapped[str] = mapped_column(String(10), nullable=False)

    def to_dict(self):
        return {name: getattr(self, name) for name in ("id", "event_id", "transaction_id", "component")}
