"""Register API v1 route blueprints."""

from __future__ import annotations

from flask import Flask

from .admin import admin_blueprint
from .analysis import analysis_blueprint
from .analytics import analytics_blueprint
from .auth import auth_blueprint
from .budgets import budget_blueprint
from .system import system_blueprint
from .transactions import transaction_blueprint


def register_blueprints(app: Flask) -> None:
    for blueprint in (
        auth_blueprint,
        transaction_blueprint,
        budget_blueprint,
        analysis_blueprint,
        analytics_blueprint,
        system_blueprint,
    ):
        app.register_blueprint(blueprint, url_prefix="/api/v1")
    app.register_blueprint(admin_blueprint)
