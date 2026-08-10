"""Password-protected operational dashboard for the project administrator."""

from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func, select

from ..extensions import db
from ..models import (
    AnalysisRun,
    AnomalyAlert,
    Budget,
    Forecast,
    Transaction,
    User,
)


admin_blueprint = Blueprint("admin", __name__)
View = TypeVar("View", bound=Callable[..., Any])
ADMIN_SESSION_KEY = "spendly_admin_authenticated"
ADMIN_CSRF_KEY = "spendly_admin_csrf"


def _unauthorized() -> Response:
    return Response(
        "Administrator credentials are required.",
        401,
        {"WWW-Authenticate": 'Basic realm="Spendly Admin"'},
    )


def _credentials_are_valid(username: str, password: str) -> bool:
    expected_user = current_app.config.get("ADMIN_USERNAME") or ""
    expected_password = current_app.config.get("ADMIN_PASSWORD") or ""
    return bool(
        expected_user
        and expected_password
        and hmac.compare_digest(username, expected_user)
        and hmac.compare_digest(password, expected_password)
    )


def _is_authorized() -> bool:
    if session.get(ADMIN_SESSION_KEY) is True:
        return True
    supplied = request.authorization
    return bool(
        supplied
        and supplied.type.lower() == "basic"
        and _credentials_are_valid(
            supplied.username or "", supplied.password or ""
        )
    )


def _csrf_token() -> str:
    token = session.get(ADMIN_CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[ADMIN_CSRF_KEY] = token
    return str(token)


def admin_required(view: View) -> View:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if not _is_authorized():
            if request.path.startswith("/api/"):
                return jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "ADMIN_AUTH_REQUIRED",
                            "message": "Administrator sign-in is required.",
                        },
                    }
                ), 401
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return cast(View, wrapped)


@admin_blueprint.route("/admin/login", methods=["GET", "POST"])
def login() -> Any:
    if request.method == "GET" and _is_authorized():
        return redirect(url_for("admin.dashboard"))

    error: str | None = None
    status_code = 200
    token = _csrf_token()
    if request.method == "POST":
        supplied_token = request.form.get("csrf_token", "")
        if not supplied_token or not hmac.compare_digest(supplied_token, token):
            error = "Your login page expired. Refresh it and try again."
            status_code = 400
        elif _credentials_are_valid(
            request.form.get("username", ""), request.form.get("password", "")
        ):
            session.clear()
            session[ADMIN_SESSION_KEY] = True
            session[ADMIN_CSRF_KEY] = secrets.token_urlsafe(32)
            return redirect(url_for("admin.dashboard"))
        else:
            error = "The administrator username or password is incorrect."
            status_code = 401

    return render_template("admin/login.html", error=error, csrf_token=token), status_code


@admin_blueprint.post("/admin/logout")
@admin_required
def logout() -> Any:
    expected_token = str(session.get(ADMIN_CSRF_KEY, ""))
    supplied_token = request.form.get("csrf_token", "")
    if not expected_token or not hmac.compare_digest(supplied_token, expected_token):
        return "Invalid logout request.", 400
    session.clear()
    return redirect(url_for("admin.login"))


def _count(model: Any, *conditions: Any) -> int:
    return int(
        db.session.scalar(select(func.count()).select_from(model).where(*conditions))
        or 0
    )


def _sum(column: Any, *conditions: Any) -> float:
    return float(db.session.scalar(select(func.sum(column)).where(*conditions)) or 0)


@admin_blueprint.get("/admin")
@admin_blueprint.get("/admin/")
@admin_required
def dashboard() -> str:
    return render_template("admin/dashboard.html", csrf_token=_csrf_token())


