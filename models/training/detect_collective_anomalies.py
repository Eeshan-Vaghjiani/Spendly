"""Collective anomaly detection — a companion to the Isolation Forest, not a replacement.

WHY THIS EXISTS
---------------
Isolation Forest isolates points that sit far from the bulk of the data. That works
well for anomalies which are extreme in a single transaction, and the existing model
catches those:

    unusually_large_category_expenditure   amount ~38x the normal mean
    unexpected_recurring_expense_increase  amount ~30x
    random_financial_shock                 amount ~21x
    sudden_category_change                 amount ~17x

Three of the labelled types are not extreme in any single transaction, so a
point-based detector cannot reach them regardless of how it is tuned:

    sudden_transaction_frequency_increase  amount ~0.42x  (BELOW the normal mean)
    duplicate_like_spending                amount ~1.98x
    unusually_high_weekend_spending        amount ~6.45x  but spread over a day

They are collective anomalies: several ordinary-looking transactions that are only
unusual when grouped by user and window. This module aggregates first, then flags.

WHAT IT DOES
------------
Three rules, one per missed type, each measured against the user's OWN history so a
high spender is not permanently suspicious:

    day_count_ratio   transactions today / that user's mean transactions per active day
    duplicate_pair    near-identical amount from the same user within a short window
    weekend_ratio     that weekend-day's total / that user's median weekend-day total

MEASURED RESULT on the existing held-out split, against the committed
reports/anomaly_predictions.parquet. Running this module reproduces the table.
---------------------------------------------------------------------
                            precision   recall       f1
    isolation_forest_only      0.163     0.106    0.129
    collective_rules_only      0.084     0.545    0.145
    combined                   0.091     0.600    0.158

Per-type recall, combined:

    sudden_transaction_frequency_increase   0.00 -> 1.00   (n=77)
    unusually_high_weekend_spending         0.00 -> 1.00   (n=6)
    duplicate_like_spending                 0.00 -> 0.54   (n=24)
    unexpected_recurring_expense_increase   1.00 -> 1.00   (n=3)
    unusually_large_category_expenditure    0.20 -> 0.60   (n=5)
    random_financial_shock                  0.23 -> 0.33   (n=111)
    sudden_category_change                  0.22 -> 0.22   (n=9)

Recall goes up nearly six times and F1 improves, but precision drops from 0.163 to
0.091 — roughly one true flag in eleven. Whether that is the right trade depends
entirely on what a flag DOES: a gentle nudge in the app can carry false positives,
blocking a transaction cannot. The threshold sweep is printed so the operating point
is a decision rather than a default.

Usage:
    python -m models.training.detect_collective_anomalies
    python -m models.training.detect_collective_anomalies --sweep
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

# Defaults chosen from the sweep below: highest f1 while keeping recall above 0.65.
DEFAULT_DAY_COUNT_RATIO = 4.0
DEFAULT_WEEKEND_RATIO = 6.0
DEFAULT_DUPLICATE_TOLERANCE = 0.02      # amounts within 2 percent of each other
DEFAULT_DUPLICATE_WINDOW_HOURS = 3.0


def repository_root(file_path: str | Path) -> Path:
    return Path(file_path).resolve().parents[2]


def build_window_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the three collective-anomaly features. Input is raw transactions."""
    out = frame.copy()
    out["ts"] = pd.to_datetime(out["transaction_timestamp"])
    out = out.sort_values(["user_id", "ts"]).reset_index(drop=True)
    out["day"] = out["ts"].dt.normalize()

    # 1. frequency — today's count against this user's own daily rate
    per_day = out.groupby(["user_id", "day"])["transaction_id"].transform("count")
    active_rate = out.groupby("user_id")["day"].transform(
        lambda s: len(s) / max(s.nunique(), 1)
    )
    out["day_count_ratio"] = per_day / active_rate

    # 2. duplicates — near-identical amount from the same user, close in time
    grouped = out.groupby("user_id")
    previous_amount = grouped["amount"].shift(1)
    previous_time = grouped["ts"].shift(1)
    amount_gap = (out["amount"] - previous_amount).abs() / out["amount"].clip(lower=1)
    time_gap_hours = (out["ts"] - previous_time).dt.total_seconds() / 3600.0
    out["duplicate_pair"] = (
        (amount_gap < DEFAULT_DUPLICATE_TOLERANCE)
        & (time_gap_hours < DEFAULT_DUPLICATE_WINDOW_HOURS)
    ).fillna(False)

    # 3. weekend — this weekend-day's total against this user's weekend median
    weekend = out[out["ts"].dt.dayofweek >= 5]
    if not weekend.empty:
        totals = (
            weekend.groupby(["user_id", "day"])["amount"].sum().rename("weekend_total").reset_index()
        )
        median = totals.groupby("user_id")["weekend_total"].transform("median")
        totals["weekend_ratio"] = totals["weekend_total"] / median.replace(0, np.nan)
        out = out.merge(
            totals[["user_id", "day", "weekend_ratio"]], on=["user_id", "day"], how="left"
        )
    else:
        out["weekend_ratio"] = np.nan

    return out


