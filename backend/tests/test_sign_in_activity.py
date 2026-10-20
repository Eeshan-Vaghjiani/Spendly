"""Activity is authenticated success evidence, not presence or request tracking."""
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import select

from backend.app.extensions import db
from backend.app.models import AdminAudit, SignInEvent, User
from backend.tests.conftest import register
from backend.tests.test_admin_management import body, sign_in
from backend.tests.test_analytics_admin import admin_headers

BASE = "/api/v1/admin/users/"


def password_login(client, password="StrongPass123!"):
    return client.post("/api/v1/auth/login", json={
        "email": "eva@example.com", "password": password,
    }, headers={"User-Agent": "untrusted-device-metadata", "X-Forwarded-For": "198.51.100.7"})


def events(app, owner):
    with app.app_context():
        return [row.to_dict() for row in db.session.scalars(
            select(SignInEvent).where(SignInEvent.user_id == owner)
            .order_by(SignInEvent.created_at, SignInEvent.id)
        )]


def test_password_success_is_recorded_but_failure_and_renewal_are_not(app, client):
    account = register(client)
    owner = account["user"]["id"]
    assert events(app, owner)[0]["event"] == "registration"
    assert password_login(client, "incorrect").status_code == 401
    assert client.post("/api/v1/auth/renew", headers={
        "Authorization": "Bearer " + account["access_token"],
    }).status_code == 200
    assert len(events(app, owner)) == 1
    later = datetime(2030, 1, 2, 12)
    with patch("backend.app.routes.auth.utc_now", return_value=later):
        assert password_login(client).status_code == 200
    recorded = events(app, owner)
    assert len(recorded) == 2
    assert recorded[-1] == {
        "id": recorded[-1]["id"], "provider": "password", "event": "sign_in",
        "created_at": "2030-01-02T12:00:00Z",
    }
    with app.app_context():
        assert db.session.get(User, owner).last_signed_in_at == later
    # App auth payloads stay unchanged; activity is an administrator-only view.
    assert "last_signed_in_at" not in account["user"]


def test_out_of_order_success_does_not_move_last_sign_in_backwards(app, client):
    owner = register(client)["user"]["id"]
    later = datetime(2030, 1, 2)
    for moment in [later, later - timedelta(days=1)]:
        with patch("backend.app.routes.auth.utc_now", return_value=moment):
            assert password_login(client).status_code == 200
    assert len(events(app, owner)) == 3
    with app.app_context():
        assert db.session.get(User, owner).last_signed_in_at == later


def test_disabled_password_account_cannot_add_activity(app, client):
    owner = register(client)["user"]["id"]
    with app.app_context():
        db.session.get(User, owner).is_active = False
        db.session.commit()
    assert password_login(client).status_code == 401
    assert len(events(app, owner)) == 1


@patch("backend.app.routes.auth.verify_google_id_token")
def test_google_success_conflicts_and_disabled_accounts(verify, app, client):
    verify.return_value = {
        "sub": "synthetic-activity-subject", "email": "activity@example.invalid",
        "name": "Activity synthetic", "email_verified": True,
    }
    first = client.post("/api/v1/auth/google", json={"id_token": "synthetic-placeholder"})
    assert first.status_code == 200
    owner = first.get_json()["data"]["user"]["id"]
    assert client.post("/api/v1/auth/google", json={"id_token": "synthetic-placeholder"}).status_code == 200
    assert [e["event"] for e in events(app, owner)] == ["registration", "sign_in"]
    assert {e["provider"] for e in events(app, owner)} == {"google"}
    with app.app_context():
        db.session.get(User, owner).is_active = False
        db.session.commit()
    assert client.post("/api/v1/auth/google", json={"id_token": "synthetic-placeholder"}).status_code == 403
    assert len(events(app, owner)) == 2
    existing = register(client)["user"]["id"]
    verify.return_value = {**verify.return_value, "sub": "different-subject", "email": "eva@example.com"}
    assert client.post("/api/v1/auth/google", json={"id_token": "synthetic-placeholder"}).status_code == 409
    assert len(events(app, existing)) == 1
    verify.side_effect = ValueError("invalid synthetic identity")
    assert client.post("/api/v1/auth/google", json={"id_token": "synthetic-placeholder"}).status_code == 401
    assert len(events(app, owner)) == 2


def test_history_requires_admin_and_is_owner_scoped_and_audited(app, client):
    first = register(client)
    second = register(client, email="second@example.invalid")
    owner = first["user"]["id"]
    url = BASE + owner + "/sign-ins"
    for headers in [{}, {"Authorization": "Bearer " + first["access_token"]},
                    {"Authorization": "Bearer " + second["access_token"]}]:
        assert client.get(url, headers=headers).status_code == 401
    result = client.get(url, headers=admin_headers())
    assert result.status_code == 200
    assert result.get_json()["data"]["items"] == events(app, owner)
    with app.app_context():
        audit = db.session.scalar(select(AdminAudit).where(AdminAudit.action == "user.sign_ins.view"))
        assert audit.target_id == owner
        assert audit.details == {"page": 1}
    assert client.get(BASE + "missing/sign-ins", headers=admin_headers()).status_code == 404


