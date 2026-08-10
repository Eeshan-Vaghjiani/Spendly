from __future__ import annotations

from datetime import datetime, timedelta, timezone


def add_weekly_history(client, auth, weeks: int) -> None:
    start = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    for week in range(weeks):
        timestamp = start + timedelta(weeks=week)
        expense = client.post(
            "/api/v1/transactions",
            json={
                "transaction_timestamp": timestamp.isoformat(),
                "amount": 1_000 + week * 50,
                "category": "food",
                "transaction_type": "expense",
                "merchant": f"Shop {week}",
                "is_recurring": False,
            },
            headers=auth,
        )
        assert expense.status_code == 201, expense.get_json()
        income = client.post(
            "/api/v1/transactions",
            json={
                "transaction_timestamp": (
                    timestamp + timedelta(hours=1)
                ).isoformat(),
                "amount": 5_000,
                "category": "salary",
                "transaction_type": "income",
                "merchant": "Employer",
                "is_recurring": True,
            },
            headers=auth,
        )
        assert income.status_code == 201, income.get_json()


def test_analysis_starts_with_progressive_three_week_baseline(client, auth) -> None:
    add_weekly_history(client, auth, 3)
    response = client.post(
        "/api/v1/analysis/run",
        json={"use_stored_transactions": True},
        headers=auth,
    )
    assert response.status_code == 200, response.get_json()
    forecast = response.get_json()["data"]["forecast"]
    assert forecast["predicted_spending"] == 1_050
    assert forecast["history_weeks"] == 3
    assert forecast["data_readiness_percent"] == 38
    assert forecast["forecast_method"] == "personal_spending_baseline"
    assert forecast["accuracy_percent"] is None


def test_vertical_backend_analysis_and_history(client, auth) -> None:
    add_weekly_history(client, auth, 8)
    budget = client.post(
        "/api/v1/budgets",
        json={
            "period_start": "2026-02-23",
            "period_end": "2026-03-01",
            "category": "total",
            "amount": 10_000,
        },
        headers=auth,
    )
    assert budget.status_code == 201
    response = client.post(
        "/api/v1/analysis/run",
        json={"use_stored_transactions": True},
        headers=auth,
    )
    assert response.status_code == 200, response.get_json()
    data = response.get_json()["data"]
    assert data["forecast"]["predicted_spending"] == 11_675
    assert data["forecast"]["baseline_prediction"] == 1_275
    assert data["forecast"]["data_readiness_percent"] == 100
    assert data["forecast"]["forecast_method"] == "validated_model_blend"
    assert data["alert_summary"]["alert_count"] == 1
    assert data["recommendations"]
    assert client.get("/api/v1/analysis/latest", headers=auth).status_code == 200
    assert client.get("/api/v1/forecasts", headers=auth).get_json()["data"]["total"] == 1
    assert client.get("/api/v1/alerts", headers=auth).get_json()["data"]["total"] == 1
    assert (
        client.get("/api/v1/recommendations", headers=auth)
        .get_json()["data"]["total"]
        >= 1
    )


def test_system_endpoints_with_loaded_fake_registry(client) -> None:
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.get_json()["data"]["status"] == "healthy"
    info = client.get("/api/v1/model-info")
    assert info.status_code == 200
    assert info.get_json()["data"]["forecasting"]["main_model"] == "LSTM"
