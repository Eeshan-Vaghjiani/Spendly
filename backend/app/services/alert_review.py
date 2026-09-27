"""User-confirmed alert review; no automatic model relabeling or training."""
from statistics import median
import hashlib
from sqlalchemy import select
from ..extensions import db
from ..models import AlertReview, Transaction


def review_version(transaction):
    return hashlib.sha256((transaction.fingerprint + '|' + str(bool(transaction.is_recurring))).encode()).hexdigest()


def review_state(transaction):
    if transaction is None:
        return "transaction_deleted"
    review = db.session.scalar(select(AlertReview).where(
        AlertReview.user_id == transaction.user_id, AlertReview.transaction_id == transaction.id))
    if review is None:
        return "pending"
    if review.transaction_fingerprint != review_version(transaction):
        return "changed_since_review"
    return review.status


def explanation_context(transaction, history):
    """Descriptive past-only context, not a causal explanation of the model score."""
    prior = [t for t in history if t.transaction_type == "expense"
             and t.transaction_timestamp < transaction.transaction_timestamp
             and t.category == transaction.category][-40:]
    category = transaction.category.replace("_", " ")
    current = float(transaction.amount)
    if prior:
        typical = median(float(t.amount) for t in prior)
        return (f"This {category} entry is KES {current:,.2f}. The median of your "
                f"{len(prior)} earlier {category} entries is KES {typical:,.2f}. "
                "This comparison is context for your review, not proof of an error.")
    return (f"This {category} entry is KES {current:,.2f}. There are no earlier "
            "recorded expenses in this category to compare. Review its amount, date and merchant.")


def alert_payload(alert):
    payload = alert.to_dict()
    transaction = db.session.get(Transaction, alert.transaction_id) if alert.transaction_id else None
    if transaction is not None and transaction.user_id != alert.user_id:
        transaction = None
    payload["review_status"] = review_state(transaction)
    payload["transaction"] = transaction.to_dict() if transaction else None
    payload["transaction_review_version"] = review_version(transaction) if transaction else None
    payload["review_required"] = payload["review_status"] in {"pending", "changed_since_review"}
    return payload
