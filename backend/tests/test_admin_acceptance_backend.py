from sqlalchemy import func, select

from backend.app.extensions import db
from backend.app.models import Budget, Transaction, User
from backend.scripts.run_admin_acceptance_backend import create_admin_acceptance_app


def test_admin_acceptance_has_multiple_pages_and_only_disposable_data():
    app = create_admin_acceptance_app()
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite+pysqlite:///:memory:'
    assert app.config['ADMIN_USERNAME'] == 'admin'
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 25
        assert db.session.scalar(select(func.count()).select_from(Transaction)) == 45
        assert db.session.scalar(select(func.count()).select_from(Budget)) == 1
        assert all(user.email.endswith('@example.invalid') for user in db.session.scalars(select(User)))
    with app.test_client() as client:
        assert client.get('/admin/manage').status_code == 302
        assert client.get('/api/v1/acceptance-target').get_json()['data']['disposable'] is True
