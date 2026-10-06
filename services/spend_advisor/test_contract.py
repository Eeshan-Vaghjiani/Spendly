import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from services.spend_advisor.app import Snapshot, create_app, money

KEY = 'synthetic-test-service-key-000000000000'


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rows = []
        for i, cat in enumerate(('Entertainment','Groceries','Transport','Airtime and Data','Rent','Savings')):
            self.rows.append(dict(budget_category_id=f'target-{i}',user_profile_id='household-a',
                month=6,year=2026,category=cat,allocated_kes='100.01',actual_kes='150.03',approval_status='APPROVED'))
        self.rows.append(dict(self.rows[0], budget_category_id='target-b', user_profile_id='household-b', actual_kes='90.00'))
        self.write_snapshot()

    def write_snapshot(self):
        p = self.root/'budget_categories.csv'
        with p.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.rows[0].keys()); writer.writeheader(); writer.writerows(self.rows)
        manifest = {'synthetic':True,'datasets':{'budget_categories':{'rows':len(self.rows), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}}
        (self.root/'snapshot.json').write_text(json.dumps(manifest))
        self.source = Snapshot(self.root)
        self.client = create_app(self.source, KEY).test_client()

    def post(self, body, key=KEY):
        return self.client.post('/recommendations', json=body, headers={'Authorization':'Bearer '+key})

    def test_contract_decimal_cap_and_deterministic_targets(self):
        response = self.post({'userId':'household-a','month':6,'year':2026})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json), {'items'})
        self.assertEqual(len(response.json['items']), 3)
        for item in response.json['items']:
            self.assertEqual(set(item), {'type','reason','savingKes','targetId'})
            self.assertEqual(item['savingKes'], 50.02)
            self.assertIn('retrospective', item['reason'])
        self.assertEqual(response.data, self.post({'userId':'household-a','month':6,'year':2026}).data)
        self.assertNotIn('target-4', response.get_data(as_text=True))

    def test_auth_and_health(self):
        self.assertEqual(self.client.get('/health').status_code, 200)
        self.assertEqual(self.post({}, 'wrong').status_code, 401)
        with self.assertRaises(ValueError): create_app(self.source, 'short')

    def test_household_scope_missing_and_empty(self):
        self.assertEqual(self.post({'userId':'household-b','month':6,'year':2026}).json, {'items':[]})
        self.assertEqual(self.post({'userId':'missing','month':6,'year':2026}).status_code,404)

    def test_bad_request(self):
        for body in ({}, [], {'userId':'household-a','month':True,'year':2026},
                     {'userId':'household-a','month':13,'year':2026},
                     {'userId':'household-a','month':6,'year':2026,'extra':1}):
            with self.subTest(body=body): self.assertEqual(self.post(body).status_code,422)

    def test_pending_budget_not_recommended(self):
        for row in self.rows: row['approval_status']='PENDING'
        self.write_snapshot()
        self.assertEqual(self.post({'userId':'household-a','month':6,'year':2026}).json, {'items':[]})

    def test_corruption_and_duplicate_rejected(self):
        (self.root/'budget_categories.csv').write_text('corrupt')
        with self.assertRaises(ValueError): Snapshot(self.root)
        self.rows.append(dict(self.rows[0]))
        with self.assertRaises(ValueError): self.write_snapshot()

    def test_invalid_money(self):
        for value in ('NaN', '-1', '0.001', '1e28', True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError): money(value)
        self.assertEqual(str(money('999999999999.99')), '999999999999.99')

    def test_ranking_and_two_actionable_owners(self):
        self.rows[2]['actual_kes'] = '200.05'
        self.rows[-1]['actual_kes'] = '999.99'
        self.write_snapshot()
        a = self.post({'userId':'household-a','month':6,'year':2026}).json['items']
        b = self.post({'userId':'household-b','month':6,'year':2026}).json['items']
        self.assertEqual(a[0]['targetId'], 'target-2')
        self.assertEqual([v['targetId'] for v in a[1:]], ['target-0','target-1'])
        self.assertEqual([v['targetId'] for v in b], ['target-b'])

    def test_exact_large_money_json(self):
        from decimal import Decimal
        self.rows[0]['actual_kes'] = '999999999999.99'
        self.write_snapshot()
        response = self.post({'userId':'household-a','month':6,'year':2026})
        parsed = json.loads(response.data, parse_float=Decimal)
        self.assertEqual(parsed['items'][0]['savingKes'], Decimal('999999999899.98'))


if __name__ == '__main__': unittest.main()
