"""Train and compare the LSTM forecaster and forecasting baselines."""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import joblib
import matplotlib
import numpy as np
import pandas as pd
import tensorflow as tf
import yaml
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt


LOGGER = logging.getLogger(__name__)
MODEL_NAMES = (
    "lstm",
    "linear_regression",
    "naive_previous_period",
    "moving_average_4",
)


def repository_root(file_path: str | Path) -> Path:
    return Path(file_path).resolve().parents[2]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Configuration must be a mapping: {path}")
    return payload


def merged_mode_settings(config: dict[str, Any], mode: str) -> dict[str, Any]:
    settings = dict(config["forecasting"])
    mode_settings = settings.pop(mode, {})
    settings.pop("quick", None)
    settings.pop("full", None)
    settings.update(mode_settings)
    return settings


def configure_reproducibility(seed: int) -> list[str]:
    random.seed(seed)
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except (AttributeError, RuntimeError):
        LOGGER.warning("TensorFlow deterministic operations could not be enabled.")
    devices = tf.config.list_physical_devices("GPU")
    for device in devices:
        try:
            tf.config.experimental.set_memory_growth(device, True)
        except RuntimeError:
            LOGGER.warning("Could not enable GPU memory growth for %s.", device)
    return [device.name for device in devices]


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as payload:
        return {name: payload[name] for name in payload.files}


def build_lstm(
    input_shape: tuple[int, int],
    units: list[int],
    dense_units: int,
    dropout_rate: float,
    learning_rate: float,
) -> tf.keras.Model:
    if not units or any(int(value) <= 0 for value in units):
        raise ValueError("At least one positive LSTM layer size is required.")
    if not 0 <= dropout_rate < 1:
        raise ValueError("dropout_rate must be in [0, 1).")
    inputs = tf.keras.Input(shape=input_shape, name="weekly_history")
    values = inputs
    for index, unit_count in enumerate(units):
        values = tf.keras.layers.LSTM(
            int(unit_count),
            return_sequences=index < len(units) - 1,
            name=f"lstm_{index + 1}",
        )(values)
        if dropout_rate > 0:
            values = tf.keras.layers.Dropout(
                dropout_rate, name=f"dropout_{index + 1}"
            )(values)
    if dense_units > 0:
        values = tf.keras.layers.Dense(
            dense_units, activation="relu", name="dense_features"
        )(values)
    outputs = tf.keras.layers.Dense(1, name="scaled_spending")(values)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="spending_lstm")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="mse",
        metrics=[tf.keras.metrics.MeanAbsoluteError(name="mae")],
    )
    return model


def inverse_target(
    scaled_values: np.ndarray, scaler: dict[str, Any]
) -> np.ndarray:
    target = scaler["target_scaler"]
    return (
        np.asarray(scaled_values, dtype=np.float64).reshape(-1)
        * float(target["scale"])
        + float(target["minimum"])
    )


def safe_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
    *,
    model_name: str,
    training_seconds: float,
    inference_seconds: float,
) -> dict[str, Any]:
    actual = np.asarray(actual, dtype=np.float64).reshape(-1)
    predicted = np.asarray(predicted, dtype=np.float64).reshape(-1)
    if actual.shape != predicted.shape:
        raise ValueError(
            f"Metric arrays differ for {model_name}: "
            f"{actual.shape} versus {predicted.shape}"
        )
    nonzero = np.abs(actual) > 1e-8
    mape = (
        float(
            np.mean(
                np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])
            )
            * 100
        )
        if nonzero.any()
        else None
    )
    return {
        "model": model_name,
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mape_percent": mape,
        "r2": float(r2_score(actual, predicted)),
        "training_seconds": float(training_seconds),
        "inference_seconds": float(inference_seconds),
        "evaluated_rows": int(len(actual)),
        "nonzero_mape_rows": int(nonzero.sum()),
    }


def timed_prediction(function: Any) -> tuple[np.ndarray, float]:
    started = time.perf_counter()
    values = np.asarray(function(), dtype=np.float64).reshape(-1)
    return values, time.perf_counter() - started


