from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models import AnalysisRun,AnomalyAlert,Transaction,AlertReview
from backend.app.services.transactions import TransactionService
from backend.app.services.alert_review import review_state
from backend.tests.conftest import register


def seed(app,client,headers):
    for i in range(10):
        response=client.post('/api/v1/transactions',headers=headers,json=dict(
            transaction_timestamp=(datetime(2025,1,6)+timedelta(weeks=i)).isoformat()+'Z',
            amount=100 if i<9 else 2000,category='food',transaction_type='expense',merchant='shop',is_recurring=False))
        assert response.status_code==201
    result=client.post('/api/v1/analysis/run',headers=headers).get_json()['data']
    return result['alert_summary']['alerts'][0]


def test_alert_links_owner_transaction_and_context(app,client,auth):
    alert=seed(app,client,auth)
    assert alert['transaction']['amount']==2000
    assert '100.00' in alert['explanation'] and '2,000.00' in alert['explanation']
    assert alert['review_status']=='pending'
    tid=alert['transaction_id']
    assert client.get('/api/v1/transactions/'+tid,headers=auth).status_code==200
    other=register(client,email='other-review@example.com')
    other_headers={'Authorization':'Bearer '+other['access_token']}
    assert client.get('/api/v1/transactions/'+tid,headers=other_headers).status_code==404
    assert client.put('/api/v1/alerts/'+alert['id']+'/review',headers=other_headers,json={'status':'intentional','transaction_review_version':alert['transaction_review_version']}).status_code==404


def test_intentional_review_preserves_spend_and_changes_advice(app,client,auth):
    alert=seed(app,client,auth)
    for _ in range(2):
        response=client.put('/api/v1/alerts/'+alert['id']+'/review',headers=auth,json={'status':'intentional','transaction_review_version':alert['transaction_review_version']})
        assert response.status_code==200 and response.get_json()['data']['review_status']=='intentional'
    with app.app_context():
        assert len(db.session.scalars(select(AlertReview)).all())==1
        assert db.session.get(Transaction,alert['transaction_id']).amount==Decimal('2000.00')
    new=client.post('/api/v1/analysis/run',headers=auth).get_json()['data']
    assert new['alert_summary']['alert_count']==0
    codes={r['recommendation_code'] for r in new['recommendations']}
    assert 'UNUSUAL_SPENDING_REVIEW' not in codes
    assert 'PLAN_CONFIRMED_SPENDING' in codes
    assert client.put('/api/v1/alerts/'+alert['id']+'/review',headers=auth,json={'status':'pending','transaction_review_version':alert['transaction_review_version']}).status_code==200
    again=client.post('/api/v1/analysis/run',headers=auth).get_json()['data']
    assert again['alert_summary']['alert_count']==1


def test_edit_invalidates_intentional_confirmation(app,client,auth):
    alert=seed(app,client,auth)
    client.put('/api/v1/alerts/'+alert['id']+'/review',headers=auth,json={'status':'intentional','transaction_review_version':alert['transaction_review_version']})
    transaction=alert['transaction']
    payload={k:transaction[k] for k in ('transaction_timestamp','amount','category','transaction_type','merchant','is_recurring')}
    payload['amount']=150
    assert client.put('/api/v1/transactions/'+alert['transaction_id'],headers=auth,json=payload).status_code==200
    latest=client.get('/api/v1/analysis/latest',headers=auth).get_json()['data']
    assert latest['alert_summary']['alerts'][0]['review_status']=='changed_since_review'
    assert client.put('/api/v1/alerts/'+alert['id']+'/review',headers=auth,json={'status':'fraud'}).status_code==422
    assert client.put('/api/v1/alerts/'+alert['id']+'/review',headers=auth,json={'status':'intentional','transaction_review_version':alert['transaction_review_version']}).status_code==409
    for status in ([],{},None,True,2):
        assert client.put('/api/v1/alerts/'+alert['id']+'/review',headers=auth,json={'status':status,'transaction_review_version':alert['transaction_review_version']}).status_code==422


def test_recurrence_edit_and_delete_review_cleanup(app,client,auth):
    alert=seed(app,client,auth)
    client.put('/api/v1/alerts/'+alert['id']+'/review',headers=auth,json={'status':'intentional','transaction_review_version':alert['transaction_review_version']})
    transaction=alert['transaction']
    payload={k:transaction[k] for k in ('transaction_timestamp','amount','category','transaction_type','merchant','is_recurring')}
    payload['is_recurring']=True
    client.put('/api/v1/transactions/'+alert['transaction_id'],headers=auth,json=payload)
    latest=client.get('/api/v1/analysis/latest',headers=auth).get_json()['data']
    assert latest['alert_summary']['alerts'][0]['review_status']=='changed_since_review'
    assert client.delete('/api/v1/transactions/'+alert['transaction_id'],headers=auth).status_code==200
    with app.app_context():assert db.session.scalar(select(AlertReview)) is None
    latest=client.get('/api/v1/analysis/latest',headers=auth).get_json()['data']
    assert latest['alert_summary']['alerts'][0]['review_status']=='transaction_deleted'
