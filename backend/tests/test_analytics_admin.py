from __future__ import annotations

import base64
import re
from datetime import date, datetime, timezone

from backend.app.extensions import db
from backend.app.models import Transaction

from .conftest import register


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


def _stored_transaction(
    app,
    user_id: str,
    timestamp: datetime,
    amount: float,
    transaction_type: str,
    category: str = "food",
) -> None:
    with app.app_context():
        db.session.add(
            Transaction(
                user_id=user_id,
                transaction_timestamp=timestamp,
                amount=amount,
                category=category,
                transaction_type=transaction_type,
                fingerprint=f"{user_id}-{timestamp.isoformat()}-{amount}",
            )
        )
        db.session.commit()


def test_dashboard_periods_use_utc_half_open_boundaries(client, app, monkeypatch) -> None:
    registered = register(client)
    user_id = registered["user"]["id"]
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    monkeypatch.setattr("backend.app.routes.analytics.utc_today", lambda: date(2026, 8, 25))
    _stored_transaction(app, user_id, datetime(2025, 12, 31, 12), 100, "expense")
    _stored_transaction(app, user_id, datetime(2026, 1, 1), 1_000, "income")
    _stored_transaction(app, user_id, datetime(2026, 5, 25, 23, 59), 200, "expense")
    _stored_transaction(app, user_id, datetime(2026, 5, 26), 300, "expense")
    _stored_transaction(app, user_id, datetime(2026, 8, 1), 400, "expense")
    _stored_transaction(app, user_id, datetime(2026, 8, 24), 500, "expense", "travel")
    _stored_transaction(app, user_id, datetime(2026, 8, 26), 900, "expense")

    weekly = client.get("/api/v1/analytics/dashboard?period=weekly", headers=headers)
    monthly = client.get("/api/v1/analytics/dashboard?period=monthly", headers=headers)
    rolling = client.get(
        "/api/v1/analytics/dashboard?period=last_3_months", headers=headers
    )
    yearly = client.get("/api/v1/analytics/dashboard?period=yearly", headers=headers)
    lifetime = client.get("/api/v1/analytics/dashboard?period=all_time", headers=headers)

    assert weekly.get_json()["data"]["expense"] == 500
    assert weekly.get_json()["data"]["period_start"] == "2026-08-24"
    assert monthly.get_json()["data"]["expense"] == 900
    assert rolling.get_json()["data"]["expense"] == 1_200
    assert rolling.get_json()["data"]["period_start"] == "2026-05-26"
    assert yearly.get_json()["data"]["expense"] == 1_400
    assert lifetime.get_json()["data"]["expense"] == 2_400
    assert lifetime.get_json()["data"]["transaction_count"] == 7
    assert weekly.get_json()["data"]["top_category"] == "travel"


def test_dashboard_empty_period_is_distinct_from_older_history(client, app, monkeypatch) -> None:
    registered = register(client)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    monkeypatch.setattr("backend.app.routes.analytics.utc_today", lambda: date(2026, 8, 25))
    _stored_transaction(
        app,
        registered["user"]["id"],
        datetime(2026, 7, 1),
        750,
        "expense",
    )
    data = client.get(
        "/api/v1/analytics/dashboard?period=weekly", headers=headers
    ).get_json()["data"]
    assert data["has_transactions"] is False
    assert data["has_older_transactions"] is True
    assert data["expense"] == 0


def test_dashboard_requires_auth_and_isolates_users(client, app, monkeypatch) -> None:
    assert client.get("/api/v1/analytics/dashboard").status_code == 401
    first = register(client)
    second = register(client, email="second@example.com", display_name="Second")
    monkeypatch.setattr("backend.app.routes.analytics.utc_today", lambda: date(2026, 8, 25))
    _stored_transaction(
        app, first["user"]["id"], datetime(2026, 8, 24), 450, "expense"
    )
    second_data = client.get(
        "/api/v1/analytics/dashboard?period=weekly",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    ).get_json()["data"]
    assert second_data["transaction_count"] == 0
    assert second_data["expense"] == 0


def test_dashboard_normalizes_timezone_and_handles_leap_day(client, monkeypatch) -> None:
    registered = register(client)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    monkeypatch.setattr("backend.app.routes.analytics.utc_today", lambda: date(2024, 3, 1))
    created = client.post(
        "/api/v1/transactions",
        json={
            "transaction_timestamp": "2024-03-01T00:30:00+03:00",
            "amount": 725,
            "category": "food",
            "transaction_type": "expense",
            "merchant": "Timezone test",
        },
        headers=headers,
    )
    assert created.status_code == 201
    monthly = client.get(
        "/api/v1/analytics/dashboard?period=monthly", headers=headers
    ).get_json()["data"]
    yearly = client.get(
        "/api/v1/analytics/dashboard?period=yearly", headers=headers
    ).get_json()["data"]
    assert monthly["transaction_count"] == 0
    assert yearly["transaction_count"] == 1
    assert yearly["expense"] == 725


def test_dashboard_rejects_unknown_period(client, auth) -> None:
    response = client.get(
        "/api/v1/analytics/dashboard?period=quarterly", headers=auth
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_admin_dashboard_and_overview_are_password_protected(client, auth) -> None:
    assert client.get("/admin").status_code == 302
    assert client.get("/admin/login").status_code == 200
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


def test_admin_can_sign_in_and_out_with_a_session(client) -> None:
    login_page = client.get("/admin/login")
    token_match = re.search(
        rb'name="csrf_token" value="([^"]+)"', login_page.data
    )
    assert token_match is not None
    csrf_token = token_match.group(1).decode("utf-8")

    invalid = client.post(
        "/admin/login",
        data={
            "csrf_token": csrf_token,
            "username": "admin",
            "password": "wrong-password",
        },
    )
    assert invalid.status_code == 401
    assert b"incorrect" in invalid.data

    signed_in = client.post(
        "/admin/login",
        data={
            "csrf_token": csrf_token,
            "username": "admin",
            "password": "test-admin-password",
        },
        follow_redirects=True,
    )
    assert signed_in.status_code == 200
    assert b"Admin overview" in signed_in.data
    assert client.get("/api/v1/admin/overview").status_code == 200

    with client.session_transaction() as session:
        logout_token = session["spendly_admin_csrf"]
    signed_out = client.post(
        "/admin/logout",
        data={"csrf_token": logout_token},
        follow_redirects=True,
    )
    assert signed_out.status_code == 200
    assert b"Admin sign in" in signed_out.data
    assert client.get("/api/v1/admin/overview").status_code == 401


def test_admin_login_accepts_unicode_credentials(client, app) -> None:
    app.config.update(
        ADMIN_USERNAME="spendly-admin",
        ADMIN_PASSWORD="Säkra-pengar-🔐",
    )
    login_page = client.get("/admin/login")
    token_match = re.search(
        rb'name="csrf_token" value="([^"]+)"', login_page.data
    )
    assert token_match is not None

    signed_in = client.post(
        "/admin/login",
        data={
            "csrf_token": token_match.group(1).decode("utf-8"),
            "username": "spendly-admin",
            "password": "Säkra-pengar-🔐",
        },
        follow_redirects=True,
    )

    assert signed_in.status_code == 200
    assert b"Admin overview" in signed_in.data
