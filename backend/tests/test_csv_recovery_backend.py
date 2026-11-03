from io import BytesIO
import xml.etree.ElementTree as ET

import pytest

from backend.scripts.run_csv_recovery_backend import create_csv_recovery_app
from scripts import check_csv_recovery as runner


def test_csv_runner_wait_accepts_a_leaf_control(monkeypatch):
    node = ET.Element('node', {'text': 'More', 'enabled': 'true'})
    clock = iter((0, 0, 1))
    monkeypatch.setattr(runner.time, 'monotonic', lambda: next(clock))
    monkeypatch.setattr(runner.time, 'sleep', lambda _: None)
    assert runner.wait_for(lambda: node, 'leaf control', seconds=1) is node


@pytest.mark.parametrize('missing', [None, False, '', []])
def test_csv_runner_wait_still_retries_missing_values(monkeypatch, missing):
    values = iter((missing, 'ready'))
    monkeypatch.setattr(runner.time, 'sleep', lambda _: None)
    assert runner.wait_for(lambda: next(values), 'ready control') == 'ready'


def test_csv_runner_wait_still_times_out(monkeypatch):
    clock = iter((0, 0, 1))
    monkeypatch.setattr(runner.time, 'monotonic', lambda: next(clock))
    monkeypatch.setattr(runner.time, 'sleep', lambda _: None)
    with pytest.raises(RuntimeError, match='Timed out: absent control'):
        runner.wait_for(lambda: None, 'absent control', seconds=1)


def test_csv_recovery_checkpoints_cannot_mask_lost_session_or_wrong_owner(client):
    assert client.get('/api/v1/csv-recovery-target').status_code == 404
    assert client.post('/api/v1/csv-recovery-ready').status_code == 404
    app = create_csv_recovery_app()
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite+pysqlite:///:memory:'
    with app.test_client() as lab:
        marker = lab.get('/api/v1/csv-recovery-target').get_json()['data']
        assert marker['bootstrap_allowed'] is True
        assert marker['starts'] == []
        assert lab.post('/api/v1/csv-recovery-ready', json={'restored': False}).status_code == 401
        account = lab.post('/api/v1/auth/login', json={
            'email': 'csv-recovery@example.invalid', 'password': 'SyntheticNativeOnly123!',
        }).get_json()['data']
        headers = {'Authorization': 'Bearer ' + account['access_token']}
        assert account['user']['id'] == marker['account_id']
        for invalid in ({}, {'restored': 1}, {'restored': 'true'}, []):
            assert lab.post('/api/v1/csv-recovery-ready', json=invalid, headers=headers).status_code == 422
        other = lab.post('/api/v1/auth/register', json={
            'email': 'other-csv@example.invalid', 'password': 'SyntheticNativeOnly123!',
            'display_name': 'Other synthetic user', 'accepted_terms': True,
            'accepted_privacy': True, 'model_training_opt_in': False,
        }).get_json()['data']
        assert lab.post('/api/v1/csv-recovery-ready', json={'restored': True},
                        headers={'Authorization': 'Bearer ' + other['access_token']}).status_code == 403
        assert lab.post('/api/v1/csv-recovery-ready', json={'restored': False}, headers=headers).status_code == 200
        assert lab.post('/api/v1/csv-recovery-ready', json={'restored': False}, headers=headers).status_code == 409
        assert lab.post('/api/v1/csv-recovery-ready', json={'restored': True}, headers=headers).status_code == 200
        marker = lab.get('/api/v1/csv-recovery-target').get_json()['data']
        assert marker['bootstrap_allowed'] is False
        assert marker['starts'] == [{'restored': False}, {'restored': True}]
        assert marker['uploads'] == []
        csv = (b'transaction_timestamp,amount,category,transaction_type,merchant,is_recurring\n'
               b'2026-10-19T12:00:00+03:00,125.50,food,expense,Synthetic recovery shop,false\n')
        for _ in range(2):
            assert lab.post('/api/v1/transactions/upload', headers=headers,
                            data={'file': (BytesIO(csv), 'synthetic.csv')}).status_code == 200
        assert lab.get('/api/v1/csv-recovery-target').get_json()['data']['uploads'] == [
            {'received_rows': 1, 'created_rows': 1, 'duplicate_rows': 0, 'invalid_rows': 0},
            {'received_rows': 1, 'created_rows': 0, 'duplicate_rows': 1, 'invalid_rows': 0},
        ]
