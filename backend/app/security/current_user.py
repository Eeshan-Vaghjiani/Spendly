"""Resolve the authenticated active user."""

from __future__ import annotations

from flask_jwt_extended import get_jwt, get_jwt_identity

from ..errors import ApiError
from ..extensions import db
from ..models import User


def current_user(*, require_consent: bool = True) -> User:
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if user is None or not user.is_active or get_jwt().get("ver", 0) != user.auth_version:
        raise ApiError(
            "UNAUTHORIZED", "A valid access token is required.", 401
        )
    if require_consent and not (
        user.terms_accepted_at and user.privacy_accepted_at
    ):
        raise ApiError(
            "CONSENT_REQUIRED",
            "Review and accept the required data-use terms before continuing.",
            403,
        )
    return user
