from concurrent.futures import ThreadPoolExecutor

from backend.scripts.run_acceptance_backend import create_acceptance_app
from backend.app.extensions import db
from sqlalchemy.pool import StaticPool


def test_acceptance_fixture_is_ephemeral_and_not_a_production_route(client):
    assert client.get('/api/v1/acceptance-target').status_code == 404
    app = create_acceptance_app()
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite+pysqlite:///:memory:'
    assert app.config['ADMIN_USERNAME'] is None
    assert app.config['GOOGLE_WEB_CLIENT_ID'] is None
    with app.app_context():
        assert isinstance(db.engine.pool, StaticPool)
        assert db.engine.pool._recycle == -1
    with app.test_client() as synthetic:
        assert synthetic.get('/api/v1/health').status_code == 200
        marker = synthetic.get('/api/v1/acceptance-target').get_json()['data']
        assert marker['disposable'] is True
        assert marker['database'] == 'in_memory'
        assert len(marker['reporting_date']) == 10

    # A real server serves requests on a different thread from db.create_all().
    def register_on_server_thread():
        with app.test_client() as synthetic:
            return synthetic.post('/api/v1/auth/register', json={
                'email': 'thread-check@example.invalid',
                'password': 'SyntheticNativeOnly123!', 'display_name': 'Synthetic',
                'accepted_terms': True, 'accepted_privacy': True,
                'model_training_opt_in': False,
            }).status_code

    with ThreadPoolExecutor(max_workers=1) as server_thread:
        assert server_thread.submit(register_on_server_thread).result() == 201
