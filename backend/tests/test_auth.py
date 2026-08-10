from __future__ import annotations

from unittest.mock import patch

from backend.app.extensions import db
from backend.app.models import User

from .conftest import register


def test_register_login_and_me(client) -> None:
    registered = register(client)
    assert registered["user"]["email"] == "eva@example.com"
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "EVA@example.com",
            "password": "StrongPass123!",
        },
    )
    assert login.status_code == 200
    token = login.get_json()["data"]["access_token"]
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.get_json()["data"]["display_name"] == "Eva"
    renewed = client.post(
        "/api/v1/auth/renew",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert renewed.status_code == 200
    assert renewed.get_json()["data"]["user"]["email"] == "eva@example.com"
    assert renewed.get_json()["data"]["access_token"] != token


def test_duplicate_registration_uses_error_contract(client) -> None:
    register(client)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "eva@example.com",
            "password": "StrongPass123!",
            "display_name": "Other",
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert response.status_code == 409
    assert response.get_json() == {
        "success": False,
        "error": {
            "code": "EMAIL_ALREADY_REGISTERED",
            "message": "An account with this email already exists.",
        },
    }


def test_invalid_login_does_not_reveal_account_state(client) -> None:
    register(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "eva@example.com", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_CREDENTIALS"


@patch("backend.app.routes.auth.verify_google_id_token")
def test_google_login_creates_local_account_requiring_consent(verify, client) -> None:
    verify.return_value = {
        "sub": "google-subject-1",
        "email": "google.user@example.com",
        "email_verified": True,
        "name": "Google User",
        "iss": "https://accounts.google.com",
    }
    response = client.post(
        "/api/v1/auth/google",
        json={"id_token": "verified-google-token-placeholder"},
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["user"]["email"] == "google.user@example.com"
    assert data["user"]["login_provider"] == "google"
    assert data["user"]["has_required_consents"] is False
    with client.application.app_context():
        user = db.session.scalar(
            db.select(User).where(User.google_subject == "google-subject-1")
        )
        assert user is not None
        assert user.password_hash is None


@patch("backend.app.routes.auth.verify_google_id_token")
def test_google_login_safely_links_matching_verified_email(verify, client) -> None:
    registered = register(client)
    verify.return_value = {
        "sub": "google-subject-linked",
        "email": registered["user"]["email"],
        "email_verified": True,
        "name": "Eva",
        "iss": "accounts.google.com",
    }
    response = client.post(
        "/api/v1/auth/google",
        json={"id_token": "verified-google-token-placeholder"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["user"]["id"] == registered["user"]["id"]
    with client.application.app_context():
        assert db.session.get(User, registered["user"]["id"]).google_subject == (
            "google-subject-linked"
        )


@patch("backend.app.routes.auth.verify_google_id_token")
def test_invalid_google_token_uses_safe_error_contract(verify, client) -> None:
    verify.side_effect = ValueError("expired")
    response = client.post(
        "/api/v1/auth/google",
        json={"id_token": "invalid-google-token-placeholder"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"] == {
        "code": "INVALID_GOOGLE_TOKEN",
        "message": "Google could not verify this sign-in. Please try again.",
    }


def test_protected_route_requires_token(client) -> None:
    response = client.get("/api/v1/transactions")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_registration_requires_service_and_privacy_acceptance(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "no-consent@example.com",
            "password": "StrongPass123!",
            "display_name": "No Consent",
            "accepted_terms": False,
            "accepted_privacy": True,
        },
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_registration_enforces_each_password_rule(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "password": "alllowercase123",
            "display_name": "Weak Password",
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_existing_user_is_blocked_until_required_consent_is_recorded(client) -> None:
    registered = register(client)
    with client.application.app_context():
        user = db.session.get(User, registered["user"]["id"])
        user.terms_accepted_at = None
        user.privacy_accepted_at = None
        db.session.commit()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    blocked = client.get("/api/v1/transactions", headers=headers)
    assert blocked.status_code == 403
    assert blocked.get_json()["error"]["code"] == "CONSENT_REQUIRED"
    consent = client.put(
        "/api/v1/auth/consent",
        json={
            "accepted_terms": True,
            "accepted_privacy": True,
            "model_training_opt_in": False,
        },
        headers=headers,
    )
    assert consent.status_code == 200
    assert consent.get_json()["data"]["has_required_consents"] is True
    assert client.get("/api/v1/transactions", headers=headers).status_code == 200
