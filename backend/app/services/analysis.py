"""Orchestrate feature preparation, inference, recommendations, and storage."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from services.recommendation_engine import (
    RecommendationContext,
    RecommendationEngine,
)

from ..extensions import db
from ..models import (
    AnalysisRun,
    AnomalyAlert,
    Budget,
    Forecast,
    RecommendationRecord,
    User,
)
from ..repositories import BudgetRepository, TransactionRepository
from .feature_preparation import FeaturePreparationService
from .model_registry import ModelRegistry


class AnalysisService:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self.features = FeaturePreparationService(
            registry.forecast_schema, registry.anomaly_schema
        )
        self.recommendations = RecommendationEngine()

    def run(self, user: User) -> dict[str, Any]:
        transactions = TransactionRepository.chronological(user.id)
        budgets = BudgetRepository.all(user.id)
        forecast_features = self.features.forecasting(
            user, transactions, budgets
        )
        model_ready = (
            forecast_features.history_periods
            >= forecast_features.required_history_periods
        )
        if model_ready:
            forecast_result = self.registry.forecast(
                forecast_features.raw_sequence
            )
            # Held-out project metrics favour the linear comparator, so the
            # production estimate weights it more heavily than the LSTM.
            predicted_spending = (
                forecast_result["lstm"] * 0.35
                + forecast_result["linear_regression"] * 0.65
            )
        else:
            # Before eight weeks, avoid sending padded, out-of-distribution
            # sequences to the trained model. A personal rolling baseline is
            # more honest and becomes progressively more representative.
            predicted_spending = forecast_features.historical_average
        anomaly_features = self.features.anomaly(transactions)
        anomaly_result = self.registry.detect_unusual(anomaly_features)
        unusual_detected = bool(
            not anomaly_result.empty
            and anomaly_result["is_unusual_spending"].any()
        )
        context = RecommendationContext(
            forecasted_spending=predicted_spending,
            budget_amount=forecast_features.next_budget,
            historical_spending_average=forecast_features.historical_average,
            spending_growth_rate=forecast_features.spending_growth_rate,
            unusual_spending_detected=unusual_detected,
            category_increases=forecast_features.category_increases,
            transaction_frequency_change=(
                forecast_features.transaction_frequency_change
            ),
            recurring_expense_current=(
                forecast_features.recurring_expense_current
            ),
            recurring_expense_previous=(
                forecast_features.recurring_expense_previous
            ),
            period_income=forecast_features.period_income,
            period_expenses=forecast_features.period_expenses,
            history_periods=forecast_features.history_periods,
        )
        recommendations = self.recommendations.evaluate(context)
        run = AnalysisRun(
            user_id=user.id,
            forecast_model_version=self.registry.forecast_version,
            anomaly_model_version=self.registry.anomaly_version,
            history_periods=forecast_features.history_periods,
        )
        db.session.add(run)
        db.session.flush()
        forecast = Forecast(
            analysis_run_id=run.id,
            user_id=user.id,
            period_start=forecast_features.next_period_start,
            period_end=forecast_features.next_period_end,
            predicted_spending=Decimal(f"{predicted_spending:.2f}"),
            baseline_prediction=Decimal(
                f"{forecast_features.historical_average:.2f}"
            ),
            model_version=self.registry.forecast_version,
        )
        db.session.add(forecast)
        alert_records: list[AnomalyAlert] = []
        if not anomaly_result.empty:
            for index, result in anomaly_result.iterrows():
                if not bool(result["is_unusual_spending"]):
                    continue
                source = anomaly_features.loc[index]
                alert = AnomalyAlert(
                    analysis_run_id=run.id,
                    user_id=user.id,
                    transaction_id=str(source["transaction_id"]),
                    is_unusual_spending=True,
                    anomaly_score=float(result["anomaly_score"]),
                    decision_threshold=float(result["decision_threshold"]),
                    explanation=str(result["explanation"]),
                    model_version=self.registry.anomaly_version,
                )
                alert_records.append(alert)
                db.session.add(alert)
        recommendation_records: list[RecommendationRecord] = []
        for recommendation in recommendations:
            payload = recommendation.to_dict()
            payload.pop("priority")
            record = RecommendationRecord(
                analysis_run_id=run.id,
                user_id=user.id,
                **payload,
            )
            recommendation_records.append(record)
            db.session.add(record)
        db.session.commit()
        return self.serialize(
            run,
            forecast,
            alert_records,
            recommendation_records,
        )

    @staticmethod
    def serialize(
        run: AnalysisRun,
        forecast: Forecast,
        alerts: list[AnomalyAlert],
        recommendations: list[RecommendationRecord],
    ) -> dict[str, Any]:
        return {
            "analysis_run_id": run.id,
            "generated_at": run.generated_at.isoformat() + "Z",
            "forecast": AnalysisService.forecast_payload(forecast),
            "alert_summary": {
                "unusual_spending_detected": bool(alerts),
                "alert_count": len(alerts),
                "alerts": [alert.to_dict() for alert in alerts],
            },
            "recommendations": [
                recommendation.to_dict()
                for recommendation in recommendations
            ],
        }

    @staticmethod
    def forecast_payload(forecast: Forecast) -> dict[str, Any]:
        payload = forecast.to_dict()
        payload["actual_spending"] = None
        if date.today() <= forecast.period_end:
            return payload
        actual, count = TransactionRepository.expense_total(
            forecast.user_id, forecast.period_start, forecast.period_end
        )
        if count == 0:
            payload["accuracy_note"] = (
                "Record that week's expenses to measure actual accuracy."
            )
            return payload
        predicted = float(forecast.predicted_spending)
        error_percent = abs(predicted - actual) / max(actual, 1.0) * 100
        payload["actual_spending"] = round(actual, 2)
        payload["accuracy_percent"] = round(
            max(0.0, 100.0 - error_percent), 1
        )
        payload["accuracy_note"] = (
            "Measured against the expenses recorded for that completed week."
        )
        return payload

    @staticmethod
    def latest(run: AnalysisRun) -> dict[str, Any]:
        return AnalysisService.serialize(
            run,
            run.forecast,
            list(run.alerts),
            list(run.recommendations),
        )
