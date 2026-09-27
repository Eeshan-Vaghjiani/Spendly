"""Privileged, audited support operations. Never grants privileges to app JWTs."""

from functools import wraps
import json
import math
from typing import Any

from flask import current_app, jsonify, render_template, request, session
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError

from ..errors import ApiError
from ..extensions import db
from ..models import (
    AdminAudit,
    AnalysisRun,
    AnomalyAlert,
    AlertReview,
    Budget,
    Forecast,
    RecommendationRecord,
    SystemSetting,
    Transaction,
    User,
)
from ..schemas import BudgetSchema
from ..services.transactions import TransactionService
from .admin import (
    ADMIN_CSRF_KEY,
    ADMIN_SESSION_KEY,
    _checked_credentials,
    _count,
    _csrf_token,
    _secure_equal,
    _sum,
    admin_blueprint,
    admin_required,
)
from .auth import USERNAME_PATTERN
from .budgets import apply_budget


def success(data: Any, status: int = 200):
    return jsonify({"success": True, "data": data}), status


def audit(action: str, target_type: str, target_id: str, reason: str, **details: Any):
    db.session.add(
        AdminAudit(
            actor=current_app.config["ADMIN_USERNAME"],
            action=action,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            details=details,
        )
    )


def commit():
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ApiError(
            "ADMIN_CONFLICT",
            "A username or financial record conflicts with an existing record. Refresh and try again.",
            409,
        ) from error


def write_required(view):
    @wraps(view)
    @admin_required
    def wrapped(*args, **kwargs):
        # Basic authentication remains read-only for existing diagnostics.
        if session.get(ADMIN_SESSION_KEY) is not True:
            raise ApiError(
                "ADMIN_SESSION_REQUIRED",
                "Sign in through the admin page before making changes.",
                403,
            )
        expected = session.get(ADMIN_CSRF_KEY, "")
        if not expected or not _secure_equal(
            request.headers.get("X-CSRF-Token", ""), expected
        ):
            raise ApiError("CSRF_INVALID", "Refresh the admin page and try again.", 403)
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise ApiError("VALIDATION_ERROR", "A JSON object is required.", 422)
        reason = payload.get("reason")
        if not isinstance(reason, str) or not 5 <= len(reason.strip()) <= 300:
            raise ApiError(
                "VALIDATION_ERROR",
                "Provide a reason of 5–300 characters. Do not include secrets.",
                422,
            )
        payload["reason"] = reason.strip()
        # Fresh credential check for every privileged write/export.
        password = payload.get("admin_password")
        if not isinstance(password, str) or not _checked_credentials(
            current_app.config["ADMIN_USERNAME"], password
        ):
            raise ApiError(
                "ADMIN_REAUTH_REQUIRED",
                "Confirm your current administrator password.",
                403,
            )
        try:
            return view(payload, *args, **kwargs)
        except Exception:
            db.session.rollback()
            raise

    return wrapped


def exact_fields(payload: dict, allowed: set[str]):
    if set(payload) - allowed - {"reason", "admin_password"}:
        raise ApiError("VALIDATION_ERROR", "Unsupported fields were supplied.", 422)


def get_user(user_id: str, *, lock: bool = False) -> User:
    query = select(User).where(User.id == user_id)
    user = db.session.scalar(query.with_for_update() if lock else query)
    if user is None:
        raise ApiError("NOT_FOUND", "User not found.", 404)
    return user


def user_data(user: User):
    return {
        **user.to_dict(),
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() + "Z",
        "monthly_income": (
            float(user.monthly_income) if user.monthly_income is not None else None
        ),
    }


def paginated(query, serialize):
    page = request.args.get("page", 1, type=int)
    size = request.args.get("per_page", 20, type=int)
    if not 1 <= page <= 100000 or not 1 <= size <= 100:
        raise ApiError("VALIDATION_ERROR", "Invalid page or page size (1–100).", 422)
    result = db.paginate(query, page=page, per_page=size, error_out=False)
    return {
        "items": [serialize(item) for item in result.items],
        "page": page,
        "per_page": size,
        "total": result.total,
        "pages": result.pages,
    }


