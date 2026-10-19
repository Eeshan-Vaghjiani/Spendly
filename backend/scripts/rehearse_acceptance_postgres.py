"""Destructive rehearsal ONLY for the documented disposable loopback container.

No DATABASE_URL is accepted. Requires an initially empty spendly_acceptance DB
on 127.0.0.1:55432, created by the issue-60 procedure. Never use a hosted DB.
"""
import re
from datetime import datetime
from decimal import Decimal

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import upgrade
from sqlalchemy import inspect, select, text

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import AdminAudit, AlertReview, Transaction, User

URL = 'postgresql+psycopg://spendly_acceptance:disposable-pg-only@127.0.0.1:55432/spendly_acceptance'


def main():
    if not __debug__:
        raise RuntimeError('Run without Python optimization so validation checks execute.')
    app = create_app({
        'TESTING': True, 'LOAD_MODELS': False,
        'SECRET_KEY': 'disposable-pg-acceptance-only-secret',
        'JWT_SECRET_KEY': 'disposable-pg-acceptance-only-jwt',
        'SQLALCHEMY_DATABASE_URI': URL,
        'ADMIN_USERNAME': 'admin', 'ADMIN_PASSWORD': 'synthetic-admin-only',
        'SESSION_COOKIE_SECURE': False, 'GOOGLE_WEB_CLIENT_ID': None,
    })
    with app.app_context():
        if db.session.scalar(text('SELECT current_database()')) != 'spendly_acceptance':
            raise RuntimeError('Refusing an unexpected database identity.')
        if inspect(db.engine).get_table_names():
            raise RuntimeError('Refusing a nonempty target.')
        db.session.remove()
        upgrade(directory='backend/migrations', revision='0004_username_onboarding')
        db.session.execute(text("""
            INSERT INTO users
            (id,email,display_name,username,username_normalized,created_at,is_active,model_training_opt_in)
            VALUES ('legacy','legacy@example.invalid','Legacy synthetic','legacy','legacy',CURRENT_TIMESTAMP,true,false)
        """))
        db.session.commit()
        upgrade(directory='backend/migrations')
        assert db.session.get(User, 'legacy').auth_version == 0
        with db.engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), db.metadata) == []
        print('PASS: legacy account survives upgrade to head; ORM metadata matches PostgreSQL.')

    with app.test_client() as client:
        response = client.post('/api/v1/auth/register', json={
            'email': 'delete-fixture@example.invalid', 'password': 'SyntheticNativeOnly123!',
            'display_name': 'Disposable fixture', 'accepted_terms': True,
            'accepted_privacy': True, 'model_training_opt_in': False,
        })
        assert response.status_code == 201
        account = response.get_json()['data']['user']
        with app.app_context():
            record = Transaction(user_id=account['id'], transaction_timestamp=datetime(2026, 10, 19, 12),
                                 amount=Decimal('125.50'), category='food', transaction_type='expense',
                                 fingerprint='postgres-synthetic-only')
            db.session.add(record)
            db.session.flush()
            review = AlertReview(user_id=account['id'], transaction_id=record.id,
                                 transaction_fingerprint=record.fingerprint, status='intentional')
            db.session.add(review)
            db.session.commit()
        page = client.get('/admin/login')
        csrf = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
        assert client.post('/admin/login', data={
            'username': 'admin', 'password': 'synthetic-admin-only', 'csrf_token': csrf,
        }).status_code == 302
        with client.session_transaction() as state:
            headers = {'X-CSRF-Token': state['spendly_admin_csrf']}
        body = {'reason': 'Disposable PostgreSQL acceptance', 'admin_password': 'synthetic-admin-only'}
        base = '/api/v1/admin/users/' + account['id']
        exported = client.post(base + '/export', headers=headers, json=body)
        assert exported.status_code == 200
        assert len(exported.get_json()['transactions']) == 1
        assert 'password_hash' not in exported.text and 'google_subject' not in exported.text
        assert client.delete(base, headers=headers, json={**body, 'confirm_username': account['username']}).status_code == 422
        assert client.patch(base, headers=headers, json={**body, 'is_active': False}).status_code == 200
        assert client.delete(base, headers=headers, json={**body, 'confirm_username': 'wrong'}).status_code == 422
        assert client.delete(base, headers=headers, json={**body, 'confirm_username': account['username']}).status_code == 200
        with app.app_context():
            assert db.session.get(User, account['id']) is None
            assert db.session.scalar(select(AlertReview).where(AlertReview.user_id == account['id'])) is None
            assert db.session.scalar(select(Transaction).where(Transaction.user_id == account['id'])) is None
            assert db.session.scalar(select(AdminAudit).where(AdminAudit.action == 'user.delete', AdminAudit.target_id == account['id'])) is not None
            assert db.session.get(User, 'legacy') is not None
        print('PASS: PostgreSQL export, disable/confirmation safeguards, dependent review cleanup and retained audit.')
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


if __name__ == '__main__':
    main()
