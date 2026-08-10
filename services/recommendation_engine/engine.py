"""Recommendation rule orchestration, priority, and suppression."""

from __future__ import annotations

from collections.abc import Iterable

from .rules import RULES, RuleFunction, insufficient_history
from .schemas import Recommendation, RecommendationContext


class RecommendationEngine:
    def __init__(
        self,
        rules: Iterable[RuleFunction] = RULES,
        *,
        maximum_recommendations: int = 3,
    ) -> None:
        if maximum_recommendations <= 0:
            raise ValueError("maximum_recommendations must be positive.")
        self._rules = tuple(rules)
        self._maximum_recommendations = maximum_recommendations

    def evaluate(
        self, context: RecommendationContext
    ) -> list[Recommendation]:
        history_result = insufficient_history(context)
        if history_result is not None:
            return [history_result]
        candidates = [
            recommendation
            for rule in self._rules
            if (recommendation := rule(context)) is not None
        ]
        if any(
            recommendation.severity in {"warning", "high", "critical"}
            for recommendation in candidates
        ):
            candidates = [
                recommendation
                for recommendation in candidates
                if recommendation.recommendation_code != "STABLE_WITHIN_BUDGET"
            ]
        by_code: dict[str, Recommendation] = {}
        for recommendation in candidates:
            current = by_code.get(recommendation.recommendation_code)
            if current is None or recommendation.priority > current.priority:
                by_code[recommendation.recommendation_code] = recommendation
        return sorted(
            by_code.values(),
            key=lambda recommendation: (
                -recommendation.priority,
                recommendation.recommendation_code,
            ),
        )[: self._maximum_recommendations]
