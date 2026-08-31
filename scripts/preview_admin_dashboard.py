"""Run a disposable, seeded admin dashboard for local visual QA."""

from __future__ import annotations

import tempfile
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import (
    AnalysisRun,
    AnomalyAlert,
    Budget,
    Forecast,
    Transaction,
    User,
    utc_now,
)
from backend.app.services.model_registry import ModelRegistry


def seed() -> None:
    now = datetime.utcnow()
    for index in range(7):
        joined = now - timedelta(days=index * 24)
        user = User(
            email=f"tester{index + 1}@example.com",
            password_hash="preview-only",
            display_name=f"Tester {index + 1}",
            username=f"tester_{index + 1}",
            username_normalized=f"tester_{index + 1}",
            terms_accepted_at=joined,
            privacy_accepted_at=joined,
            consent_version="preview",
            model_training_opt_in=index % 3 == 0,
            created_at=joined,
        )
        db.session.add(user)
        db.session.flush()
        for month_offset in range(6):
            timestamp = now - timedelta(days=month_offset * 30 + index)
            income = Decimal(str(42000 + index * 2500))
            expense = Decimal(str(19000 + month_offset * 900 + index * 350))
            for kind, amount, category in (
                ("income", income, "salary"),
                ("expense", expense, "living_costs"),
            ):
                db.session.add(
                    Transaction(
                        user_id=user.id,
                        transaction_timestamp=timestamp,
                        amount=amount,
                        category=category,
                        transaction_type=kind,
                        merchant="Preview data",
                        is_recurring=kind == "income",
                        source="preview",
                        fingerprint=f"{user.id}-{month_offset}-{kind}",
                    )
                )
        db.session.add(
            Budget(
                user_id=user.id,
                period_start=date.today().replace(day=1),
                period_end=date.today() + timedelta(days=30),
                category="total",
                amount=Decimal("30000"),
            )
        )
        run = AnalysisRun(
            user_id=user.id,
            forecast_model_version="v1",
            anomaly_model_version="v1",
            history_periods=8,
            generated_at=now - timedelta(hours=index * 5),
        )
        db.session.add(run)
        db.session.flush()
        db.session.add(
            Forecast(
                analysis_run_id=run.id,
                user_id=user.id,
                period_start=date.today(),
                period_end=date.today() + timedelta(days=6),
                predicted_spending=Decimal(str(21000 + index * 1250)),
                baseline_prediction=Decimal(str(20000 + index * 1000)),
                model_version="v1",
                created_at=run.generated_at,
            )
        )
        if index in {1, 4}:
            db.session.add(
                AnomalyAlert(
                    analysis_run_id=run.id,
                    user_id=user.id,
                    is_unusual_spending=True,
                    anomaly_score=0.17 + index / 100,
                    decision_threshold=0.1,
                    explanation="Preview unusual-spending alert.",
                    model_version="v1",
                    created_at=run.generated_at,
                )
            )
    db.session.commit()


def main() -> None:
    database_file = tempfile.NamedTemporaryFile(
        prefix="spending-admin-preview-", suffix=".db", delete=False
    )
    database_file.close()
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "preview-secret-key-at-least-32-bytes",
            "JWT_SECRET_KEY": "preview-jwt-secret-at-least-32-bytes",
            "SQLALCHEMY_DATABASE_URI": f"sqlite+pysqlite:///{database_file.name}",
            "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
            "LOAD_MODELS": False,
            "MODEL_RUNTIME": "lightweight",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "preview-admin-password",
        }
    )
    registry = ModelRegistry(
        PROJECT_ROOT / "artifacts" / "models", "v1", "v1", "lightweight"
    )
    registry.load()
    app.extensions["model_registry"] = registry
    with app.app_context():
        db.create_all()
        seed()
    print("Preview: http://127.0.0.1:5055/admin")
    print("Credentials: admin / preview-admin-password")
    try:
        app.run(host="127.0.0.1", port=5055, debug=False, use_reloader=False)
    finally:
        Path(database_file.name).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
