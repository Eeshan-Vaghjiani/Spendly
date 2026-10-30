"""Disposable loopback-only backend for the separate Android acceptance APK.

Run from the repository root: python -m backend.scripts.run_acceptance_backend
The database is always in memory; DATABASE_URL and persistent Compose are ignored.
"""
from pathlib import Path

from sqlalchemy.pool import StaticPool

from backend.app import create_app
from backend.app.extensions import db
from backend.app.reporting_time import reporting_today


def create_acceptance_app():
    root = Path(__file__).resolve().parents[2]
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'disposable-local-acceptance-only-32-bytes',
        'JWT_SECRET_KEY': 'disposable-local-acceptance-jwt-32-bytes',
        'SQLALCHEMY_DATABASE_URI': 'sqlite+pysqlite:///:memory:',
        # Recycling an in-memory connection destroys its tables. Share one
        # connection across the setup/server threads for this serial fixture.
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'poolclass': StaticPool, 'pool_recycle': -1,
            'connect_args': {'check_same_thread': False},
        },
        'MODEL_ROOT': root/'artifacts/models',
        'SELECTED_MODEL_ROOT': root/'artifacts/candidates/selected_v6',
        'MODEL_RUNTIME': 'lightweight', 'LOAD_MODELS': True,
        'ADMIN_USERNAME': None, 'ADMIN_PASSWORD': None,
        'SESSION_COOKIE_SECURE': False, 'SOURCE_REVISION': None,
        'GOOGLE_WEB_CLIENT_ID': None,
        'ALLOWED_CORS_ORIGINS': ('http://localhost',),
    })
    with app.app_context():
        db.create_all()

    @app.get('/api/v1/acceptance-target')
    def acceptance_target():
        return {'success': True, 'data': {'disposable': True, 'database': 'in_memory',
                                        'reporting_date': reporting_today().isoformat()}}

    return app


if __name__ == '__main__':
    create_acceptance_app().run(
        host='127.0.0.1', port=5057, debug=False, use_reloader=False, threaded=False,
    )
