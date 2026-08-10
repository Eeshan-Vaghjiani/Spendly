from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app import create_app
from backend.app.extensions import db


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_real_model_vertical_slice() -> None:
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "vertical-test-secret-key-at-least-32-bytes",
            "JWT_SECRET_KEY": "vertical-test-jwt-secret-at-least-32-bytes",
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "LOAD_MODELS": True,
            "MODEL_ROOT": PROJECT_ROOT / "artifacts" / "models",
            "FORECAST_MODEL_VERSION": "v1",
            "ANOMALY_MODEL_VERSION": "v1",
            "ALLOWED_CORS_ORIGINS": ("http://localhost",),
        }
    )
    with app.app_context():
        db.create_all()
    client = app.test_client()
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "vertical@example.com",
            "password": "StrongPass123!",
            "display_name": "Vertical Test",
            "accepted_terms": True,
            "accepted_privacy": True,
            "model_training_opt_in": False,
        },
    )
    assert registration.status_code == 201, registration.get_json()
    token = registration.get_json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    start = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    for week in range(8):
        timestamp = start + timedelta(weeks=week)
        expense = client.post(
            "/api/v1/transactions",
            json={
                "transaction_timestamp": timestamp.isoformat(),
                "amount": 100_000 if week == 7 else 1_000 + week * 50,
                "category": "food",
                "transaction_type": "expense",
                "merchant": f"Vertical Shop {week}",
                "is_recurring": False,
            },
            headers=headers,
        )
        assert expense.status_code == 201, expense.get_json()
        income = client.post(
            "/api/v1/transactions",
            json={
                "transaction_timestamp": (
                    timestamp + timedelta(hours=1)
                ).isoformat(),
                "amount": 20_000,
                "category": "salary",
                "transaction_type": "income",
                "merchant": "Vertical Employer",
                "is_recurring": True,
            },
            headers=headers,
        )
        assert income.status_code == 201, income.get_json()

    budget = client.post(
        "/api/v1/budgets",
        json={
            "period_start": "2026-03-02",
            "period_end": "2026-03-08",
            "category": "total",
            "amount": 15_000,
        },
        headers=headers,
    )
    assert budget.status_code == 201, budget.get_json()

    analysis = client.post(
        "/api/v1/analysis/run",
        json={"use_stored_transactions": True},
        headers=headers,
    )
    assert analysis.status_code == 200, analysis.get_json()
    result = analysis.get_json()["data"]
    assert result["forecast"]["predicted_spending"] >= 0
    assert result["forecast"]["model_version"] == "v1"
    assert "unusual_spending_detected" in result["alert_summary"]
    assert result["recommendations"]

    assert client.get("/api/v1/analysis/latest", headers=headers).status_code == 200
    assert (
        client.get("/api/v1/forecasts", headers=headers)
        .get_json()["data"]["total"]
        == 1
    )
    assert (
        client.get("/api/v1/recommendations", headers=headers)
        .get_json()["data"]["total"]
        >= 1
    )
