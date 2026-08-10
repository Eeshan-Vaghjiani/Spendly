from __future__ import annotations

import pytest

from services.recommendation_engine.engine import RecommendationEngine
from services.recommendation_engine.rules import (
    forecast_exceeds_budget,
    high_transaction_frequency,
    rapid_category_increase,
    recurring_expense_increase,
    spending_exceeds_income,
    spending_growth,
    stable_within_budget,
    unusual_spending,
)
from services.recommendation_engine.schemas import RecommendationContext


def complete_context(**overrides: object) -> RecommendationContext:
    values: dict[str, object] = {
        "forecasted_spending": 10_000,
        "budget_amount": 15_000,
        "historical_spending_average": 9_500,
        "spending_growth_rate": 0.05,
        "unusual_spending_detected": False,
        "category_increases": {"food": 0.05},
        "transaction_frequency_change": 0.10,
        "recurring_expense_current": 2_000,
        "recurring_expense_previous": 2_000,
        "period_income": 40_000,
        "period_expenses": 10_000,
        "history_periods": 8,
    }
    values.update(overrides)
    return RecommendationContext(**values)


def test_forecast_exceeds_budget_rule() -> None:
    result = forecast_exceeds_budget(
        complete_context(forecasted_spending=16_000)
    )
    assert result is not None
    assert result.recommendation_code == "FORECAST_EXCEEDS_BUDGET"
    assert result.supporting_values["difference"] == 1_000


def test_forecast_equal_to_budget_is_not_over_budget() -> None:
    assert (
        forecast_exceeds_budget(
            complete_context(forecasted_spending=15_000)
        )
        is None
    )


def test_category_increase_boundary() -> None:
    result = rapid_category_increase(
        complete_context(category_increases={"food and dining": 0.30})
    )
    assert result is not None
    assert result.recommendation_code == "CATEGORY_INCREASE_FOOD_AND_DINING"


def test_category_rule_selects_largest_increase() -> None:
    result = rapid_category_increase(
        complete_context(
            category_increases={"food": 0.31, "transport": 0.55}
        )
    )
    assert result is not None
    assert result.supporting_values["category"] == "transport"


def test_frequency_boundary() -> None:
    assert (
        high_transaction_frequency(
            complete_context(transaction_frequency_change=0.50)
        )
        is not None
    )


def test_recurring_expense_increase_boundary() -> None:
    result = recurring_expense_increase(
        complete_context(
            recurring_expense_previous=1_000,
            recurring_expense_current=1_100,
        )
    )
    assert result is not None


def test_zero_previous_recurring_expense_is_safe() -> None:
    assert (
        recurring_expense_increase(
            complete_context(
                recurring_expense_previous=0,
                recurring_expense_current=1_000,
            )
        )
        is None
    )


def test_spending_exceeds_income_rule() -> None:
    result = spending_exceeds_income(
        complete_context(period_income=12_000, period_expenses=14_000)
    )
    assert result is not None
    assert result.severity == "critical"


def test_equal_expenses_and_income_is_not_exceeding() -> None:
    assert (
        spending_exceeds_income(
            complete_context(period_income=12_000, period_expenses=12_000)
        )
        is None
    )


def test_unusual_spending_rule() -> None:
    result = unusual_spending(
        complete_context(unusual_spending_detected=True)
    )
    assert result is not None
    assert "fraud" not in (result.title + result.message).lower()


def test_spending_growth_boundary() -> None:
    assert (
        spending_growth(complete_context(spending_growth_rate=0.25))
        is not None
    )


def test_stable_within_budget_rule() -> None:
    result = stable_within_budget(complete_context())
    assert result is not None
    assert result.severity == "positive"


def test_stable_rule_respects_historical_limit() -> None:
    assert (
        stable_within_budget(
            complete_context(
                forecasted_spending=12_000,
                historical_spending_average=9_000,
            )
        )
        is None
    )


@pytest.mark.parametrize(
    "field",
    [
        "forecasted_spending",
        "budget_amount",
        "historical_spending_average",
        "period_income",
        "period_expenses",
    ],
)
def test_missing_values_do_not_crash(field: str) -> None:
    context = complete_context(**{field: None})
    RecommendationEngine().evaluate(context)


def test_insufficient_history_suppresses_personalised_rules() -> None:
    results = RecommendationEngine().evaluate(
        complete_context(
            history_periods=7,
            forecasted_spending=20_000,
            unusual_spending_detected=True,
        )
    )
    assert [result.recommendation_code for result in results] == [
        "INSUFFICIENT_HISTORY"
    ]


def test_conflicting_warning_suppresses_on_track() -> None:
    results = RecommendationEngine().evaluate(
        complete_context(
            spending_growth_rate=0.25,
            forecasted_spending=10_000,
        )
    )
    codes = {result.recommendation_code for result in results}
    assert "SPENDING_GROWTH" in codes
    assert "STABLE_WITHIN_BUDGET" not in codes


def test_priority_ordering() -> None:
    results = RecommendationEngine().evaluate(
        complete_context(
            period_income=5_000,
            period_expenses=20_000,
            unusual_spending_detected=True,
            forecasted_spending=20_000,
        )
    )
    assert [result.priority for result in results] == sorted(
        [result.priority for result in results], reverse=True
    )
    assert results[0].recommendation_code == "SPENDING_EXCEEDS_INCOME"


def test_duplicate_suppression() -> None:
    engine = RecommendationEngine(
        rules=(unusual_spending, unusual_spending)
    )
    results = engine.evaluate(
        complete_context(unusual_spending_detected=True)
    )
    assert len(results) == 1


def test_maximum_recommendation_limit() -> None:
    context = complete_context(
        period_income=5_000,
        period_expenses=20_000,
        unusual_spending_detected=True,
        forecasted_spending=20_000,
        category_increases={"food": 0.50},
        transaction_frequency_change=0.80,
        recurring_expense_previous=1_000,
        recurring_expense_current=1_500,
        spending_growth_rate=0.50,
    )
    assert len(RecommendationEngine(maximum_recommendations=3).evaluate(context)) == 3


def test_default_recommendation_limit_keeps_output_focused() -> None:
    context = complete_context(
        period_income=5_000,
        period_expenses=20_000,
        unusual_spending_detected=True,
        forecasted_spending=20_000,
        category_increases={"food": 0.50},
        transaction_frequency_change=0.80,
        recurring_expense_previous=1_000,
        recurring_expense_current=1_500,
        spending_growth_rate=0.50,
    )
    assert len(RecommendationEngine().evaluate(context)) == 3


def test_negative_money_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        complete_context(period_income=-1)


def test_every_recommendation_contains_required_explanation_fields() -> None:
    results = RecommendationEngine().evaluate(
        complete_context(
            forecasted_spending=20_000,
            unusual_spending_detected=True,
        )
    )
    assert results
    for result in results:
        payload = result.to_dict()
        assert payload["recommendation_code"]
        assert payload["title"]
        assert payload["message"]
        assert payload["severity"]
        assert payload["reason"]
        assert payload["supporting_values"]
        assert payload["suggested_action"]
        assert "not professional financial advice" in payload["disclaimer"]
