"""Create deterministic development-only sample data."""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from werkzeug.security import generate_password_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import Budget, ModelVersion, User
from backend.app.services.transactions import TransactionService


def seed() -> None:
    password = os.getenv("SAMPLE_USER_PASSWORD")
    if not password:
        raise RuntimeError("SAMPLE_USER_PASSWORD is required to seed development data.")
    app = create_app()
    with app.app_context():
        email = "demo@example.com"
        user = db.session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                display_name="Demo User",
                username="demo_user",
                username_normalized="demo_user",
                password_hash=generate_password_hash(password),
                monthly_income=Decimal("50000.00"),
            )
            db.session.add(user)
            db.session.flush()
            start = datetime(2026, 1, 5, 9, 0)
            for week in range(10):
                timestamp = start + timedelta(weeks=week)
                TransactionService.create(
                    user.id,
                    {
                        "transaction_timestamp": timestamp.isoformat(),
                        "amount": 1_500 + week * 50,
                        "category": "food",
                        "transaction_type": "expense",
                        "merchant": f"Demo Shop {week}",
                        "is_recurring": False,
                    },
                    source="seed",
                    commit=False,
                )
                TransactionService.create(
                    user.id,
                    {
                        "transaction_timestamp": (
                            timestamp + timedelta(hours=1)
                        ).isoformat(),
                        "amount": 12_500,
                        "category": "salary",
                        "transaction_type": "income",
                        "merchant": "Demo Employer",
                        "is_recurring": True,
                    },
                    source="seed",
                    commit=False,
                )
            db.session.add(
                Budget(
                    user_id=user.id,
                    period_start=date(2026, 3, 16),
                    period_end=date(2026, 3, 22),
                    category="total",
                    amount=Decimal("15000.00"),
                )
            )
        for component in ("forecasting", "anomaly"):
            version = app.extensions["model_registry"].forecast_version if component == "forecasting" else app.extensions["model_registry"].anomaly_version
            existing = db.session.scalar(
                select(ModelVersion).where(
                    ModelVersion.component == component,
                    ModelVersion.version == version,
                )
            )
            if existing is None:
                registry = app.extensions["model_registry"]
                metadata = (
                    registry.forecast_metadata
                    if component == "forecasting"
                    else registry.anomaly_metadata
                )
                db.session.add(
                    ModelVersion(
                        component=component,
                        version=version,
                        artifact_path=str(
                            app.config["MODEL_ROOT"] / component / version
                        ),
                        metadata_json=json.loads(json.dumps(metadata)),
                    )
                )
        db.session.commit()
        print(f"Seed complete. Development user: {email}")


if __name__ == "__main__":
    seed()