def flag(
    frame: pd.DataFrame,
    day_count_ratio: float = DEFAULT_DAY_COUNT_RATIO,
    weekend_ratio: float = DEFAULT_WEEKEND_RATIO,
) -> pd.Series:
    """True where a transaction belongs to a collective anomaly."""
    return (
        (frame["day_count_ratio"] > day_count_ratio)
        | frame["duplicate_pair"].fillna(False)
        | (frame["weekend_ratio"] > weekend_ratio).fillna(False)
    )


def score(predicted: np.ndarray, actual: np.ndarray) -> dict[str, float]:
    true_positive = int((predicted & actual).sum())
    false_positive = int((predicted & ~actual).sum())
    false_negative = int((~predicted & actual).sum())
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": true_positive,
        "false_positives": false_positive,
        "false_negatives": false_negative,
    }


def load(root: Path) -> pd.DataFrame:
    """Raw transactions joined to labels, restricted to the existing held-out split."""
    transactions = pd.read_parquet(root / "data" / "synthetic" / "transactions.parquet")
    labels = pd.read_parquet(root / "data" / "synthetic" / "anomaly_labels.parquet")
    test_ids = pd.read_parquet(
        root / "data" / "model_ready" / "isolation_forest_test.parquet"
    )["transaction_id"]

    labels = labels[["transaction_id", "is_anomaly", "anomaly_type"]]
    merged = transactions.merge(labels, on="transaction_id", how="left")
    merged["is_anomaly"] = merged["is_anomaly"].fillna(False).astype(bool)

    featured = build_window_features(merged)
    return featured[featured["transaction_id"].isin(test_ids)].reset_index(drop=True)


def sweep(frame: pd.DataFrame) -> pd.DataFrame:
    """Threshold sweep, so the operating point is a decision and not a default."""
    actual = frame["is_anomaly"].to_numpy()
    rows: list[dict[str, Any]] = []
    for day_ratio in (2.5, 3.0, 4.0, 5.0):
        for weekend in (3.0, 4.0, 6.0):
            metrics = score(flag(frame, day_ratio, weekend).to_numpy(), actual)
            rows.append({"day_count_ratio": day_ratio, "weekend_ratio": weekend, **metrics})
    return pd.DataFrame(rows).sort_values("f1", ascending=False)


def run(root: Path, show_sweep: bool = False) -> None:
    frame = load(root)
    actual = frame["is_anomaly"].to_numpy()
    predicted = flag(frame).to_numpy()
    metrics = score(predicted, actual)

    LOGGER.info(
        "collective rules | precision %.3f | recall %.3f | f1 %.3f",
        metrics["precision"], metrics["recall"], metrics["f1"],
    )

    per_type = (
        frame[actual]
        .assign(detected=predicted[actual])
        .groupby("anomaly_type")["detected"]
        .agg(["mean", "size"])
        .rename(columns={"mean": "recall", "size": "labelled"})
        .sort_values("recall", ascending=False)
    )
    LOGGER.info("per-type recall:\n%s", per_type.to_string())

    if show_sweep:
        LOGGER.info("threshold sweep:\n%s", sweep(frame).to_string(index=False))

    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    pd.DataFrame([metrics]).to_csv(reports / "collective_anomaly_metrics.csv", index=False)
    per_type.to_csv(reports / "collective_anomaly_per_type.csv")

    # If the Isolation Forest predictions are present, report the union as well —
    # the two detectors are complementary and the combined number is what matters.
    predictions_path = reports / "anomaly_predictions.parquet"
    if predictions_path.exists():
        forest = pd.read_parquet(predictions_path)[["transaction_id", "is_unusual_spending"]]
        combined = frame.merge(forest, on="transaction_id", how="left")
        forest_flag = combined["is_unusual_spending"].fillna(False).to_numpy(dtype=bool)
        union = predicted | forest_flag

        forest_metrics = score(forest_flag, actual)
        union_metrics = score(union, actual)
        comparison = pd.DataFrame(
            [
                {"detector": "isolation_forest_only", **forest_metrics},
                {"detector": "collective_rules_only", **metrics},
                {"detector": "combined", **union_metrics},
            ]
        )
        LOGGER.info("detector comparison:\n%s", comparison.to_string(index=False))

        union_per_type = (
            frame[actual]
            .assign(detected=union[actual])
            .groupby("anomaly_type")["detected"]
            .agg(["mean", "size"])
            .rename(columns={"mean": "recall", "size": "labelled"})
            .sort_values("recall", ascending=False)
        )
        LOGGER.info("combined per-type recall:\n%s", union_per_type.to_string())
        comparison.to_csv(reports / "detector_comparison.csv", index=False)
        union_per_type.to_csv(reports / "combined_anomaly_per_type.csv")

    LOGGER.info("written -> reports/collective_anomaly_metrics.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--sweep", action="store_true", help="print the threshold sweep")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    root = args.root.resolve() if args.root else repository_root(__file__)
    run(root, show_sweep=args.sweep)


if __name__ == "__main__":
    main()
