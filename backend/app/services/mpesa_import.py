"""Validate normalized events and atomically account for their components."""
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from ..extensions import db
from ..models import MpesaComponent, MpesaEvent, Transaction
from ..repositories import TransactionRepository
from .transactions import TransactionService, fingerprint

SMS_CONSENT_VERSION = "2026-10-22"
REFERENCE = re.compile(r"[A-Z0-9]{10}", re.ASCII)
MONEY = re.compile(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,2})?", re.ASCII)
KINDS = {"sent", "received", "airtime", "till", "paybill", "withdrawal", "deposit", "payment", "reversal"}


def normalized_event(raw):
    """Reject extra fields (especially bodies/user IDs) and non-decimal money."""
    common = {"external_reference", "transaction_timestamp", "kind", "parser_version"}
    financial = {"amount", "transaction_cost", "transaction_type", "category", "merchant"}
    reversal = {"original_reference", "amount", "original_transaction_type", "fee_refund_amount"}
    if not isinstance(raw, dict) or not common <= raw.keys():
        raise ValueError("INVALID_EVENT")
    kind = raw["kind"]
    if not isinstance(kind, str) or kind not in KINDS:
        raise ValueError("UNSUPPORTED_KIND")
    if set(raw) - common - (reversal if kind == "reversal" else financial):
        raise ValueError("UNEXPECTED_FIELDS")
    result = {key: raw[key] for key in common}
    for key in ("external_reference",) + (("original_reference",) if kind == "reversal" else ()):
        value = raw.get(key)
        if not isinstance(value, str) or not REFERENCE.fullmatch(value):
            raise ValueError("INVALID_REFERENCE")
        result[key] = value
    if not isinstance(raw["parser_version"], str) or raw["parser_version"] != "mpesa-v1":
        raise ValueError("UNSUPPORTED_PARSER")
    stamp = raw["transaction_timestamp"]
    if not isinstance(stamp, str) or len(stamp) > 40:
        raise ValueError("INVALID_TIMESTAMP")
    try:
        timestamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("INVALID_TIMESTAMP") from None
    if timestamp.tzinfo is None or not 2000 <= timestamp.year <= 2099:
        raise ValueError("INVALID_TIMESTAMP")
    result["transaction_timestamp"] = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    for key in ("amount", "fee_refund_amount" if kind == "reversal" else "transaction_cost"):
        value = raw.get(key, "0.00" if key != "amount" else None)
        if not isinstance(value, str) or not MONEY.fullmatch(value):
            raise ValueError("INVALID_MONEY")
        money = Decimal(value)
        if money > Decimal("999999999999.99") or (key == "amount" and money < Decimal("0.01")):
            raise ValueError("INVALID_MONEY")
        result[key] = money.quantize(Decimal("0.01"))
    if kind == "reversal":
        if result["original_reference"] == result["external_reference"] or raw.get("original_transaction_type") not in ("income", "expense"):
            raise ValueError("INVALID_REVERSAL")
        result["original_transaction_type"] = raw["original_transaction_type"]
    else:
        expected = "income" if kind in {"received", "deposit"} else "expense"
        if raw.get("transaction_type") != expected:
            raise ValueError("INVALID_DIRECTION")
        if expected == "income" and result["transaction_cost"] != 0:
            raise ValueError("UNSUPPORTED_INCOMING_FEE")
        category, merchant = raw.get("category"), raw.get("merchant")
        if not isinstance(category, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", category):
            raise ValueError("INVALID_CATEGORY")
        if merchant is not None and (not isinstance(merchant, str) or len(merchant) > 120 or any(ord(c) < 32 for c in merchant)):
            raise ValueError("INVALID_MERCHANT")
        if kind == "airtime" and category != "airtime_and_data":
            raise ValueError("INVALID_CATEGORY")
        result.update(category=category, merchant=merchant, transaction_type=expected)
    return result


def event_hash(event):
    canonical = {key: value.isoformat() if isinstance(value, datetime) else str(value) if isinstance(value, Decimal) else value
                 for key, value in event.items()}
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def find_event(user_id, reference):
    return db.session.scalar(select(MpesaEvent).where(
        MpesaEvent.user_id == user_id, MpesaEvent.external_reference == reference))


def apply_reversal(user_id, original, reversal):
    if (original.kind == "reversal" or original.status == "needs_review" or original.principal_amount != reversal.principal_amount or original.direction != reversal.direction
            or reversal.fee_amount not in (Decimal("0"), original.fee_amount)):
        reversal.status = "needs_review"
        return False
    for component in db.session.scalars(select(MpesaComponent).where(
        MpesaComponent.user_id == user_id, MpesaComponent.event_id == original.id)):
        if component.component == "fee" and reversal.fee_amount == 0:
            continue
        transaction = TransactionRepository.owned(component.transaction_id, user_id) if component.transaction_id else None
        if transaction is not None and transaction.source == "mpesa_sms":
            transaction.is_reversed = True
    original.status = "reversed"
    reversal.status = "reconciled"
    return True


def import_event(user_id, event):
    digest = event_hash(event)
    existing = find_event(user_id, event["external_reference"])
    if existing:
        if existing.payload_hash != digest:
            raise ValueError("REFERENCE_CONFLICT")
        return {"status": "duplicate", "created_transactions": 0}
    ledger = MpesaEvent(
        user_id=user_id, external_reference=event["external_reference"],
        original_reference=event.get("original_reference"), kind=event["kind"],
        payload_hash=digest, parser_version=event["parser_version"],
        transaction_timestamp=event["transaction_timestamp"], status="imported",
        principal_amount=event["amount"],
        fee_amount=event.get("fee_refund_amount", event.get("transaction_cost", Decimal("0"))),
        direction=event.get("original_transaction_type", event.get("transaction_type")))
    db.session.add(ledger)
    db.session.flush()
    if event["kind"] == "reversal":
        original = find_event(user_id, event["original_reference"])
        if original:
            apply_reversal(user_id, original, ledger)
        else:
            ledger.status = "pending_reversal"
        # A reversal cannot itself be reversed through this importer. Resolve
        # pre-existing pending chains without altering the target's status.
        pending_chains = list(db.session.scalars(select(MpesaEvent).where(
                MpesaEvent.user_id == user_id, MpesaEvent.kind == "reversal",
                MpesaEvent.original_reference == ledger.external_reference,
                MpesaEvent.status == "pending_reversal")))
        for pending in pending_chains:
            pending.status = "needs_review"
        return {"status": ledger.status, "created_transactions": 0, "review_required": bool(pending_chains)}
    # Validate against the existing schema/normalizer, while retaining exact
    # Decimal values for persistence; no fee is added to a principal with floats.
    payload = {key: event[key] for key in ("transaction_timestamp", "amount", "transaction_type", "category", "merchant")}
    payload["transaction_timestamp"] = payload["transaction_timestamp"].isoformat() + "Z"
    payload["amount"] = str(event["amount"])
    payload["is_recurring"] = False
    normalized = TransactionService.validated(payload)
    normalized["amount"] = event["amount"]
    components = [("principal", normalized)]
    if event["transaction_cost"] > 0:
        components.append(("fee", normalized | {"amount": event["transaction_cost"],
            "transaction_type": "expense", "category": "transaction_fees", "merchant": "M-PESA transaction fee"}))
    signatures = [fingerprint(user_id, values) for _, values in components]
    if len(set(signatures)) != len(signatures) or any(TransactionRepository.by_fingerprint(user_id, sig) for sig in signatures):
        ledger.status = "needs_review"
        return {"status": "needs_review", "created_transactions": 0}
    ids = []
    for (component, values), signature in zip(components, signatures):
        transaction = Transaction(user_id=user_id, **values, source="mpesa_sms", fingerprint=signature)
        db.session.add(transaction)
        db.session.flush()
        db.session.add(MpesaComponent(user_id=user_id, event_id=ledger.id,
            transaction_id=transaction.id, component=component))
        ids.append(transaction.id)
    db.session.flush()
    pending = list(db.session.scalars(select(MpesaEvent).where(
        MpesaEvent.user_id == user_id, MpesaEvent.kind == "reversal",
        MpesaEvent.original_reference == ledger.external_reference)))
    for reversal in pending:
        apply_reversal(user_id, ledger, reversal)
    return {"status": ledger.status if ledger.status == "reversed" else "created", "created_transactions": len(ids),
            "review_required": any(row.status == "needs_review" for row in pending), "transaction_ids": ids}
