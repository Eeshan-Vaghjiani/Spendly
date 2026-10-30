import unittest
import pandas as pd
from diagnose_large_weeks import aggregate_weeks,join_predictions,average_predictions,summarize


class AttributionChecks(unittest.TestCase):
    def test_expenses_cutoff_and_scenario_accounting(self):
        raw=pd.DataFrame(dict(user_id=['u']*4,transaction_id=['1','2','3','4'],
            transaction_timestamp=['2022-01-03T08:00:00+03:00','2022-01-04T08:00:00+03:00',
                '2022-01-05T08:00:00+03:00','2022-01-10T00:00:00+03:00'],
            transaction_type=['income','expense','expense','expense'],amount=[1000.,100.,50.,900.],
            category=['Income','Rent','Food','Rent'],is_anomaly=[0,0,1,0],anomaly_type=[None,None,'large',None]))
        weekly=aggregate_weeks(raw,'2022-01-10')
        self.assertEqual(len(weekly),1)
        self.assertEqual(weekly.amount.iloc[0],150.)
        self.assertEqual(weekly.ordinary_bill_spend.iloc[0],100.)
        self.assertEqual(weekly.injected_spend.iloc[0],50.)
        self.assertEqual(weekly.scenario_large.iloc[0],50.)
        p=weekly[['user_id','target_week']].assign(actual=150.,prediction=120.)
        joined=join_predictions(p,weekly)
        self.assertEqual(joined.absolute_error.iloc[0],30.)
        with self.assertRaises(ValueError):join_predictions(p.assign(actual=151.),weekly)

    def test_zero_week_is_valid_but_missing_nonzero_target_rejected(self):
        weekly=pd.DataFrame(columns=['user_id','target_week','amount'])
        p=pd.DataFrame(dict(user_id=['u'],target_week=['2022-01-03'],actual=[0.],prediction=[10.]))
        self.assertEqual(join_predictions(p,weekly).absolute_error.iloc[0],10.)
        with self.assertRaises(ValueError):join_predictions(p.assign(actual=10.),weekly)

    def seed(self):
        return pd.DataFrame(dict(user_id=['a','b'],target_week=pd.to_datetime(['2022-01-03','2022-01-10']),
            fold=[0,1],actual=[10.,0.],prediction=[12.,1.],recurring=[9.,1.],recurring_median=[8.,1.],recurring_share=[.5,0.]))

    def test_seed_alignment_and_finite_values(self):
        p=self.seed()
        r=average_predictions([p,p.iloc[::-1],p],'2022-01-17')
        self.assertEqual(len(r),2)
        for bad in (p.iloc[:1],p.assign(prediction=[float('nan'),1.]),p.assign(prediction=[float('inf'),1.])):
            with self.assertRaises(ValueError):average_predictions([p,bad,p],'2022-01-17')

    def test_zero_target_at_cutoff_is_rejected(self):
        p=self.seed()
        with self.assertRaises(ValueError):average_predictions([p,p,p],'2022-01-10')

    def test_summary_includes_baseline(self):
        frame=pd.DataFrame(dict(user_id=['a'],actual=[10.],prediction=[8.],error=[-2.],absolute_error=[2.],
            recurring_median=[7.],injected_spend=[0.],ordinary_bill_spend=[4.],ordinary_nonbill_spend=[6.]))
        self.assertAlmostEqual(summarize(frame,2.)['recurring_median_WAPE'],.3)


if __name__=='__main__':unittest.main()
