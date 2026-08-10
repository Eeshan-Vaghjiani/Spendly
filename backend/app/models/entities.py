"""SQLAlchemy entities for user-owned financial records and analysis results."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    google_subject: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_income: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime)
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime)
    consent_version: Mapped[str | None] = mapped_column(String(30))
    model_training_opt_in: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    model_training_consented_at: Mapped[datetime | None] = mapped_column(
        DateTime
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    budgets: Mapped[list["Budget"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "has_required_consents": bool(
                self.terms_accepted_at and self.privacy_accepted_at
            ),
            "model_training_opt_in": self.model_training_opt_in,
            "consent_version": self.consent_version,
            "login_provider": "google" if self.google_subject else "password",
        }


class Transaction(db.Model):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "fingerprint", name="uq_transaction_user_fingerprint"),
        Index("ix_transaction_user_timestamp", "user_id", "transaction_timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    transaction_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    merchant: Mapped[str | None] = mapped_column(String(120))
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    user: Mapped[User] = relationship(back_populates="transactions")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "transaction_timestamp": self.transaction_timestamp.isoformat() + "Z",
            "amount": float(self.amount),
            "currency": self.currency,
            "category": self.category,
            "transaction_type": self.transaction_type,
            "merchant": self.merchant,
            "is_recurring": self.is_recurring,
        }


class Budget(db.Model):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "period_start",
            "period_end",
            "category",
            name="uq_budget_user_period_category",
        ),
        Index("ix_budget_user_period", "user_id", "period_start", "period_end"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="budgets")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "category": self.category,
            "amount": float(self.amount),
            "currency": self.currency,
        }


class AnalysisRun(db.Model):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    forecast_model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    anomaly_model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    history_periods: Mapped[int] = mapped_column(nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    forecast: Mapped["Forecast"] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan", uselist=False
    )
    alerts: Mapped[list["AnomalyAlert"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["RecommendationRecord"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )


class Forecast(db.Model):
    __tablename__ = "forecasts"
    __table_args__ = (Index("ix_forecast_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_spending: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    baseline_prediction: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="forecast")

    def to_dict(self) -> dict[str, Any]:
        history_weeks = min(
            self.analysis_run.history_periods if self.analysis_run else 0,
            8,
        )
        readiness = min(100, int(history_weeks * 100 / 8 + 0.5))
        if history_weeks <= 2:
            confidence_label = "Very low"
        elif history_weeks <= 4:
            confidence_label = "Low"
        elif history_weeks < 8:
            confidence_label = "Improving"
        else:
            confidence_label = "Established data"
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() + "Z",
            "model_version": self.model_version,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "predicted_spending": float(self.predicted_spending),
            "baseline_prediction": (
                float(self.baseline_prediction)
                if self.baseline_prediction is not None
                else None
            ),
            "currency": self.currency,
            "history_weeks": history_weeks,
            "required_history_weeks": 8,
            "data_readiness_percent": readiness,
            "confidence_label": confidence_label,
            "forecast_method": (
                "validated_model_blend"
                if history_weeks >= 8
                else "personal_spending_baseline"
            ),
            "accuracy_percent": None,
            "accuracy_note": (
                "Accuracy can be measured after this forecast week ends."
            ),
            "experimental_model": True,
        }


class AnomalyAlert(db.Model):
    __tablename__ = "anomaly_alerts"
    __table_args__ = (Index("ix_alert_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    transaction_id: Mapped[str | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL")
    )
    is_unusual_spending: Mapped[bool] = mapped_column(Boolean, nullable=False)
    anomaly_score: Mapped[float] = mapped_column(nullable=False)
    decision_threshold: Mapped[float] = mapped_column(nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="alerts")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() + "Z",
            "transaction_id": self.transaction_id,
            "is_unusual_spending": self.is_unusual_spending,
            "anomaly_score": self.anomaly_score,
            "decision_threshold": self.decision_threshold,
            "explanation": self.explanation,
            "model_version": self.model_version,
        }


class RecommendationRecord(db.Model):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendation_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recommendation_code: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_values: Mapped[dict[str, Any]] = mapped_column(db.JSON, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    analysis_run: Mapped[AnalysisRun] = relationship(
        back_populates="recommendations"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() + "Z",
            "recommendation_code": self.recommendation_code,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "reason": self.reason,
            "supporting_values": self.supporting_values,
            "suggested_action": self.suggested_action,
            "disclaimer": self.disclaimer,
        }


class ModelVersion(db.Model):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("component", "version", name="uq_model_component_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    component: Mapped[str] = mapped_column(String(30), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(db.JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