@admin_blueprint.get("/api/v1/admin/overview")
@admin_required
def overview() -> tuple[Any, int]:
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    users = list(db.session.scalars(select(User).order_by(User.created_at.asc())))
    recent_users = list(
        db.session.scalars(select(User).order_by(User.created_at.desc()).limit(8))
    )
    forecasts = list(
        db.session.execute(
            select(Forecast, User)
            .join(User, User.id == Forecast.user_id)
            .order_by(Forecast.created_at.desc())
            .limit(10)
        )
    )
    alerts = list(
        db.session.execute(
            select(AnomalyAlert, User)
            .join(User, User.id == AnomalyAlert.user_id)
            .where(AnomalyAlert.is_unusual_spending.is_(True))
            .order_by(AnomalyAlert.created_at.desc())
            .limit(10)
        )
    )
    transactions = list(db.session.scalars(select(Transaction)))

    month_starts: list[datetime] = []
    cursor = datetime(now.year, now.month, 1)
    for offset in range(5, -1, -1):
        month_index = cursor.year * 12 + cursor.month - 1 - offset
        month_starts.append(datetime(month_index // 12, month_index % 12 + 1, 1))
    growth = []
    cashflow = []
    for start in month_starts:
        next_month = (
            datetime(start.year + 1, 1, 1)
            if start.month == 12
            else datetime(start.year, start.month + 1, 1)
        )
        growth.append(
            {
                "label": start.strftime("%b %Y"),
                "new_users": sum(1 for user in users if start <= user.created_at < next_month),
            }
        )
        period_items = [
            item for item in transactions if start <= item.transaction_timestamp < next_month
        ]
        cashflow.append(
            {
                "label": start.strftime("%b"),
                "income": round(
                    sum(float(item.amount) for item in period_items if item.transaction_type == "income"),
                    2,
                ),
                "expense": round(
                    sum(float(item.amount) for item in period_items if item.transaction_type == "expense"),
                    2,
                ),
            }
        )

    total_income = _sum(Transaction.amount, Transaction.transaction_type == "income")
    total_expense = _sum(Transaction.amount, Transaction.transaction_type == "expense")
    registry = current_app.extensions.get("model_registry")
    model_info = registry.info() if registry and registry.loaded else {}

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "generated_at": now.isoformat() + "Z",
                    "metrics": {
                        "users": len(users),
                        "active_users": sum(1 for user in users if user.is_active),
                        "google_users": sum(
                            1 for user in users if user.google_subject is not None
                        ),
                        "new_users_30d": sum(1 for user in users if user.created_at >= month_ago),
                        "engaged_users": len({item.user_id for item in transactions}),
                        "training_opt_ins": sum(1 for user in users if user.model_training_opt_in),
                        "transactions": len(transactions),
                        "income": round(total_income, 2),
                        "expense": round(total_expense, 2),
                        "net_savings": round(total_income - total_expense, 2),
                        "budgeted": round(_sum(Budget.amount), 2),
                        "analysis_runs": _count(AnalysisRun),
                        "forecasts": _count(Forecast),
                        "predicted_spending": round(_sum(Forecast.predicted_spending), 2),
                        "unusual_alerts": _count(
                            AnomalyAlert, AnomalyAlert.is_unusual_spending.is_(True)
                        ),
                    },
                    "user_growth": growth,
                    "cashflow": cashflow,
                    "recent_users": [
                        {
                            "display_name": user.display_name,
                            "email": user.email,
                            "joined_at": user.created_at.isoformat() + "Z",
                            "active": user.is_active,
                            "training_opt_in": user.model_training_opt_in,
                            "login_provider": (
                                "Google" if user.google_subject else "Password"
                            ),
                        }
                        for user in recent_users
                    ],
                    "recent_forecasts": [
                        {
                            "user": user.display_name,
                            "email": user.email,
                            "predicted_spending": float(forecast.predicted_spending),
                            "period_start": forecast.period_start.isoformat(),
                            "period_end": forecast.period_end.isoformat(),
                            "model_version": forecast.model_version,
                            "created_at": forecast.created_at.isoformat() + "Z",
                        }
                        for forecast, user in forecasts
                    ],
                    "recent_unusual_alerts": [
                        {
                            "user": user.display_name,
                            "score": alert.anomaly_score,
                            "model_version": alert.model_version,
                            "created_at": alert.created_at.isoformat() + "Z",
                        }
                        for alert, user in alerts
                    ],
                    "model_info": model_info,
                },
            }
        ),
        200,
    )
