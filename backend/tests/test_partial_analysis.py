from datetime import timedelta

import pandas as pd
import pytest
from sqlalchemy import select, func

from backend.app.extensions import db
from backend.app.models import AnalysisRun, Forecast
from backend.tests.conftest import register
from services.aligned_inference.features import InsufficientHistory


def selected_stub(app):
    registry = app.extensions['model_registry']
    calls = []
    def forecast(transactions, owner, target, start):
        calls.append('forecast')
        return 1234.56
    def detect(transactions, owner):
        calls.append('detect')
        assert all(t.user_id == owner for t in transactions)
        frame = pd.DataFrame({'transaction_id': [t.id for t in transactions]})
        frame['anomaly_score'] = .8
        frame['is_unusual_spending'] = True
        frame['decision_threshold'] = .5
        frame['explanation'] = 'Review recorded spending.'
        return frame
    registry.forecast_history = forecast
    registry.detect_history = detect
    registry.forecast_version = 'selected-lstm-v6'
    return registry, calls


def add_expense(client, auth):
    response = client.post('/api/v1/transactions', headers=auth, json={
        'transaction_timestamp': '2026-01-05T12:00:00Z', 'amount': 100,
        'category': 'food', 'transaction_type': 'expense', 'merchant': 'shop',
        'is_recurring': False})
    assert response.status_code == 201
    return response.get_json()['data']['id']


@pytest.mark.parametrize('weeks', [None, 0, 1, 7, 8])
def test_partial_history_preserves_insights_and_legacy_contract(app, client, auth, weeks):
    registry, calls = selected_stub(app)
    transaction_id = add_expense(client, auth)
    now = pd.Timestamp.now(tz='Africa/Nairobi').tz_localize(None)
    target = now.normalize() - pd.Timedelta(days=now.weekday())
    payload = {'allow_partial_results': True}
    if weeks is not None:
        payload['history_complete_from'] = (target - timedelta(weeks=weeks)).date().isoformat()
    response = client.post('/api/v1/analysis/run', headers=auth, json=payload)
    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['alert_summary']['alerts'][0]['transaction_id'] == transaction_id
    assert data['recommendations']
    if weeks == 8:
        assert data['forecast']['predicted_spending'] == 1234.56
        assert data['forecast_unavailable'] is None
        assert calls == ['forecast', 'detect']
    else:
        assert data['forecast'] is None
        expected = 'HISTORY_CONFIRMATION_REQUIRED' if weeks is None else 'INSUFFICIENT_HISTORY'
        assert data['forecast_unavailable']['code'] == expected
        codes = {r['recommendation_code'] for r in data['recommendations']}
        assert 'UNUSUAL_SPENDING_REVIEW' in codes
        assert 'SPENDING_EXCEEDS_INCOME' in codes
        assert 'FORECAST_EXCEEDS_BUDGET' not in codes
        assert calls == ['detect']
        assert db.session.scalar(select(func.count()).select_from(Forecast)) == 0
        assert client.get('/api/v1/analysis/latest', headers=auth).status_code == 404
        legacy = dict(payload, allow_partial_results=False)
        assert client.post('/api/v1/analysis/run', headers=auth, json=legacy).status_code == 422
    restored = client.get('/api/v1/analysis/latest?allow_partial_results=true', headers=auth)
    assert restored.get_json()['data'] == data
    other = register(client, email='other@example.com')
    other_auth = {'Authorization': 'Bearer ' + other['access_token']}
    assert client.get('/api/v1/analysis/latest?allow_partial_results=true', headers=other_auth).status_code == 404


def test_known_insufficient_history_is_partial_but_runtime_errors_propagate(app, client, auth):
    registry, calls = selected_stub(app)
    def unavailable(*args):
        raise InsufficientHistory('No recorded spending')
    registry.forecast_history = unavailable
    payload = {'allow_partial_results': True, 'history_complete_from': '2020-01-01'}
    result = client.post('/api/v1/analysis/run', headers=auth, json=payload)
    assert result.status_code == 200
    assert result.get_json()['data']['forecast'] is None
    assert calls == ['detect']
    def failed(*args):
        raise RuntimeError('synthetic model failure')
    registry.forecast_history = failed
    failed_response = client.post('/api/v1/analysis/run', headers=auth, json=payload)
    assert failed_response.status_code == 500
    assert db.session.scalar(select(func.count()).select_from(AnalysisRun)) == 1


@pytest.mark.parametrize('value', ['invalid', 7, {}, '2026-02-30'])
def test_bad_history_date_does_not_become_partial_success(app, client, auth, value):
    _, calls = selected_stub(app)
    result = client.post('/api/v1/analysis/run', headers=auth, json={
        'allow_partial_results': True, 'history_complete_from': value})
    assert result.status_code == 422
    assert calls == []


def test_legacy_latest_skips_newer_partial_result(app, client, auth):
    selected_stub(app)
    add_expense(client, auth)
    complete = client.post('/api/v1/analysis/run', headers=auth,
                           json={'history_complete_from': '2020-01-01'}).get_json()['data']
    partial = client.post('/api/v1/analysis/run', headers=auth,
                          json={'allow_partial_results': True}).get_json()['data']
    assert client.get('/api/v1/analysis/latest', headers=auth).get_json()['data']['analysis_run_id'] == complete['analysis_run_id']
    assert client.get('/api/v1/analysis/latest?allow_partial_results=true', headers=auth).get_json()['data']['analysis_run_id'] == partial['analysis_run_id']


def test_actual_portable_empty_history_never_predicts(app, client, auth):
    from pathlib import Path
    from backend.app.services.selected_registry import SelectedModelRegistry
    root = Path(__file__).resolve().parents[2]
    registry = SelectedModelRegistry(root/'artifacts/models', root/'artifacts/candidates/selected_v6')
    registry.load()
    def unexpected(*args):
        raise AssertionError('Ineligible history reached prediction')
    registry.portable.predict_features = unexpected
    app.extensions['model_registry'] = registry
    result = client.post('/api/v1/analysis/run', headers=auth, json={
        'allow_partial_results': True, 'history_complete_from': '2020-01-01'})
    assert result.status_code == 200
    assert result.get_json()['data']['forecast'] is None


def test_actual_portable_confirmed_quiet_weeks_are_eligible(app, client, auth):
    from pathlib import Path
    from backend.app.services.selected_registry import SelectedModelRegistry
    root = Path(__file__).resolve().parents[2]
    registry = SelectedModelRegistry(root/'artifacts/models', root/'artifacts/candidates/selected_v6')
    registry.load()
    app.extensions['model_registry'] = registry
    now = pd.Timestamp.now(tz='Africa/Nairobi').tz_localize(None)
    target = now.normalize() - pd.Timedelta(days=now.weekday())
    # Explicitly confirmed zero-spending weeks are valid; one recorded week supplies signal.
    response = client.post('/api/v1/transactions', headers=auth, json={
        'transaction_timestamp': (target - timedelta(days=4)).isoformat() + '+03:00',
        'amount': 100, 'category': 'food', 'transaction_type': 'expense',
        'merchant': 'shop', 'is_recurring': False})
    assert response.status_code == 201
    result = client.post('/api/v1/analysis/run', headers=auth, json={
        'allow_partial_results': True,
        'history_complete_from': (target-timedelta(weeks=8)).date().isoformat()})
    assert result.status_code == 200
    assert result.get_json()['data']['forecast']['predicted_spending'] >= 0
    assert result.get_json()['data']['forecast_unavailable'] is None
