"""User-scoped cash-flow analytics for mobile visualisations."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select

from ..errors import ApiError
from ..extensions import db
from ..models import Budget, Transaction
from ..security.current_user import current_user


analytics_blueprint = Blueprint("analytics", __name__)
_BUCKET_COUNTS = {
    "daily": 14,
    "weekly": 12,
    "monthly": 12,
    "quarterly": 8,
    "yearly": 5,
}


def _month_start(value: date, offset: int = 0) -> date:
    month_index = value.year * 12 + value.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def _current_period_start(today: date, resolution: str) -> date:
    if resolution == "daily":
        return today
    if resolution == "weekly":
        return today - timedelta(days=today.weekday())
    if resolution == "monthly":
        return today.replace(day=1)
    if resolution == "quarterly":
        return date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    return date(today.year, 1, 1)


def _advance(value: date, resolution: str, steps: int = 1) -> date:
    if resolution == "daily":
        return value + timedelta(days=steps)
    if resolution == "weekly":
        return value + timedelta(weeks=steps)
    if resolution == "monthly":
        return _month_start(value, steps)
    if resolution == "quarterly":
        return _month_start(value, steps * 3)
    return date(value.year + steps, 1, 1)


def _label(value: date, resolution: str) -> str:
    if resolution == "daily":
        return value.strftime("%d %b")
    if resolution == "weekly":
        return f"Wk {value.strftime('%d %b')}"
    if resolution == "monthly":
        return value.strftime("%b %Y")
    if resolution == "quarterly":
        return f"Q{((value.month - 1) // 3) + 1} {value.year}"
    return str(value.year)


@analytics_blueprint.get("/analytics/cashflow")
@jwt_required()
def cashflow() -> tuple[Any, int]:
    user = current_user()
    resolution = request.args.get("resolution", "monthly").lower()
    if resolution not in _BUCKET_COUNTS:
        raise ApiError(
            "VALIDATION_ERROR",
            "resolution must be daily, weekly, monthly, quarterly, or yearly.",
            422,
        )

    today = datetime.utcnow().date()
    count = _BUCKET_COUNTS[resolution]
    current_start = _current_period_start(today, resolution)
    first_start = _advance(current_start, resolution, -(count - 1))
    final_end_exclusive = _advance(current_start, resolution)
    start_datetime = datetime.combine(first_start, time.min)
    end_datetime = datetime.combine(final_end_exclusive, time.min)

    selected_transactions = list(
        db.session.scalars(
            select(Transaction)
            .where(
                Transaction.user_id == user.id,
                Transaction.transaction_timestamp >= start_datetime,
                Transaction.transaction_timestamp < end_datetime,
            )
            .order_by(Transaction.transaction_timestamp.asc())
        )
    )
    all_transactions = list(
        db.session.scalars(
            select(Transaction).where(Transaction.user_id == user.id)
        )
    )
    budgets = list(
        db.session.scalars(
            select(Budget).where(
                Budget.user_id == user.id,
                Budget.period_end >= first_start,
                Budget.period_start < final_end_exclusive,
            )
        )
    )

    buckets: list[dict[str, Any]] = []
    for index in range(count):
        period_start = _advance(first_start, resolution, index)
        period_end_exclusive = _advance(period_start, resolution)
        income = 0.0
        expense = 0.0
        for transaction in selected_transactions:
            transaction_date = transaction.transaction_timestamp.date()
            if period_start <= transaction_date < period_end_exclusive:
                if transaction.transaction_type == "income":
                    income += float(transaction.amount)
                else:
                    expense += float(transaction.amount)
        buckets.append(
            {
                "period_start": period_start.isoformat(),
                "period_end": (period_end_exclusive - timedelta(days=1)).isoformat(),
                "label": _label(period_start, resolution),
                "income": round(income, 2),
                "expense": round(expense, 2),
                "net": round(income - expense, 2),
            }
        )

    period_income = sum(item["income"] for item in buckets)
    period_expense = sum(item["expense"] for item in buckets)
    all_income = sum(
        float(item.amount)
        for item in all_transactions
        if item.transaction_type == "income"
    )
    all_expense = sum(
        float(item.amount)
        for item in all_transactions
        if item.transaction_type == "expense"
    )
    period_net = period_income - period_expense
    savings_rate = period_net / period_income * 100 if period_income > 0 else 0.0

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "resolution": resolution,
                    "period_start": first_start.isoformat(),
                    "period_end": (final_end_exclusive - timedelta(days=1)).isoformat(),
                    "currency": "KES",
                    "summary": {
                        "income": round(period_income, 2),
                        "expense": round(period_expense, 2),
                        "net": round(period_net, 2),
                        "cash_balance": round(all_income - all_expense, 2),
                        "savings_rate": round(savings_rate, 1),
                        "budgeted": round(sum(float(item.amount) for item in budgets), 2),
                    },
                    "series": buckets,
                },
            }
        ),
        200,
    )
