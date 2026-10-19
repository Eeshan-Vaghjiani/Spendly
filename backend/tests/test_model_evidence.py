import json
from pathlib import Path

import pytest

from backend.app.services.model_evidence import evaluation_metadata
from backend.app.services.selected_registry import SelectedModelRegistry
from backend.tests.test_analytics_admin import admin_headers

ROOT = Path(__file__).resolve().parents[2]
SELECTED = ROOT / 'artifacts/candidates/selected_v6'


def registry():
    value = SelectedModelRegistry(ROOT/'artifacts/models', SELECTED)
    value.load()
    return value


def test_admin_reports_loaded_identity_and_bound_evaluation(app, client):
    app.extensions['model_registry'] = registry()
    app.config['SOURCE_REVISION'] = 'a'*40
    assert client.get('/api/v1/admin/overview').status_code == 401
    response = client.get('/api/v1/admin/overview', headers=admin_headers())
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    data = response.get_json()['data']
    assert data['release'] == {'api_release':'1.3.4', 'source_revision':'a'*40}
    info = data['model_info']
    assert info['forecasting']['method'] == 'v6_reference_lstm'
    assert info['forecasting']['feature_count'] == 26
    assert info['forecasting']['reporting_timezone'] == 'Africa/Nairobi'
    assert info['anomaly']['feature_count'] == 5
    assert info['anomaly']['trees'] == 300
    assert info['anomaly']['max_samples'] == 128
    settings = client.get('/api/v1/admin/settings', headers=admin_headers()).get_json()['data']
    assert settings['model_runtime'] == 'portable_lstm'
    assert info['anomaly']['evaluation']['status'] == 'artifact_matched'
    standard, shifted, external = info['anomaly']['evaluation']['cohorts']
    assert standard['metrics']['precision'] == pytest.approx(554/889)
    assert shifted['metrics']['F1'] == pytest.approx(.6141015921152388)
    assert external['metrics'] == {}
    public = client.get('/api/v1/model-info').get_json()['data']
    assert 'evaluation' not in public['forecasting']
    assert 'weights_sha256' not in public['forecasting']
    assert str(SELECTED) not in json.dumps(data)


@pytest.mark.parametrize('key', ['weights_sha256','source_forecast_sha256','source_alert_sha256','threshold','format'])
def test_evaluation_mismatch_is_unavailable_without_affecting_inference(tmp_path, key):
    identity = json.loads((SELECTED/'manifest.json').read_text())
    data = json.loads((SELECTED/'evaluation.json').read_text())
    data['identity'][key] = 'mismatch'
    path = tmp_path/'evaluation.json'
    path.write_text(json.dumps(data))
    result = evaluation_metadata(path, identity)
    assert all(item == {'status':'unavailable','cohorts':[]} for item in result.values())


def test_bad_or_missing_aggregate_metadata_fails_closed(tmp_path):
    identity = json.loads((SELECTED/'manifest.json').read_text())
    path = tmp_path/'missing.json'
    for content in [None, 'malformed', '{}']:
        if content is not None:
            path.write_text(content)
        assert evaluation_metadata(path, identity)['forecasting']['status'] == 'unavailable'
    data = json.loads((SELECTED/'evaluation.json').read_text())
    data['forecasting'][0]['metrics']['WAPE'] = float('nan')
    path.write_text(json.dumps(data))
    assert evaluation_metadata(path, identity)['forecasting']['status'] == 'unavailable'


@pytest.mark.parametrize('malformed', ['overflow', 'nesting'])
def test_optional_bad_evidence_cannot_stop_real_registry_loading(tmp_path, monkeypatch, malformed):
    from backend.app.services import selected_registry
    original = evaluation_metadata
    path = tmp_path/'bad.json'
    if malformed == 'overflow':
        data = json.loads((SELECTED/'evaluation.json').read_text())
        data['forecasting'][0]['metrics']['WAPE'] = 10**400
        path.write_text(json.dumps(data))
    else:
        path.write_text('['*2000+'0'+']'*2000)
    monkeypatch.setattr(selected_registry, 'evaluation_metadata', lambda ignored, identity: original(path, identity))
    value = registry()
    assert value.loaded is True
    assert value.admin_info()['forecasting']['evaluation']['status'] == 'unavailable'


def test_unknown_source_revision_is_explicit_and_public_health_matches(app, client):
    app.config['SOURCE_REVISION'] = 'not-a-commit-or-a-secret-value'
    data = client.get('/api/v1/admin/overview', headers=admin_headers()).get_json()['data']
    assert data['release']['source_revision'] is None
    assert client.get('/api/v1/health').get_json()['data']['api_release'] == data['release']['api_release']
    page = client.get('/admin', headers=admin_headers())
    assert b'aria-live="polite"' in page.data
    assert b'Experimental educational models' in page.data
    assert b'WAPE is forecast error' in page.data
