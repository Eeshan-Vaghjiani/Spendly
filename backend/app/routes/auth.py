"""Registration, login, and current-user routes."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..errors import ApiError
from ..extensions import db
from ..models import User, utc_now
from ..schemas import ConsentSchema, GoogleLoginSchema, LoginSchema, RegisterSchema
from ..security.current_user import current_user
from ..security.google_identity import verify_google_id_token


auth_blueprint = Blueprint("auth", __name__)
register_schema = RegisterSchema()
login_schema = LoginSchema()
google_login_schema = GoogleLoginSchema()
consent_schema = ConsentSchema()
CONSENT_VERSION = "2026-08-02"


def auth_payload(user: User) -> dict[str, Any]:
    expiry = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    expires_in = int(
        expiry.total_seconds() if isinstance(expiry, timedelta) else expiry
    )
    return {
        "access_token": create_access_token(identity=user.id),
        "token_type": "Bearer",
        "expires_in": expires_in,
        "user": user.to_dict(),
    }


@auth_blueprint.post("/auth/register")
def register() -> tuple[Any, int]:
    payload = register_schema.load(request.get_json(silent=True) or {})
    email = payload["email"].strip().lower()
    if db.session.scalar(select(User).where(User.email == email)):
        raise ApiError(
            "EMAIL_ALREADY_REGISTERED",
            "An account with this email already exists.",
            409,
        )
    user = User(
        email=email,
        display_name=payload["display_name"].strip(),
        password_hash=generate_password_hash(payload["password"]),
        terms_accepted_at=utc_now(),
        privacy_accepted_at=utc_now(),
        consent_version=CONSENT_VERSION,
        model_training_opt_in=payload["model_training_opt_in"],
        model_training_consented_at=(
            utc_now() if payload["model_training_opt_in"] else None
        ),
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ApiError(
            "EMAIL_ALREADY_REGISTERED",
            "An account with this email already exists.",
            409,
        ) from error
    return jsonify({"success": True, "data": auth_payload(user)}), 201


@auth_blueprint.post("/auth/login")
def login() -> tuple[Any, int]:
    payload = login_schema.load(request.get_json(silent=True) or {})
    user = db.session.scalar(
        select(User).where(User.email == payload["email"].strip().lower())
    )
    if (
        user is None
        or not user.is_active
        or not user.password_hash
        or not check_password_hash(user.password_hash, payload["password"])
    ):
        raise ApiError(
            "INVALID_CREDENTIALS", "Email or password is incorrect.", 401
        )
    return jsonify({"success": True, "data": auth_payload(user)}), 200


@auth_blueprint.post("/auth/google")
def google_login() -> tuple[Any, int]:
    payload = google_login_schema.load(request.get_json(silent=True) or {})
    audience = current_app.config.get("GOOGLE_WEB_CLIENT_ID")
    if not audience:
        raise ApiError(
            "GOOGLE_AUTH_NOT_CONFIGURED",
            "Google sign-in is not configured for this deployment.",
            503,
        )
    try:
        claims = verify_google_id_token(payload["id_token"], audience)
    except ValueError as error:
        raise ApiError(
            "INVALID_GOOGLE_TOKEN",
            "Google could not verify this sign-in. Please try again.",
            401,
        ) from error

    subject = str(claims["sub"])
    email = str(claims["email"]).strip().lower()
    user = db.session.scalar(select(User).where(User.google_subject == subject))
    if user is None:
        user = db.session.scalar(select(User).where(User.email == email))
        if user is not None and user.google_subject not in (None, subject):
            raise ApiError(
                "GOOGLE_ACCOUNT_CONFLICT",
                "This email is already linked to a different Google account.",
                409,
            )
        if user is None:
            display_name = str(claims.get("name") or email.split("@", 1)[0])
            user = User(
                email=email,
                display_name=display_name[:100],
                password_hash=None,
                google_subject=subject,
                is_active=True,
            )
            db.session.add(user)
        else:
            user.google_subject = subject

    if not user.is_active:
        raise ApiError("ACCOUNT_DISABLED", "This account is disabled.", 403)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ApiError(
            "GOOGLE_ACCOUNT_CONFLICT",
            "This Google account is already linked to another user.",
            409,
        ) from error
    return jsonify({"success": True, "data": auth_payload(user)}), 200


@auth_blueprint.get("/auth/me")
@jwt_required()
def me() -> tuple[Any, int]:
    return (
        jsonify(
            {
                "success": True,
                "data": current_user(require_consent=False).to_dict(),
            }
        ),
        200,
    )


@auth_blueprint.post("/auth/renew")
@jwt_required()
def renew_session() -> tuple[Any, int]:
    user = current_user(require_consent=False)
    return jsonify({"success": True, "data": auth_payload(user)}), 200


@auth_blueprint.put("/auth/consent")
@jwt_required()
def update_consent() -> tuple[Any, int]:
    payload = consent_schema.load(request.get_json(silent=True) or {})
    user = current_user(require_consent=False)
    accepted_at = utc_now()
    user.terms_accepted_at = accepted_at
    user.privacy_accepted_at = accepted_at
    user.consent_version = CONSENT_VERSION
    user.model_training_opt_in = payload["model_training_opt_in"]
    user.model_training_consented_at = (
        accepted_at if payload["model_training_opt_in"] else None
    )
    db.session.commit()
    return jsonify({"success": True, "data": user.to_dict()}), 200