@admin_blueprint.get("/admin/manage")
@admin_required
def manage():
    return render_template("admin/manage.html", csrf_token=_csrf_token())


@admin_blueprint.get("/api/v1/admin/users")
@admin_required
def users():
    query = select(User)
    search = request.args.get("q", "").strip()[:100].lower()
    if search:
        # Escape wildcard characters: this is literal, parameterised search.
        term = (
            "%" + search.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
        )
        query = query.where(
            or_(
                User.email.ilike(term, escape="!"),
                User.display_name.ilike(term, escape="!"),
                User.username_normalized.ilike(term, escape="!"),
            )
        )
    status = request.args.get("status", "all")
    if status not in {"all", "active", "disabled"}:
        raise ApiError("VALIDATION_ERROR", "Unknown account status.", 422)
    if status != "all":
        query = query.where(User.is_active.is_(status == "active"))
    return success(
        paginated(query.order_by(User.created_at.desc(), User.id), user_data)
    )


@admin_blueprint.get("/api/v1/admin/users/<user_id>")
@admin_required
def user_detail(user_id):
    user = get_user(user_id)
    data = {
        "user": user_data(user),
        "counts": {
            "transactions": _count(Transaction, Transaction.user_id == user_id),
            "budgets": _count(Budget, Budget.user_id == user_id),
            "analyses": _count(AnalysisRun, AnalysisRun.user_id == user_id),
            "alerts": _count(AnomalyAlert, AnomalyAlert.user_id == user_id),
        },
        "income": _sum(
            Transaction.amount,
            Transaction.user_id == user_id,
            Transaction.transaction_type == "income",
        ),
        "expense": _sum(
            Transaction.amount,
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
        ),
    }
    audit("user.view", "user", user_id, "Support account detail viewed")
    commit()
    return success(data)


RECORDS = {
    "transactions": (Transaction, Transaction.transaction_timestamp),
    "budgets": (Budget, Budget.period_start),
    "forecasts": (Forecast, Forecast.created_at),
    "alerts": (AnomalyAlert, AnomalyAlert.created_at),
    "recommendations": (RecommendationRecord, RecommendationRecord.created_at),
}


@admin_blueprint.get("/api/v1/admin/users/<user_id>/records/<kind>")
@admin_required
def records(user_id, kind):
    get_user(user_id)
    if kind not in RECORDS:
        raise ApiError("NOT_FOUND", "Unknown record type.", 404)
    model, order = RECORDS[kind]
    data = paginated(
        select(model).where(model.user_id == user_id).order_by(order.desc(), model.id),
        lambda row: row.to_dict(),
    )
    audit(
        "records.view",
        "user",
        user_id,
        "Support records viewed",
        kind=kind,
        page=data["page"],
    )
    commit()
    return success(data)


@admin_blueprint.patch("/api/v1/admin/users/<user_id>")
@write_required
def update_user(payload, user_id):
    exact_fields(payload, {"display_name", "username", "is_active"})
    user = get_user(user_id, lock=True)
    changed = []
    for field in ("display_name", "username"):
        if field in payload:
            value = payload[field]
            if not isinstance(value, str):
                raise ApiError("VALIDATION_ERROR", "Profile fields must be text.", 422)
            value = value.strip()
            if (field == "username" and not USERNAME_PATTERN.fullmatch(value)) or (
                field == "display_name" and not 1 <= len(value) <= 100
            ):
                raise ApiError(
                    "VALIDATION_ERROR",
                    "Use a name of 1–100 characters and a username of 3–30 letters, digits or underscores.",
                    422,
                )
            if getattr(user, field) != value:
                setattr(user, field, value)
                changed.append(field)
            if field == "username":
                user.username_normalized = value.casefold()
    if "is_active" in payload:
        if type(payload["is_active"]) is not bool:
            raise ApiError("VALIDATION_ERROR", "is_active must be true or false.", 422)
        if user.is_active != payload["is_active"]:
            user.is_active = payload["is_active"]
            user.auth_version += 1
            changed.append("is_active")
    if not changed:
        raise ApiError("UNCHANGED", "No changes to save.", 422)
    audit("user.update", "user", user_id, payload["reason"], changed_fields=changed)
    commit()
    return success(user_data(user))


