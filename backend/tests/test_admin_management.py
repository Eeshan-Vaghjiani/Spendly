from datetime import datetime, timedelta
import re
import time

import pytest
from sqlalchemy import select

from backend.app.extensions import db
from backend.app.models import (
    AdminAudit,
    AnalysisRun,
    AnomalyAlert,
    Budget,
    Forecast,
    RecommendationRecord,
    Transaction,
    User,
)
from backend.tests.conftest import register
from backend.tests.test_analytics_admin import admin_headers

BASE = "/api/v1/admin"


def sign_in(client):
    page = client.get("/admin/login")
    csrf = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": csrf,
            "username": "admin",
            "password": "test-admin-password",
        },
    )
    assert response.status_code == 302
    with client.session_transaction() as state:
        return {"X-CSRF-Token": state["spendly_admin_csrf"]}


def body(**fields):
    return {
        "reason": "Support ticket from account owner",
        "admin_password": "test-admin-password",
        **fields,
    }


def transaction(**fields):
    return {
        "transaction_timestamp": "2026-08-10T12:00:00Z",
        "amount": 320,
        "category": "food",
        "transaction_type": "expense",
        "merchant": "Shop",
        "is_recurring": False,
        **fields,
    }


@pytest.mark.parametrize(
    "path",
    [
        "/users",
        "/settings",
        "/audit",
        "/users/missing",
        "/users/missing/records/transactions",
    ],
)
def test_admin_reads_reject_normal_user_tokens(client, auth, path):
    assert client.get(BASE + path).status_code == 401
    assert client.get(BASE + path, headers=auth).status_code == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("PATCH", "/users/missing"),
        ("DELETE", "/users/missing"),
        ("POST", "/users/missing/export"),
        ("POST", "/users/missing/revoke-sessions"),
        ("POST", "/users/missing/records/transactions"),
        ("PUT", "/users/missing/records/budgets/missing"),
        ("PUT", "/settings"),
    ],
)
def test_writes_require_admin_session_not_basic_or_user_jwt(client, auth, method, path):
    assert (
        client.open(BASE + path, method=method, json=body(), headers=auth).status_code
        == 401
    )
    assert (
        client.open(
            BASE + path, method=method, json=body(), headers=admin_headers()
        ).status_code
        == 403
    )


def test_mutations_require_csrf_current_password_and_reason(client):
    user = register(client)["user"]
    headers = sign_in(client)
    url = BASE + "/users/" + user["id"]
    assert client.patch(url, json=body(is_active=False)).status_code == 403
    assert (
        client.patch(
            url, json=body(is_active=False), headers={"X-CSRF-Token": "wrong"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            url, json=body(is_active=False, admin_password="wrong"), headers=headers
        ).status_code
        == 403
    )
    assert (
        client.patch(
            url, json=body(is_active=False, reason=" "), headers=headers
        ).status_code
        == 422
    )
    assert client.get(url).get_json()["data"]["user"]["is_active"] is True


def test_disable_and_enable_revokes_old_tokens_permanently(client):
    account = register(client)
    headers = sign_in(client)
    url = BASE + "/users/" + account["user"]["id"]
    bearer = {"Authorization": "Bearer " + account["access_token"]}
    assert (
        client.patch(url, json=body(is_active=False), headers=headers).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=bearer).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "eva@example.com", "password": "StrongPass123!"},
        ).status_code
        == 401
    )
    assert (
        client.patch(url, json=body(is_active=True), headers=headers).status_code == 200
    )
    assert client.get("/api/v1/auth/me", headers=bearer).status_code == 401
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "eva@example.com", "password": "StrongPass123!"},
    )
    token = login.get_json()["data"]["access_token"]
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer " + token}
        ).status_code
        == 200
    )
    assert (
        client.post(url + "/revoke-sessions", json=body(), headers=headers).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/renew", headers={"Authorization": "Bearer " + token}
        ).status_code
        == 401
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("email", "changed@example.com"),
        ("password_hash", "hash"),
        ("google_subject", "identity"),
        ("model_training_opt_in", True),
        ("auth_version", 0),
        ("role", "admin"),
        ("onboarding_completed_at", None),
    ],
)
def test_admin_cannot_change_identity_consent_or_escalate_profile(client, field, value):
    user = register(client)["user"]
    headers = sign_in(client)
    assert (
        client.patch(
            BASE + "/users/" + user["id"], json=body(**{field: value}), headers=headers
        ).status_code
        == 422
    )


