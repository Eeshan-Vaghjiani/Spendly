from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import tempfile
from pathlib import Path
import unittest

from services.spend_advisor.app import create_app, json_money
from services.spend_advisor.feedback import FeedbackStore, StaleOffer

KEY = 'synthetic-only-service-key-0000000000000'
PERIOD = ('household-a', 6, 2026)


def item(amount='20.00'):
    return dict(type='review_category_budget', reason='Synthetic planning scenario',
                savingKes=Decimal(amount), targetId='target-a')


class Source:
    sha256 = 'fixture'
    def advice(self, *key):
        if key != PERIOD: raise LookupError()
        return [item()]


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'feedback.sqlite'
        self.store = FeedbackStore(self.path)
        self.client = create_app(Source(), KEY, self.store).test_client()

    def issue(self, items=None):
        return self.store.issue(PERIOD, items if items is not None else [item()], json_money, source_identity='fixture')[0]['offerId']

    def test_restart_retries_and_unanswered_denominator(self):
        offers = self.store.issue(PERIOD, [item(), dict(item(),targetId='second')], json_money, source_identity='fixture')
        self.store.feedback(PERIOD, offers[0]['offerId'], accepted=True, source_identity='fixture')
        with self.assertRaises(StaleOffer):
            self.store.feedback(PERIOD, offers[0]['offerId'], accepted=True, source_identity='fixture')
        restarted = FeedbackStore(self.path)
        restarted.issue(PERIOD, [item(), dict(item(),targetId='second')], json_money, source_identity='fixture')
        metrics = restarted.metrics(PERIOD)
        self.assertEqual((metrics['delivered'], metrics['shown'], metrics['responded'], metrics['accepted']), (2,1,1,1))
        self.assertEqual(metrics['acceptRate'], Decimal('.5000'))

    def test_changed_offer_does_not_inherit_decision(self):
        original = self.issue(); self.store.feedback(PERIOD, original, accepted=True, source_identity='fixture')
        replacement = self.issue([item('30.00')])
        self.assertNotEqual(original, replacement)
        with self.assertRaises(StaleOffer): self.store.feedback(PERIOD, original, accepted=False, source_identity='fixture')
        self.assertEqual(self.store.metrics(PERIOD)['acceptRate'], Decimal('.5000'))
        self.store.feedback(PERIOD, replacement, accepted=False, source_identity='fixture')
        self.assertEqual(self.store.metrics(PERIOD)['responded'], 2)

    def test_withdrawal_owner_and_period_scope(self):
        offer = self.issue()
        for key in (('household-b',6,2026), ('household-a',7,2026)):
            with self.assertRaises(LookupError): self.store.feedback(key, offer, accepted=True, source_identity='fixture')
            self.assertIsNone(self.store.metrics(key)['acceptRate'])
        self.store.issue(PERIOD, [], json_money, source_identity='fixture')
        with self.assertRaises(StaleOffer): self.store.feedback(PERIOD, offer, accepted=True, source_identity='fixture')

    def test_display_is_explicit_and_latest_decision_wins(self):
        offer = self.issue()
        self.assertEqual(self.store.metrics(PERIOD)['shown'], 0)
        self.store.feedback(PERIOD, offer, shown=True, source_identity='fixture')
        self.assertEqual(self.store.metrics(PERIOD)['responded'], 0)
        self.store.feedback(PERIOD, offer, accepted=True, source_identity='fixture')
        self.store.feedback(PERIOD, offer, accepted=False, expected_revision=1, source_identity='fixture')
        with self.assertRaises(StaleOffer):
            self.store.feedback(PERIOD, offer, accepted=True, expected_revision=0, source_identity='fixture')
        self.assertEqual(self.store.metrics(PERIOD)['accepted'], 0)
        self.assertEqual(self.store.metrics(PERIOD)['responded'], 1)

    def test_concurrent_delivery_deduplicates(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(lambda _: self.issue(), range(12)))
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual(self.store.metrics(PERIOD)['delivered'], 1)

    def post(self, endpoint, body, key=KEY):
        return self.client.post(endpoint,json=body,headers={'Authorization':'Bearer '+key})

    def test_endpoint_contract_auth_and_no_cache(self):
        body = dict(userId=PERIOD[0],month=6,year=2026)
        response = self.post('/recommendations',body)
        self.assertEqual(set(response.json), {'items'})
        offers = self.post('/recommendations/offers',body).json['offers']
        feedback = dict(body,offerId=offers[0]['offerId'],action='accepted',expectedRevision=0)
        self.assertEqual(self.post('/recommendations/feedback',feedback).status_code,200)
        response = self.post('/recommendations/metrics',body)
        self.assertEqual(response.json['acceptRate'], 1.)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.post('/recommendations/metrics',body,'wrong').status_code,401)
        self.assertEqual(self.post('/recommendations/feedback',dict(feedback,userId='other')).status_code,404)
        self.assertEqual(self.post('/recommendations/feedback',dict(feedback,action='invalid')).status_code,422)

    def test_snapshot_change_preserves_identity_blocks_old_worker(self):
        original = self.issue()
        self.store.feedback(PERIOD, original, accepted=True, source_identity='fixture')
        self.store.activate_source('next-snapshot')
        with self.assertRaises(StaleOffer): self.issue()
        current = self.store.issue(PERIOD,[item()],json_money,source_identity='next-snapshot')
        self.assertEqual(current[0]['offerId'],original)
        self.assertEqual(self.store.metrics(PERIOD)['delivered'],1)

    def test_withdrawn_snapshot_offer_rejected_without_new_delivery(self):
        body = dict(userId=PERIOD[0],month=6,year=2026)
        offer = self.post('/recommendations/offers',body).json['offers'][0]
        class Changed(Source):
            sha256 = 'changed'
            def advice(self,*key): return []
        self.client = create_app(Changed(),KEY,self.store).test_client()
        response = self.post('/recommendations/feedback',dict(body,offerId=offer['offerId'],action='accepted',expectedRevision=0))
        self.assertEqual(response.status_code,409)


if __name__ == '__main__': unittest.main()
