"""User-scoped budget routes."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from ..errors import ApiError
from ..extensions import db
from ..models import Budget
from ..repositories import BudgetRepository
from ..schemas import BudgetSchema
from ..security.current_user import current_user
from ..services.transactions import normalize_category


budget_blueprint = Blueprint("budgets", __name__)
budget_schema = BudgetSchema()


def apply_budget(budget: Budget, payload: dict[str, Any]) -> None:
    budget.period_start = payload["period_start"]
    budget.period_end = payload["period_end"]
    budget.category = normalize_category(payload["category"])
    budget.amount = Decimal(f"{payload['amount']:.2f}")


@budget_blueprint.post("/budgets")
@jwt_required()
def create_budget() -> tuple[Any, int]:
    user = current_user()
    payload = budget_schema.load(request.get_json(silent=True) or {})
    budget = Budget(user_id=user.id)
    apply_budget(budget, payload)
    db.session.add(budget)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ApiError(
            "BUDGET_ALREADY_EXISTS",
            "A budget already exists for this period and category.",
            409,
        ) from error
    return jsonify({"success": True, "data": budget.to_dict()}), 201


@budget_blueprint.get("/budgets")
@jwt_required()
def list_budgets() -> tuple[Any, int]:
    user = current_user()
    return (
        jsonify(
            {
                "success": True,
                "data": [
                    budget.to_dict()
                    for budget in BudgetRepository.all(user.id)
                ],
            }
        ),
        200,
    )


@budget_blueprint.put("/budgets/<string:budget_id>")
@jwt_required()
def update_budget(budget_id: str) -> tuple[Any, int]:
    user = current_user()
    budget = BudgetRepository.owned(budget_id, user.id)
    if budget is None:
        raise ApiError(
            "NOT_FOUND", "The requested budget was not found.", 404
        )
    payload = budget_schema.load(request.get_json(silent=True) or {})
    apply_budget(budget, payload)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ApiError(
            "BUDGET_ALREADY_EXISTS",
            "A budget already exists for this period and category.",
            409,
        ) from error
    return jsonify({"success": True, "data": budget.to_dict()}), 200


@budget_blueprint.delete("/budgets/<string:budget_id>")
@jwt_required()
def delete_budget(budget_id: str) -> tuple[Any, int]:
    user = current_user()
    budget = BudgetRepository.owned(budget_id, user.id)
    if budget is None:
        raise ApiError(
            "NOT_FOUND", "The requested budget was not found.", 404
        )
    db.session.delete(budget)
    db.session.commit()
    return jsonify({"success": True, "data": {"deleted_id": budget_id}}), 200
