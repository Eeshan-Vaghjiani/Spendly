"""Transaction normalisation, fingerprinting, and CSV ingestion."""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage

from ..errors import ApiError
from ..extensions import db
from ..models import Transaction
from ..repositories import TransactionRepository
from ..schemas import TransactionSchema


CATEGORY_ALIASES = {
    "airtime": "airtime_and_data",
    "data": "airtime_and_data",
    "airtime and data": "airtime_and_data",
    "dining": "food",
    "groceries": "food",
    "medical": "healthcare",
    "subscription": "subscriptions",
    "public transport": "transport",
    "electricity": "utilities",
    "water": "utilities",
}
REQUIRED_CSV_COLUMNS = {
    "transaction_timestamp",
    "amount",
    "category",
    "transaction_type",
    "merchant",
    "is_recurring",
}


def normalize_category(value: str) -> str:
    cleaned = " ".join(value.strip().lower().replace("_", " ").split())
    cleaned = CATEGORY_ALIASES.get(cleaned, cleaned)
    return cleaned.replace(" ", "_")


def normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def fingerprint(user_id: str, data: dict[str, Any]) -> str:
    merchant = (data.get("merchant") or "").strip().lower()
    canonical = "|".join(
        [
            user_id,
            data["transaction_timestamp"].isoformat(timespec="seconds"),
            f"{float(data['amount']):.2f}",
            data["category"],
            data["transaction_type"],
            merchant,
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TransactionService:
    schema = TransactionSchema()

    @classmethod
    def validated(cls, payload: dict[str, Any]) -> dict[str, Any]:
        data = cls.schema.load(payload)
        data["transaction_timestamp"] = normalize_timestamp(
            data["transaction_timestamp"]
        )
        data["category"] = normalize_category(data["category"])
        data["transaction_type"] = data["transaction_type"].lower()
        if data["merchant"] is not None:
            data["merchant"] = data["merchant"].strip() or None
        return data

    @classmethod
    def create(
        cls,
        user_id: str,
        payload: dict[str, Any],
        *,
        source: str = "manual",
        commit: bool = True,
    ) -> Transaction:
        data = cls.validated(payload)
        signature = fingerprint(user_id, data)
        if TransactionRepository.by_fingerprint(user_id, signature):
            raise ApiError(
                "DUPLICATE_TRANSACTION",
                "An identical transaction already exists.",
                409,
            )
        transaction = Transaction(
            user_id=user_id,
            transaction_timestamp=data["transaction_timestamp"],
            amount=Decimal(f"{data['amount']:.2f}"),
            category=data["category"],
            transaction_type=data["transaction_type"],
            merchant=data["merchant"],
            is_recurring=data["is_recurring"],
            source=source,
            fingerprint=signature,
        )
        db.session.add(transaction)
        if commit:
            try:
                db.session.commit()
            except IntegrityError as error:
                db.session.rollback()
                raise ApiError(
                    "DUPLICATE_TRANSACTION",
                    "An identical transaction already exists.",
                    409,
                ) from error
        return transaction

    @classmethod
    def update(
        cls,
        transaction: Transaction,
        payload: dict[str, Any],
    ) -> Transaction:
        data = cls.validated(payload)
        signature = fingerprint(transaction.user_id, data)
        duplicate = TransactionRepository.by_fingerprint(
            transaction.user_id, signature
        )
        if duplicate is not None and duplicate.id != transaction.id:
            raise ApiError(
                "DUPLICATE_TRANSACTION",
                "An identical transaction already exists.",
                409,
            )
        transaction.transaction_timestamp = data["transaction_timestamp"]
        transaction.amount = Decimal(f"{data['amount']:.2f}")
        transaction.category = data["category"]
        transaction.transaction_type = data["transaction_type"]
        transaction.merchant = data["merchant"]
        transaction.is_recurring = data["is_recurring"]
        transaction.fingerprint = signature
        try:
            db.session.commit()
        except IntegrityError as error:
            db.session.rollback()
            raise ApiError(
                "DUPLICATE_TRANSACTION",
                "An identical transaction already exists.",
                409,
            ) from error
        return transaction

    @classmethod
    def upload(cls, user_id: str, file: FileStorage) -> dict[str, Any]:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise ApiError(
                "INVALID_FILE_TYPE", "A .csv file is required.", 422
            )
        try:
            text = file.stream.read().decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ApiError(
                "INVALID_FILE_ENCODING",
                "The CSV must use UTF-8 encoding.",
                422,
            ) from error
        reader = csv.DictReader(io.StringIO(text))
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_CSV_COLUMNS - headers)
        if missing:
            raise ApiError(
                "INVALID_CSV_HEADERS",
                "The CSV is missing required columns.",
                422,
                {"missing_columns": missing},
            )
        rows = list(reader)
        errors: list[dict[str, Any]] = []
        created: list[Transaction] = []
        seen: set[str] = set()
        duplicate_rows = 0
        for row_number, row in enumerate(rows, start=2):
            try:
                data = cls.validated(row)
                signature = fingerprint(user_id, data)
                if (
                    signature in seen
                    or TransactionRepository.by_fingerprint(user_id, signature)
                ):
                    duplicate_rows += 1
                    continue
                seen.add(signature)
                created.append(
                    Transaction(
                        user_id=user_id,
                        transaction_timestamp=data["transaction_timestamp"],
                        amount=Decimal(f"{data['amount']:.2f}"),
                        category=data["category"],
                        transaction_type=data["transaction_type"],
                        merchant=data["merchant"],
                        is_recurring=data["is_recurring"],
                        source="csv_upload",
                        fingerprint=signature,
                    )
                )
            except ValidationError as error:
                errors.append(
                    {
                        "row": row_number,
                        "code": "INVALID_ROW",
                        "message": str(error.messages),
                    }
                )
        db.session.add_all(created)
        try:
            db.session.commit()
        except IntegrityError as error:
            db.session.rollback()
            raise ApiError(
                "UPLOAD_CONFLICT",
                "The upload conflicted with an existing transaction.",
                409,
            ) from error
        return {
            "received_rows": len(rows),
            "created_rows": len(created),
            "duplicate_rows": duplicate_rows,
            "invalid_rows": len(errors),
            "errors": errors,
        }
