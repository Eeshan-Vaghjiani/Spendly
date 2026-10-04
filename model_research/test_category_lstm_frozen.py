import unittest
from pathlib import Path
import tempfile

import pandas as pd

from category_lstm_frozen import history_panel, FrozenCategoryLSTM, FEATURES
from category_lstm_features import add_model_features
from check_category_lstm import fixture


class FrozenInputTests(unittest.TestCase):
    def test_quiet_weeks_and_income_exclusion(self):
        records, coverage = fixture(26)
        panel = history_panel(records, **coverage)
        self.assertEqual(len(panel), 26)
        self.assertEqual(panel.total_spend.iloc[0], 0)
        self.assertEqual(panel.total_spend.iloc[-1], 0)
        income = records.iloc[[0]].assign(transaction_id='income', transaction_type='income', category='Income', amount=1e6)
        pd.testing.assert_frame_equal(panel, history_panel(pd.concat([records, income]), **coverage))
        income_panel = history_panel(income, **coverage)
        self.assertEqual(income_panel.total_spend.sum(), 0)

    def test_invalid_history_and_incomplete_period_rejected(self):
        records, coverage = fixture(26)
        for change in ({'history_complete':False}, {'owner':'another'},
                       {'observed_from':'2024-01-01'}, {'as_of':'2024-02-01T00:00:00+03:00'},
                       {'target_start':'2024-07-03T00:00:00+03:00'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                history_panel(records, **dict(coverage, **change))
        for column, value in [('amount',float('inf')), ('amount',-1), ('category','Unknown'),
                              ('transaction_type','unknown'), ('transaction_timestamp',coverage['target_start'])]:
            with self.subTest(column=column), self.assertRaises(ValueError):
                history_panel(records.assign(**{column:value}), **coverage)
        with self.assertRaises(ValueError):
            history_panel(pd.concat([records,records.iloc[[0]]]), **coverage)

    def test_timezone_and_order_invariance(self):
        records, coverage = fixture(52)
        expected = history_panel(records, **coverage)
        records.transaction_timestamp = pd.to_datetime(records.transaction_timestamp, utc=True)
        pd.testing.assert_frame_equal(expected, history_panel(records.sample(frac=1, random_state=1), **coverage))

    def test_feature_future_invariance_and_order(self):
        records, coverage = fixture(80)
        panel = history_panel(records, **coverage)
        original, columns = add_model_features(panel)
        self.assertEqual(columns, FEATURES)
        shorter, _ = add_model_features(panel.iloc[:52])
        pd.testing.assert_frame_equal(shorter[FEATURES], original[FEATURES].iloc[:52])

    def test_trust_and_integrity_before_deserialization(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PermissionError):
                FrozenCategoryLSTM(tmp)
            (Path(tmp)/'model.keras').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                FrozenCategoryLSTM(tmp, trusted=True)

    def test_empty_confirmed_history_retains_zero_weeks(self):
        records, coverage = fixture(26)
        panel = history_panel(records.iloc[:0], **coverage)
        self.assertEqual(len(panel), 26)
        self.assertEqual(panel.total_spend.sum(), 0)

    def test_notebook_rebuild_and_cpu_default(self):
        import json
        import build_lstm_readiness_notebook as builder
        nb = builder.build()
        self.assertEqual(nb, json.loads(builder.OUTPUT.read_text()))
        code = '\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
        self.assertIn("os.environ['CUDA_VISIBLE_DEVICES'] = '-1'", code)
        self.assertIn('RUN_CHECK = False', code)
        for cell in nb['cells']:
            if cell['cell_type']=='code':
                compile(''.join(cell['source']), cell['id'], 'exec')
                self.assertFalse(cell['outputs'])


if __name__ == '__main__':
    unittest.main()
