"""Loopback-only, in-memory fixture for Android CSV process recovery.

Never registered by the production application. Restart for each lab run.
"""
from flask import request
from flask_jwt_extended import jwt_required

from backend.app.security.current_user import current_user
from backend.scripts.run_acceptance_backend import create_acceptance_app


def create_csv_recovery_app():
    app = create_acceptance_app()
    starts = []
    uploads = []

    @app.after_request
    def record_upload(response):
        if request.path == '/api/v1/transactions/upload' and response.status_code == 200:
            summary = response.get_json()['data']
            uploads.append({key: summary[key] for key in
                            ('received_rows', 'created_rows', 'duplicate_rows', 'invalid_rows')})
        return response

    @app.get('/api/v1/csv-recovery-target')
    def target():
        return {'success': True, 'data': {
            'disposable': True, 'database': 'in_memory', 'scenario': 'csv_recovery',
            'account_id': account['user']['id'], 'bootstrap_allowed': not starts,
            'starts': starts, 'uploads': uploads,
        }}

    @app.post('/api/v1/csv-recovery-ready')
    @jwt_required()
    def ready():
        if current_user().id != account['user']['id']:
            return {'success': False, 'error': {'code': 'WRONG_FIXTURE_OWNER'}}, 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or type(body.get('restored')) is not bool:
            return {'success': False, 'error': {'code': 'INVALID_CHECKPOINT'}}, 422
        if starts and not body['restored']:
            return {'success': False, 'error': {'code': 'SESSION_NOT_RESTORED'}}, 409
        starts.append({'restored': body['restored']})
        return {'success': True, 'data': {'start_count': len(starts)}}

    with app.test_client() as client:
        response = client.post('/api/v1/auth/register', json={
            'email': 'csv-recovery@example.invalid',
            'password': 'SyntheticNativeOnly123!', 'display_name': 'CSV Recovery',
            'accepted_terms': True, 'accepted_privacy': True,
            'model_training_opt_in': False,
        })
        if response.status_code != 201:
            raise RuntimeError('Synthetic account setup failed.')
        account = response.get_json()['data']
        response = client.put('/api/v1/auth/onboarding', json={'action': 'skipped'},
                              headers={'Authorization': 'Bearer ' + account['access_token']})
        if response.status_code != 200:
            raise RuntimeError('Synthetic onboarding setup failed.')
    return app


if __name__ == '__main__':
    create_csv_recovery_app().run(
        host='127.0.0.1', port=5057, debug=False, use_reloader=False, threaded=False,
    )
