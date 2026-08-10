"""Unauthenticated health and non-sensitive model metadata routes."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from ..extensions import db


system_blueprint = Blueprint("system", __name__)


@system_blueprint.get("/health")
def health() -> tuple[Any, int]:
    database = "connected"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        database = "unavailable"
    registry = current_app.extensions.get("model_registry")
    models_loaded = bool(registry and registry.loaded)
    healthy = database == "connected" and models_loaded
    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "status": "healthy" if healthy else "degraded",
                    "database": database,
                    "forecasting_model": (
                        "loaded" if models_loaded else "unavailable"
                    ),
                    "anomaly_model": (
                        "loaded" if models_loaded else "unavailable"
                    ),
                },
            }
        ),
        200 if healthy else 503,
    )


@system_blueprint.get("/model-info")
def model_info() -> tuple[Any, int]:
    registry = current_app.extensions["model_registry"]
    if not registry.loaded:
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "MODELS_UNAVAILABLE",
                        "message": "Model artefacts are not loaded.",
                    },
                }
            ),
            503,
        )
    return jsonify({"success": True, "data": registry.info()}), 200
