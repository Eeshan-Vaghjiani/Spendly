"""Own temporary PostgreSQL container only; never accepts DATABASE_URL.

Uses an already installed postgres:16-alpine image and a loopback-only port.
Container data lives in tmpfs. The generated fixture password is never printed.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
import os
import secrets
import subprocess
from threading import Event
import time
from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask import request
from flask_migrate import downgrade, upgrade
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import URL

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import MpesaComponent, MpesaEvent, Transaction, User
from backend.app.routes import mpesa


def docker(*args, **kwargs):
    return subprocess.run(['docker', *args], check=True, capture_output=True,
                          text=True, timeout=40, **kwargs).stdout.strip()


def event(reference='PGSM000001', **changes):
    return {'external_reference': reference, 'kind': 'sent', 'parser_version': 'mpesa-v1',
            'transaction_timestamp': '2026-10-01T13:10:00Z', 'amount': '214.25',
            'transaction_cost': '8.50', 'transaction_type': 'expense',
            'category': 'transfers', 'merchant': 'Fictional recipient', **changes}


def account(app, suffix):
    with app.test_client() as client:
        response = client.post('/api/v1/auth/register', json={
            'email': suffix+'@example.invalid', 'password': 'SyntheticNativeOnly123!',
            'display_name': 'PG fixture', 'accepted_terms': True,
            'accepted_privacy': True, 'model_training_opt_in': False})
        assert response.status_code == 201
        data = response.get_json()['data']
        return data['user']['id'], {'Authorization': 'Bearer '+data['access_token']}


def consent(app, headers, enabled=True):
    with app.test_client() as client:
        return client.put('/api/v1/mpesa/settings', headers=headers, json={
            'enabled': enabled, 'disclosure_accepted': True,
            'consent_version': '2026-10-22'}).status_code


def importing(app, headers, payload):
    with app.test_client() as client:
        response = client.post('/api/v1/transactions/mpesa/import', headers=headers,
                               json={'events': [payload]})
        return response.status_code, response.get_json()['data'] if response.status_code == 200 else None


def migration_checks(app):
    with app.app_context():
        assert db.session.scalar(text('SELECT current_database()')) == 'spendly_acceptance'
        if inspect(db.engine).get_table_names():
            raise RuntimeError('Refusing a nonempty rehearsal database')
        db.session.remove()
        upgrade(directory='backend/migrations', revision='0007_sign_in_activity')
        db.session.execute(text("""INSERT INTO users
            (id,email,display_name,username,username_normalized,created_at,is_active,model_training_opt_in)
            VALUES ('pg-legacy','pg-legacy@example.invalid','Legacy','pg_legacy','pg_legacy',CURRENT_TIMESTAMP,true,false)"""))
        db.session.execute(text("""INSERT INTO transactions
            (id,user_id,transaction_timestamp,amount,currency,category,transaction_type,is_recurring,source,fingerprint,created_at)
            VALUES ('pg-legacy-tx','pg-legacy',CURRENT_TIMESTAMP,125.50,'KES','food','expense',false,'manual','pg-legacy-fingerprint',CURRENT_TIMESTAMP)"""))
        db.session.commit()
        upgrade(directory='backend/migrations')
        assert db.session.get(User, 'pg-legacy').mpesa_sms_import_enabled is False
        assert db.session.get(Transaction, 'pg-legacy-tx').is_reversed is False
        assert db.session.get(Transaction, 'pg-legacy-tx').amount == Decimal('125.50')
        with db.engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), db.metadata) == []
        db.session.remove()
        downgrade(directory='backend/migrations', revision='0007_sign_in_activity')
        assert 'mpesa_events' not in inspect(db.engine).get_table_names()
        assert db.session.scalar(text("SELECT amount FROM transactions WHERE id='pg-legacy-tx'")) == Decimal('125.50')
        db.session.commit()
        upgrade(directory='backend/migrations')
        with db.engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), db.metadata) == []
    print('PASS: PostgreSQL 0007 -> 0008 -> 0007 -> 0008; legacy data/defaults and metadata parity.', flush=True)


def duplicate_checks(app):
    owner, headers = account(app, 'pg-duplicates')
    assert importing(app, headers, event())[0] == 403
    assert consent(app, headers) == 200
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: importing(app, headers, event()), range(4)))
    assert all(code == 200 for code, _ in results)
    assert sum(data['created'] for _, data in results) == 2
    assert sum(data['duplicate'] for _, data in results) == 3
    with app.app_context():
        assert db.session.scalar(select(func.count(MpesaEvent.id)).where(MpesaEvent.user_id == owner)) == 1
        assert db.session.scalar(select(func.count(MpesaComponent.id)).where(MpesaComponent.user_id == owner)) == 2
        rows = list(db.session.scalars(select(Transaction).where(Transaction.user_id == owner)))
        assert sorted(row.amount for row in rows) == [Decimal('8.50'), Decimal('214.25')]
        principal = next(row.id for row in rows if row.category == 'transfers')
    with app.test_client() as client:
        assert client.delete('/api/v1/transactions/'+principal, headers=headers).status_code == 200
    assert importing(app, headers, event())[1]['duplicate'] == 1
    with app.app_context():
        link = db.session.scalar(select(MpesaComponent).where(MpesaComponent.user_id == owner,
                                                              MpesaComponent.component == 'principal'))
        assert link.transaction_id is None
    other, other_headers = account(app, 'pg-other-owner')
    assert consent(app, other_headers) == 200
    assert importing(app, other_headers, event())[1]['created'] == 2
    print('PASS: four concurrent imports -> one source/two components; deletion/replay and second-owner isolation.', flush=True)


def consent_race_checks(app, disable_first):
    owner, headers = account(app, 'pg-disable-'+str(disable_first).lower())
    assert consent(app, headers) == 200
    acquired, release, second_started = Event(), Event(), Event()
    original = mpesa.locked_user
    first_method = 'PUT' if disable_first else 'POST'

    def locked():
        if request.method != first_method:
            second_started.set()
        user = original()
        if request.method == first_method:
            acquired.set()
            assert release.wait(10)
        return user

    mpesa.locked_user = locked
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            disable = lambda: consent(app, headers, False)
            submit = lambda: importing(app, headers, event())[0]
            first = pool.submit(disable if disable_first else submit)
            assert acquired.wait(10)
            second = pool.submit(submit if disable_first else disable)
            assert second_started.wait(10)
            assert not second.done()
            release.set()
            assert first.result(timeout=15) == 200
            assert second.result(timeout=15) == (403 if disable_first else 200)
    finally:
        release.set()
        mpesa.locked_user = original
    assert importing(app, headers, event('PGSM000009'))[0] == 403
    with app.app_context():
        assert db.session.scalar(select(func.count(Transaction.id)).where(Transaction.user_id == owner)) == (0 if disable_first else 2)
    print('PASS: PostgreSQL consent/import ordering, disable_first='+str(disable_first)+'.', flush=True)


def main():
    if not __debug__:
        raise RuntimeError('Assertions must be enabled')
    name = 'spendly-mpesa-pg-'+uuid4().hex[:10]
    password = secrets.token_urlsafe(32)
    child_env = {**os.environ, 'POSTGRES_PASSWORD': password}
    container = None
    app = None
    try:
        container = docker('run', '--pull=never', '--rm', '-d', '--name', name,
                           '--label', 'spendly.disposable=mpesa-release-rehearsal',
                           '--tmpfs', '/var/lib/postgresql/data:rw,size=512m',
                           '-p', '127.0.0.1:55432:5432', '-e', 'POSTGRES_PASSWORD',
                           '-e', 'POSTGRES_USER=spendly_acceptance',
                           '-e', 'POSTGRES_DB=spendly_acceptance', 'postgres:16-alpine', env=child_env)
        if len(container) != 64 or any(c not in '0123456789abcdef' for c in container):
            raise RuntimeError('Unexpected container identity')
        for _ in range(45):
            try:
                docker('exec', container, 'pg_isready', '-U', 'spendly_acceptance', '-d', 'spendly_acceptance')
                break
            except subprocess.CalledProcessError:
                time.sleep(1)
        else:
            raise RuntimeError('Disposable PostgreSQL did not become ready')
        app = create_app({'TESTING': True, 'LOAD_MODELS': False, 'SELECTED_MODEL_ROOT': None,
            'MPESA_SMS_ENABLED': True, 'SECRET_KEY': 'pg-sms-disposable-only-secret-32-bytes',
            'JWT_SECRET_KEY': 'pg-sms-disposable-only-jwt-key-32-bytes',
            'SQLALCHEMY_DATABASE_URI': URL.create('postgresql+psycopg', username='spendly_acceptance',
                password=password, host='127.0.0.1', port=55432, database='spendly_acceptance'),
            'ADMIN_USERNAME': None, 'ADMIN_PASSWORD': None, 'GOOGLE_WEB_CLIENT_ID': None})
        migration_checks(app)
        duplicate_checks(app)
        consent_race_checks(app, False)
        consent_race_checks(app, True)
        print('PASS: all disposable PostgreSQL M-PESA release checks.', flush=True)
    finally:
        if app:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        if container:
            # Remove only the exact container created by this invocation.
            docker('rm', '-f', container)
            print('CLEANUP: owned temporary container removed; no persistent volume.', flush=True)


if __name__ == '__main__':
    main()
