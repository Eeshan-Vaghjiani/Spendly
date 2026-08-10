"""Validate model-ready files before any final model training.

Critical validation failures are written to the Markdown report and then cause
the process to exit with a non-zero status.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pipeline_utils import configure_logging, load_config, repo_root_from_file


LOGGER = logging.getLogger(__name__)

LSTM_SPLITS = ("train", "validation", "test")
ISOLATION_FEATURES = (
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
)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    details: str
    critical: bool = True


def _add(
    checks: list[Check],
    name: str,
    condition: bool,
    success: str,
    failure: str,
    *,
    critical: bool = True,
) -> None:
    checks.append(
        Check(
            name=name,
            passed=bool(condition),
            details=success if condition else failure,
            critical=critical,
        )
    )


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as payload:
        return {name: payload[name] for name in payload.files}


def _date_series(values: np.ndarray | pd.Series) -> pd.Series:
    return pd.Series(pd.to_datetime(values, errors="coerce"))


def _duplicates(user_ids: np.ndarray, targets: np.ndarray) -> int:
    frame = pd.DataFrame(
        {
            "user_id": user_ids.astype(str),
            "target_timestamp": pd.to_datetime(targets, errors="coerce"),
        }
    )
    return int(frame.duplicated(["user_id", "target_timestamp"]).sum())


def _ordered_within_user(user_ids: np.ndarray, targets: np.ndarray) -> bool:
    frame = pd.DataFrame(
        {
            "user_id": user_ids.astype(str),
            "target_timestamp": pd.to_datetime(targets, errors="coerce"),
        }
    )
    return all(
        group["target_timestamp"].is_monotonic_increasing
        for _, group in frame.groupby("user_id", sort=False)
    )


def _numeric_finite(frame: pd.DataFrame, columns: list[str]) -> bool:
    values = frame[columns].to_numpy(dtype=np.float64)
    return bool(np.isfinite(values).all())


def validate(root: Path, config: dict[str, Any]) -> tuple[list[Check], dict[str, Any]]:
    model_dir = root / "data" / "model_ready"
    metadata_path = model_dir / "lstm_metadata.json"
    required = [
        *(model_dir / f"lstm_{split}.npz" for split in LSTM_SPLITS),
        metadata_path,
        *(model_dir / f"linear_regression_{split}.parquet" for split in LSTM_SPLITS),
        model_dir / "isolation_forest_train.parquet",
        model_dir / "isolation_forest_test.parquet",
        model_dir / "isolation_forest_labels.parquet",
        model_dir / "recommendation_test_cases.csv",
    ]
    checks: list[Check] = []
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    _add(
        checks,
        "Required files exist",
        not missing,
        f"All {len(required)} required files are present.",
        f"Missing files: {', '.join(missing)}",
    )
    if missing:
        return checks, {"missing_files": missing}

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    feature_names = metadata.get("feature_names", [])
    expected_lookback = int(config["lstm_lookback_window"])
    expected_horizon = int(config["forecast_horizon"])
    _add(
        checks,
        "Feature schema",
        isinstance(feature_names, list)
        and len(feature_names) == 20
        and len(feature_names) == len(set(feature_names)),
        f"Metadata defines {len(feature_names)} unique ordered features.",
        "Feature names are missing, duplicated, or do not contain the expected 20 features.",
    )
    _add(
        checks,
        "Target definition",
        "next" in str(metadata.get("target_definition", "")).lower()
        and any(
            term in str(metadata.get("target_definition", "")).lower()
            for term in ("spending", "expense outflow", "expenditure")
        ),
        metadata.get("target_definition", ""),
        "Metadata does not define next-period spending as the target.",
    )
    _add(
        checks,
        "Look-back and horizon",
        metadata.get("look_back_window") == expected_lookback
        and metadata.get("forecast_horizon") == expected_horizon,
        f"Look-back={expected_lookback}; forecast horizon={expected_horizon}.",
        (
            f"Metadata look-back/horizon are {metadata.get('look_back_window')}/"
            f"{metadata.get('forecast_horizon')}, expected "
            f"{expected_lookback}/{expected_horizon}."
        ),
    )

    lstm: dict[str, dict[str, np.ndarray]] = {}
    required_arrays = {
        "X",
        "y",
        "y_raw",
        "user_id",
        "input_end_timestamp",
        "target_timestamp",
    }
    for split in LSTM_SPLITS:
        payload = _load_npz(model_dir / f"lstm_{split}.npz")
        lstm[split] = payload
        missing_arrays = required_arrays.difference(payload)
        _add(
            checks,
            f"LSTM {split} arrays",
            not missing_arrays,
            f"All required arrays are present in the {split} partition.",
            f"Missing arrays in {split}: {sorted(missing_arrays)}",
        )
        if missing_arrays:
            continue
        row_count = len(payload["y"])
        aligned = all(len(payload[name]) == row_count for name in required_arrays if name != "X")
        shape_ok = (
            payload["X"].ndim == 3
            and payload["X"].shape
            == (row_count, expected_lookback, len(feature_names))
        )
        _add(
            checks,
            f"LSTM {split} shapes",
            aligned and shape_ok and row_count > 0,
            f"X={payload['X'].shape}; y={payload['y'].shape}.",
            f"Unaligned or invalid arrays: X={payload['X'].shape}; rows={row_count}.",
        )
        finite = all(
            np.isfinite(payload[name].astype(np.float64)).all()
            for name in ("X", "y", "y_raw")
        )
        _add(
            checks,
            f"LSTM {split} missing/non-finite values",
            finite,
            "No missing or infinite numeric values.",
            "Missing or infinite numeric values were found.",
        )
        input_dates = _date_series(payload["input_end_timestamp"])
        target_dates = _date_series(payload["target_timestamp"])
        dates_valid = bool(input_dates.notna().all() and target_dates.notna().all())
        strictly_future = bool((target_dates > input_dates).all()) if dates_valid else False
        _add(
            checks,
            f"LSTM {split} future target",
            dates_valid and strictly_future,
            "Every target period occurs strictly after its input window.",
            "A missing date or target at/before its input window was detected.",
        )
        duplicate_count = _duplicates(payload["user_id"], payload["target_timestamp"])
        _add(
            checks,
            f"LSTM {split} duplicate user-periods",
            duplicate_count == 0,
            "No duplicate user/target-period records.",
            f"Found {duplicate_count} duplicate user/target-period records.",
        )
        _add(
            checks,
            f"LSTM {split} within-user chronology",
            _ordered_within_user(payload["user_id"], payload["target_timestamp"]),
            "Target periods are ordered within every user.",
            "At least one user's target periods are out of order.",
        )

    split_ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}
    for split, payload in lstm.items():
        dates = _date_series(payload["target_timestamp"])
        split_ranges[split] = (dates.min(), dates.max())
    separation_ok = (
        split_ranges["train"][1] < split_ranges["validation"][0]
        and split_ranges["validation"][1] < split_ranges["test"][0]
    )
    _add(
        checks,
        "Chronological split separation",
        separation_ok,
        (
            f"Train ends {split_ranges['train'][1].date()}, validation spans "
            f"{split_ranges['validation'][0].date()} to "
            f"{split_ranges['validation'][1].date()}, and test begins "
            f"{split_ranges['test'][0].date()}."
        ),
        f"Partition ranges overlap or are not chronological: {split_ranges}.",
    )

    scaler = metadata.get("scaler_information", {})
    feature_scaler = scaler.get("feature_scaler", {})
    target_scaler = scaler.get("target_scaler", {})
    feature_min = np.asarray(feature_scaler.get("minimum", []), dtype=np.float64)
    feature_scale = np.asarray(feature_scaler.get("scale", []), dtype=np.float64)
    scaler_schema_ok = (
        feature_scaler.get("fit_partition") == "training_only"
        and target_scaler.get("fit_partition") == "training_only"
        and len(feature_min) == len(feature_names)
        and len(feature_scale) == len(feature_names)
        and np.isfinite(feature_min).all()
        and np.isfinite(feature_scale).all()
        and (feature_scale > 0).all()
        and float(target_scaler.get("scale", 0)) > 0
    )
    _add(
        checks,
        "Training-only scaler metadata",
        scaler_schema_ok,
        "Feature and target min-max scalers are marked training-only with valid parameters.",
        "Scaler metadata are incomplete, invalid, or not marked training-only.",
    )
    if scaler_schema_ok:
        target_min = float(target_scaler["minimum"])
        target_scale = float(target_scaler["scale"])
        all_scaled_targets_match = all(
            np.allclose(
                payload["y"].astype(np.float64),
                (payload["y_raw"].astype(np.float64) - target_min) / target_scale,
                rtol=1e-5,
                atol=1e-5,
            )
            for payload in lstm.values()
        )
        _add(
            checks,
            "Stored target scaling",
            all_scaled_targets_match,
            "Every scaled target matches the training-fitted target scaler.",
            "At least one stored scaled target does not match scaler metadata.",
        )

    linear: dict[str, pd.DataFrame] = {}
    for split in LSTM_SPLITS:
        frame = pd.read_parquet(model_dir / f"linear_regression_{split}.parquet")
        linear[split] = frame
        lag_columns = [column for column in frame if column.startswith("lag_")]
        required_columns = {
            "user_id",
            "input_end_timestamp",
            "target_timestamp",
            "target_total_spending",
        }
        schema_ok = required_columns.issubset(frame.columns) and len(lag_columns) == (
            expected_lookback * len(feature_names)
        )
        _add(
            checks,
            f"Linear Regression {split} schema",
            schema_ok,
            f"{len(frame):,} rows and {len(lag_columns)} ordered lag features.",
            "Missing identifier/target columns or incorrect lag-feature count.",
        )
        if schema_ok:
            _add(
                checks,
                f"Linear Regression {split} missing/non-finite values",
                frame[list(required_columns)].notna().all().all()
                and _numeric_finite(
                    frame, lag_columns + ["target_total_spending"]
                ),
                "No missing or infinite feature/target values.",
                "Missing or infinite feature/target values were found.",
            )
            duplicate_count = int(
                frame.duplicated(["user_id", "target_timestamp"]).sum()
            )
            _add(
                checks,
                f"Linear Regression {split} duplicate user-periods",
                duplicate_count == 0,
                "No duplicate user/target-period records.",
                f"Found {duplicate_count} duplicate user/target-period records.",
            )

            lstm_index = pd.DataFrame(
                {
                    "user_id": lstm[split]["user_id"].astype(str),
                    "input_end_timestamp": pd.to_datetime(
                        lstm[split]["input_end_timestamp"]
                    ),
                    "target_timestamp": pd.to_datetime(
                        lstm[split]["target_timestamp"]
                    ),
                    "target_total_spending": lstm[split]["y_raw"].astype(
                        np.float64
                    ),
                }
            ).sort_values(["user_id", "target_timestamp"]).reset_index(drop=True)
            linear_index = (
                frame[
                    [
                        "user_id",
                        "input_end_timestamp",
                        "target_timestamp",
                        "target_total_spending",
                    ]
                ]
                .assign(user_id=lambda value: value["user_id"].astype(str))
                .sort_values(["user_id", "target_timestamp"])
                .reset_index(drop=True)
            )
            keys_match = lstm_index[
                ["user_id", "input_end_timestamp", "target_timestamp"]
            ].equals(
                linear_index[
                    ["user_id", "input_end_timestamp", "target_timestamp"]
                ]
            )
            targets_match = np.allclose(
                lstm_index["target_total_spending"],
                linear_index["target_total_spending"],
                rtol=1e-6,
                atol=1e-2,
            )
            _add(
                checks,
                f"LSTM/Linear Regression {split} target consistency",
                keys_match and targets_match,
                "User, input date, target date, and raw target match exactly.",
                "The forecasting models do not use identical records and targets.",
            )

    expected_users = int(metadata.get("number_of_users", 0))
    coverage = {
        split: len(set(payload["user_id"].astype(str)))
        for split, payload in lstm.items()
    }
    _add(
        checks,
        "Forecasting user coverage",
        expected_users > 0 and all(count == expected_users for count in coverage.values()),
        f"All partitions contain all {expected_users} users.",
        f"Expected {expected_users} users; observed {coverage}.",
    )

    isolation_train = pd.read_parquet(
        model_dir / "isolation_forest_train.parquet"
    )
    isolation_test = pd.read_parquet(model_dir / "isolation_forest_test.parquet")
    isolation_labels = pd.read_parquet(
        model_dir / "isolation_forest_labels.parquet"
    )
    isolation_schema_ok = all(
        column in isolation_train.columns and column in isolation_test.columns
        for column in ISOLATION_FEATURES
    )
    _add(
        checks,
        "Isolation Forest feature schema",
        isolation_schema_ok,
        f"Both partitions contain the expected {len(ISOLATION_FEATURES)} features.",
        "One or more expected Isolation Forest features are missing.",
    )
    if isolation_schema_ok:
        _add(
            checks,
            "Isolation Forest missing/non-finite values",
            _numeric_finite(isolation_train, list(ISOLATION_FEATURES))
            and _numeric_finite(isolation_test, list(ISOLATION_FEATURES)),
            "No missing or infinite model features.",
            "Missing or infinite Isolation Forest features were found.",
        )
    no_label_leakage = not any(
        column in isolation_train.columns
        for column in ("is_anomaly", "anomaly_type", "label_source", "explanation")
    )
    _add(
        checks,
        "Isolation Forest label leakage",
        no_label_leakage,
        "Anomaly labels are absent from the training feature table.",
        "An anomaly label or label-derived field is present in training data.",
    )
    anomaly_separation = (
        pd.to_datetime(isolation_train["transaction_timestamp"]).max()
        < pd.to_datetime(isolation_test["transaction_timestamp"]).min()
    )
    _add(
        checks,
        "Isolation Forest chronological separation",
        anomaly_separation,
        (
            f"Train ends {isolation_train['transaction_timestamp'].max()}; "
            f"test begins {isolation_test['transaction_timestamp'].min()}."
        ),
        "Isolation Forest train/test timestamps overlap.",
    )
    label_keys = isolation_labels[
        ["transaction_id", "user_id", "transaction_timestamp"]
    ].reset_index(drop=True)
    test_keys = isolation_test[
        ["transaction_id", "user_id", "transaction_timestamp"]
    ].reset_index(drop=True)
    _add(
        checks,
        "Isolation Forest label compatibility",
        len(isolation_labels) == len(isolation_test)
        and label_keys.equals(test_keys)
        and isolation_labels["is_anomaly"].notna().all(),
        (
            f"All {len(isolation_test):,} test rows have aligned evaluation "
            f"labels; {int(isolation_labels['is_anomaly'].sum()):,} are positive."
        ),
        "Test features and anomaly labels are not one-to-one and identically ordered.",
    )

    summary = {
        "feature_names": feature_names,
        "target_definition": metadata.get("target_definition"),
        "lookback": expected_lookback,
        "forecast_horizon": expected_horizon,
        "lstm_shapes": {
            split: list(payload["X"].shape) for split, payload in lstm.items()
        },
        "split_ranges": {
            split: [start.isoformat(), end.isoformat()]
            for split, (start, end) in split_ranges.items()
        },
        "user_coverage": coverage,
        "isolation_rows": {
            "train": len(isolation_train),
            "test": len(isolation_test),
            "positive_labels": int(isolation_labels["is_anomaly"].sum()),
        },
    }
    return checks, summary


def write_report(
    path: Path, checks: list[Check], summary: dict[str, Any]
) -> None:
    passed = sum(check.passed for check in checks)
    critical_failures = [
        check for check in checks if check.critical and not check.passed
    ]
    status = "PASSED" if not critical_failures else "FAILED"
    lines = [
        "# Model Data Validation",
        "",
        f"Overall status: **{status}**",
        "",
        f"Checks passed: **{passed}/{len(checks)}**",
        "",
        "Final model training is permitted only when this report passes.",
        "",
        "## Validation checks",
        "",
        "| Check | Result | Details |",
        "|---|---:|---|",
    ]
    for check in checks:
        result = "PASS" if check.passed else "FAIL"
        details = check.details.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {check.name} | {result} | {details} |")
    lines.extend(
        [
            "",
            "## Validated model contract",
            "",
            f"- Look-back window: {summary.get('lookback', 'unavailable')}",
            f"- Forecast horizon: {summary.get('forecast_horizon', 'unavailable')}",
            f"- Target: {summary.get('target_definition', 'unavailable')}",
            f"- Ordered feature count: {len(summary.get('feature_names', []))}",
            f"- User coverage: {summary.get('user_coverage', {})}",
            f"- LSTM shapes: {summary.get('lstm_shapes', {})}",
            f"- Chronological ranges: {summary.get('split_ranges', {})}",
            f"- Isolation Forest rows: {summary.get('isolation_rows', {})}",
            "",
            "## Leakage decision",
            "",
            (
                "No critical leakage or schema problem was detected."
                if not critical_failures
                else "Training is blocked by the critical failures listed above."
            ),
            "",
            "Synthetic data are used for controlled development only and are not "
            "evidence of real Kenyan young-adult spending behaviour.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)
    root = args.root.resolve() if args.root else repo_root_from_file(__file__)
    config = load_config(root, args.config)
    checks, summary = validate(root, config)
    report_path = root / "reports" / "model_data_validation.md"
    write_report(report_path, checks, summary)
    critical_failures = [
        check for check in checks if check.critical and not check.passed
    ]
    if critical_failures:
        details = "; ".join(
            f"{check.name}: {check.details}" for check in critical_failures
        )
        raise SystemExit(f"Critical model-data validation failed: {details}")
    LOGGER.info(
        "Model-data validation passed (%d/%d checks). Report: %s",
        sum(check.passed for check in checks),
        len(checks),
        report_path,
    )


if __name__ == "__main__":
    main()
