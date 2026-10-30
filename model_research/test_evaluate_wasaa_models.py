import unittest
import numpy as np
import pandas as pd
from evaluate_wasaa_models import metric, adapt, category_panel, MAP, PROTOCOL


class EvaluationTests(unittest.TestCase):
    def test_known_metrics(self):
        result=metric([100,200],[90,220])
        self.assertAlmostEqual(result['WAPE'],.1)
        self.assertEqual(result['MAE_KES'],15)
        self.assertEqual(result['bias_KES'],5)
        with self.assertRaises(ValueError):metric([1],[np.inf])

    def test_mapping_and_coverage_are_explicit(self):
        self.assertNotIn('Savings',MAP)
        self.assertNotIn('Household Help',MAP)
        self.assertNotIn('Airtime and Data',MAP)
        self.assertEqual(MAP['Groceries'],'Food')
        self.assertIn('unavailable',PROTOCOL['anomaly_labels'])

    def test_timezone_panel_and_no_fabricated_merchants(self):
        raw=pd.DataFrame(dict(spending_record_id=['a'],user_profile_id=['u'],budget_category_id=['b'],
                              amount_kes=[100.],category=['Food'],transaction_date=['2026-07-05T22:00:00Z']))
        converted=adapt(raw)
        self.assertEqual(converted.merchant.iloc[0],'')
        self.assertEqual(converted.transaction_timestamp.iloc[0],pd.Timestamp('2026-07-06T01:00:00'))
        panel=category_panel(converted,'u',pd.Timestamp('2026-06-29'),pd.Timestamp('2026-07-20'),['Food','Rent'])
        self.assertEqual(panel.total_spend.tolist(),[0,100,0])
        self.assertEqual(panel.spend_1.sum(),0)


if __name__=='__main__':unittest.main()