def test_profile_search_pagination_and_duplicate_rollback(client, app):
    first = register(client)["user"]
    second = register(client, "other@example.com", display_name="Second")["user"]
    headers = sign_in(client)
    url = BASE + "/users/" + first["id"]
    result = client.patch(
        url, json=body(username=" Eeshan_2 ", display_name=" Eeshan "), headers=headers
    )
    assert result.status_code == 200
    assert result.get_json()["data"]["username"] == "Eeshan_2"
    conflict = client.patch(
        url,
        json=body(username=second["username"].upper(), display_name="Wrong"),
        headers=headers,
    )
    assert conflict.status_code == 409
    assert client.get(url).get_json()["data"]["user"]["display_name"] == "Eeshan"
    assert client.get(BASE + "/users?q=EESHAN_2").get_json()["data"]["total"] == 1
    assert client.get(BASE + "/users?q=%25").get_json()["data"]["total"] == 0
    assert (
        client.get(BASE + "/users?per_page=1&page=2").get_json()["data"]["total"] == 2
    )
    assert client.get(BASE + "/users?status=disabled").get_json()["data"]["total"] == 0
    assert client.get(BASE + "/users?per_page=101").status_code == 422
    with app.app_context():
        actions = list(
            db.session.scalars(
                select(AdminAudit).where(AdminAudit.action == "user.update")
            )
        )
        assert len(actions) == 1
        assert actions[0].details == {"changed_fields": ["display_name", "username"]}


def test_record_crud_is_owned_validated_and_audited(client, app):
    first = register(client)["user"]
    other = register(client, "other@example.com")["user"]
    headers = sign_in(client)
    base = BASE + "/users/" + first["id"] + "/records/transactions"
    created = client.post(base, json=body(record=transaction()), headers=headers)
    assert created.status_code == 201
    record_id = created.get_json()["data"]["id"]
    assert (
        client.post(base, json=body(record=transaction()), headers=headers).status_code
        == 409
    )
    wrong_owner = BASE + "/users/" + other["id"] + "/records/transactions/" + record_id
    assert (
        client.put(
            wrong_owner, json=body(record=transaction(amount=850)), headers=headers
        ).status_code
        == 404
    )
    assert (
        client.delete(
            wrong_owner, json=body(confirm_id=record_id), headers=headers
        ).status_code
        == 404
    )
    assert (
        client.put(
            base + "/" + record_id,
            json=body(record=transaction(amount=850)),
            headers=headers,
        ).status_code
        == 200
    )
    assert client.get(base).get_json()["data"]["items"][0]["amount"] == 850
    assert (
        client.delete(base + "/" + record_id, json=body(), headers=headers).status_code
        == 422
    )
    assert (
        client.delete(
            base + "/" + record_id, json=body(confirm_id=record_id), headers=headers
        ).status_code
        == 200
    )
    assert client.get(base).get_json()["data"]["total"] == 0
    with app.app_context():
        audit = list(
            db.session.scalars(
                select(AdminAudit).where(AdminAudit.target_id == record_id)
            )
        )
        assert [row.action for row in audit] == [
            "transactions.post",
            "transactions.put",
            "transactions.delete",
        ]
        assert all("850" not in str(row.details) for row in audit)


@pytest.mark.parametrize(
    "invalid",
    [
        {"amount": 0},
        {"amount": 0.001},
        {"amount": 1e20},
        {"amount": True},
        {"category": "   "},
        {"transaction_type": "transfer"},
        {"currency": "USD"},
    ],
)
def test_record_invalid_input(client, invalid):
    user = register(client)["user"]
    headers = sign_in(client)
    response = client.post(
        BASE + "/users/" + user["id"] + "/records/transactions",
        json=body(record=transaction(**invalid)),
        headers=headers,
    )
    assert response.status_code == 422


