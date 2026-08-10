"""Generate reproducible, explicitly synthetic young-adult personal-finance data.

The generator creates Kenyan-shilling simulations for development and controlled
experiments. It does not claim to estimate or reproduce actual Kenyan behaviour.
Anomaly labels are kept in a separate file and never added to transactions.
"""

from __future__ import annotations

import argparse
import math
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pipeline_utils import (
    LOGGER,
    append_lineage,
    configure_logging,
    ensure_output_directories,
    load_config,
    mode_config,
    repo_root_from_file,
    write_csv_sample,
    write_parquet,
)

CATEGORIES = [
    "Rent",
    "Transport",
    "Food",
    "Utilities",
    "Airtime and Data",
    "Entertainment",
    "Education",
    "Subscriptions",
    "Healthcare",
    "Savings",
    "Irregular Expenses",
]
DISCRETIONARY_CATEGORIES = [
    "Transport",
    "Food",
    "Airtime and Data",
    "Entertainment",
    "Education",
    "Healthcare",
    "Irregular Expenses",
]
PAYMENT_METHODS = ["M-Pesa", "Debit Card", "Cash", "Bank Transfer"]
MERCHANTS = {
    "Rent": ["Landlord transfer"],
    "Transport": ["Matatu", "Ride hailing", "Fuel station", "Boda boda"],
    "Food": ["Supermarket", "Market", "Cafe", "Restaurant"],
    "Utilities": ["Electricity", "Water", "Cooking gas"],
    "Airtime and Data": ["Mobile network"],
    "Entertainment": ["Cinema", "Streaming", "Social outing"],
    "Education": ["Bookshop", "Course provider", "Tuition"],
    "Subscriptions": ["Music subscription", "Video subscription", "Cloud service"],
    "Healthcare": ["Pharmacy", "Clinic"],
    "Savings": ["Savings transfer"],
    "Irregular Expenses": ["Household repair", "Family support", "Unexpected purchase"],
    "Income": ["Employer", "Client payment", "Family support"],
}


def user_profile(rng: np.random.Generator, index: int, start: date) -> dict[str, Any]:
    age = int(rng.integers(18, 36))
    if age <= 23:
        status = str(rng.choice(["student", "employed", "self_employed"], p=[0.55, 0.30, 0.15]))
    else:
        status = str(rng.choice(["student", "employed", "self_employed"], p=[0.10, 0.68, 0.22]))
    if status == "student":
        monthly_income = float(np.clip(rng.lognormal(math.log(22_000), 0.35), 8_000, 55_000))
    elif status == "self_employed":
        monthly_income = float(np.clip(rng.lognormal(math.log(65_000), 0.45), 20_000, 180_000))
    else:
        monthly_income = float(np.clip(rng.lognormal(math.log(72_000), 0.38), 28_000, 220_000))
    income_band = (
        "low" if monthly_income < 35_000 else "middle" if monthly_income < 100_000 else "higher"
    )
    birthday_this_year = start.replace(year=start.year) - timedelta(days=int(rng.integers(0, 365)))
    date_of_birth = birthday_this_year.replace(year=birthday_this_year.year - age)
    payday = int(rng.choice([25, 28, 30], p=[0.35, 0.45, 0.20]))
    return {
        "user_id": f"SYN{index:05d}",
        "age": age,
        "date_of_birth": date_of_birth,
        "income": round(monthly_income, 2),
        "income_band": income_band,
        "employment_status": status,
        "income_day": payday,
        "source_dataset": "synthetic_kenyan_young_adult_finance",
        "is_synthetic": True,
    }


def category_probabilities(status: str) -> np.ndarray:
    if status == "student":
        values = np.array([0.20, 0.34, 0.13, 0.11, 0.13, 0.04, 0.05])
    elif status == "self_employed":
        values = np.array([0.24, 0.37, 0.11, 0.10, 0.07, 0.05, 0.06])
    else:
        values = np.array([0.22, 0.40, 0.10, 0.13, 0.05, 0.04, 0.06])
    return values / values.sum()


def base_amount(category: str, monthly_income: float, rng: np.random.Generator) -> float:
    scales = {
        "Transport": max(70.0, monthly_income * 0.0022),
        "Food": max(100.0, monthly_income * 0.0030),
        "Airtime and Data": max(50.0, monthly_income * 0.0012),
        "Entertainment": max(120.0, monthly_income * 0.0040),
        "Education": max(180.0, monthly_income * 0.0060),
        "Healthcare": max(180.0, monthly_income * 0.0050),
        "Irregular Expenses": max(250.0, monthly_income * 0.0080),
    }
    return float(rng.gamma(shape=2.0, scale=scales[category] / 2.0))


