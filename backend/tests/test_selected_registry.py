from datetime import datetime,timedelta
from pathlib import Path
from backend.tests.conftest import register


def test_selected_path_requires_confirmation_and_never_calls_linear(app,client,auth):
    registry=app.extensions['model_registry']
    calls=[]
    def forecast_history(transactions,owner,target,start):
        calls.append((owner,target,start))
        assert target.weekday()==0 and target==target.normalize()
        return 1234.56
    def detect_history(transactions,owner):
        import pandas as pd
        return pd.DataFrame(columns=['transaction_id','anomaly_score','is_unusual_spending','decision_threshold','explanation'])
    registry.forecast_history=forecast_history
    registry.detect_history=detect_history
    registry.forecast_version='selected-lstm-v6'
    registry.forecast=lambda *args: (_ for _ in ()).throw(AssertionError('Linear/V1 path called'))
    for i in range(10):
        assert client.post('/api/v1/transactions',headers=auth,json=dict(
            transaction_timestamp=(datetime.now()-timedelta(weeks=12-i)).isoformat()+'Z',
            amount=100,category='food',transaction_type='expense',merchant='shop',is_recurring=False)).status_code==201
    assert client.post('/api/v1/analysis/run',headers=auth).status_code==422
    response=client.post('/api/v1/analysis/run',headers=auth,json={'history_complete_from':'2020-01-01'})
    assert response.status_code==200,response.get_json()
    forecast=response.get_json()['data']['forecast']
    assert forecast['forecast_method']=='v6_reference_lstm'
    assert forecast['predicted_spending']==1234.56
    assert len(calls)==1


def test_actual_portable_backend_without_tensorflow(app,client,auth):
    import sys
    from backend.app.services.selected_registry import SelectedModelRegistry
    root=Path(__file__).resolve().parents[2]
    selected=SelectedModelRegistry(root/'artifacts/models',root/'artifacts/candidates/selected_v6')
    selected.load()
    app.extensions['model_registry']=selected
    for i in range(12):
        response=client.post('/api/v1/transactions',headers=auth,json=dict(
            transaction_timestamp=(datetime.now()-timedelta(weeks=14-i)).isoformat()+'Z',amount=100+i,
            category='food',transaction_type='expense',merchant='shop',is_recurring=False))
        assert response.status_code==201
    result=client.post('/api/v1/analysis/run',headers=auth,json={'history_complete_from':'2020-01-01'})
    assert result.status_code==200,result.get_json()
    assert result.get_json()['data']['forecast']['forecast_method']=='v6_reference_lstm'
    assert 'tensorflow' not in sys.modules
