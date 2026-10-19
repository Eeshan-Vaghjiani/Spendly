import pytest

from backend.app import create_app
from backend.app.config import cors_origins


@pytest.mark.parametrize('origins,origin,allowed', [
    ((), 'https://untrusted.example', False),
    (cors_origins('*'), 'https://untrusted.example', False),
    (('https://dashboard.example',), 'https://untrusted.example', False),
    (('https://dashboard.example',), 'https://dashboard.example', True),
])
def test_cors_preflight_respects_explicit_origin_configuration(origins, origin, allowed):
    app = create_app({
        'TESTING': True, 'LOAD_MODELS': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite+pysqlite:///:memory:',
        'ALLOWED_CORS_ORIGINS': origins,
    })
    with app.test_client() as client:
        response = client.options('/api/v1/auth/register', headers={
            'Origin': origin,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type',
        })
        assert response.status_code == 200
        assert response.headers.get('Access-Control-Allow-Origin') == (origin if allowed else None)
        assert 'Access-Control-Allow-Credentials' not in response.headers


def test_retained_host_wildcard_does_not_override_explicit_origins():
    assert cors_origins(' *, https://dashboard.example, , * ') == ('https://dashboard.example',)