def timestamp_for_day(day: date, rng: np.random.Generator, hour_low: int = 6) -> datetime:
    return datetime.combine(
        day,
        time(
            hour=int(rng.integers(hour_low, 23)),
            minute=int(rng.integers(0, 60)),
            second=int(rng.integers(0, 60)),
        ),
    )


def generate_synthetic_data(
    root: Path,
    mode: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    settings = mode_config(config, mode)
    seed = int(settings["random_seed"])
    rng = np.random.default_rng(seed)
    user_count = int(settings["synthetic_users"])
    days = int(settings["synthetic_days"])
    start = date(2024, 1, 1) if mode == "quick" else date(2023, 1, 1)
    end = start + timedelta(days=days - 1)

    users = [user_profile(rng, index + 1, start) for index in range(user_count)]
    transaction_records: list[dict[str, Any]] = []
    budget_records: list[dict[str, Any]] = []
    anomaly_records: list[dict[str, Any]] = []
    transaction_counter = 0
    anomaly_counter = 0

    def add_transaction(
        user_id: str,
        timestamp: datetime,
        amount: float,
        category: str,
        transaction_type: str,
        merchant: str,
        payment_method: str,
        is_recurring: bool,
        anomaly_type: str | None = None,
        explanation: str | None = None,
    ) -> str:
        nonlocal transaction_counter, anomaly_counter
        transaction_counter += 1
        transaction_id = f"SYNTRX{transaction_counter:09d}"
        transaction_records.append(
            {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "transaction_timestamp": pd.Timestamp(timestamp),
                "amount": round(max(1.0, float(amount)), 2),
                "currency": "KES",
                "category": category,
                "transaction_type": transaction_type,
                "merchant": merchant,
                "payment_method": payment_method,
                "is_recurring": bool(is_recurring),
                "source_dataset": "synthetic_kenyan_young_adult_finance",
                "is_synthetic": True,
            }
        )
        if anomaly_type:
            anomaly_counter += 1
            anomaly_records.append(
                {
                    "anomaly_id": f"SYNANOM{anomaly_counter:07d}",
                    "transaction_id": transaction_id,
                    "user_period_id": pd.NA,
                    "user_id": user_id,
                    "anomaly_type": anomaly_type,
                    "is_anomaly": True,
                    "label_source": "controlled_synthetic_scenario",
                    "explanation": explanation or anomaly_type.replace("_", " "),
                }
            )
        return transaction_id

    LOGGER.info(
        "Generating %s synthetic data: %d users over %d days (%s to %s)",
        mode,
        user_count,
        days,
        start,
        end,
    )
    for user_index, user in enumerate(users, start=1):
        user_id = user["user_id"]
        monthly_income = float(user["income"])
        status = str(user["employment_status"])
        rent = monthly_income * (0.16 if status == "student" else 0.23) * rng.uniform(0.85, 1.15)
        utilities = monthly_income * rng.uniform(0.035, 0.065)
        subscriptions = monthly_income * rng.uniform(0.008, 0.022)
        savings = monthly_income * rng.uniform(0.08, 0.18)
        base_daily_rate = 0.72 if status == "student" else 0.95
        gradual_growth = float(rng.uniform(0.00, 0.10))
        probabilities = category_probabilities(status)

        scenario_type: str | None = None
        scenario_day: date | None = None
        if rng.random() < 0.45:
            scenario_type = str(
                rng.choice(
                    [
                        "unusually_large_category_expenditure",
                        "sudden_transaction_frequency_increase",
                        "duplicate_like_spending",
                        "unexpected_recurring_expense_increase",
                        "unusually_high_weekend_spending",
                        "sudden_category_change",
                    ]
                )
            )
            scenario_offset = int(rng.integers(max(14, days // 5), days - 2))
            scenario_day = start + timedelta(days=scenario_offset)
            if scenario_type == "unusually_high_weekend_spending":
                while scenario_day.weekday() < 5 and scenario_day < end:
                    scenario_day += timedelta(days=1)

        month_starts = pd.date_range(start=start, end=end, freq="MS")
        for month_start in month_starts:
            next_month = month_start + pd.offsets.MonthBegin(1)
            period_end = min(pd.Timestamp(end), next_month - pd.Timedelta(days=1))
            category_budgets = {
                "Rent": rent,
                "Transport": monthly_income * 0.10,
                "Food": monthly_income * 0.18,
                "Utilities": utilities,
                "Airtime and Data": monthly_income * 0.035,
                "Entertainment": monthly_income * 0.06,
                "Education": monthly_income * (0.09 if status == "student" else 0.03),
                "Subscriptions": subscriptions,
                "Healthcare": monthly_income * 0.04,
                "Savings": savings,
                "Irregular Expenses": monthly_income * 0.05,
            }
            for category, value in category_budgets.items():
                budget_records.append(
                    {
                        "user_id": user_id,
                        "period_start": month_start,
                        "period_end": period_end,
                        "category": category,
                        "budget_amount": round(value, 2),
                        "source_dataset": "synthetic_kenyan_young_adult_finance",
                        "is_synthetic": True,
                    }
                )

        current = start
        while current <= end:
            progress = (current - start).days / max(1, days - 1)
            trend_multiplier = 1.0 + gradual_growth * progress
            weekend = current.weekday() >= 5
            days_to_payday = (int(user["income_day"]) - current.day) % 30
            payday_multiplier = 1.18 if days_to_payday <= 3 else 1.0

            if current.day == min(int(user["income_day"]), 28):
                missed_income = rng.random() < (0.05 if status == "self_employed" else 0.025)
                if not missed_income:
                    income_variation = rng.normal(1.0, 0.18 if status == "self_employed" else 0.04)
                    add_transaction(
                        user_id,
                        datetime.combine(current, time(8, 0)),
                        monthly_income * income_variation,
                        "Income",
                        "income",
                        "Client payment" if status == "self_employed" else "Employer",
                        "Bank Transfer",
                        True,
                    )

            if current.day == 2:
                recurring_multiplier = 1.0
                anomaly = None
                explanation = None
                if (
                    scenario_type == "unexpected_recurring_expense_increase"
                    and scenario_day
                    and current.year == scenario_day.year
                    and current.month == scenario_day.month
                ):
                    recurring_multiplier = 1.65
                    anomaly = scenario_type
                    explanation = "Controlled rent increase substantially above this user's recurring baseline."
                add_transaction(
                    user_id,
                    datetime.combine(current, time(9, 0)),
                    rent * recurring_multiplier,
                    "Rent",
                    "expense",
                    "Landlord transfer",
                    "M-Pesa",
                    True,
                    anomaly,
                    explanation,
                )
            if current.day == 10:
                add_transaction(
                    user_id,
                    datetime.combine(current, time(18, 0)),
                    utilities * rng.normal(1.0, 0.08),
                    "Utilities",
                    "expense",
                    str(rng.choice(MERCHANTS["Utilities"])),
                    "M-Pesa",
                    True,
                )
            if current.day == 15:
                add_transaction(
                    user_id,
                    datetime.combine(current, time(7, 0)),
                    subscriptions,
                    "Subscriptions",
                    "expense",
                    str(rng.choice(MERCHANTS["Subscriptions"])),
                    "Debit Card",
                    True,
                )
            if current.day == 26 and rng.random() < 0.88:
                add_transaction(
                    user_id,
                    datetime.combine(current, time(10, 0)),
                    savings,
                    "Savings",
                    "expense",
                    "Savings transfer",
                    "Bank Transfer",
                    True,
                )

            daily_rate = base_daily_rate * (1.25 if weekend else 1.0)
            daily_count = int(rng.poisson(daily_rate))
            for _ in range(daily_count):
                category = str(rng.choice(DISCRETIONARY_CATEGORIES, p=probabilities))
                amount = base_amount(category, monthly_income, rng)
                if weekend and category == "Entertainment":
                    amount *= 1.35
                if current.month in {11, 12}:
                    amount *= 1.12
                if current.month in {1, 8} and category == "Education":
                    amount *= 1.55
                amount *= trend_multiplier * payday_multiplier
                add_transaction(
                    user_id,
                    timestamp_for_day(current, rng),
                    amount,
                    category,
                    "expense",
                    str(rng.choice(MERCHANTS[category])),
                    str(rng.choice(PAYMENT_METHODS, p=[0.48, 0.20, 0.25, 0.07])),
                    False,
                )

            if rng.random() < 1 / max(120, days):
                add_transaction(
                    user_id,
                    timestamp_for_day(current, rng),
                    monthly_income * rng.uniform(0.18, 0.45),
                    "Irregular Expenses",
                    "expense",
                    str(rng.choice(MERCHANTS["Irregular Expenses"])),
                    "M-Pesa",
                    False,
                    "random_financial_shock",
                    "Controlled random financial shock for robustness testing.",
                )

            if scenario_day == current and scenario_type:
                if scenario_type == "unusually_large_category_expenditure":
                    category = str(rng.choice(["Food", "Entertainment", "Education"]))
                    add_transaction(
                        user_id,
                        timestamp_for_day(current, rng),
                        monthly_income * rng.uniform(0.45, 0.80),
                        category,
                        "expense",
                        str(rng.choice(MERCHANTS[category])),
                        "M-Pesa",
                        False,
                        scenario_type,
                        "Controlled category expenditure far above the user's expected scale.",
                    )
                elif scenario_type == "sudden_transaction_frequency_increase":
                    for event in range(7):
                        add_transaction(
                            user_id,
                            datetime.combine(current, time(12, min(59, event * 7))),
                            rng.uniform(80, 600),
                            "Food",
                            "expense",
                            "Cafe",
                            "M-Pesa",
                            False,
                            scenario_type,
                            "Controlled same-day burst of transactions.",
                        )
                elif scenario_type == "duplicate_like_spending":
                    duplicate_amount = round(rng.uniform(500, 2500), 2)
                    base_time = datetime.combine(current, time(14, 10))
                    for minute_offset in (0, 2):
                        add_transaction(
                            user_id,
                            base_time + timedelta(minutes=minute_offset),
                            duplicate_amount,
                            "Food",
                            "expense",
                            "Restaurant",
                            "M-Pesa",
                            False,
                            scenario_type,
                            "Controlled duplicate-like amount at the same merchant within minutes.",
                        )
                elif scenario_type == "unusually_high_weekend_spending":
                    for event in range(3):
                        add_transaction(
                            user_id,
                            datetime.combine(current, time(17 + event, 10)),
                            monthly_income * rng.uniform(0.08, 0.14),
                            "Entertainment",
                            "expense",
                            "Social outing",
                            "M-Pesa",
                            False,
                            scenario_type,
                            "Controlled weekend entertainment spending well above baseline.",
                        )
                elif scenario_type == "sudden_category_change":
                    add_transaction(
                        user_id,
                        timestamp_for_day(current, rng),
                        monthly_income * rng.uniform(0.18, 0.32),
                        "Education" if status != "student" else "Healthcare",
                        "expense",
                        "Course provider" if status != "student" else "Clinic",
                        "M-Pesa",
                        False,
                        scenario_type,
                        "Controlled expenditure in a category rarely used by this profile.",
                    )
                # recurring increase is injected on the month's rent date above

            current += timedelta(days=1)
        if user_index % 100 == 0 or user_index == user_count:
            LOGGER.info(
                "Generated %d/%d users (%d transactions)",
                user_index,
                user_count,
                len(transaction_records),
            )

    users_df = pd.DataFrame(users).sort_values("user_id").reset_index(drop=True)
    users_df["date_of_birth"] = pd.to_datetime(users_df["date_of_birth"])
    transactions_df = (
        pd.DataFrame(transaction_records)
        .sort_values(["user_id", "transaction_timestamp", "transaction_id"])
        .reset_index(drop=True)
    )
    budgets_df = (
        pd.DataFrame(budget_records)
        .sort_values(["user_id", "period_start", "category"])
        .reset_index(drop=True)
    )
    anomaly_columns = [
        "anomaly_id",
        "transaction_id",
        "user_period_id",
        "user_id",
        "anomaly_type",
        "is_anomaly",
        "label_source",
        "explanation",
    ]
    anomaly_df = pd.DataFrame(anomaly_records, columns=anomaly_columns)
    if not anomaly_df.empty:
        anomaly_df = anomaly_df.sort_values("anomaly_id").reset_index(drop=True)

    mode_dir = root / "data" / "synthetic" / mode
    active_dir = root / "data" / "synthetic"
    outputs = {
        "users": users_df,
        "transactions": transactions_df,
        "budgets": budgets_df,
        "anomaly_labels": anomaly_df,
    }
    for name, frame in outputs.items():
        write_parquet(frame, mode_dir / f"{name}.parquet")
        write_parquet(frame, active_dir / f"{name}.parquet")
        write_csv_sample(frame, mode_dir / f"{name}_sample.csv")
        write_csv_sample(frame, active_dir / f"{name}_sample.csv")

    append_lineage(
        root,
        [
            {
                "output_path": output_path,
                "pipeline_stage": "synthetic_generation",
                "mode": mode,
                "source_paths": "scripts/generate_synthetic_finance_data.py; config/data_config.yaml",
                "processing_history": (
                    f"Generated with NumPy seed {seed}; {user_count} simulated users; "
                    f"{days} simulated days; KES; controlled patterns and separate labels"
                    + (
                        "; first 250 rows exported for human-readable inspection."
                        if output_path.endswith("_sample.csv")
                        else "."
                    )
                ),
                "is_synthetic": True,
            }
            for name in outputs
            for output_path in (
                f"data/synthetic/{name}.parquet",
                f"data/synthetic/{name}_sample.csv",
                f"data/synthetic/{mode}/{name}.parquet",
                f"data/synthetic/{mode}/{name}_sample.csv",
            )
        ],
    )
    return {
        "mode": mode,
        "users": len(users_df),
        "transactions": len(transactions_df),
        "budgets": len(budgets_df),
        "anomaly_labels": len(anomaly_df),
        "date_range": [str(start), str(end)],
        "currency": "KES",
        "is_synthetic": True,
        "random_seed": seed,
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
    summary = generate_synthetic_data(root, args.mode, config)
    LOGGER.info("Synthetic data complete: %s", summary)


if __name__ == "__main__":
    main()