def test_history_stable_pagination_and_bounds(app, client):
    owner = register(client)["user"]["id"]
    when = datetime(2030, 1, 1)
    with app.app_context():
        for suffix in ["a", "b", "c"]:
            db.session.add(SignInEvent(id=suffix, user_id=owner, provider="password", event="sign_in", created_at=when))
        db.session.commit()
    url = BASE + owner + "/sign-ins"
    one = client.get(url + "?per_page=2", headers=admin_headers()).get_json()["data"]
    two = client.get(url + "?per_page=2&page=2", headers=admin_headers()).get_json()["data"]
    assert one["total"] == 4 and one["pages"] == 2
    assert [x["id"] for x in one["items"]] == ["a", "b"]
    assert len({x["id"] for x in one["items"] + two["items"]}) == 4
    assert client.get(url + "?per_page=101", headers=admin_headers()).status_code == 422
    assert client.get(url + "?page=0", headers=admin_headers()).status_code == 422


def test_legacy_account_is_unknown_not_fabricated(app, client):
    with app.app_context():
        user = User(email="legacy@example.invalid", display_name="Legacy", username="legacy", username_normalized="legacy")
        db.session.add(user)
        db.session.commit()
        owner = user.id
    detail = client.get(BASE + owner, headers=admin_headers()).get_json()["data"]
    assert detail["user"]["last_signed_in_at"] is None
    history = client.get(BASE + owner + "/sign-ins", headers=admin_headers()).get_json()["data"]
    assert history["total"] == 0 and history["items"] == []


def test_admin_last_sign_in_summary_and_rolling_counts(app, client):
    recent = register(client)["user"]["id"]
    old = register(client, email="old@example.invalid")["user"]["id"]
    with app.app_context():
        db.session.get(User, old).last_signed_in_at = datetime.utcnow() - timedelta(days=31)
        db.session.commit()
    listing = client.get(BASE.rstrip("/"), headers=admin_headers()).get_json()["data"]
    assert next(x for x in listing["items"] if x["id"] == recent)["last_signed_in_at"].endswith("Z")
    overview = client.get("/api/v1/admin/overview", headers=admin_headers()).get_json()["data"]
    assert overview["metrics"]["signed_in_users_7d"] == 1
    assert overview["metrics"]["signed_in_users_30d"] == 1
    assert all("last_signed_in_at" in x for x in overview["recent_users"])


def test_export_and_confirmed_deletion_cover_activity_without_other_users(app, client):
    owner = register(client)["user"]
    other = register(client, email="preserve@example.invalid")["user"]["id"]
    headers = sign_in(client)
    url = BASE + owner["id"]
    export = client.post(url + "/export", headers=headers, json=body()).get_json()
    assert export["sign_ins"] == events(app, owner["id"])
    assert "password_hash" not in export["user"] and "google_subject" not in export["user"]
    assert client.patch(url, headers=headers, json=body(is_active=False)).status_code == 200
    deleted = client.delete(url, headers=headers, json=body(confirm_username=owner["username"]))
    assert deleted.status_code == 200
    assert deleted.get_json()["data"]["deleted_counts"]["sign_in_events"] == 1
    assert events(app, owner["id"]) == []
    assert len(events(app, other)) == 1
    with app.app_context():
        assert db.session.get(User, other) is not None
        assert db.session.scalar(select(AdminAudit).where(AdminAudit.action == "user.delete")) is not None


def test_admin_page_activity_controls_and_presence_wording(client):
    sign_in(client)
    page = client.get("/admin/manage").text
    assert 'id="signins-list"' in page and 'id="refresh-signins"' in page
    assert "not that the user is online" in page
    assert "Token renewals are excluded" in page
    assert "Last sign-in" in page


def test_token_creation_failure_cannot_persist_a_success(app, client):
    owner = register(client)["user"]["id"]
    with patch("backend.app.routes.auth.create_access_token", side_effect=RuntimeError("synthetic token failure")):
        response = password_login(client)
        assert response.status_code == 500 and "data" not in response.get_json()
    assert len(events(app, owner)) == 1


def test_registration_failure_rolls_back_account_and_history(app, client):
    with patch("backend.app.routes.auth.create_access_token", side_effect=RuntimeError("synthetic token failure")):
        response = client.post("/api/v1/auth/register", json={
            "email": "rollback@example.invalid", "password": "SyntheticPass123!",
            "display_name": "Rollback", "accepted_terms": True,
            "accepted_privacy": True, "model_training_opt_in": False,
        })
    assert response.status_code == 500
    with app.app_context():
        # An unrelated later commit in the same session must not persist a failed signup.
        db.session.commit()
        assert db.session.scalar(select(User).where(User.email == "rollback@example.invalid")) is None
        assert db.session.scalar(select(SignInEvent)) is None
