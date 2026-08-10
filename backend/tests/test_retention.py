from datetime import date, datetime, timedelta
from decimal import Decimal

from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models import Budget, Transaction, User


def test_retention_command_is_dry_run_until_explicitly_applied(app):
    app.config["DATA_RETENTION_DAYS"] = 30
    user = User(
        email="retention@example.com",
        password_hash=generate_password_hash("StrongPass123!"),
        display_name="Retention Test",
    )
    db.session.add(user)
    db.session.flush()
    old_timestamp = datetime.utcnow() - timedelta(days=60)
    current_timestamp = datetime.utcnow() - timedelta(days=1)
    db.session.add_all(
        [
            Transaction(
                user_id=user.id,
                transaction_timestamp=old_timestamp,
                amount=Decimal("100.00"),
                category="food",
                transaction_type="expense",
                fingerprint="old-transaction",
            ),
            Transaction(
                user_id=user.id,
                transaction_timestamp=current_timestamp,
                amount=Decimal("200.00"),
                category="food",
                transaction_type="expense",
                fingerprint="current-transaction",
            ),
            Budget(
                user_id=user.id,
                period_start=date.today() - timedelta(days=70),
                period_end=date.today() - timedelta(days=60),
                category="total",
                amount=Decimal("1000.00"),
            ),
            Budget(
                user_id=user.id,
                period_start=date.today(),
                period_end=date.today() + timedelta(days=7),
                category="total",
                amount=Decimal("2000.00"),
            ),
        ]
    )
    db.session.commit()

    runner = app.test_cli_runner()
    dry_run = runner.invoke(args=["purge-retained-data"])
    assert dry_run.exit_code == 0
    assert "Dry run" in dry_run.output
    assert db.session.query(Transaction).count() == 2
    assert db.session.query(Budget).count() == 2

    applied = runner.invoke(args=["purge-retained-data", "--apply"])
    assert applied.exit_code == 0
    assert "committed" in applied.output
    assert db.session.query(Transaction).count() == 1
    assert db.session.query(Budget).count() == 1
