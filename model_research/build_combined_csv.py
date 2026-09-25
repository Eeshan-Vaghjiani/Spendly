"""Rebuild the intentionally raw, transaction-level university trial CSV."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "synthetic"
OUTPUT = Path(__file__).resolve().parent / "combined_finance_raw.csv"


def main() -> None:
    transactions = pd.read_parquet(SOURCE / "transactions.parquet")
    users = pd.read_parquet(SOURCE / "users.parquet").rename(
        columns={
            "age": "user_age",
            "date_of_birth": "user_date_of_birth",
            "income": "user_monthly_income",
            "income_band": "user_income_band",
            "employment_status": "user_employment_status",
            "income_day": "user_income_day",
            "source_dataset": "user_source_dataset",
            "is_synthetic": "user_is_synthetic",
        }
    )
    budgets = pd.read_parquet(SOURCE / "budgets.parquet").rename(
        columns={
            "period_start": "budget_period_start",
            "period_end": "budget_period_end",
            "source_dataset": "budget_source_dataset",
            "is_synthetic": "budget_is_synthetic",
        }
    )
    anomaly_labels = pd.read_parquet(SOURCE / "anomaly_labels.parquet").rename(
        columns={
            "user_id": "anomaly_user_id",
            "user_period_id": "anomaly_user_period_id",
            "explanation": "anomaly_explanation",
        }
    )

    transactions["budget_month"] = pd.to_datetime(
        transactions["transaction_timestamp"]
    ).dt.to_period("M").astype(str)
    budgets["budget_month"] = pd.to_datetime(
        budgets["budget_period_start"]
    ).dt.to_period("M").astype(str)

    combined = transactions.merge(users, on="user_id", how="left")
    combined = combined.merge(
        budgets,
        on=["user_id", "category", "budget_month"],
        how="left",
        validate="many_to_one",
    )
    combined = combined.merge(
        anomaly_labels,
        on="transaction_id",
        how="left",
        validate="one_to_one",
    )
    # Missing labels intentionally remain empty: this is the raw teaching copy.
    combined.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(combined):,} rows x {len(combined.columns)} columns to {OUTPUT}")


if __name__ == "__main__":
    main()
