"""Create training-compatible forecasting and anomaly features."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from ..errors import ApiError
from ..models import Budget, Transaction, User


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


@dataclass(frozen=True)
class ForecastFeatureBundle:
    raw_sequence: np.ndarray
    history_periods: int
    required_history_periods: int
    next_period_start: date
    next_period_end: date
    historical_average: float
    spending_growth_rate: float
    category_increases: dict[str, float]
    transaction_frequency_change: float
    recurring_expense_current: float
    recurring_expense_previous: float
    period_income: float
    period_expenses: float
    next_budget: float | None


class FeaturePreparationService:
    def __init__(self, forecast_schema: dict[str, Any], anomaly_schema: dict[str, Any]) -> None:
        self.feature_names = list(
            forecast_schema["lstm"]["ordered_features"]
        )
        self.lookback = int(forecast_schema["lstm"]["look_back_window"])
        self.anomaly_features = list(anomaly_schema["ordered_features"])
        self.category_mapping = {
            str(key): int(value)
            for key, value in anomaly_schema["category_mapping"].items()
        }
        self.unknown_category_code = int(
            anomaly_schema.get("unknown_category_code", -1)
        )

    @staticmethod
    def _transactions_frame(transactions: list[Transaction]) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "transaction_id": transaction.id,
                    "transaction_timestamp": transaction.transaction_timestamp,
                    "amount": float(transaction.amount),
                    "category": transaction.category,
                    "transaction_type": transaction.transaction_type,
                    "is_recurring": transaction.is_recurring,
                }
                for transaction in transactions
            ]
        )

    @staticmethod
    def _budget_for_period(
        budgets: list[Budget], start: date, end: date
    ) -> float | None:
        matching = [
            float(budget.amount)
            for budget in budgets
            if budget.period_start <= end and budget.period_end >= start
        ]
        return sum(matching) if matching else None

    def forecasting(
        self,
        user: User,
        transactions: list[Transaction],
        budgets: list[Budget],
    ) -> ForecastFeatureBundle:
        del user
        if not transactions:
            raise ApiError(
                "INSUFFICIENT_HISTORY",
                "More transaction history is required before a forecast can be produced.",
                422,
            )
        frame = self._transactions_frame(transactions)
        frame["transaction_timestamp"] = pd.to_datetime(
            frame["transaction_timestamp"]
        )
        frame["period_start"] = (
            frame["transaction_timestamp"]
            .dt.to_period("W-SUN")
            .dt.start_time
        )
        minimum = frame["period_start"].min()
        maximum = frame["period_start"].max()
        periods = pd.date_range(minimum, maximum, freq="W-MON")
        expense = frame[frame["transaction_type"] == "expense"].copy()
        income = frame[frame["transaction_type"] == "income"].copy()
        weekly = pd.DataFrame({"period_start": periods})
        if expense.empty:
            expense_totals = pd.DataFrame(
                columns=[
                    "period_start",
                    "total_spending",
                    "transaction_count",
                    "average_transaction_amount",
                    "recurring_expenses",
                ]
            )
        else:
            expense_totals = (
                expense.groupby("period_start")
                .agg(
                    total_spending=("amount", "sum"),
                    transaction_count=("transaction_id", "count"),
                    average_transaction_amount=("amount", "mean"),
                    recurring_expenses=(
                        "amount",
                        lambda values: float(
                            values[
                                expense.loc[values.index, "is_recurring"].astype(bool)
                            ].sum()
                        ),
                    ),
                )
                .reset_index()
            )
        weekly = weekly.merge(expense_totals, how="left", on="period_start")
        weekly["income"] = weekly["period_start"].map(
            income.groupby("period_start")["amount"].sum()
            if not income.empty
            else {}
        )
        category_features = [
            feature for feature in self.feature_names if feature.startswith("category_")
        ]
        for feature in category_features:
            weekly[feature] = 0.0
        if not expense.empty:
            expense["category_feature"] = (
                "category_" + expense["category"].astype(str).map(slug)
            )
            grouped_category = (
                expense.groupby(["period_start", "category_feature"])["amount"]
                .sum()
            )
            period_index = {
                timestamp: index
                for index, timestamp in enumerate(weekly["period_start"])
            }
            for (period, feature), amount in grouped_category.items():
                if feature in weekly.columns and period in period_index:
                    weekly.loc[period_index[period], feature] = float(amount)
        numeric = [
            "total_spending",
            "transaction_count",
            "average_transaction_amount",
            "recurring_expenses",
            "income",
            *category_features,
        ]
        weekly[numeric] = weekly[numeric].fillna(0.0)
        weekly["budget_amount"] = [
            self._budget_for_period(
                budgets,
                timestamp.date(),
                (timestamp + pd.Timedelta(days=6)).date(),
            )
            or 0.0
            for timestamp in weekly["period_start"]
        ]
        weekly["budget_difference"] = (
            weekly["budget_amount"] - weekly["total_spending"]
        )
        weekly["previous_period_spending"] = weekly["total_spending"].shift(1)
        weekly["rolling_average_4"] = (
            weekly["total_spending"].shift(1).rolling(4, min_periods=1).mean()
        )
        previous = weekly["previous_period_spending"]
        weekly["spending_growth_rate"] = np.where(
            previous > 0,
            (weekly["total_spending"] - previous) / previous,
            0.0,
        )
        weekly[
            [
                "previous_period_spending",
                "rolling_average_4",
                "spending_growth_rate",
            ]
        ] = weekly[
            [
                "previous_period_spending",
                "rolling_average_4",
                "spending_growth_rate",
            ]
        ].fillna(0.0)
        actual_sequence_frame = weekly.tail(self.lookback)
        raw_sequence = actual_sequence_frame[self.feature_names].to_numpy(
            dtype=np.float64
        )
        if len(raw_sequence) < self.lookback:
            padding = np.repeat(
                raw_sequence[:1], self.lookback - len(raw_sequence), axis=0
            )
            raw_sequence = np.vstack([padding, raw_sequence])
        latest = actual_sequence_frame.iloc[-1]
        previous_row = (
            actual_sequence_frame.iloc[-2]
            if len(actual_sequence_frame) >= 2
            else latest
        )
        category_increases: dict[str, float] = {}
        for feature in category_features:
            previous_value = float(previous_row[feature])
            current_value = float(latest[feature])
            if previous_value > 0:
                category_increases[feature.removeprefix("category_")] = (
                    current_value / previous_value - 1
                )
        previous_count = float(previous_row["transaction_count"])
        frequency_change = (
            float(latest["transaction_count"]) / previous_count - 1
            if previous_count > 0
            else 0.0
        )
        next_start_timestamp = maximum + pd.Timedelta(days=7)
        next_start = next_start_timestamp.date()
        next_end = (next_start_timestamp + pd.Timedelta(days=6)).date()
        return ForecastFeatureBundle(
            raw_sequence=raw_sequence,
            history_periods=int(len(periods)),
            required_history_periods=self.lookback,
            next_period_start=next_start,
            next_period_end=next_end,
            historical_average=float(
                actual_sequence_frame["total_spending"].tail(4).mean()
            ),
            spending_growth_rate=float(latest["spending_growth_rate"]),
            category_increases=category_increases,
            transaction_frequency_change=frequency_change,
            recurring_expense_current=float(latest["recurring_expenses"]),
            recurring_expense_previous=float(
                previous_row["recurring_expenses"]
            ),
            period_income=float(latest["income"]),
            period_expenses=float(latest["total_spending"]),
            next_budget=self._budget_for_period(
                budgets, next_start, next_end
            ),
        )

    def anomaly(self, transactions: list[Transaction], limit: int = 20) -> pd.DataFrame:
        frame = self._transactions_frame(transactions)
        if frame.empty:
            return pd.DataFrame(columns=["transaction_id", *self.anomaly_features])
        frame = frame[frame["transaction_type"] == "expense"].copy()
        frame["transaction_timestamp"] = pd.to_datetime(
            frame["transaction_timestamp"]
        )
        frame = frame.sort_values(
            ["transaction_timestamp", "transaction_id"]
        ).reset_index(drop=True)
        rows: list[dict[str, Any]] = []
        start_index = max(0, len(frame) - limit)
        for index in range(start_index, len(frame)):
            current = frame.iloc[index]
            prior = frame.iloc[:index]
            timestamp = pd.Timestamp(current["transaction_timestamp"])
            previous_timestamp = (
                pd.Timestamp(prior.iloc[-1]["transaction_timestamp"])
                if not prior.empty
                else None
            )
            recent = prior[
                prior["transaction_timestamp"]
                >= timestamp - pd.Timedelta(days=7)
            ]
            previous_28 = prior[
                (prior["transaction_timestamp"] < timestamp - pd.Timedelta(days=7))
                & (
                    prior["transaction_timestamp"]
                    >= timestamp - pd.Timedelta(days=35)
                )
            ]
            historical_average = (
                float(prior["amount"].mean()) if not prior.empty else 0.0
            )
            comparable_week = (
                float(previous_28["amount"].sum()) / 4
                if not previous_28.empty
                else 0.0
            )
            recent_change = (
                float(recent["amount"].sum()) / comparable_week - 1
                if comparable_week > 0
                else 0.0
            )
            category = str(current["category"])
            category_proportion = (
                float((prior["category"] == category).sum()) / len(prior)
                if len(prior)
                else 0.0
            )
            amount = float(current["amount"])
            record = {
                "transaction_id": current["transaction_id"],
                "amount": amount,
                "category_code": self.category_mapping.get(
                    category, self.unknown_category_code
                ),
                "transaction_count_last_7d": float(len(recent)),
                "time_since_previous_hours": (
                    (timestamp - previous_timestamp).total_seconds() / 3600
                    if previous_timestamp is not None
                    else 0.0
                ),
                "deviation_from_historical_average": (
                    amount / historical_average - 1
                    if historical_average > 0
                    else 0.0
                ),
                "recent_spending_change": recent_change,
                "category_proportion": category_proportion,
                "is_recurring": bool(current["is_recurring"]),
                "hour_of_day": int(timestamp.hour),
                "is_weekend": int(timestamp.dayofweek >= 5),
            }
            rows.append(record)
        return pd.DataFrame(rows)
