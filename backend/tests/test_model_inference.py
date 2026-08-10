from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.services.model_registry import ModelRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_real_saved_model_artifacts_load_and_infer() -> None:
    registry = ModelRegistry(
        PROJECT_ROOT / "artifacts" / "models", "v1", "v1"
    )
    registry.load()
    with np.load(
        PROJECT_ROOT / "data" / "model_ready" / "lstm_test.npz"
    ) as payload:
        scaled_sequence = payload["X"][0].astype(np.float64)
    scaler = registry.forecast_scaler["feature_scaler"]
    raw_sequence = (
        scaled_sequence * np.asarray(scaler["scale"])
        + np.asarray(scaler["minimum"])
    )
    forecast = registry.forecast(raw_sequence)
    assert set(forecast) == {"lstm", "linear_regression"}
    assert all(np.isfinite(value) and value >= 0 for value in forecast.values())

    anomaly = pd.read_parquet(
        PROJECT_ROOT
        / "data"
        / "model_ready"
        / "isolation_forest_test.parquet"
    ).head(10)
    result = registry.detect_unusual(anomaly)
    assert len(result) == 10
    assert result["anomaly_score"].notna().all()
    assert result["is_unusual_spending"].dtype == bool
    flagged_explanations = result.loc[
        result["is_unusual_spending"], "explanation"
    ]
    assert all("heuristic" not in text.lower() for text in flagged_explanations)
    assert all("=" not in text for text in flagged_explanations)

    lightweight = ModelRegistry(
        PROJECT_ROOT / "artifacts" / "models",
        "v1",
        "v1",
        "lightweight",
    )
    lightweight.load()
    lightweight_forecast = lightweight.forecast(raw_sequence)
    assert lightweight.lstm_model is None
    assert lightweight_forecast["lstm"] == lightweight_forecast["linear_regression"]
    assert lightweight.info()["forecasting"]["runtime"] == "lightweight"
