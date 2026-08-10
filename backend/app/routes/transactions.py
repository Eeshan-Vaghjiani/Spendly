"""User-scoped transaction CRUD and CSV upload."""

from __future__ import annotations

from datetime import date
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..errors import ApiError
from ..extensions import db
from ..repositories import TransactionRepository
from ..security.current_user import current_user
from ..services.transactions import TransactionService


transaction_blueprint = Blueprint("transactions", __name__)


def parse_date(name: str) -> date | None:
    value = request.args.get(name)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ApiError(
            "VALIDATION_ERROR",
            f"{name} must use YYYY-MM-DD format.",
            422,
        ) from error


@transaction_blueprint.post("/transactions")
@jwt_required()
def create_transaction() -> tuple[Any, int]:
    user = current_user()
    transaction = TransactionService.create(
        user.id, request.get_json(silent=True) or {}
    )
    return jsonify({"success": True, "data": transaction.to_dict()}), 201


@transaction_blueprint.get("/transactions")
@jwt_required()
def list_transactions() -> tuple[Any, int]:
    user = current_user()
    page = max(1, request.args.get("page", default=1, type=int))
    per_page = min(
        100, max(1, request.args.get("per_page", default=20, type=int))
    )
    query = TransactionRepository.list_query(
        user.id,
        start_date=parse_date("start_date"),
        end_date=parse_date("end_date"),
        category=request.args.get("category"),
    )
    pagination = db.paginate(
        query, page=page, per_page=per_page, error_out=False
    )
    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "items": [item.to_dict() for item in pagination.items],
                    "page": page,
                    "per_page": per_page,
                    "total": pagination.total,
                },
            }
        ),
        200,
    )


@transaction_blueprint.post("/transactions/upload")
@jwt_required()
def upload_transactions() -> tuple[Any, int]:
    user = current_user()
    file = request.files.get("file")
    if file is None:
        raise ApiError(
            "FILE_REQUIRED", "A CSV file must be supplied as 'file'.", 422
        )
    result = TransactionService.upload(user.id, file)
    return jsonify({"success": True, "data": result}), 200


@transaction_blueprint.put("/transactions/<string:transaction_id>")
@jwt_required()
def update_transaction(transaction_id: str) -> tuple[Any, int]:
    user = current_user()
    transaction = TransactionRepository.owned(transaction_id, user.id)
    if transaction is None:
        raise ApiError(
            "NOT_FOUND", "The requested transaction was not found.", 404
        )
    transaction = TransactionService.update(
        transaction, request.get_json(silent=True) or {}
    )
    return jsonify({"success": True, "data": transaction.to_dict()}), 200


@transaction_blueprint.delete("/transactions/<string:transaction_id>")
@jwt_required()
def delete_transaction(transaction_id: str) -> tuple[Any, int]:
    user = current_user()
    transaction = TransactionRepository.owned(transaction_id, user.id)
    if transaction is None:
        raise ApiError(
            "NOT_FOUND", "The requested transaction was not found.", 404
        )
    db.session.delete(transaction)
    db.session.commit()
    return (
        jsonify(
            {"success": True, "data": {"deleted_id": transaction_id}}
        ),
        200,
    )
