"""Combined analysis and stored result-history routes."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select

from ..errors import ApiError
from ..extensions import db
from ..models import AnalysisRun
from ..repositories import HistoryRepository
from ..security.current_user import current_user
from ..services.analysis import AnalysisService


analysis_blueprint = Blueprint("analysis", __name__)


def analysis_service() -> AnalysisService:
    registry = current_app.extensions["model_registry"]
    return AnalysisService(registry)


@analysis_blueprint.post("/analysis/run")
@jwt_required()
def run_analysis() -> tuple[Any, int]:
    payload = request.get_json(silent=True) or {}
    if payload.get("use_stored_transactions", True) is not True:
        raise ApiError(
            "UNSUPPORTED_ANALYSIS_INPUT",
            "This version analyses the authenticated user's stored transactions.",
            422,
        )
    result = analysis_service().run(current_user())
    return jsonify({"success": True, "data": result}), 200


@analysis_blueprint.get("/analysis/latest")
@jwt_required()
def latest_analysis() -> tuple[Any, int]:
    user = current_user()
    run = db.session.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.user_id == user.id)
        .order_by(AnalysisRun.generated_at.desc())
        .limit(1)
    )
    if run is None:
        raise ApiError(
            "NOT_FOUND", "No stored analysis is available.", 404
        )
    return (
        jsonify(
            {"success": True, "data": AnalysisService.latest(run)}
        ),
        200,
    )


def history(kind: str) -> tuple[Any, int]:
    user = current_user()
    page = max(1, request.args.get("page", default=1, type=int))
    per_page = min(
        100, max(1, request.args.get("per_page", default=20, type=int))
    )
    pagination = db.paginate(
        HistoryRepository.query(kind, user.id),
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "items": [
                        AnalysisService.forecast_payload(item)
                        if kind == "forecasts"
                        else item.to_dict()
                        for item in pagination.items
                    ],
                    "page": page,
                    "per_page": per_page,
                    "total": pagination.total,
                },
            }
        ),
        200,
    )


@analysis_blueprint.get("/forecasts")
@jwt_required()
def forecasts() -> tuple[Any, int]:
    return history("forecasts")


@analysis_blueprint.get("/alerts")
@jwt_required()
def alerts() -> tuple[Any, int]:
    return history("alerts")


@analysis_blueprint.get("/recommendations")
@jwt_required()
def recommendations() -> tuple[Any, int]:
    return history("recommendations")
