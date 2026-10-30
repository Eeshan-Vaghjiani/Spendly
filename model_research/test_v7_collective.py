"""Regression cases motivated by the PR review; no existing datasets accessed."""
import unittest
import numpy as np
import pandas as pd
from v7_collective import collective_features, capped_rule_threshold, collective_diagnostics


def transaction(identifier, at, amount=100., merchant='shop', category='Food', user='fixture'):
    return dict(user_id=user,transaction_id=identifier,transaction_timestamp=pd.Timestamp(at),
        amount=amount,merchant=merchant,category=category,observation_start=pd.Timestamp('2026-01-01'))


class CollectiveChecks(unittest.TestCase):
    def test_future_invariance_and_full_day_leakage(self):
        data=pd.DataFrame([transaction('old','2026-01-01'),transaction('target','2026-02-02 10:00')])
        before=collective_features(data)
        future=[transaction('later'+str(i),pd.Timestamp('2026-02-02 11:00')+pd.Timedelta(minutes=i)) for i in range(30)]
        future+=[transaction('tomorrow','2026-02-03',100000.)]
        after=collective_features(pd.concat([data,pd.DataFrame(future)],ignore_index=True))
        pd.testing.assert_frame_equal(before,after.iloc[:2])
        self.assertEqual(before.iloc[-1].day_count_ratio,1.)

    def test_duplicate_search_context_and_ties(self):
        data=pd.DataFrame([transaction('a','2026-02-02 10:00'),
            transaction('unrelated','2026-02-02 10:30',merchant='bus',category='Transport'),
            transaction('b','2026-02-02 11:00'),transaction('tie','2026-02-02 11:00'),
            transaction('expired','2026-02-02 15:00')])
        result=collective_features(data)
        self.assertEqual(result.duplicate_count.tolist(),[0,0,1,1,0])
        shuffled=data.sample(frac=1,random_state=3)
        actual=collective_features(shuffled).sort_index()
        pd.testing.assert_frame_equal(result,actual)

    def test_cold_users_and_empty_merchants(self):
        data=pd.DataFrame([transaction('a','2026-01-02 10:00'),transaction('b','2026-01-02 11:00')])
        self.assertFalse(collective_features(data).eligible.any())
        self.assertTrue(collective_features(data).collective_score.eq(0).all())
        data=pd.DataFrame([transaction('a','2026-02-02 10:00',merchant=''),transaction('b','2026-02-02 11:00',merchant='')])
        self.assertTrue(collective_features(data).duplicate_count.eq(0).all())

    def test_weekend_baseline_excludes_later_weekends(self):
        data=pd.DataFrame([transaction('a','2026-02-07',100.)])
        before=collective_features(data)
        after=collective_features(pd.concat([data,pd.DataFrame([transaction('b','2026-02-14',1e7)])],ignore_index=True))
        self.assertEqual(before.iloc[0].weekend_ratio,after.iloc[0].weekend_ratio)
        self.assertGreater(before.iloc[0].weekend_ratio,0.)

    def test_tied_scores_respect_budget_and_ignore_positive_scores(self):
        scores=np.array([0.]*90+[2.]*10+[100.])
        labels=np.array([0]*100+[1])
        result=capped_rule_threshold(scores,labels,.05)
        self.assertLessEqual(result['calibration_FPR'],.05)
        self.assertGreater(result['threshold'],2.)
        scores[-1]=0.
        self.assertEqual(result,capped_rule_threshold(scores,labels,.05))
        self.assertTrue(np.isinf(capped_rule_threshold([1.],[1],.01)['threshold']))
        with self.assertRaises(ValueError): capped_rule_threshold([1.],[np.nan],.01)

    def test_union_bound(self):
        labels=np.zeros(1000)
        a=np.arange(1000,dtype=float); b=a[::-1]
        ta=capped_rule_threshold(a,labels,.005)['threshold']
        tb=capped_rule_threshold(b,labels,.005)['threshold']
        self.assertLessEqual(np.mean((a>=ta)|(b>=tb)),.01)

    def test_event_and_daily_denominators(self):
        frame=pd.DataFrame(dict(user_id=['u']*4,label=[1,1,0,1],family=['burst','burst','normal','duplicate'],
            event_id=['e','e',None,None],time=pd.to_datetime(['2026-01-01']*3+['2026-01-02'])))
        types,burden=collective_diagnostics(frame,[False,True,True,False],'rules')
        burst=next(t for t in types if t['family']=='burst')
        self.assertEqual(burst['transaction_recall'],.5)
        self.assertEqual(burst['event_recall'],1.)
        self.assertEqual(burden['alerts'],2)
        self.assertEqual(burden['alerted_user_days'],1)
        self.assertEqual(burden['active_user_days'],2)

    def test_invalid_inputs_fail(self):
        data=pd.DataFrame([transaction('a','2026-02-02')]*2)
        with self.assertRaises(ValueError): collective_features(data)
        data=data.iloc[:1].copy(); data['amount']=np.inf
        with self.assertRaises(ValueError): collective_features(data)


if __name__=='__main__':
    unittest.main()
