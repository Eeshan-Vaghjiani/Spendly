"""Combined analysis and stored result-history routes."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..errors import ApiError
from ..extensions import db
from ..models import AnalysisRun, SystemSetting, AnomalyAlert, AlertReview, Transaction, utc_now
from ..repositories import HistoryRepository
from ..security.current_user import current_user
from ..services.analysis import AnalysisService
from ..services.alert_review import alert_payload, review_version

analysis_blueprint = Blueprint("analysis", __name__)


def analysis_service() -> AnalysisService:
    registry = current_app.extensions["model_registry"]
    return AnalysisService(registry)


@analysis_blueprint.post("/analysis/run")
@jwt_required()
def run_analysis() -> tuple[Any, int]:
    user = current_user()
    setting = db.session.get(SystemSetting, "analysis_enabled")
    if setting is not None and not setting.enabled:
        raise ApiError(
            "ANALYSIS_PAUSED",
            "New insights are temporarily paused by the administrator. Your records remain available.",
            503,
        )
    payload = request.get_json(silent=True) or {}
    if payload.get("use_stored_transactions", True) is not True:
        raise ApiError(
            "UNSUPPORTED_ANALYSIS_INPUT",
            "This version analyses the authenticated user's stored transactions.",
            422,
        )
    result = analysis_service().run(user, observed_from=payload.get("history_complete_from"))
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
        raise ApiError("NOT_FOUND", "No stored analysis is available.", 404)
    return (
        jsonify({"success": True, "data": AnalysisService.latest(run)}),
        200,
    )


def history(kind: str) -> tuple[Any, int]:
    user = current_user()
    page = max(1, request.args.get("page", default=1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", default=20, type=int)))
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
                        (
                            AnalysisService.forecast_payload(item)
                            if kind == "forecasts"
                            else alert_payload(item) if kind == "alerts" else item.to_dict()
                        )
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


@analysis_blueprint.put("/alerts/<string:alert_id>/review")
@jwt_required()
def review_alert(alert_id: str) -> tuple[Any, int]:
    user = current_user()
    payload = request.get_json(silent=True)
    if (not isinstance(payload, dict) or set(payload) != {"status", "transaction_review_version"}
            or not isinstance(payload["status"], str) or payload["status"] not in {"intentional", "pending"}
            or not isinstance(payload["transaction_review_version"], str)):
        raise ApiError("VALIDATION_ERROR", "Choose intentional or pending review status.", 422)
    alert = db.session.scalar(select(AnomalyAlert).where(AnomalyAlert.id == alert_id, AnomalyAlert.user_id == user.id))
    if alert is None:
        raise ApiError("NOT_FOUND", "The requested alert was not found.", 404)
    transaction = db.session.scalar(select(Transaction).where(
        Transaction.id == alert.transaction_id, Transaction.user_id == user.id).with_for_update()) if alert.transaction_id else None
    if transaction is None or transaction.user_id != user.id:
        raise ApiError("NOT_FOUND", "The linked transaction is no longer available.", 404)
    if payload["transaction_review_version"] != review_version(transaction):
        raise ApiError("TRANSACTION_CHANGED", "This transaction changed. Reopen it before confirming.", 409)
    review = db.session.scalar(select(AlertReview).where(AlertReview.user_id == user.id, AlertReview.transaction_id == transaction.id))
    if review is None:
        review = AlertReview(user_id=user.id, transaction_id=transaction.id)
        db.session.add(review)
    review.transaction_fingerprint = review_version(transaction)
    review.status = payload["status"]
    review.reviewed_at = utc_now()
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ApiError("REVIEW_CONFLICT", "Another review was saved. Refresh this alert and try again.", 409) from error
    return jsonify({"success": True, "data": alert_payload(alert)}), 200


@analysis_blueprint.get("/recommendations")
@jwt_required()
def recommendations() -> tuple[Any, int]:
    return history("recommendations")
