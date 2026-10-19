from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.extensions import db
from backend.app.models import AnalysisRun, Forecast, Transaction
from backend.app.reporting_time import reporting_date, utc_start
from backend.app.repositories import TransactionRepository
from backend.tests.conftest import register


@pytest.mark.parametrize('day,period', [(date(2026,1,5),'weekly'), (date(2026,8,1),'monthly'), (date(2026,1,1),'yearly')])
def test_nairobi_boundaries_agree_across_financial_views(app, client, monkeypatch, day, period):
    account = register(client)
    other = register(client, email='other@example.com')
    owner = account['user']['id']
    auth = {'Authorization': 'Bearer '+account['access_token']}
    monkeypatch.setattr('backend.app.routes.analytics.reporting_today', lambda: day)
    monkeypatch.setattr('backend.app.services.analysis.reporting_today', lambda: day+timedelta(days=1))
    left, right = utc_start(day), utc_start(day+timedelta(days=1))
    timestamps = [left-timedelta(microseconds=1), left, right-timedelta(microseconds=1), right]
    ids=[]
    for stamp, amount in zip(timestamps, [10,20,30,40]):
        response=client.post('/api/v1/transactions',headers=auth,json={
            'transaction_timestamp':stamp.isoformat()+'Z', 'amount':amount,
            'category':'food', 'transaction_type':'expense', 'is_recurring':False})
        assert response.status_code==201
        ids.append(response.get_json()['data']['id'])
    db.session.add(Transaction(user_id=other['user']['id'], transaction_timestamp=left,
                               amount=500, category='food', transaction_type='expense', fingerprint='other'))
    db.session.commit()
    filtered=client.get(f'/api/v1/transactions?start_date={day}&end_date={day}',headers=auth).get_json()['data']['items']
    assert {item['id'] for item in filtered}==set(ids[1:3])
    assert client.post('/api/v1/budgets',headers=auth,json={
        'period_start':day.isoformat(),'period_end':day.isoformat(),'category':'total','amount':100}).status_code==201
    dashboard=client.get(f'/api/v1/analytics/dashboard?period={period}',headers=auth).get_json()['data']
    assert dashboard['expense']==50
    assert dashboard['active_budget']['spent']==50
    assert dashboard['has_older_transactions'] is True
    assert dashboard['reporting_timezone']=='Africa/Nairobi'
    all_time=client.get('/api/v1/analytics/dashboard?period=all_time',headers=auth).get_json()['data']
    assert all_time['expense']==100
    assert all_time['period_start']==(day-timedelta(days=1)).isoformat()
    cashflow=client.get('/api/v1/analytics/cashflow?resolution=daily',headers=auth).get_json()['data']
    assert cashflow['series'][-1]['expense']==50
    assert TransactionRepository.expense_total(owner,day,day)==(50,2)
    run=AnalysisRun(user_id=owner, forecast_model_version='selected-lstm-v6', anomaly_model_version='selected-if-v6', history_periods=8)
    db.session.add(run)
    db.session.flush()
    db.session.add(Forecast(user_id=owner,analysis_run_id=run.id,period_start=day,period_end=day,predicted_spending=Decimal('50'),model_version='selected-lstm-v6'))
    db.session.commit()
    forecast=client.get('/api/v1/forecasts',headers=auth).get_json()['data']['items'][0]
    assert forecast['actual_spending']==50
    assert list(db.session.scalars(select(Transaction.transaction_timestamp).where(Transaction.user_id==owner).order_by(Transaction.transaction_timestamp)))==timestamps


def test_reporting_conversion_does_not_shift_aware_values_twice():
    assert reporting_date(datetime(2026,1,4,21,30))==date(2026,1,5)
    assert reporting_date(datetime.fromisoformat('2026-01-05T00:30:00+03:00'))==date(2026,1,5)
    assert reporting_date(datetime(2026,1,4,21,30,tzinfo=timezone.utc))==date(2026,1,5)


@pytest.mark.parametrize('version,expected', [('v1',30), ('selected-lstm-v6',50)])
def test_forecast_actuals_retain_original_model_calendar(app, client, auth, monkeypatch, version, expected):
    from backend.app.models import User
    owner=db.session.scalar(select(User.id))
    monkeypatch.setattr('backend.app.services.analysis.reporting_today',lambda:date(2026,1,6))
    for timestamp,amount in [('2026-01-04T21:30:00Z',20),('2026-01-05T12:00:00Z',30)]:
        assert client.post('/api/v1/transactions',headers=auth,json={
            'transaction_timestamp':timestamp,'amount':amount,'category':'food','transaction_type':'expense'}).status_code==201
    run=AnalysisRun(user_id=owner,forecast_model_version=version,anomaly_model_version='v1',history_periods=8)
    db.session.add(run)
    db.session.flush()
    db.session.add(Forecast(user_id=owner,analysis_run_id=run.id,period_start=date(2026,1,5),period_end=date(2026,1,5),predicted_spending=50,model_version=version))
    db.session.commit()
    result=client.get('/api/v1/forecasts',headers=auth).get_json()['data']['items'][0]
    assert result['actual_spending']==expected


@pytest.mark.parametrize('version,expected', [('v1',None), ('selected-lstm-v6',50)])
def test_forecast_closure_uses_original_calendar(app, client, auth, monkeypatch, version, expected):
    from backend.app.models import User
    owner=db.session.scalar(select(User.id))
    # One instant: Nairobi Monday00:30, UTC Sunday21:30.
    monkeypatch.setattr('backend.app.services.analysis.reporting_today',lambda:date(2026,1,5))
    monkeypatch.setattr('backend.app.services.analysis.utc_today',lambda:date(2026,1,4))
    db.session.add(Transaction(user_id=owner,transaction_timestamp=datetime(2026,1,4,12),amount=50,
                               category='food',transaction_type='expense',fingerprint='closing'))
    run=AnalysisRun(user_id=owner,forecast_model_version=version,anomaly_model_version='v1',history_periods=8)
    db.session.add(run)
    db.session.flush()
    db.session.add(Forecast(user_id=owner,analysis_run_id=run.id,period_start=date(2025,12,29),period_end=date(2026,1,4),predicted_spending=50,model_version=version))
    db.session.commit()
    result=client.get('/api/v1/forecasts',headers=auth).get_json()['data']['items'][0]
    assert result['actual_spending']==expected
