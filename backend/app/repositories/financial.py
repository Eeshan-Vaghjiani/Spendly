"""Queries that enforce user ownership at the persistence boundary."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import Select, func, select

from ..extensions import db
from ..models import (
    AnomalyAlert,
    Budget,
    Forecast,
    RecommendationRecord,
    Transaction,
)


class TransactionRepository:
    @staticmethod
    def owned(transaction_id: str, user_id: str) -> Transaction | None:
        return db.session.scalar(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
        )

    @staticmethod
    def by_fingerprint(user_id: str, fingerprint: str) -> Transaction | None:
        return db.session.scalar(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.fingerprint == fingerprint,
            )
        )

    @staticmethod
    def list_query(
        user_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        category: str | None = None,
    ) -> Select[tuple[Transaction]]:
        query = select(Transaction).where(Transaction.user_id == user_id)
        if start_date:
            query = query.where(
                Transaction.transaction_timestamp >= start_date
            )
        if end_date:
            query = query.where(
                Transaction.transaction_timestamp
                < date.fromordinal(end_date.toordinal() + 1)
            )
        if category:
            query = query.where(Transaction.category == category)
        return query.order_by(Transaction.transaction_timestamp.desc())

    @staticmethod
    def chronological(user_id: str) -> list[Transaction]:
        return list(
            db.session.scalars(
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .order_by(
                    Transaction.transaction_timestamp.asc(),
                    Transaction.id.asc(),
                )
            )
        )

    @staticmethod
    def expense_total(
        user_id: str, start_date: date, end_date: date, *, nairobi: bool = False
    ) -> tuple[float, int]:
        start = datetime.combine(start_date, time.min)
        end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min)
        if nairobi:
            start -= timedelta(hours=3)
            end_exclusive -= timedelta(hours=3)
        total, count = db.session.execute(
            select(func.sum(Transaction.amount), func.count(Transaction.id)).where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "expense",
                Transaction.transaction_timestamp >= start,
                Transaction.transaction_timestamp < end_exclusive,
            )
        ).one()
        return float(total or 0), int(count or 0)


class BudgetRepository:
    @staticmethod
    def owned(budget_id: str, user_id: str) -> Budget | None:
        return db.session.scalar(
            select(Budget).where(
                Budget.id == budget_id, Budget.user_id == user_id
            )
        )

    @staticmethod
    def all(user_id: str) -> list[Budget]:
        return list(
            db.session.scalars(
                select(Budget)
                .where(Budget.user_id == user_id)
                .order_by(Budget.period_start.desc(), Budget.category.asc())
            )
        )


class HistoryRepository:
    MODEL_BY_KIND = {
        "forecasts": Forecast,
        "alerts": AnomalyAlert,
        "recommendations": RecommendationRecord,
    }

    @classmethod
    def query(cls, kind: str, user_id: str) -> Select:
        model = cls.MODEL_BY_KIND[kind]
        return (
            select(model)
            .where(model.user_id == user_id)
            .order_by(model.created_at.desc())
        )