@admin_blueprint.post("/api/v1/admin/users/<user_id>/revoke-sessions")
@write_required
def revoke_sessions(payload, user_id):
    exact_fields(payload, set())
    user = get_user(user_id, lock=True)
    user.auth_version += 1
    audit("user.revoke_sessions", "user", user_id, payload["reason"])
    commit()
    return success(
        {
            "message": "All previous access tokens are revoked. The user must sign in again."
        }
    )


@admin_blueprint.delete("/api/v1/admin/users/<user_id>")
@write_required
def delete_user(payload, user_id):
    exact_fields(payload, {"confirm_username"})
    user = get_user(user_id, lock=True)
    if user.is_active or payload.get("confirm_username") != user.username:
        raise ApiError(
            "CONFIRMATION_REQUIRED",
            "Disable this account first, then type its exact username to confirm permanent deletion.",
            422,
        )
    counts = {}
    for model in (
        AlertReview,
        RecommendationRecord,
        AnomalyAlert,
        Forecast,
        AnalysisRun,
        Budget,
        Transaction,
    ):
        counts[model.__tablename__] = _count(model, model.user_id == user_id)
        db.session.execute(delete(model).where(model.user_id == user_id))
    db.session.execute(delete(User).where(User.id == user_id))
    audit("user.delete", "user", user_id, payload["reason"], deleted_counts=counts)
    commit()
    return success({"deleted_id": user_id, "deleted_counts": counts})


def validate_money(payload):
    value = payload.get("amount")
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not 0.01 <= value <= 999999999999.99
    ):
        raise ApiError(
            "VALIDATION_ERROR",
            "Amount must be between 0.01 and 999999999999.99 KES.",
            422,
        )
    if not isinstance(payload.get("category"), str) or not payload["category"].strip():
        raise ApiError("VALIDATION_ERROR", "Category cannot be blank.", 422)


@admin_blueprint.route("/api/v1/admin/users/<user_id>/records/<kind>", methods=["POST"])
@admin_blueprint.route(
    "/api/v1/admin/users/<user_id>/records/<kind>/<record_id>",
    methods=["PUT", "DELETE"],
)
@write_required
def change_record(payload, user_id, kind, record_id=None):
    exact_fields(payload, {"record", "confirm_id"})
    get_user(user_id, lock=True)
    if kind not in {"transactions", "budgets"}:
        raise ApiError(
            "NOT_FOUND", "Only transactions and budgets can be corrected.", 404
        )
    model = RECORDS[kind][0]
    row = None
    if record_id:
        row = db.session.scalar(
            select(model)
            .where(model.id == record_id, model.user_id == user_id)
            .with_for_update()
        )
        if row is None:
            raise ApiError("NOT_FOUND", "Record not found for this user.", 404)
    if request.method == "DELETE":
        if payload.get("confirm_id") != record_id:
            raise ApiError("CONFIRMATION_REQUIRED", "Confirm the exact record ID.", 422)
        if kind == "transactions":
            db.session.execute(delete(AlertReview).where(AlertReview.user_id == user_id, AlertReview.transaction_id == record_id))
            db.session.execute(
                update(AnomalyAlert)
                .where(AnomalyAlert.transaction_id == record_id)
                .values(transaction_id=None)
            )
        db.session.delete(row)
    else:
        data = payload.get("record")
        if not isinstance(data, dict):
            raise ApiError("VALIDATION_ERROR", "A record object is required.", 422)
        validate_money(data)
        if kind == "transactions":
            row = (
                TransactionService.update(row, data, commit=False)
                if row
                else TransactionService.create(
                    user_id, data, source="admin", commit=False
                )
            )
        else:
            data = BudgetSchema().load(data)
            row = row or Budget(user_id=user_id)
            apply_budget(row, data)
            db.session.add(row)
    # Flush inside the same error/rollback boundary as the audit entry.
    try:
        db.session.flush()
    except IntegrityError as error:
        db.session.rollback()
        raise ApiError(
            "ADMIN_CONFLICT", "This record conflicts with an existing record.", 409
        ) from error
    audit(
        f"{kind}.{request.method.lower()}",
        kind,
        row.id,
        payload["reason"],
        user_id=user_id,
    )
    result = {"deleted_id": record_id} if request.method == "DELETE" else row.to_dict()
    commit()
    return success(result, 201 if request.method == "POST" else 200)


