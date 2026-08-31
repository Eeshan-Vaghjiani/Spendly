"""User-scoped cash-flow analytics for mobile visualisations."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import case, func, select

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


def utc_today() -> date:
    """Return the current UTC date; kept separate for boundary-focused tests."""
    return datetime.utcnow().date()


def _shift_months(value: date, offset: int) -> date:
    month_index = value.year * 12 + value.month - 1 + offset
    year = month_index // 12
    month = month_index % 12 + 1
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    last_day = (next_month - timedelta(days=1)).day
    return date(year, month, min(value.day, last_day))


def _dashboard_range(period: str, today: date) -> tuple[date | None, date]:
    end_exclusive = today + timedelta(days=1)
    if period == "weekly":
        return today - timedelta(days=today.weekday()), end_exclusive
    if period == "monthly":
        return today.replace(day=1), end_exclusive
    if period == "last_3_months":
        return _shift_months(end_exclusive, -3), end_exclusive
    if period == "yearly":
        return date(today.year, 1, 1), end_exclusive
    return None, end_exclusive


def _transaction_filters(
    user_id: str,
    start: date | None,
    end_exclusive: date | None,
) -> list[Any]:
    filters: list[Any] = [Transaction.user_id == user_id]
    if end_exclusive is not None:
        filters.append(
            Transaction.transaction_timestamp
            < datetime.combine(end_exclusive, time.min)
        )
    if start is not None:
        filters.append(
            Transaction.transaction_timestamp >= datetime.combine(start, time.min)
        )
    return filters


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

    today = utc_today()
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


@analytics_blueprint.get("/analytics/dashboard")
@jwt_required()
def dashboard_summary() -> tuple[Any, int]:
    user = current_user()
    period = request.args.get("period", "monthly").lower()
    allowed = {"weekly", "monthly", "last_3_months", "yearly", "all_time"}
    if period not in allowed:
        raise ApiError(
            "VALIDATION_ERROR",
            "period must be weekly, monthly, last_3_months, yearly, or all_time.",
            422,
        )

    today = utc_today()
    start, end_exclusive = _dashboard_range(period, today)
    filters = _transaction_filters(
        user.id,
        start,
        None if period == "all_time" else end_exclusive,
    )
    aggregate = db.session.execute(
        select(
            func.count(Transaction.id),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == "income", Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == "expense", Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(*filters)
    ).one()
    transaction_count = int(aggregate[0])
    income = float(aggregate[1])
    expense = float(aggregate[2])

    lifetime = db.session.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == "income", Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == "expense", Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ),
            func.min(Transaction.transaction_timestamp),
            func.max(Transaction.transaction_timestamp),
        ).where(Transaction.user_id == user.id)
    ).one()
    cash_balance = float(lifetime[0]) - float(lifetime[1])
    first_transaction = lifetime[2]
    last_transaction = lifetime[3]

    has_older_transactions = False
    if start is not None:
        has_older_transactions = bool(
            db.session.scalar(
                select(func.count(Transaction.id)).where(
                    Transaction.user_id == user.id,
                    Transaction.transaction_timestamp
                    < datetime.combine(start, time.min),
                )
            )
        )

    top_category_row = db.session.execute(
        select(Transaction.category, func.sum(Transaction.amount).label("amount"))
        .where(*filters, Transaction.transaction_type == "expense")
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc(), Transaction.category.asc())
        .limit(1)
    ).first()

    active_budgets = list(
        db.session.scalars(
            select(Budget).where(
                Budget.user_id == user.id,
                Budget.period_start <= today,
                Budget.period_end >= today,
            )
        )
    )
    total_budgets = [
        budget for budget in active_budgets if budget.category.casefold() == "total"
    ]
    budgets_for_summary = total_budgets or active_budgets
    budget_amount = sum(float(budget.amount) for budget in budgets_for_summary)
    budget_spent = 0.0
    for budget in budgets_for_summary:
        budget_filters = [
            Transaction.user_id == user.id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_timestamp
            >= datetime.combine(budget.period_start, time.min),
            Transaction.transaction_timestamp
            < datetime.combine(budget.period_end + timedelta(days=1), time.min),
        ]
        if budget.category.casefold() != "total":
            budget_filters.append(func.lower(Transaction.category) == budget.category.lower())
        budget_spent += float(
            db.session.scalar(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    *budget_filters
                )
            )
        )

    response_start = start
    if period == "all_time" and first_transaction is not None:
        response_start = first_transaction.date()
    response_end = (
        max(today, last_transaction.date())
        if period == "all_time" and last_transaction is not None
        else today
    )
    net = income - expense
    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "period": period,
                    "period_start": response_start.isoformat()
                    if response_start
                    else None,
                    "period_end": response_end.isoformat(),
                    "currency": "KES",
                    "transaction_count": transaction_count,
                    "has_transactions": transaction_count > 0,
                    "has_older_transactions": has_older_transactions,
                    "income": round(income, 2),
                    "expense": round(expense, 2),
                    "net": round(net, 2),
                    "cash_balance": round(cash_balance, 2),
                    "top_category": top_category_row[0] if top_category_row else None,
                    "top_category_amount": round(float(top_category_row[1]), 2)
                    if top_category_row
                    else 0.0,
                    "active_budget": {
                        "amount": round(budget_amount, 2),
                        "spent": round(budget_spent, 2),
                        "percent_used": round(
                            budget_spent / budget_amount * 100, 1
                        )
                        if budget_amount > 0
                        else 0.0,
                        "is_set": budget_amount > 0,
                    },
                },
            }
        ),
        200,
    )
