"""Load immutable model artefacts once and provide inference methods."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


LOGGER = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(
        self,
        model_root: Path,
        forecast_version: str,
        anomaly_version: str,
        runtime: str = "full",
    ) -> None:
        self.model_root = Path(model_root)
        self.forecast_version = forecast_version
        self.anomaly_version = anomaly_version
        if runtime not in {"full", "lightweight"}:
            raise ValueError("Model runtime must be 'full' or 'lightweight'.")
        self.runtime = runtime
        self.loaded = False
        self.lstm_model: Any = None
        self.linear_model: Any = None
        self.forecast_scaler: dict[str, Any] = {}
        self.forecast_schema: dict[str, Any] = {}
        self.forecast_metadata: dict[str, Any] = {}
        self.anomaly_model: Any = None
        self.anomaly_preprocessor: Any = None
        self.anomaly_schema: dict[str, Any] = {}
        self.anomaly_metadata: dict[str, Any] = {}

    def load(self) -> None:
        if self.loaded:
            return
        forecast_dir = (
            self.model_root / "forecasting" / self.forecast_version
        )
        anomaly_dir = self.model_root / "anomaly" / self.anomaly_version
        required = [
            forecast_dir / "linear_regression.joblib",
            forecast_dir / "feature_schema.json",
            forecast_dir / "model_metadata.json",
            anomaly_dir / "isolation_forest.joblib",
            anomaly_dir / "preprocessor.joblib",
            anomaly_dir / "feature_schema.json",
            anomaly_dir / "model_metadata.json",
        ]
        if self.runtime == "full":
            required.extend(
                [forecast_dir / "lstm.keras", forecast_dir / "scaler.joblib"]
            )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                "Required model artefacts are missing: " + ", ".join(missing)
            )
        if self.runtime == "full":
            import tensorflow as tf

            self.lstm_model = tf.keras.models.load_model(
                forecast_dir / "lstm.keras"
            )
            self.forecast_scaler = joblib.load(forecast_dir / "scaler.joblib")
        self.linear_model = joblib.load(
            forecast_dir / "linear_regression.joblib"
        )
        self.forecast_schema = json.loads(
            (forecast_dir / "feature_schema.json").read_text(encoding="utf-8")
        )
        self.forecast_metadata = json.loads(
            (forecast_dir / "model_metadata.json").read_text(encoding="utf-8")
        )
        self.anomaly_model = joblib.load(
            anomaly_dir / "isolation_forest.joblib"
        )
        self.anomaly_preprocessor = joblib.load(
            anomaly_dir / "preprocessor.joblib"
        )
        self.anomaly_schema = json.loads(
            (anomaly_dir / "feature_schema.json").read_text(encoding="utf-8")
        )
        self.anomaly_metadata = json.loads(
            (anomaly_dir / "model_metadata.json").read_text(encoding="utf-8")
        )
        self.loaded = True
        LOGGER.info(
            "Loaded forecasting model %s and anomaly model %s once at startup.",
            self.forecast_version,
            self.anomaly_version,
        )

    def ensure_loaded(self) -> None:
        if not self.loaded:
            raise RuntimeError("Model artefacts are not loaded.")

    def forecast(self, raw_sequence: np.ndarray) -> dict[str, float]:
        self.ensure_loaded()
        raw_sequence = np.asarray(raw_sequence, dtype=np.float64)
        expected_shape = tuple(
            self.forecast_schema["lstm"]["input_shape"]
        )
        if raw_sequence.shape != expected_shape:
            raise ValueError(
                f"Forecast sequence has shape {raw_sequence.shape}; "
                f"expected {expected_shape}."
            )
        linear_row: dict[str, float] = {}
        feature_names = self.forecast_schema["lstm"]["ordered_features"]
        lookback = raw_sequence.shape[0]
        for index in range(lookback):
            lag = lookback - index
            for feature_index, feature_name in enumerate(feature_names):
                linear_row[f"lag_{lag}_{feature_name}"] = float(
                    raw_sequence[index, feature_index]
                )
        linear_features = self.forecast_schema["linear_regression"][
            "ordered_features"
        ]
        linear_frame = pd.DataFrame(
            [[linear_row[name] for name in linear_features]],
            columns=linear_features,
        )
        linear_prediction = float(
            self.linear_model.predict(linear_frame).reshape(-1)[0]
        )
        if self.lstm_model is None:
            linear_prediction = max(0.0, linear_prediction)
            return {
                "lstm": linear_prediction,
                "linear_regression": linear_prediction,
            }
        feature_scaler = self.forecast_scaler["feature_scaler"]
        feature_min = np.asarray(
            feature_scaler["minimum"], dtype=np.float64
        )
        feature_scale = np.asarray(
            feature_scaler["scale"], dtype=np.float64
        )
        scaled_sequence = (raw_sequence - feature_min) / feature_scale
        scaled_prediction = float(
            self.lstm_model.predict(
                scaled_sequence[np.newaxis, ...], verbose=0
            ).reshape(-1)[0]
        )
        target_scaler = self.forecast_scaler["target_scaler"]
        lstm_prediction = (
            scaled_prediction * float(target_scaler["scale"])
            + float(target_scaler["minimum"])
        )
        return {
            "lstm": max(0.0, lstm_prediction),
            "linear_regression": max(0.0, linear_prediction),
        }

    def detect_unusual(
        self, feature_frame: pd.DataFrame
    ) -> pd.DataFrame:
        self.ensure_loaded()
        features = self.anomaly_schema["ordered_features"]
        if feature_frame.empty:
            return pd.DataFrame(
                columns=["anomaly_score", "is_unusual_spending", "explanation"]
            )
        scaled = self.anomaly_preprocessor.transform(
            feature_frame[features]
        )
        scores = -self.anomaly_model.decision_function(scaled)
        threshold = float(self.anomaly_schema["decision_threshold"])
        predictions = scores >= threshold
        explanations: list[str] = []
        for row_position, (_, row) in enumerate(feature_frame.iterrows()):
            if not predictions[row_position]:
                explanations.append(
                    "No unusual-spending alert was produced for this transaction."
                )
                continue
            ranked = np.argsort(np.abs(scaled[row_position]))[::-1]
            strongest_feature = features[int(ranked[0])]
            if strongest_feature in {
                "amount",
                "deviation_from_historical_average",
            }:
                explanation = (
                    "This amount is noticeably different from what you usually "
                    "record."
                )
            elif strongest_feature in {
                "transaction_count_last_7d",
                "recent_spending_change",
            }:
                explanation = (
                    "Your recent pace of spending is different from your usual "
                    "pattern."
                )
            elif strongest_feature in {"category_code", "category_proportion"}:
                explanation = (
                    "Spending in this category looks different from your usual "
                    "mix."
                )
            elif strongest_feature in {"hour_of_day", "is_weekend"}:
                explanation = (
                    "This entry was recorded at a different time from your usual "
                    "spending."
                )
            elif strongest_feature == "is_recurring":
                explanation = (
                    "This entry's recurring pattern differs from your recent "
                    "records."
                )
            else:
                explanation = (
                    "This entry is different from what you usually record."
                )
            explanations.append(explanation)
        return pd.DataFrame(
            {
                "anomaly_score": scores,
                "decision_threshold": threshold,
                "is_unusual_spending": predictions,
                "explanation": explanations,
            },
            index=feature_frame.index,
        )

    def info(self) -> dict[str, Any]:
        self.ensure_loaded()
        return {
            "forecasting": {
                "version": self.forecast_version,
                "main_model": (
                    "LSTM"
                    if self.runtime == "full"
                    else "Multiple Linear Regression (lightweight runtime)"
                ),
                "baseline_model": "Multiple Linear Regression",
                "runtime": self.runtime,
                "aggregation_period": self.forecast_metadata[
                    "aggregation_period"
                ],
                "forecast_horizon": self.forecast_metadata[
                    "forecast_horizon"
                ],
                "synthetic_records_used": self.forecast_metadata[
                    "synthetic_records_used"
                ],
                "metrics": self.forecast_metadata["metrics"],
            },
            "anomaly": {
                "version": self.anomaly_version,
                "purpose": self.anomaly_metadata["purpose"],
                "synthetic_records_used": self.anomaly_metadata[
                    "synthetic_records_used"
                ],
                "metrics": self.anomaly_metadata["evaluation_metrics"],
            },
        }
