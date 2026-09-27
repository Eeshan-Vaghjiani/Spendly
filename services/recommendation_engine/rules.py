"""Individual deterministic recommendation rules."""

from __future__ import annotations

import re
from collections.abc import Callable

from .explanations import DISCLAIMER, kes, percent
from .schemas import Recommendation, RecommendationContext


RuleFunction = Callable[[RecommendationContext], Recommendation | None]


def insufficient_history(
    context: RecommendationContext,
) -> Recommendation | None:
    minimum_periods = 8
    if context.history_periods >= minimum_periods:
        return None
    return Recommendation(
        recommendation_code="INSUFFICIENT_HISTORY",
        title="More spending history is needed",
        message=(
            f"Only {context.history_periods} completed period(s) are available. "
            f"At least {minimum_periods} are needed for personalised forecasting."
        ),
        severity="info",
        reason="The forecasting model requires a complete look-back window.",
        supporting_values={
            "available_periods": context.history_periods,
            "required_periods": minimum_periods,
        },
        suggested_action=(
            "Continue adding transactions until a complete history window is available."
        ),
        disclaimer=DISCLAIMER,
        priority=100,
    )


def spending_exceeds_income(
    context: RecommendationContext,
) -> Recommendation | None:
    if context.period_income is None or context.period_expenses is None:
        return None
    if context.period_expenses <= context.period_income:
        return None
    difference = context.period_expenses - context.period_income
    return Recommendation(
        recommendation_code="SPENDING_EXCEEDS_INCOME",
        title="Expenses are above income",
        message=(
            f"Recorded expenses exceed income by {kes(difference)} for this period."
        ),
        severity="critical",
        reason="Period expenses are greater than period income.",
        supporting_values={
            "period_income": context.period_income,
            "period_expenses": context.period_expenses,
            "difference": difference,
        },
        suggested_action=(
            "Review non-essential expenses and adjust the next budget before adding "
            "new discretionary commitments."
        ),
        disclaimer=DISCLAIMER,
        priority=95,
    )


def unusual_spending(
    context: RecommendationContext,
) -> Recommendation | None:
    if context.unusual_spending_detected is not True:
        return None
    return Recommendation(
        recommendation_code="UNUSUAL_SPENDING_REVIEW",
        title="Review unusual spending",
        message=(
            "A recent transaction pattern differs from the available spending history."
        ),
        severity="high",
        reason="The unusual-spending model crossed its configured alert threshold.",
        supporting_values={"unusual_spending_detected": True},
        suggested_action=(
            "Review the flagged transactions and correct any entry that is inaccurate."
        ),
        disclaimer=DISCLAIMER,
        priority=90,
    )


def forecast_exceeds_budget(
    context: RecommendationContext,
) -> Recommendation | None:
    if context.forecasted_spending is None or context.budget_amount is None:
        return None
    if context.forecasted_spending <= context.budget_amount:
        return None
    difference = context.forecasted_spending - context.budget_amount
    return Recommendation(
        recommendation_code="FORECAST_EXCEEDS_BUDGET",
        title="Forecast is above budget",
        message=(
            f"Next-period spending is forecast at "
            f"{kes(context.forecasted_spending)}, which is {kes(difference)} "
            "above the current budget."
        ),
        severity="high",
        reason="Forecasted spending is greater than the configured budget.",
        supporting_values={
            "forecasted_spending": context.forecasted_spending,
            "budget_amount": context.budget_amount,
            "difference": difference,
        },
        suggested_action=(
            "Review the largest planned categories and set a realistic spending limit."
        ),
        disclaimer=DISCLAIMER,
        priority=85,
    )


def rapid_category_increase(
    context: RecommendationContext,
) -> Recommendation | None:
    if not context.category_increases:
        return None
    category, increase = max(
        (
            (str(category).strip(), float(value))
            for category, value in context.category_increases.items()
        ),
        key=lambda item: item[1],
    )
    if increase < 0.30:
        return None
    safe_category = re.sub(r"[^A-Z0-9]+", "_", category.upper()).strip("_")
    return Recommendation(
        recommendation_code=f"CATEGORY_INCREASE_{safe_category}",
        title=f"{category.title()} spending is increasing",
        message=(
            f"{category.title()} spending increased by {percent(increase)} "
            "relative to its comparison period."
        ),
        severity="warning",
        reason="The largest category increase is at or above 30%.",
        supporting_values={
            "category": category,
            "category_increase": increase,
        },
        suggested_action=(
            f"Review recent {category.lower()} transactions and decide whether "
            "the increase should continue."
        ),
        disclaimer=DISCLAIMER,
        priority=75,
    )