def save_plots(
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    history: dict[str, list[float]],
    figures_dir: Path,
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    aggregated = (
        predictions.groupby(["model", "target_timestamp"], as_index=False)[
            ["actual_spending", "predicted_spending"]
        ]
        .mean()
        .sort_values("target_timestamp")
    )
    figure, axis = plt.subplots(figsize=(10, 5))
    actual = (
        aggregated[aggregated["model"] == "lstm"][
            ["target_timestamp", "actual_spending"]
        ]
        .drop_duplicates()
        .sort_values("target_timestamp")
    )
    axis.plot(
        actual["target_timestamp"],
        actual["actual_spending"],
        marker="o",
        linewidth=2,
        label="Actual",
    )
    for model_name in ("lstm", "linear_regression"):
        subset = aggregated[aggregated["model"] == model_name]
        axis.plot(
            subset["target_timestamp"],
            subset["predicted_spending"],
            marker="o",
            label=model_name.replace("_", " ").title(),
        )
    axis.set_title("Mean actual versus predicted weekly spending")
    axis.set_ylabel("KES")
    axis.legend()
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(figures_dir / "actual_vs_predicted_spending.png", dpi=160)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8, 5))
    axis.plot(history.get("loss", []), label="Training loss")
    axis.plot(history.get("val_loss", []), label="Validation loss")
    axis.set_title("LSTM training history")
    axis.set_xlabel("Epoch")
    axis.set_ylabel("Scaled MSE")
    axis.legend()
    figure.tight_layout()
    figure.savefig(figures_dir / "lstm_training_validation_loss.png", dpi=160)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(9, 5))
    for model_name in ("lstm", "linear_regression"):
        residuals = predictions.loc[
            predictions["model"] == model_name, "residual"
        ]
        axis.hist(
            residuals,
            bins=40,
            alpha=0.55,
            label=model_name.replace("_", " ").title(),
        )
    axis.set_title("Forecast residual distribution")
    axis.set_xlabel("Actual minus predicted spending (KES)")
    axis.legend()
    figure.tight_layout()
    figure.savefig(figures_dir / "forecast_residual_distribution.png", dpi=160)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(9, 5))
    positions = np.arange(len(metrics))
    width = 0.38
    axis.bar(positions - width / 2, metrics["mae"], width, label="MAE")
    axis.bar(positions + width / 2, metrics["rmse"], width, label="RMSE")
    axis.set_xticks(positions)
    axis.set_xticklabels(
        [value.replace("_", "\n") for value in metrics["model"]]
    )
    axis.set_ylabel("KES")
    axis.set_title("Forecasting baseline comparison")
    axis.legend()
    figure.tight_layout()
    figure.savefig(figures_dir / "forecasting_baseline_comparison.png", dpi=160)
    plt.close(figure)


def markdown_comparison(
    metrics: pd.DataFrame,
    metadata: dict[str, Any],
    history: dict[str, list[float]],
) -> str:
    ordered = metrics.sort_values("mae").reset_index(drop=True)
    lstm_mae = float(metrics.loc[metrics["model"] == "lstm", "mae"].iloc[0])
    competitor_mae = float(
        metrics.loc[metrics["model"] != "lstm", "mae"].min()
    )
    outcome = (
        "The LSTM achieved the lowest test MAE."
        if lstm_mae < competitor_mae
        else (
            "The LSTM did not achieve the lowest test MAE. It remains the main "
            "project model, but this controlled experiment does not justify "
            "claiming that its complexity improved forecast accuracy."
        )
    )
    lines = [
        "# Forecasting Model Comparison",
        "",
        f"Training date (UTC): {metadata['training_date_utc']}",
        "",
        "Evaluation uses the same 900 chronologically held-out weekly targets for "
        "the LSTM, Multiple Linear Regression, previous-period naive forecast, "
        "and four-period moving average.",
        "",
        "| Model | MAE (KES) | RMSE (KES) | MAPE (%) | R-squared | Train seconds | Inference seconds |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ordered.to_dict(orient="records"):
        mape = "n/a" if row["mape_percent"] is None else f"{row['mape_percent']:.3f}"
        lines.append(
            f"| {row['model']} | {row['mae']:.3f} | {row['rmse']:.3f} | "
            f"{mape} | {row['r2']:.4f} | {row['training_seconds']:.3f} | "
            f"{row['inference_seconds']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Result",
            "",
            outcome,
            "",
            f"The LSTM ran for {len(history.get('loss', []))} epoch(s); its best "
            "checkpoint was selected using validation loss and test data were not "
            "used for model selection.",
            "",
            "MAPE excludes actual values equal to zero. The metrics table records "
            "the number of non-zero rows included.",
            "",
            "## Limitations",
            "",
            "- All training and evaluation records are synthetic controlled data.",
            "- Metrics do not establish performance for real Kenyan young adults.",
            "- The quick dataset covers approximately 180 days, limiting seasonal "
            "evaluation.",
            "- Multiple records share the same three weekly test dates across "
            "users, so uncertainty across longer calendar periods is not measured.",
        ]
    )
    return "\n".join(lines) + "\n"


