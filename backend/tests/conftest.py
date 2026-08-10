from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from backend.app import create_app
from backend.app.extensions import db


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FakeRegistry:
    def __init__(self) -> None:
        forecast_dir = (
            PROJECT_ROOT / "artifacts" / "models" / "forecasting" / "v1"
        )
        anomaly_dir = (
            PROJECT_ROOT / "artifacts" / "models" / "anomaly" / "v1"
        )
        self.forecast_schema = json.loads(
            (forecast_dir / "feature_schema.json").read_text(encoding="utf-8")
        )
        self.anomaly_schema = json.loads(
            (anomaly_dir / "feature_schema.json").read_text(encoding="utf-8")
        )
        self.forecast_version = "v1"
        self.anomaly_version = "v1"
        self.loaded = True

    def forecast(self, raw_sequence: Any) -> dict[str, float]:
        assert raw_sequence.shape == (8, 20)
        return {"lstm": 12_000.0, "linear_regression": 11_500.0}

    def detect_unusual(self, feature_frame: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(
            {
                "anomaly_score": [-0.1] * len(feature_frame),
                "decision_threshold": [0.0] * len(feature_frame),
                "is_unusual_spending": [False] * len(feature_frame),
                "explanation": ["No unusual-spending alert."] * len(feature_frame),
            },
            index=feature_frame.index,
        )
        if not result.empty:
            last = result.index[-1]
            result.loc[last, "anomaly_score"] = 0.1
            result.loc[last, "is_unusual_spending"] = True
            result.loc[last, "explanation"] = "Test unusual-spending alert."
        return result

    def info(self) -> dict[str, Any]:
        return {
            "forecasting": {"version": "v1", "main_model": "LSTM"},
            "anomaly": {
                "version": "v1",
                "purpose": "Unusual spending behaviour detection",
            },
        }


@pytest.fixture()
def app():
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret-key-at-least-32-bytes",
            "JWT_SECRET_KEY": "test-only-jwt-secret-at-least-32-bytes",
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "LOAD_MODELS": False,
            "ALLOWED_CORS_ORIGINS": ("http://localhost",),
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "test-admin-password",
            "GOOGLE_WEB_CLIENT_ID": "test-web-client.apps.googleusercontent.com",
        }
    )
    application.extensions["model_registry"] = FakeRegistry()
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register(
    client: Any,
    email: str = "eva@example.com",
    password: str = "StrongPass123!",
    display_name: str = "Eva",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "accepted_terms": True,
            "accepted_privacy": True,
            "model_training_opt_in": False,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["data"]


@pytest.fixture()
def auth(client):
    data = register(client)
    return {
        "Authorization": f"Bearer {data['access_token']}",
        "Content-Type": "application/json",
    }