def high_transaction_frequency(
    context: RecommendationContext,
) -> Recommendation | None:
    change = context.transaction_frequency_change
    if change is None or change < 0.50:
        return None
    return Recommendation(
        recommendation_code="HIGH_TRANSACTION_FREQUENCY",
        title="Transaction frequency increased",
        message=(
            f"Transaction frequency increased by {percent(change)} compared with "
            "the previous period."
        ),
        severity="warning",
        reason="Transaction frequency increased by at least 50%.",
        supporting_values={"transaction_frequency_change": change},
        suggested_action=(
            "Check whether frequent small purchases are contributing to overspending."
        ),
        disclaimer=DISCLAIMER,
        priority=70,
    )


def recurring_expense_increase(
    context: RecommendationContext,
) -> Recommendation | None:
    current = context.recurring_expense_current
    previous = context.recurring_expense_previous
    if current is None or previous is None or previous <= 0:
        return None
    increase = current / previous - 1
    if increase < 0.10:
        return None
    return Recommendation(
        recommendation_code="RECURRING_EXPENSE_INCREASE",
        title="Recurring expenses increased",
        message=(
            f"Recurring expenses increased by {percent(increase)}, from "
            f"{kes(previous)} to {kes(current)}."
        ),
        severity="warning",
        reason="Recurring expenses increased by at least 10%.",
        supporting_values={
            "recurring_expense_current": current,
            "recurring_expense_previous": previous,
            "increase": increase,
        },
        suggested_action=(
            "Review subscriptions and other recurring charges for changes or "
            "services that are no longer needed."
        ),
        disclaimer=DISCLAIMER,
        priority=65,
    )


def spending_growth(
    context: RecommendationContext,
) -> Recommendation | None:
    growth = context.spending_growth_rate
    if growth is None or growth < 0.25:
        return None
    return Recommendation(
        recommendation_code="SPENDING_GROWTH",
        title="Overall spending is growing",
        message=(
            f"Overall spending increased by {percent(growth)} relative to the "
            "comparison period."
        ),
        severity="warning",
        reason="The spending growth rate is at or above 25%.",
        supporting_values={"spending_growth_rate": growth},
        suggested_action=(
            "Compare the main category totals with the previous period and "
            "prioritise reductions that will not affect essential needs."
        ),
        disclaimer=DISCLAIMER,
        priority=60,
    )


def stable_within_budget(
    context: RecommendationContext,
) -> Recommendation | None:
    forecast = context.forecasted_spending
    budget = context.budget_amount
    historical = context.historical_spending_average
    if forecast is None or budget is None or historical is None:
        return None
    stable_limit = historical * 1.10
    if forecast > budget or forecast > stable_limit:
        return None
    return Recommendation(
        recommendation_code="STABLE_WITHIN_BUDGET",
        title="Spending is on track",
        message=(
            f"The {kes(forecast)} forecast is within budget and close to the "
            "available historical average."
        ),
        severity="positive",
        reason=(
            "Forecasted spending is within budget and no more than 10% above "
            "the historical average."
        ),
        supporting_values={
            "forecasted_spending": forecast,
            "budget_amount": budget,
            "historical_spending_average": historical,
        },
        suggested_action=(
            "Continue monitoring transactions and keep the current budget under review."
        ),
        disclaimer=DISCLAIMER,
        priority=10,
    )


def confirmed_spending_plan(context: RecommendationContext) -> Recommendation | None:
    if context.confirmed_spending_count <= 0:
        return None
    return Recommendation(
        recommendation_code="PLAN_CONFIRMED_SPENDING",
        title="Plan around confirmed spending",
        message="You confirmed that flagged spending was intentional. It remains included in your spending totals.",
        severity="info",
        reason="Confirmed entries need budget planning rather than another error-review prompt.",
        supporting_values={"confirmed_entries": context.confirmed_spending_count},
        suggested_action="If this expense will repeat, allow for it in your budget. If it was one-off, review the remaining budget before new optional spending.",
        disclaimer=DISCLAIMER,
        priority=70,
    )


RULES: tuple[RuleFunction, ...] = (
    confirmed_spending_plan,
    spending_exceeds_income,
    unusual_spending,
    forecast_exceeds_budget,
    rapid_category_increase,
    high_transaction_frequency,
    recurring_expense_increase,
    spending_growth,
    stable_within_budget,
)
