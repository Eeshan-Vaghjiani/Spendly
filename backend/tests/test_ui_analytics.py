from datetime import date, datetime

from backend.app.extensions import db
from backend.app.models import SignInEvent, Transaction, User
from .conftest import register
from .test_analytics_admin import _stored_transaction, admin_headers


def test_category_bars_match_owner_reversal_and_nairobi_range(client, app, monkeypatch):
    first = register(client)
    second = register(client, email="other-bars@example.invalid", display_name="Other")
    monkeypatch.setattr("backend.app.routes.analytics.reporting_today", lambda: date(2026, 10, 20))
    uid = first["user"]["id"]
    headers = {"Authorization": f"Bearer {first['access_token']}"}
    for timestamp, amount, kind in [
        (datetime(2026, 10, 18, 20, 59), 100, "expense"),
        (datetime(2026, 10, 18, 21), 10.25, "expense"),
        (datetime(2026, 10, 20, 20, 59), 20.75, "expense"),
        (datetime(2026, 10, 20, 21), 40, "expense"),
        (datetime(2026, 10, 1), 50, "expense"),
        (datetime(2026, 10, 19), 5000, "income"),
        (datetime(2026, 10, 19), 60, "expense"),
    ]:
        _stored_transaction(app, uid, timestamp, amount, kind)
    _stored_transaction(app, second["user"]["id"], datetime(2026, 10, 19), 999, "expense")
    with app.app_context():
        reversed_row = db.session.scalar(db.select(Transaction).where(Transaction.user_id == uid, Transaction.amount == 60))
        reversed_row.is_reversed = True
        db.session.commit()
    for route, expected in [("dashboard?period=weekly", 31), ("cashflow?resolution=daily", 131)]:
        data = client.get(f"/api/v1/analytics/{route}", headers=headers).get_json()["data"]
        assert data["expense_categories"] == [{"category": "food", "amount": expected}]
        expense = data["summary"]["expense"] if "summary" in data else data["expense"]
        assert sum(row["amount"] for row in data["expense_categories"]) == expense
    other = client.get("/api/v1/analytics/dashboard?period=weekly", headers={"Authorization": f"Bearer {second['access_token']}"}).get_json()["data"]
    assert other["expense_categories"] == [{"category": "food", "amount": 999}]


def test_category_bars_empty_and_income_only(client, auth):
    for route in ["dashboard", "cashflow"]:
        data = client.get(f"/api/v1/analytics/{route}", headers=auth).get_json()["data"]
        assert data["expense_categories"] == []


def test_admin_activity_uses_calendar_days_and_excludes_registrations(client, app, monkeypatch):
    class Clock(datetime):
        @classmethod
        def utcnow(cls):
            return cls(2026, 10, 20, 22)

    monkeypatch.setattr("backend.app.routes.admin.datetime", Clock)
    monkeypatch.setattr("backend.app.routes.admin.reporting_today", lambda: date(2026, 10, 21))
    owner = register(client)
    uid = owner["user"]["id"]
    with app.app_context():
        db.session.query(SignInEvent).delete()
        db.session.get(User, uid).created_at = datetime(2026, 10, 20, 21)
        for timestamp, event in [
            (datetime(2026, 10, 20, 20, 59), "sign_in"),
            (datetime(2026, 10, 20, 20, 59, 30), "sign_in"),
            (datetime(2026, 10, 20, 21), "sign_in"),
            (datetime(2026, 10, 20, 21), "registration"),
            (datetime(2026, 10, 21), "sign_in"),
        ]:
            db.session.add(SignInEvent(user_id=uid, provider="password", event=event, created_at=timestamp))
        db.session.commit()
    assert client.get("/api/v1/admin/overview").status_code == 401
    response = client.get("/api/v1/admin/overview", headers=admin_headers())
    assert response.status_code == 200
    activity = response.get_json()["data"]["account_activity"]
    assert activity["reporting_timezone"] == "Africa/Nairobi"
    assert len(activity["days"]) == 7
    assert activity["days"][-2] == {"date": "2026-10-20", "sign_ins": 2, "new_users": 0}
    assert activity["days"][-1] == {"date": "2026-10-21", "sign_ins": 1, "new_users": 1}
    assert response.headers["Cache-Control"].find("no-store") >= 0
