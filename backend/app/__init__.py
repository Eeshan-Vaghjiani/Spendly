"""Production-structured Flask application factory."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask

from .config import Config
from .errors import register_error_handlers
from .extensions import cors, db, jwt, migrate
from .retention import register_retention_command
from .routes import register_blueprints
from .security.jwt_callbacks import configure_jwt_callbacks
from .services.model_registry import ModelRegistry


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get("TESTING"):
        missing = [
            name
            for name in (
                "SECRET_KEY",
                "JWT_SECRET_KEY",
                "SQLALCHEMY_DATABASE_URI",
            )
            if not app.config.get(name)
        ]
        if missing:
            raise RuntimeError(
                "Missing required environment configuration: "
                + ", ".join(missing)
            )
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    configure_jwt_callbacks(jwt)
    cors.init_app(
        app,
        resources={
            r"/api/v1/*": {
                "origins": app.config["ALLOWED_CORS_ORIGINS"]
            }
        },
    )
    register_error_handlers(app)
    register_blueprints(app)
    register_retention_command(app)
    if app.config.get("SELECTED_MODEL_ROOT"):
        from .services.selected_registry import SelectedModelRegistry
        registry = SelectedModelRegistry(app.config["MODEL_ROOT"],app.config["SELECTED_MODEL_ROOT"])
    else:
        registry = ModelRegistry(
            app.config["MODEL_ROOT"],app.config["FORECAST_MODEL_VERSION"],
            app.config["ANOMALY_MODEL_VERSION"],app.config["MODEL_RUNTIME"],
        )
    if app.config.get("LOAD_MODELS", True):
        registry.load()
    app.extensions["model_registry"] = registry
    logging.getLogger(__name__).info("Flask application initialised.")
    return app
