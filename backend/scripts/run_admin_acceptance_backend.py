"""Repeatable admin browser acceptance using invented, in-memory records only."""
from datetime import timedelta
from decimal import Decimal
import os

from backend.app.extensions import db
from backend.app.models import Budget, SignInEvent, Transaction, User, utc_now
from backend.app.reporting_time import reporting_today
from backend.scripts.run_acceptance_backend import create_acceptance_app


def create_admin_acceptance_app(admin_password: str):
    if len(admin_password) < 16:
        raise ValueError('Supply a disposable admin password of at least 16 characters.')
    app = create_acceptance_app()
    app.config.update(
        ADMIN_USERNAME='admin', ADMIN_PASSWORD=admin_password,
        SESSION_COOKIE_SECURE=False,
    )
    now = utc_now()
    with app.app_context():
        for index in range(25):
            user = User(
                email=f'synthetic-{index + 1:02}@example.invalid',
                display_name=f'Synthetic account {index + 1:02}',
                username=f'synthetic_{index + 1:02}',
                username_normalized=f'synthetic_{index + 1:02}',
                created_at=now - timedelta(minutes=index),
            )
            db.session.add(user)
            db.session.flush()
            if index != 0:
                continue
            user.last_signed_in_at = now
            for event_index in range(45):
                db.session.add(SignInEvent(
                    user_id=user.id, provider='password', event='sign_in',
                    created_at=now - timedelta(hours=event_index),
                ))
            for record in range(45):
                db.session.add(Transaction(
                    user_id=user.id,
                    transaction_timestamp=now - timedelta(hours=record),
                    # Deliberately large synthetic total for narrow-screen wrapping.
                    amount=Decimal('9999999.99') if record == 0 else Decimal('125.50'),
                    category='food',
                    transaction_type='expense', merchant='Synthetic fixture',
                    source='manual', fingerprint=f'admin-fixture-{record}',
                ))
            db.session.add(Budget(
                user_id=user.id, period_start=reporting_today(),
                period_end=reporting_today(), category='total', amount=Decimal('6000'),
            ))
        db.session.commit()
    return app


if __name__ == '__main__':
    create_admin_acceptance_app(os.getenv('SPENDLY_ACCEPTANCE_ADMIN_PASSWORD', '')).run(
        host='127.0.0.1', port=5058, debug=False, use_reloader=False, threaded=False,
    )
