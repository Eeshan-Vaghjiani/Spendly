"""Run lightweight CPU smoke tests for all four project components.

The results validate file compatibility, shapes and executable training paths.
They are not final model-performance estimates.
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Any

try:
    # Import PyTorch before pandas/scikit-learn on Windows. Their native numerical
    # runtimes can otherwise be loaded first and prevent c10.dll initialization.
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    TORCH_IMPORT_ERROR: Exception | None = None
except (ImportError, OSError) as exc:  # pragma: no cover - environment validation
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    DataLoader = None  # type: ignore[assignment]
    TensorDataset = None  # type: ignore[assignment]
    TORCH_IMPORT_ERROR = exc

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

from pipeline_utils import (
    LOGGER,
    configure_logging,
    load_config,
    mode_config,
    repo_root_from_file,
    write_json,
)


def recommendation_category(row: pd.Series) -> str:
    """Transparent priority-ordered recommendation rules."""
    if bool(row["detected_unusual_spending"]):
        return "unusual_spending_alert"
    if float(row["forecasted_spending"]) > float(row["current_budget"]):
        return "budget_risk"
    if float(row["category_increase"]) >= 0.25:
        return "category_overspending"
    if float(row["forecasted_spending"]) > 1.15 * float(row["historical_average"]):
        return "spending_increase"
    if float(row["period_expenses"]) > float(row["period_income"]):
        return "income_expense_warning"
    return "on_track"


def smoke_lstm(
    root: Path,
    epochs: int,
    hidden_size: int,
    batch_size: int,
    seed: int,
) -> dict[str, Any]:
    if TORCH_IMPORT_ERROR is not None or torch is None:
        raise RuntimeError(
            "PyTorch is required for the CPU LSTM smoke test and its Windows DLLs "
            f"must initialize successfully. Original error: {TORCH_IMPORT_ERROR}"
        ) from TORCH_IMPORT_ERROR

    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    train = np.load(root / "data" / "model_ready" / "lstm_train.npz")
    validation = np.load(root / "data" / "model_ready" / "lstm_validation.npz")
    x_train = torch.tensor(train["X"], dtype=torch.float32)
    y_train = torch.tensor(train["y"], dtype=torch.float32).view(-1, 1)
    x_validation = torch.tensor(validation["X"], dtype=torch.float32)
    y_validation = torch.tensor(validation["y"], dtype=torch.float32).view(-1, 1)
    if x_train.ndim != 3 or y_train.ndim != 2:
        raise ValueError(f"Unexpected LSTM shapes: X={x_train.shape}, y={y_train.shape}")

    class TinyLSTM(nn.Module):  # type: ignore[misc,union-attr]
        def __init__(self, features: int, hidden: int) -> None:
            super().__init__()
            self.lstm = nn.LSTM(features, hidden, batch_first=True)
            self.output = nn.Linear(hidden, 1)

        def forward(self, values: Any) -> Any:
            sequence, _ = self.lstm(values)
            return self.output(sequence[:, -1, :])

    model = TinyLSTM(x_train.shape[-1], hidden_size)
    learning_rate = 0.01
    loss_function = nn.MSELoss()
    loader = DataLoader(
        TensorDataset(x_train, y_train),
        batch_size=min(batch_size, len(x_train)),
        shuffle=False,
    )
    started = time.perf_counter()
    epoch_losses: list[float] = []
    model.train()
    for _ in range(epochs):
        batch_losses = []
        for batch_x, batch_y in loader:
            model.zero_grad(set_to_none=True)
            prediction = model(batch_x)
            loss = loss_function(prediction, batch_y)
            loss.backward()
            # Manual SGD avoids optional torch.compile/Triton optimizer wrappers and
            # keeps this smoke path lightweight and CPU-only.
            with torch.no_grad():
                for parameter in model.parameters():
                    if parameter.grad is not None:
                        parameter.add_(parameter.grad, alpha=-learning_rate)
            batch_losses.append(float(loss.detach().cpu()))
        epoch_losses.append(float(np.mean(batch_losses)))
    elapsed = time.perf_counter() - started
    model.eval()
    with torch.no_grad():
        validation_prediction = model(x_validation)
        validation_loss = float(loss_function(validation_prediction, y_validation).cpu())
    if not np.isfinite(epoch_losses + [validation_loss]).all():
        raise ValueError("The LSTM smoke test produced non-finite losses")
    return {
        "framework": "PyTorch CPU",
        "epochs": epochs,
        "train_shape": list(x_train.shape),
        "validation_shape": list(x_validation.shape),
        "epoch_losses_scaled_space": epoch_losses,
        "validation_loss_scaled_space": validation_loss,
        "training_seconds": round(elapsed, 3),
        "status": "passed",
        "performance_note": "Sanity-only scaled loss; not a final performance claim.",
    }


def smoke_linear_regression(root: Path) -> dict[str, Any]:
    train = pd.read_parquet(
        root / "data" / "model_ready" / "linear_regression_train.parquet"
    )
    validation = pd.read_parquet(
        root / "data" / "model_ready" / "linear_regression_validation.parquet"
    )
    feature_columns = [
        column
        for column in train.columns
        if column.startswith("lag_") and pd.api.types.is_numeric_dtype(train[column])
    ]
    if not feature_columns:
        raise ValueError("No linear-regression lag features were found")
    model = LinearRegression()
    started = time.perf_counter()
    model.fit(train[feature_columns], train["target_total_spending"])
    elapsed = time.perf_counter() - started
    predictions = model.predict(validation[feature_columns])
    mse = float(mean_squared_error(validation["target_total_spending"], predictions))
    if not np.isfinite(mse):
        raise ValueError("Linear Regression smoke test produced a non-finite validation MSE")
    return {
        "train_rows": len(train),
        "validation_rows": len(validation),
        "feature_count": len(feature_columns),
        "validation_mse_raw_space": mse,
        "training_seconds": round(elapsed, 3),
        "status": "passed",
        "performance_note": "Sanity-only validation MSE; not a final performance claim.",
    }


def smoke_isolation_forest(
    root: Path,
    sample_rows: int,
    seed: int,
) -> dict[str, Any]:
    train = pd.read_parquet(
        root / "data" / "model_ready" / "isolation_forest_train.parquet"
    )
    test = pd.read_parquet(
        root / "data" / "model_ready" / "isolation_forest_test.parquet"
    )
    feature_columns = [
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
    sample = train.sample(n=min(sample_rows, len(train)), random_state=seed)
    model = IsolationForest(
        n_estimators=50,
        contamination=0.03,
        random_state=seed,
        n_jobs=-1,
    )
    started = time.perf_counter()
    model.fit(sample[feature_columns])
    elapsed = time.perf_counter() - started
    test_sample = test.head(min(2_000, len(test)))
    predictions = model.predict(test_sample[feature_columns])
    return {
        "fit_rows": len(sample),
        "test_rows_checked": len(test_sample),
        "feature_count": len(feature_columns),
        "flagged_in_checked_rows": int((predictions == -1).sum()),
        "training_seconds": round(elapsed, 3),
        "status": "passed",
        "performance_note": "Flag count is a pipeline sanity check, not final anomaly performance.",
    }


def smoke_rules(root: Path) -> dict[str, Any]:
    cases = pd.read_csv(
        root / "data" / "model_ready" / "recommendation_test_cases.csv"
    )
    cases["actual_recommendation_category"] = cases.apply(
        recommendation_category, axis=1
    )
    cases["passed"] = (
        cases["actual_recommendation_category"]
        == cases["expected_recommendation_category"]
    )
    if not cases["passed"].all():
        failed = cases.loc[
            ~cases["passed"],
            [
                "case_id",
                "expected_recommendation_category",
                "actual_recommendation_category",
            ],
        ]
        raise AssertionError(f"Rule-engine smoke test failures:\n{failed.to_string(index=False)}")
    return {
        "test_cases": len(cases),
        "passed_cases": int(cases["passed"].sum()),
        "status": "passed",
    }


def run_smoke_tests(root: Path, mode: str, config: dict[str, Any]) -> dict[str, Any]:
    settings = mode_config(config, mode)
    smoke = settings.get("smoke_test", config.get("smoke_test", {}))
    started = time.perf_counter()
    results = {
        "mode": mode,
        "purpose": (
            "Lightweight file/shape/training-path validation only; no final model "
            "performance is claimed."
        ),
        "lstm": smoke_lstm(
            root,
            epochs=int(smoke.get("lstm_epochs", 2)),
            hidden_size=int(smoke.get("lstm_hidden_size", 16)),
            batch_size=int(smoke.get("batch_size", 128)),
            seed=int(settings["random_seed"]),
        ),
        "linear_regression": smoke_linear_regression(root),
        "isolation_forest": smoke_isolation_forest(
            root,
            sample_rows=int(smoke.get("isolation_sample_rows", 10_000)),
            seed=int(settings["random_seed"]),
        ),
        "rule_based_engine": smoke_rules(root),
    }
    results["total_seconds"] = round(time.perf_counter() - started, 3)
    results["all_passed"] = all(
        component.get("status") == "passed"
        for component in (
            results["lstm"],
            results["linear_regression"],
            results["isolation_forest"],
            results["rule_based_engine"],
        )
    )
    write_json(results, root / "reports" / "smoke_test_results.json")
    return results


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
    config = load_config(root, args.config)
    results = run_smoke_tests(root, args.mode, config)
    LOGGER.info("Smoke tests complete in %.3fs: all_passed=%s", results["total_seconds"], results["all_passed"])


if __name__ == "__main__":
    main()