@admin_blueprint.post("/api/v1/admin/users/<user_id>/export")
@write_required
def export_user(payload, user_id):
    exact_fields(payload, set())
    user = get_user(user_id)
    # Bounded export; fail explicitly rather than silently truncating a backup.
    total = sum(
        _count(model, model.user_id == user_id) for model, _ in RECORDS.values()
    )
    if total > 50000:
        raise ApiError(
            "EXPORT_TOO_LARGE",
            "This account exceeds 50,000 records. Arrange a secure database export.",
            413,
        )
    data = {"user": user_data(user)}
    for kind, (model, order) in RECORDS.items():
        data[kind] = [
            row.to_dict()
            for row in db.session.scalars(
                select(model).where(model.user_id == user_id).order_by(order, model.id)
            )
        ]
    audit("user.export", "user", user_id, payload["reason"], records=total)
    commit()
    response = current_app.response_class(json.dumps(data), mimetype="application/json")
    response.headers["Content-Disposition"] = (
        f'attachment; filename="spendly-user-{user_id}.json"'
    )
    return response


@admin_blueprint.get("/api/v1/admin/audit")
@admin_required
def audit_log():
    query = select(AdminAudit)
    if request.args.get("target_id"):
        query = query.where(AdminAudit.target_id == request.args["target_id"])
    return success(
        paginated(
            query.order_by(AdminAudit.created_at.desc(), AdminAudit.id),
            lambda row: row.to_dict(),
        )
    )


@admin_blueprint.get("/api/v1/admin/settings")
@admin_required
def settings():
    setting = db.session.get(SystemSetting, "analysis_enabled")
    registry = current_app.extensions.get("model_registry")
    return success(
        {
            "analysis_enabled": setting.enabled if setting else True,
            "model_runtime": current_app.config["MODEL_RUNTIME"],
            "models_loaded": bool(registry and registry.loaded),
            "model_info": registry.info() if registry and registry.loaded else {},
        }
    )


@admin_blueprint.put("/api/v1/admin/settings")
@write_required
def update_settings(payload):
    exact_fields(payload, {"analysis_enabled"})
    if type(payload.get("analysis_enabled")) is not bool:
        raise ApiError(
            "VALIDATION_ERROR", "analysis_enabled must be true or false.", 422
        )
    row = db.session.get(SystemSetting, "analysis_enabled")
    before = row.enabled if row else True
    if before == payload["analysis_enabled"]:
        raise ApiError("UNCHANGED", "No changes to save.", 422)
    row = row or SystemSetting(key="analysis_enabled")
    row.enabled = payload["analysis_enabled"]
    db.session.add(row)
    audit(
        "system.analysis_enabled",
        "system",
        "analysis_enabled",
        payload["reason"],
        before=before,
        after=row.enabled,
    )
    commit()
    return success({"analysis_enabled": row.enabled})
