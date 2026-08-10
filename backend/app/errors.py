"""Consistent API error responses."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import RequestEntityTooLarge


LOGGER = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def error_response(
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> tuple[Any, int]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return jsonify({"success": False, "error": error}), status_code


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> tuple[Any, int]:
        return error_response(
            error.code, error.message, error.status_code, error.details
        )

    @app.errorhandler(ValidationError)
    def handle_validation(error: ValidationError) -> tuple[Any, int]:
        return error_response(
            "VALIDATION_ERROR",
            "One or more request fields are invalid.",
            422,
            error.messages,
        )

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(error: RequestEntityTooLarge) -> tuple[Any, int]:
        del error
        return error_response(
            "FILE_TOO_LARGE",
            "The uploaded CSV exceeds the configured size limit.",
            413,
        )

    @app.errorhandler(404)
    def handle_not_found(error: Exception) -> tuple[Any, int]:
        del error
        return error_response(
            "NOT_FOUND", "The requested resource was not found.", 404
        )

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception) -> tuple[Any, int]:
        LOGGER.exception(
            "Unhandled API error of type %s.", type(error).__name__
        )
        return error_response(
            "INTERNAL_ERROR",
            "The request could not be completed.",
            500,
        )