def test_budget_crud_duplicates_and_date_validation(client):
    user = register(client)["user"]
    headers = sign_in(client)
    base = BASE + "/users/" + user["id"] + "/records/budgets"
    record = {
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "category": "food",
        "amount": 2000,
    }
    result = client.post(base, json=body(record=record), headers=headers)
    assert result.status_code == 201
    record_id = result.get_json()["data"]["id"]
    assert (
        client.post(base, json=body(record=record), headers=headers).status_code == 409
    )
    assert (
        client.put(
            base + "/" + record_id,
            json=body(record={**record, "amount": 3000}),
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.put(
            base + "/" + record_id,
            json=body(record={**record, "period_end": "2025-01-01"}),
            headers=headers,
        ).status_code
        == 422
    )
    assert (
        client.delete(
            base + "/" + record_id, json=body(confirm_id=record_id), headers=headers
        ).status_code
        == 200
    )


def test_export_delete_with_dependencies_and_audit_retention(client, app):
    account = register(client)
    other = register(client, "other@example.com")["user"]
    bearer = {"Authorization": "Bearer " + account["access_token"]}
    assert (
        client.post(
            "/api/v1/transactions", json=transaction(), headers=bearer
        ).status_code
        == 201
    )
    assert (
        client.post("/api/v1/analysis/run", json={}, headers=bearer).status_code == 200
    )
    headers = sign_in(client)
    user = account["user"]
    base = BASE + "/users/" + user["id"]
    exported = client.post(base + "/export", json=body(), headers=headers)
    assert exported.status_code == 200
    assert "attachment" in exported.headers["Content-Disposition"]
    assert len(exported.get_json()["transactions"]) == 1
    assert (
        "password_hash" not in exported.text and "google_subject" not in exported.text
    )
    assert (
        client.delete(
            base, json=body(confirm_username=user["username"]), headers=headers
        ).status_code
        == 422
    )
    assert (
        client.patch(base, json=body(is_active=False), headers=headers).status_code
        == 200
    )
    assert (
        client.delete(
            base, json=body(confirm_username="wrong"), headers=headers
        ).status_code
        == 422
    )
    deleted = client.delete(
        base, json=body(confirm_username=user["username"]), headers=headers
    )
    assert deleted.status_code == 200
    assert client.get(base).status_code == 404
    with app.app_context():
        assert db.session.get(User, other["id"]) is not None
        for model in (
            User,
            Transaction,
            Budget,
            AnalysisRun,
            Forecast,
            AnomalyAlert,
            RecommendationRecord,
        ):
            condition = (
                model.id == user["id"] if model is User else model.user_id == user["id"]
            )
            assert db.session.scalar(select(model).where(condition)) is None
        assert (
            db.session.scalar(
                select(AdminAudit).where(
                    AdminAudit.action == "user.delete",
                    AdminAudit.target_id == user["id"],
                )
            )
            is not None
        )


def test_analysis_pause_preserves_financial_routes_and_persists(client, auth):
    headers = sign_in(client)
    assert (
        client.put(
            BASE + "/settings", json=body(analysis_enabled=False), headers=headers
        ).status_code
        == 200
    )
    assert (
        client.get(BASE + "/settings").get_json()["data"]["analysis_enabled"] is False
    )
    result = client.post("/api/v1/analysis/run", json={}, headers=auth)
    assert result.status_code == 503
    assert result.get_json()["error"]["code"] == "ANALYSIS_PAUSED"
    assert client.get("/api/v1/analytics/dashboard", headers=auth).status_code == 200
    assert (
        client.post(
            "/api/v1/transactions", json=transaction(), headers=auth
        ).status_code
        == 201
    )
    assert (
        client.put(
            BASE + "/settings", json=body(analysis_enabled=True), headers=headers
        ).status_code
        == 200
    )
    assert client.post("/api/v1/analysis/run", json={}, headers=auth).status_code == 200


@pytest.mark.parametrize("mode", ["idle", "absolute", "rotated"])
def test_admin_session_expiry_and_rotation(client, app, mode):
    sign_in(client)
    if mode == "rotated":
        app.config["ADMIN_PASSWORD"] = "changed-admin-password"
    else:
        with client.session_transaction() as state:
            state["admin_last_seen" if mode == "idle" else "admin_started"] = (
                time.time() - 90000
            )
    assert client.get(BASE + "/users").status_code == 401


def test_admin_login_throttle_applies_to_basic_and_session_attempts(client):
    import base64

    token = base64.b64encode(b"admin:wrong").decode()
    for _ in range(10):
        assert (
            client.get(
                BASE + "/overview", headers={"Authorization": "Basic " + token}
            ).status_code
            == 401
        )
    assert client.get(BASE + "/overview", headers=admin_headers()).status_code == 429


def test_management_html_and_security_headers(client):
    sign_in(client)
    page = client.get("/admin/manage")
    assert page.status_code == 200
    assert b"System management" in page.data
    assert page.headers["Cache-Control"] == "no-store"
    assert page.headers["X-Frame-Options"] == "DENY"
    assert client.get(BASE + "/users").headers["Cache-Control"] == "no-store"


def test_audit_is_not_mutable_and_legacy_jwt_remains_valid_until_revocation(
    client, app
):
    from flask_jwt_extended import create_access_token

    user = register(client)["user"]
    with app.app_context():
        old_token = create_access_token(identity=user["id"])
    bearer = {"Authorization": "Bearer " + old_token}
    assert client.get("/api/v1/auth/me", headers=bearer).status_code == 200
    headers = sign_in(client)
    client.post(
        BASE + "/users/" + user["id"] + "/revoke-sessions", json=body(), headers=headers
    )
    assert client.get("/api/v1/auth/me", headers=bearer).status_code == 401
    # No API exists for editing or deleting audit entries.
    assert (
        client.delete(BASE + "/audit/missing", json=body(), headers=headers).status_code
        == 404
    )


def test_partial_validation_failure_cannot_commit_via_later_read(client):
    user = register(client)["user"]
    headers = sign_in(client)
    base = BASE + "/users/" + user["id"]
    response = client.patch(
        base,
        json=body(display_name="Must not persist", is_active="false"),
        headers=headers,
    )
    assert response.status_code == 422
    assert (
        client.get(base).get_json()["data"]["user"]["display_name"]
        == user["display_name"]
    )


def test_audit_failure_rolls_back_financial_write(client, app, monkeypatch):
    from backend.app.routes import admin_management

    user = register(client)["user"]
    headers = sign_in(client)

    def fail(*args, **kwargs):
        raise RuntimeError("Simulated audit persistence failure")

    monkeypatch.setattr(admin_management, "audit", fail)
    response = client.post(
        BASE + "/users/" + user["id"] + "/records/transactions",
        json=body(record=transaction()),
        headers=headers,
    )
    assert response.status_code == 500
    with app.app_context():
        assert (
            db.session.scalar(
                select(Transaction).where(Transaction.user_id == user["id"])
            )
            is None
        )


def test_admin_migration_preserves_existing_accounts(tmp_path):
    from backend.app import create_app
    from flask_migrate import upgrade
    from sqlalchemy import inspect, text
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    application = create_app(
        {
            "TESTING": True,
            "LOAD_MODELS": False,
            "SECRET_KEY": "migration-test-only-secret",
            "JWT_SECRET_KEY": "migration-test-only-jwt",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "migration.db"),
        }
    )
    with application.app_context():
        upgrade(directory="backend/migrations", revision="0004_username_onboarding")
        db.session.execute(
            text(
                "INSERT INTO users (id,email,display_name,username,username_normalized,created_at,is_active,model_training_opt_in) VALUES ('legacy','legacy@example.com','Legacy','legacy','legacy',CURRENT_TIMESTAMP,1,0)"
            )
        )
        db.session.commit()
        upgrade(directory="backend/migrations")
        assert db.session.get(User, "legacy").auth_version == 0
        assert {"admin_audit", "admin_login_attempts", "system_settings"} <= set(
            inspect(db.engine).get_table_names()
        )
        with db.engine.connect() as connection:
            context = MigrationContext.configure(connection)
            differences = compare_metadata(context, db.metadata)
            assert differences == []
