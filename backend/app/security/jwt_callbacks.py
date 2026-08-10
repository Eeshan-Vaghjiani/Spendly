"""JWT callbacks using the shared error contract."""

from __future__ import annotations

from typing import Any

from flask_jwt_extended import JWTManager

from ..errors import error_response


def configure_jwt_callbacks(jwt: JWTManager) -> None:
    @jwt.unauthorized_loader
    def missing(reason: str) -> tuple[Any, int]:
        del reason
        return error_response(
            "UNAUTHORIZED", "A valid access token is required.", 401
        )

    @jwt.invalid_token_loader
    def invalid(reason: str) -> tuple[Any, int]:
        del reason
        return error_response(
            "UNAUTHORIZED", "The access token is invalid.", 401
        )

    @jwt.expired_token_loader
    def expired(header: dict[str, Any], payload: dict[str, Any]) -> tuple[Any, int]:
        del header, payload
        return error_response(
            "TOKEN_EXPIRED", "The access token has expired.", 401
        )
