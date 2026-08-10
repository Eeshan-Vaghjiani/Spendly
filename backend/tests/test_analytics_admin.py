from __future__ import annotations

import base64
from datetime import datetime, timezone


def add_transaction(client, auth, *, amount: float, transaction_type: str) -> None:
    response = client.post(
        "/api/v1/transactions",
        json={
            "transaction_timestamp": datetime.now(timezone.utc).isoformat(),
            "amount": amount,
            "category": "salary" if transaction_type == "income" else "food",
            "transaction_type": transaction_type,
            "merchant": "Test source",
            "is_recurring": False,
        },
        headers=auth,
    )
    assert response.status_code == 201, response.get_json()


def admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:test-admin-password").decode("ascii")
    return {"Authorization": f"Basic {token}"}


def test_cashflow_analytics_reports_balance_and_series(client, auth) -> None:
    add_transaction(client, auth, amount=50_000, transaction_type="income")
    add_transaction(client, auth, amount=12_500, transaction_type="expense")

    response = client.get(
        "/api/v1/analytics/cashflow?resolution=daily", headers=auth
    )

    assert response.status_code == 200, response.get_json()
    data = response.get_json()["data"]
    assert len(data["series"]) == 14
    assert data["summary"]["income"] == 50_000
    assert data["summary"]["expense"] == 12_500
    assert data["summary"]["net"] == 37_500
    assert data["summary"]["cash_balance"] == 37_500
    assert data["summary"]["savings_rate"] == 75


def test_cashflow_analytics_rejects_unknown_resolution(client, auth) -> None:
    response = client.get(
        "/api/v1/analytics/cashflow?resolution=hourly", headers=auth
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_admin_dashboard_and_overview_are_password_protected(client, auth) -> None:
    assert client.get("/admin").status_code == 401
    assert client.get("/api/v1/admin/overview").status_code == 401
    add_transaction(client, auth, amount=20_000, transaction_type="income")
    add_transaction(client, auth, amount=5_000, transaction_type="expense")

    page = client.get("/admin", headers=admin_headers())
    overview = client.get("/api/v1/admin/overview", headers=admin_headers())

    assert page.status_code == 200
    assert b"Admin overview" in page.data
    assert overview.status_code == 200
    metrics = overview.get_json()["data"]["metrics"]
    assert metrics["users"] == 1
    assert metrics["transactions"] == 2
    assert metrics["net_savings"] == 15_000
