"""Prepare leakage-safe datasets for LSTM, linear baseline, Isolation Forest and rules."""

from __future__ import annotations

import argparse
import re
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pipeline_utils import (
    LOGGER,
    append_lineage,
    chronological_boundaries,
    configure_logging,
    ensure_output_directories,
    load_config,
    mode_config,
    repo_root_from_file,
    write_csv_sample,
    write_json,
    write_parquet,
)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def period_start(series: pd.Series, aggregation: str) -> pd.Series:
    timestamps = pd.to_datetime(series)
    if aggregation == "daily":
        return timestamps.dt.floor("D")
    if aggregation == "weekly":
        return timestamps.dt.to_period("W-SUN").dt.start_time
    if aggregation == "monthly":
        return timestamps.dt.to_period("M").dt.start_time
    raise ValueError(f"Unsupported aggregation period: {aggregation}")


def period_frequency(aggregation: str) -> str:
    return {"daily": "D", "weekly": "W-MON", "monthly": "MS"}[aggregation]


def validate_inputs(
    users: pd.DataFrame,
    transactions: pd.DataFrame,
    budgets: pd.DataFrame,
    minimum_age: int,
    maximum_age: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    user_required = {"user_id", "age", "is_synthetic"}
    transaction_required = {
        "transaction_id",
        "user_id",
        "transaction_timestamp",
        "amount",
        "currency",
        "category",
        "transaction_type",
        "is_recurring",
        "is_synthetic",
    }
    budget_required = {"user_id", "period_start", "period_end", "category", "budget_amount"}
    for label, frame, required in (
        ("users", users, user_required),
        ("transactions", transactions, transaction_required),
        ("budgets", budgets, budget_required),
    ):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{label} is missing required columns: {sorted(missing)}")
    valid_users = users[users["age"].between(minimum_age, maximum_age, inclusive="both")].copy()
    if valid_users.empty:
        raise ValueError("No users remain after the configured young-adult filter")
    user_ids = set(valid_users["user_id"].astype(str))
    filtered_transactions = transactions[
        transactions["user_id"].astype(str).isin(user_ids)
    ].copy()
    filtered_budgets = budgets[budgets["user_id"].astype(str).isin(user_ids)].copy()
    filtered_transactions["transaction_timestamp"] = pd.to_datetime(
        filtered_transactions["transaction_timestamp"], errors="coerce"
    )
    filtered_transactions["amount"] = pd.to_numeric(
        filtered_transactions["amount"], errors="coerce"
    )
    filtered_transactions = filtered_transactions.dropna(
        subset=["transaction_timestamp", "amount"]
    )
    filtered_transactions = filtered_transactions[filtered_transactions["amount"] > 0]
    currencies = set(filtered_transactions["currency"].dropna().astype(str).str.upper())
    if currencies != {"KES"}:
        raise ValueError(
            f"Model-ready young-adult data must use a single KES currency; found {sorted(currencies)}"
        )
    return valid_users, filtered_transactions, filtered_budgets


def aggregate_transactions(
    users: pd.DataFrame,
    transactions: pd.DataFrame,
    budgets: pd.DataFrame,
    aggregation: str,
) -> tuple[pd.DataFrame, list[str]]:
    working = transactions.copy()
    working["period_start"] = period_start(working["transaction_timestamp"], aggregation)
    expense = working[working["transaction_type"].astype(str).str.lower() == "expense"].copy()
    income = working[working["transaction_type"].astype(str).str.lower() == "income"].copy()
    if expense.empty:
        raise ValueError("No expense transactions are available for spending forecasting")

    category_names = sorted(expense["category"].dropna().astype(str).unique())
    category_columns = [f"category_{slug(category)}" for category in category_names]
    category_map = dict(zip(category_names, category_columns))
    expense["category_feature"] = expense["category"].map(category_map)

    base = (
        expense.groupby(["user_id", "period_start"])
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
    category = (
        expense.pivot_table(
            index=["user_id", "period_start"],
            columns="category_feature",
            values="amount",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    income_agg = (
        income.groupby(["user_id", "period_start"])["amount"]
        .sum()
        .rename("income")
        .reset_index()
    )

    minimum = working["period_start"].min()
    maximum = working["period_start"].max()
    periods = pd.date_range(minimum, maximum, freq=period_frequency(aggregation))
    grid = pd.MultiIndex.from_product(
        [users["user_id"].astype(str).sort_values().unique(), periods],
        names=["user_id", "period_start"],
    ).to_frame(index=False)
    aggregated = (
        grid.merge(base, how="left", on=["user_id", "period_start"])
        .merge(category, how="left", on=["user_id", "period_start"])
        .merge(income_agg, how="left", on=["user_id", "period_start"])
    )
    numeric_fill = [
        "total_spending",
        "transaction_count",
        "average_transaction_amount",
        "recurring_expenses",
        "income",
        *category_columns,
    ]
    for column in numeric_fill:
        if column not in aggregated:
            aggregated[column] = 0.0
    aggregated[numeric_fill] = aggregated[numeric_fill].fillna(0.0)

    budget_work = budgets.copy()
    budget_work["period_start"] = pd.to_datetime(budget_work["period_start"])
    budget_work["budget_month"] = budget_work["period_start"].dt.to_period("M").astype(str)
    monthly_budgets = (
        budget_work.groupby(["user_id", "budget_month"])["budget_amount"]
        .sum()
        .rename("monthly_budget")
        .reset_index()
    )
    aggregated["budget_month"] = aggregated["period_start"].dt.to_period("M").astype(str)
    aggregated = aggregated.merge(
        monthly_budgets, how="left", on=["user_id", "budget_month"]
    )
    aggregated["monthly_budget"] = aggregated["monthly_budget"].fillna(0.0)
    if aggregation == "daily":
        scale = 1.0 / aggregated["period_start"].dt.days_in_month
    elif aggregation == "weekly":
        scale = 7.0 / aggregated["period_start"].dt.days_in_month
    else:
        scale = 1.0
    aggregated["budget_amount"] = aggregated["monthly_budget"] * scale
    aggregated["budget_difference"] = (
        aggregated["budget_amount"] - aggregated["total_spending"]
    )

    aggregated = aggregated.sort_values(["user_id", "period_start"]).reset_index(drop=True)
    grouped = aggregated.groupby("user_id", group_keys=False)
    aggregated["previous_period_spending"] = grouped["total_spending"].shift(1)
    aggregated["rolling_average_4"] = grouped["total_spending"].transform(
        lambda values: values.shift(1).rolling(4, min_periods=1).mean()
    )
    previous = aggregated["previous_period_spending"]
    aggregated["spending_growth_rate"] = np.where(
        previous > 0,
        (aggregated["total_spending"] - previous) / previous,
        0.0,
    )
    aggregated[
        ["previous_period_spending", "rolling_average_4", "spending_growth_rate"]
    ] = aggregated[
        ["previous_period_spending", "rolling_average_4", "spending_growth_rate"]
    ].fillna(0.0)
    feature_names = [
        "total_spending",
        *category_columns,
        "transaction_count",
        "average_transaction_amount",
        "income",
        "recurring_expenses",
        "budget_difference",
        "previous_period_spending",
        "rolling_average_4",
        "spending_growth_rate",
    ]
    return aggregated, feature_names


def build_sequences(
    aggregated: pd.DataFrame,
    feature_names: list[str],
    lookback: int,
    forecast_horizon: int,
) -> dict[str, np.ndarray]:
    x_values: list[np.ndarray] = []
    y_values: list[float] = []
    user_ids: list[str] = []
    input_end_dates: list[str] = []
    target_dates: list[str] = []
    for user_id, group in aggregated.groupby("user_id", sort=True):
        group = group.sort_values("period_start").reset_index(drop=True)
        features = group[feature_names].to_numpy(dtype=np.float64)
        targets = group["total_spending"].to_numpy(dtype=np.float64)
        dates = pd.to_datetime(group["period_start"])
        for input_end in range(lookback - 1, len(group) - forecast_horizon):
            target_index = input_end + forecast_horizon
            x_values.append(features[input_end - lookback + 1 : input_end + 1])
            y_values.append(float(targets[target_index]))
            user_ids.append(str(user_id))
            input_end_dates.append(dates.iloc[input_end].isoformat())
            target_dates.append(dates.iloc[target_index].isoformat())
    if not x_values:
        raise ValueError(
            f"No LSTM sequences could be built with lookback={lookback} and "
            f"horizon={forecast_horizon}"
        )
    return {
        "X": np.stack(x_values),
        "y_raw": np.asarray(y_values, dtype=np.float64),
        "user_id": np.asarray(user_ids),
        "input_end_timestamp": np.asarray(input_end_dates),
        "target_timestamp": np.asarray(target_dates),
    }


def split_and_scale_sequences(
    sequences: dict[str, np.ndarray],
) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, Any]]:
    target_dates = pd.Series(pd.to_datetime(sequences["target_timestamp"]))
    train_end, validation_end = chronological_boundaries(target_dates)
    masks = {
        "train": (target_dates <= train_end).to_numpy(),
        "validation": ((target_dates > train_end) & (target_dates <= validation_end)).to_numpy(),
        "test": (target_dates > validation_end).to_numpy(),
    }
    if any(not mask.any() for mask in masks.values()):
        raise ValueError(
            f"Chronological split produced an empty partition: "
            f"{ {name: int(mask.sum()) for name, mask in masks.items()} }"
        )

    train_x = sequences["X"][masks["train"]]
    feature_min = train_x.reshape(-1, train_x.shape[-1]).min(axis=0)
    feature_max = train_x.reshape(-1, train_x.shape[-1]).max(axis=0)
    feature_scale = np.where(feature_max > feature_min, feature_max - feature_min, 1.0)
    train_y = sequences["y_raw"][masks["train"]]
    target_min = float(train_y.min())
    target_max = float(train_y.max())
    target_scale = target_max - target_min if target_max > target_min else 1.0

    output: dict[str, dict[str, np.ndarray]] = {}
    for name, mask in masks.items():
        x_raw = sequences["X"][mask]
        y_raw = sequences["y_raw"][mask]
        output[name] = {
            "X": ((x_raw - feature_min) / feature_scale).astype(np.float32),
            "y": ((y_raw - target_min) / target_scale).astype(np.float32),
            "y_raw": y_raw.astype(np.float32),
            "user_id": sequences["user_id"][mask],
            "input_end_timestamp": sequences["input_end_timestamp"][mask],
            "target_timestamp": sequences["target_timestamp"][mask],
        }
    scaler = {
        "feature_scaler": {
            "type": "min_max",
            "fit_partition": "training_only",
            "minimum": feature_min.tolist(),
            "maximum": feature_max.tolist(),
            "scale": feature_scale.tolist(),
        },
        "target_scaler": {
            "type": "min_max",
            "fit_partition": "training_only",
            "minimum": target_min,
            "maximum": target_max,
            "scale": target_scale,
        },
        "split_boundaries": {
            "training_end": train_end.isoformat(),
            "validation_end": validation_end.isoformat(),
        },
    }
    return output, scaler


def save_lstm_outputs(
    root: Path,
    splits: dict[str, dict[str, np.ndarray]],
    metadata: dict[str, Any],
) -> None:
    output_dir = root / "data" / "model_ready"
    filename_map = {
        "train": "lstm_train.npz",
        "validation": "lstm_validation.npz",
        "test": "lstm_test.npz",
    }
    for split_name, payload in splits.items():
        np.savez_compressed(output_dir / filename_map[split_name], **payload)
    write_json(metadata, output_dir / "lstm_metadata.json")
    index_sample = pd.concat(
        [
            pd.DataFrame(
                {
                    "split": split_name,
                    "user_id": payload["user_id"],
                    "input_end_timestamp": payload["input_end_timestamp"],
                    "target_timestamp": payload["target_timestamp"],
                    "target_spending_raw": payload["y_raw"],
                }
            ).head(100)
            for split_name, payload in splits.items()
        ],
        ignore_index=True,
    )
    index_sample.to_csv(output_dir / "lstm_sequence_index_sample.csv", index=False)


def build_linear_baseline(
    feature_names: list[str],
    raw_sequences: dict[str, np.ndarray],
    splits: dict[str, dict[str, np.ndarray]],
    root: Path,
) -> dict[str, int]:
    lookup: dict[tuple[str, str], int] = {
        (str(user), str(timestamp)): index
        for index, (user, timestamp) in enumerate(
            zip(raw_sequences["user_id"], raw_sequences["target_timestamp"])
        )
    }
    counts: dict[str, int] = {}
    for split_name, split in splits.items():
        rows: list[dict[str, Any]] = []
        for user_id, input_end, target_timestamp in zip(
            split["user_id"],
            split["input_end_timestamp"],
            split["target_timestamp"],
        ):
            index = lookup[(str(user_id), str(target_timestamp))]
            x = raw_sequences["X"][index]
            record: dict[str, Any] = {
                "user_id": str(user_id),
                "input_end_timestamp": pd.Timestamp(str(input_end)),
                "target_timestamp": pd.Timestamp(str(target_timestamp)),
                "target_total_spending": float(raw_sequences["y_raw"][index]),
            }
            for lag_index in range(x.shape[0]):
                lag = x.shape[0] - lag_index
                for feature_index, feature in enumerate(feature_names):
                    record[f"lag_{lag}_{feature}"] = float(x[lag_index, feature_index])
            rows.append(record)
        frame = pd.DataFrame(rows)
        path = (
            root
            / "data"
            / "model_ready"
            / f"linear_regression_{split_name}.parquet"
        )
        write_parquet(frame, path)
        write_csv_sample(
            frame,
            root / "data" / "model_ready" / f"linear_regression_{split_name}_sample.csv",
        )
        counts[split_name] = len(frame)
    return counts


def rolling_past_features(group: pd.DataFrame) -> pd.DataFrame:
    """Compute strictly past-only transaction features for one user."""
    ordered = group.sort_values("transaction_timestamp").copy()
    times = pd.to_datetime(ordered["transaction_timestamp"]).to_numpy()
    amounts = ordered["amount"].to_numpy(dtype=float)
    count_7 = np.zeros(len(ordered), dtype=float)
    sum_7 = np.zeros(len(ordered), dtype=float)
    sum_previous_28 = np.zeros(len(ordered), dtype=float)
    left_7 = 0
    left_35 = 0
    running_7 = 0.0
    running_35 = 0.0
    queue_7: deque[tuple[np.datetime64, float]] = deque()
    queue_35: deque[tuple[np.datetime64, float]] = deque()
    for index, (timestamp, amount) in enumerate(zip(times, amounts)):
        cutoff_7 = timestamp - np.timedelta64(7, "D")
        cutoff_35 = timestamp - np.timedelta64(35, "D")
        while queue_7 and queue_7[0][0] < cutoff_7:
            running_7 -= queue_7.popleft()[1]
            left_7 += 1
        while queue_35 and queue_35[0][0] < cutoff_35:
            running_35 -= queue_35.popleft()[1]
            left_35 += 1
        count_7[index] = len(queue_7)
        sum_7[index] = running_7
        sum_previous_28[index] = max(0.0, running_35 - running_7)
        queue_7.append((timestamp, amount))
        queue_35.append((timestamp, amount))
        running_7 += amount
        running_35 += amount
    ordered["transaction_count_last_7d"] = count_7
    ordered["recent_7d_spending"] = sum_7
    ordered["previous_28d_spending"] = sum_previous_28
    comparable_week = sum_previous_28 / 4.0
    recent_change = np.zeros(len(ordered), dtype=float)
    np.divide(
        sum_7,
        comparable_week,
        out=recent_change,
        where=comparable_week > 0,
    )
    recent_change[comparable_week > 0] -= 1.0
    ordered["recent_spending_change"] = recent_change
    return ordered


def build_isolation_forest_data(
    transactions: pd.DataFrame,
    anomaly_labels: pd.DataFrame,
    root: Path,
) -> dict[str, int]:
    expense = transactions[
        transactions["transaction_type"].astype(str).str.lower() == "expense"
    ].copy()
    expense = expense.sort_values(["user_id", "transaction_timestamp", "transaction_id"])
    expense["time_since_previous_hours"] = (
        expense.groupby("user_id")["transaction_timestamp"]
        .diff()
        .dt.total_seconds()
        .div(3600)
    )
    expense["historical_average_amount"] = expense.groupby("user_id")["amount"].transform(
        lambda values: values.shift(1).expanding(min_periods=1).mean()
    )
    expense["deviation_from_historical_average"] = np.where(
        expense["historical_average_amount"] > 0,
        expense["amount"] / expense["historical_average_amount"] - 1.0,
        0.0,
    )
    expense["past_user_count"] = expense.groupby("user_id").cumcount()
    expense["past_category_count"] = expense.groupby(["user_id", "category"]).cumcount()
    expense["category_proportion"] = np.where(
        expense["past_user_count"] > 0,
        expense["past_category_count"] / expense["past_user_count"],
        0.0,
    )
    expense = pd.concat(
        [rolling_past_features(group) for _, group in expense.groupby("user_id", sort=False)],
        ignore_index=True,
    )
    expense["category_code"] = pd.Categorical(expense["category"]).codes
    expense["hour_of_day"] = expense["transaction_timestamp"].dt.hour
    expense["is_weekend"] = expense["transaction_timestamp"].dt.dayofweek.ge(5).astype(int)
    feature_names = [
        "amount",
        "category_code",
        "transaction_count_last_7d",
        "time_since_previous_hours",
        "deviation_from_historical_average",
        "recent_spending_change",
        "category_proportion",
        "is_recurring",
        "hour_of_day",
        "is_weekend",
    ]
    expense[feature_names] = (
        expense[feature_names]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(
            {
                "time_since_previous_hours": 0.0,
                "historical_average_amount": 0.0,
            }
        )
        .fillna(0.0)
    )
    split_date = pd.Series(
        expense["transaction_timestamp"].sort_values().unique()
    ).quantile(0.70, interpolation="nearest")
    train = expense[expense["transaction_timestamp"] <= split_date].copy()
    test = expense[expense["transaction_timestamp"] > split_date].copy()
    columns = [
        "transaction_id",
        "user_id",
        "transaction_timestamp",
        "category",
        *feature_names,
    ]
    train = train[columns]
    test = test[columns]
    labels = test[["transaction_id", "user_id", "transaction_timestamp"]].merge(
        anomaly_labels[
            ["transaction_id", "anomaly_type", "is_anomaly", "label_source", "explanation"]
        ],
        how="left",
        on="transaction_id",
    )
    labels["is_anomaly"] = labels["is_anomaly"].fillna(False).astype(bool)
    labels["anomaly_type"] = labels["anomaly_type"].fillna("normal")
    labels["label_source"] = labels["label_source"].fillna("synthetic_unlabelled_normal")
    labels["explanation"] = labels["explanation"].fillna(
        "No controlled anomaly scenario was assigned."
    )
    output_dir = root / "data" / "model_ready"
    write_parquet(train, output_dir / "isolation_forest_train.parquet")
    write_parquet(test, output_dir / "isolation_forest_test.parquet")
    write_parquet(labels, output_dir / "isolation_forest_labels.parquet")
    write_csv_sample(train, output_dir / "isolation_forest_train_sample.csv")
    write_csv_sample(test, output_dir / "isolation_forest_test_sample.csv")
    write_csv_sample(labels, output_dir / "isolation_forest_labels_sample.csv")
    return {"train": len(train), "test": len(test), "labelled_anomalies": int(labels["is_anomaly"].sum())}


def recommendation_cases() -> pd.DataFrame:
    records = [
        {
            "case_id": "REC001",
            "forecasted_spending": 18000,
            "current_budget": 15000,
            "historical_average": 12500,
            "category_increase": 0.10,
            "detected_unusual_spending": False,
            "period_income": 50000,
            "period_expenses": 18000,
            "expected_recommendation_category": "budget_risk",
        },
        {
            "case_id": "REC002",
            "forecasted_spending": 12000,
            "current_budget": 15000,
            "historical_average": 11000,
            "category_increase": 0.42,
            "detected_unusual_spending": False,
            "period_income": 45000,
            "period_expenses": 12000,
            "expected_recommendation_category": "category_overspending",
        },
        {
            "case_id": "REC003",
            "forecasted_spending": 11000,
            "current_budget": 15000,
            "historical_average": 10500,
            "category_increase": 0.08,
            "detected_unusual_spending": True,
            "period_income": 42000,
            "period_expenses": 11000,
            "expected_recommendation_category": "unusual_spending_alert",
        },
        {
            "case_id": "REC004",
            "forecasted_spending": 15500,
            "current_budget": 18000,
            "historical_average": 12000,
            "category_increase": 0.12,
            "detected_unusual_spending": False,
            "period_income": 48000,
            "period_expenses": 15500,
            "expected_recommendation_category": "spending_increase",
        },
        {
            "case_id": "REC005",
            "forecasted_spending": 14000,
            "current_budget": 16000,
            "historical_average": 13000,
            "category_increase": 0.05,
            "detected_unusual_spending": False,
            "period_income": 12000,
            "period_expenses": 14000,
            "expected_recommendation_category": "income_expense_warning",
        },
        {
            "case_id": "REC006",
            "forecasted_spending": 11000,
            "current_budget": 16000,
            "historical_average": 10800,
            "category_increase": 0.05,
            "detected_unusual_spending": False,
            "period_income": 40000,
            "period_expenses": 11000,
            "expected_recommendation_category": "on_track",
        },
    ]
    return pd.DataFrame(records)


def prepare_model_data(root: Path, mode: str, config: dict[str, Any]) -> dict[str, Any]:
    settings = mode_config(config, mode)
    synthetic_dir = root / "data" / "synthetic"
    users = pd.read_parquet(synthetic_dir / "users.parquet")
    transactions = pd.read_parquet(synthetic_dir / "transactions.parquet")
    budgets = pd.read_parquet(synthetic_dir / "budgets.parquet")
    anomaly_labels = pd.read_parquet(synthetic_dir / "anomaly_labels.parquet")
    minimum_age, maximum_age = map(int, settings["selected_age_range"])
    users, transactions, budgets = validate_inputs(
        users, transactions, budgets, minimum_age, maximum_age
    )
    aggregation = str(settings["aggregation_period"])
    lookback = int(settings["lstm_lookback_window"])
    horizon = int(settings["forecast_horizon"])

    aggregated, feature_names = aggregate_transactions(
        users, transactions, budgets, aggregation
    )
    raw_sequences = build_sequences(aggregated, feature_names, lookback, horizon)
    splits, scaler = split_and_scale_sequences(raw_sequences)
    split_metadata: dict[str, Any] = {}
    for name, payload in splits.items():
        dates = pd.to_datetime(payload["target_timestamp"])
        split_metadata[name] = {
            "sequences": int(len(payload["y"])),
            "target_date_range": [dates.min().isoformat(), dates.max().isoformat()],
            "users": int(pd.Series(payload["user_id"]).nunique()),
        }
    metadata = {
        "project_title": config["project_title"],
        "mode": mode,
        "source_dataset": "synthetic_kenyan_young_adult_finance",
        "is_synthetic": True,
        "synthetic_data_disclaimer": (
            "These simulations are for development, controlled experimentation and system "
            "testing only. They are not evidence of actual young-adult spending behaviour in Kenya."
        ),
        "aggregation_period": aggregation,
        "forecast_horizon": horizon,
        "look_back_window": lookback,
        "feature_names": feature_names,
        "target_definition": (
            f"Total expense outflow in the next {horizon} {aggregation} period(s) for the same user"
        ),
        "scaler_information": scaler,
        "number_of_users": int(users["user_id"].nunique()),
        "number_of_sequences": int(len(raw_sequences["y_raw"])),
        "source_transaction_date_range": [
            transactions["transaction_timestamp"].min().isoformat(),
            transactions["transaction_timestamp"].max().isoformat(),
        ],
        "splits": split_metadata,
        "leakage_controls": [
            "All sequence targets occur after their input windows.",
            "Training/validation/test assignment uses global chronological target-date cutoffs.",
            "Feature and target scalers are fitted only on training sequences.",
            "Isolation Forest rolling features use prior transactions only.",
        ],
        "random_seed": int(settings["random_seed"]),
    }
    save_lstm_outputs(root, splits, metadata)
    linear_counts = build_linear_baseline(feature_names, raw_sequences, splits, root)
    isolation_counts = build_isolation_forest_data(transactions, anomaly_labels, root)
    cases = recommendation_cases()
    cases.to_csv(
        root / "data" / "model_ready" / "recommendation_test_cases.csv", index=False
    )
    write_csv_sample(aggregated, root / "data" / "model_ready" / "aggregated_periods_sample.csv")

    model_outputs = [
        "lstm_train.npz",
        "lstm_validation.npz",
        "lstm_test.npz",
        "lstm_metadata.json",
        "lstm_sequence_index_sample.csv",
        "aggregated_periods_sample.csv",
        "linear_regression_train.parquet",
        "linear_regression_validation.parquet",
        "linear_regression_test.parquet",
        "linear_regression_train_sample.csv",
        "linear_regression_validation_sample.csv",
        "linear_regression_test_sample.csv",
        "isolation_forest_train.parquet",
        "isolation_forest_test.parquet",
        "isolation_forest_labels.parquet",
        "isolation_forest_train_sample.csv",
        "isolation_forest_test_sample.csv",
        "isolation_forest_labels_sample.csv",
        "recommendation_test_cases.csv",
    ]
    append_lineage(
        root,
        [
            {
                "output_path": f"data/model_ready/{name}",
                "pipeline_stage": "model_data_preparation",
                "mode": mode,
                "source_paths": (
                    "data/synthetic/users.parquet; data/synthetic/transactions.parquet; "
                    "data/synthetic/budgets.parquet; data/synthetic/anomaly_labels.parquet"
                ),
                "processing_history": (
                    f"Age filtered to {minimum_age}-{maximum_age}; {aggregation} aggregation; "
                    f"lookback={lookback}; horizon={horizon}; chronological 70/15/15 forecasting "
                    "splits; training-only scaling; past-only behaviour features."
                ),
                "is_synthetic": True,
            }
            for name in model_outputs
        ],
    )
    return {
        "mode": mode,
        "aggregation": aggregation,
        "lookback": lookback,
        "forecast_horizon": horizon,
        "users": int(users["user_id"].nunique()),
        "transactions": len(transactions),
        "lstm_sequences": int(len(raw_sequences["y_raw"])),
        "lstm_split_counts": {
            name: int(len(payload["y"])) for name, payload in splits.items()
        },
        "linear_regression_rows": linear_counts,
        "isolation_forest_rows": isolation_counts,
        "recommendation_cases": len(cases),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)
    root = args.root.resolve() if args.root else repo_root_from_file(__file__)
    ensure_output_directories(root)
    config = load_config(root, args.config)
    summary = prepare_model_data(root, args.mode, config)
    LOGGER.info("Model data preparation complete: %s", summary)


if __name__ == "__main__":
    main()