def train(
    root: Path,
    mode: str,
    data_config: dict[str, Any],
    model_config: dict[str, Any],
) -> dict[str, Any]:
    settings = merged_mode_settings(model_config, mode)
    seed = int(model_config.get("random_seed", data_config["random_seed"]))
    gpu_devices = configure_reproducibility(seed)
    version = str(model_config["model_version"])
    model_dir = root / "data" / "model_ready"
    artifact_dir = root / "artifacts" / "models" / "forecasting" / version
    report_dir = root / "reports"
    figures_dir = report_dir / "figures"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = model_dir / "lstm_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    train_data = load_npz(model_dir / "lstm_train.npz")
    validation_data = load_npz(model_dir / "lstm_validation.npz")
    test_data = load_npz(model_dir / "lstm_test.npz")
    scaler = metadata["scaler_information"]

    lstm_path = artifact_dir / "lstm.keras"
    model = build_lstm(
        (train_data["X"].shape[1], train_data["X"].shape[2]),
        [int(value) for value in settings["lstm_units"]],
        int(settings["dense_units"]),
        float(settings["dropout_rate"]),
        float(settings["learning_rate"]),
    )
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=int(settings["early_stopping_patience"]),
            min_delta=float(settings["minimum_delta"]),
            restore_best_weights=True,
            mode="min",
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=lstm_path,
            monitor="val_loss",
            save_best_only=True,
            save_weights_only=False,
            mode="min",
        ),
        tf.keras.callbacks.TerminateOnNaN(),
    ]
    training_started = time.perf_counter()
    fitted = model.fit(
        train_data["X"],
        train_data["y"],
        validation_data=(validation_data["X"], validation_data["y"]),
        epochs=int(settings["maximum_epochs"]),
        batch_size=int(settings["batch_size"]),
        shuffle=False,
        verbose=2,
        callbacks=callbacks,
    )
    lstm_training_seconds = time.perf_counter() - training_started
    model = tf.keras.models.load_model(lstm_path)
    scaled_prediction, lstm_inference_seconds = timed_prediction(
        lambda: model.predict(
            test_data["X"],
            batch_size=int(settings["batch_size"]),
            verbose=0,
        )
    )
    lstm_prediction = inverse_target(scaled_prediction, scaler)

    linear_train = pd.read_parquet(
        model_dir / "linear_regression_train.parquet"
    )
    linear_test = pd.read_parquet(
        model_dir / "linear_regression_test.parquet"
    )
    feature_order = [
        column for column in linear_train.columns if column.startswith("lag_")
    ]
    linear_model = LinearRegression()
    linear_started = time.perf_counter()
    linear_model.fit(
        linear_train[feature_order],
        linear_train["target_total_spending"],
    )
    linear_training_seconds = time.perf_counter() - linear_started
    linear_prediction, linear_inference_seconds = timed_prediction(
        lambda: linear_model.predict(linear_test[feature_order])
    )
    joblib.dump(linear_model, artifact_dir / "linear_regression.joblib")
    joblib.dump(scaler, artifact_dir / "scaler.joblib")

    naive_prediction, naive_inference_seconds = timed_prediction(
        lambda: linear_test["lag_1_total_spending"].to_numpy()
    )
    moving_columns = [
        f"lag_{lag}_total_spending" for lag in range(1, 5)
    ]
    moving_prediction, moving_inference_seconds = timed_prediction(
        lambda: linear_test[moving_columns].mean(axis=1).to_numpy()
    )
    actual = test_data["y_raw"].astype(np.float64)
    prediction_values = {
        "lstm": lstm_prediction,
        "linear_regression": linear_prediction,
        "naive_previous_period": naive_prediction,
        "moving_average_4": moving_prediction,
    }
    timing = {
        "lstm": (lstm_training_seconds, lstm_inference_seconds),
        "linear_regression": (
            linear_training_seconds,
            linear_inference_seconds,
        ),
        "naive_previous_period": (0.0, naive_inference_seconds),
        "moving_average_4": (0.0, moving_inference_seconds),
    }
    metric_records = [
        safe_metrics(
            actual,
            prediction_values[name],
            model_name=name,
            training_seconds=timing[name][0],
            inference_seconds=timing[name][1],
        )
        for name in MODEL_NAMES
    ]
    metrics = pd.DataFrame(metric_records)
    metrics.to_csv(report_dir / "forecasting_metrics.csv", index=False)

    base_index = pd.DataFrame(
        {
            "user_id": test_data["user_id"].astype(str),
            "input_end_timestamp": pd.to_datetime(
                test_data["input_end_timestamp"]
            ),
            "target_timestamp": pd.to_datetime(test_data["target_timestamp"]),
            "actual_spending": actual,
        }
    )
    prediction_frames = []
    for name, values in prediction_values.items():
        frame = base_index.copy()
        frame["model"] = name
        frame["predicted_spending"] = values
        frame["residual"] = frame["actual_spending"] - values
        prediction_frames.append(frame)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions.to_parquet(
        report_dir / "forecasting_predictions.parquet", index=False
    )

    history = {
        key: [float(value) for value in values]
        for key, values in fitted.history.items()
    }
    (artifact_dir / "training_history.json").write_text(
        json.dumps(history, indent=2), encoding="utf-8"
    )
    feature_schema = {
        "lstm": {
            "ordered_features": metadata["feature_names"],
            "look_back_window": metadata["look_back_window"],
            "input_shape": [
                metadata["look_back_window"],
                len(metadata["feature_names"]),
            ],
            "input_scaling": "training-only min-max parameters in scaler.joblib",
        },
        "linear_regression": {
            "ordered_features": feature_order,
            "target": "target_total_spending",
        },
    }
    (artifact_dir / "feature_schema.json").write_text(
        json.dumps(feature_schema, indent=2), encoding="utf-8"
    )
    training_date = datetime.now(timezone.utc).isoformat()
    model_metadata = {
        "model_version": version,
        "training_date_utc": training_date,
        "project_title": data_config["project_title"],
        "framework": f"TensorFlow {tf.__version__}",
        "compute": {
            "gpu_devices": gpu_devices,
            "device_used": "GPU" if gpu_devices else "CPU",
        },
        "dataset_sources": ["synthetic_kenyan_young_adult_finance"],
        "synthetic_records_used": True,
        "synthetic_data_disclaimer": metadata["synthetic_data_disclaimer"],
        "aggregation_period": metadata["aggregation_period"],
        "look_back_window": metadata["look_back_window"],
        "forecast_horizon": metadata["forecast_horizon"],
        "feature_names": metadata["feature_names"],
        "target_definition": metadata["target_definition"],
        "data_date_ranges": {
            "source_transactions": metadata["source_transaction_date_range"],
            "splits": metadata["splits"],
        },
        "architecture": {
            "lstm_units": [int(value) for value in settings["lstm_units"]],
            "dense_units": int(settings["dense_units"]),
            "dropout_rate": float(settings["dropout_rate"]),
            "maximum_epochs": int(settings["maximum_epochs"]),
            "epochs_completed": len(history.get("loss", [])),
            "early_stopping_patience": int(
                settings["early_stopping_patience"]
            ),
            "batch_size": int(settings["batch_size"]),
        },
        "metrics": {
            record["model"]: {
                key: value for key, value in record.items() if key != "model"
            }
            for record in metric_records
        },
        "known_limitations": [
            "Training and evaluation use synthetic controlled-development data.",
            "Results are not evidence of forecast accuracy for real Kenyan young adults.",
            "The quick dataset spans approximately 180 days.",
            "Only three unique weekly target dates are present in the test split.",
        ],
    }
    (artifact_dir / "model_metadata.json").write_text(
        json.dumps(model_metadata, indent=2), encoding="utf-8"
    )
    save_plots(predictions, metrics, history, figures_dir)
    (report_dir / "forecasting_model_comparison.md").write_text(
        markdown_comparison(metrics, model_metadata, history),
        encoding="utf-8",
    )
    LOGGER.info(
        "Forecasting training complete. LSTM test MAE=%.3f KES.",
        metric_records[0]["mae"],
    )
    return model_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("quick", "full"), default="quick")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--data-config", type=Path, default=None)
    parser.add_argument("--model-config", type=Path, default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    root = args.root.resolve() if args.root else repository_root(__file__)
    data_config_path = (
        args.data_config.resolve()
        if args.data_config
        else root / "config" / "data_config.yaml"
    )
    model_config_path = (
        args.model_config.resolve()
        if args.model_config
        else root / "config" / "model_config.yaml"
    )
    train(
        root,
        args.mode,
        load_yaml(data_config_path),
        load_yaml(model_config_path),
    )


if __name__ == "__main__":
    main()
