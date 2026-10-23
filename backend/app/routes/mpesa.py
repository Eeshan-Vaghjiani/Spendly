"""Authenticated optional SMS consent and normalized-event ingestion."""
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from marshmallow import ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..errors import ApiError, error_response
from ..extensions import db
from ..models import User, utc_now
from ..security.current_user import current_user
from ..services.mpesa_import import SMS_CONSENT_VERSION, event_hash, find_event, import_event, normalized_event

mpesa_blueprint = Blueprint("mpesa", __name__)


@mpesa_blueprint.errorhandler(SQLAlchemyError)
def sanitized_storage_failure(error):
    # Database exceptions can contain bound financial parameters. Never pass
    # them to the global traceback logger or expose them in an API response.
    db.session.rollback()
    return error_response("SMS_STORE_RETRY", "Import storage is temporarily unavailable. Retry the same source events safely.", 503)


def locked_user():
    user = current_user()
    # Acquire the write boundary before reading consent. SELECT FOR UPDATE
    # alone is ignored by SQLite; a no-op UPDATE also serializes its writers.
    db.session.execute(update(User).where(User.id == user.id)
        .values(mpesa_sms_import_enabled=User.mpesa_sms_import_enabled)
        .execution_options(synchronize_session=False))
    user = db.session.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    if user is None or not user.is_active or get_jwt().get("ver", 0) != user.auth_version:
        raise ApiError("UNAUTHORIZED", "Sign in again before importing.", 401)
    return user


def settings(user):
    return {"account_id": user.id, "available": bool(current_app.config["MPESA_SMS_ENABLED"]),
            "enabled": user.mpesa_sms_import_enabled,
            "consent_version": user.mpesa_sms_consent_version,
            "required_consent_version": SMS_CONSENT_VERSION,
            "consented_at": user.mpesa_sms_consented_at.isoformat() + "Z" if user.mpesa_sms_consented_at else None}


@mpesa_blueprint.get("/mpesa/settings")
@jwt_required()
def get_settings():
    return jsonify(success=True, data=settings(current_user()))


@mpesa_blueprint.put("/mpesa/settings")
@jwt_required()
def update_settings():
    user = locked_user()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) - {"enabled", "disclosure_accepted", "consent_version"} or type(payload.get("enabled")) is not bool:
        raise ApiError("VALIDATION_ERROR", "Choose whether to enable SMS import.", 422)
    if payload["enabled"]:
        if not current_app.config["MPESA_SMS_ENABLED"]:
            raise ApiError("SMS_UNAVAILABLE", "SMS import is not enabled on this service.", 503)
        if payload.get("disclosure_accepted") is not True or payload.get("consent_version") != SMS_CONSENT_VERSION:
            raise ApiError("SMS_CONSENT_REQUIRED", "Read and accept the SMS disclosure first.", 422)
        user.mpesa_sms_consented_at = utc_now()
        user.mpesa_sms_consent_version = SMS_CONSENT_VERSION
    user.mpesa_sms_import_enabled = payload["enabled"]
    db.session.commit()
    return jsonify(success=True, data=settings(user))


@mpesa_blueprint.post("/transactions/mpesa/import")
@jwt_required()
def import_events():
    user = locked_user()
    if not current_app.config["MPESA_SMS_ENABLED"]:
        raise ApiError("SMS_UNAVAILABLE", "SMS import is not enabled on this service.", 503)
    if not user.mpesa_sms_import_enabled or user.mpesa_sms_consent_version != SMS_CONSENT_VERSION:
        raise ApiError("SMS_CONSENT_REQUIRED", "Enable SMS import and accept its disclosure first.", 403)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"events"} or not isinstance(payload["events"], list) or not 1 <= len(payload["events"]) <= 50:
        raise ApiError("VALIDATION_ERROR", "Supply between 1 and 50 normalized events.", 422)
    summary = {"received": len(payload["events"]), "created": 0, "duplicate": 0, "invalid": 0, "needs_review": 0, "reversals": 0, "results": []}
    for index, raw in enumerate(payload["events"]):
        try:
            event = normalized_event(raw)
            with db.session.begin_nested():
                result = import_event(user.id, event)
                db.session.flush()
        except (ValueError, ValidationError) as error:
            result = {"status": "invalid", "code": str(error) if isinstance(error, ValueError) else "INVALID_EVENT"}
        except IntegrityError:
            existing = find_event(user.id, event["external_reference"])
            result = {"status": "duplicate", "created_transactions": 0} if existing and existing.payload_hash == event_hash(event) else {"status": "invalid", "code": "IMPORT_CONFLICT"}
        status = result["status"]
        summary["created"] += result.get("created_transactions", 0)
        if result.get("review_required"):
            summary["needs_review"] += 1
        if status in {"duplicate", "invalid", "needs_review"}:
            summary[status] += 1
        elif status in {"reversed", "pending_reversal", "reconciled"}:
            summary["reversals"] += 1
        summary["results"].append({"index": index, **result})
    db.session.commit()
    return jsonify(success=True, data=summary)
