"""Typed inputs and outputs for the recommendation engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Mapping


Severity = Literal["info", "positive", "warning", "high", "critical"]


def _optional_nonnegative(name: str, value: float | None) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if numeric < 0:
        raise ValueError(f"{name} cannot be negative.")
    return numeric


@dataclass(frozen=True)
class RecommendationContext:
    forecasted_spending: float | None = None
    budget_amount: float | None = None
    historical_spending_average: float | None = None
    spending_growth_rate: float | None = None
    unusual_spending_detected: bool | None = None
    category_increases: Mapping[str, float] = field(default_factory=dict)
    transaction_frequency_change: float | None = None
    recurring_expense_current: float | None = None
    recurring_expense_previous: float | None = None
    period_income: float | None = None
    period_expenses: float | None = None
    history_periods: int = 0
    confirmed_spending_count: int = 0

    def __post_init__(self) -> None:
        for name in (
            "forecasted_spending",
            "budget_amount",
            "historical_spending_average",
            "recurring_expense_current",
            "recurring_expense_previous",
            "period_income",
            "period_expenses",
        ):
            _optional_nonnegative(name, getattr(self, name))
        if self.history_periods < 0:
            raise ValueError("history_periods cannot be negative.")
        if self.confirmed_spending_count < 0:
            raise ValueError("confirmed_spending_count cannot be negative.")
        for category, increase in self.category_increases.items():
            if not str(category).strip():
                raise ValueError("Category names cannot be blank.")
            float(increase)


@dataclass(frozen=True)
class Recommendation:
    recommendation_code: str
    title: str
    message: str
    severity: Severity
    reason: str
    supporting_values: Mapping[str, Any]
    suggested_action: str
    disclaimer: str
    priority: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
