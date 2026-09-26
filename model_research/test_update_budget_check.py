import unittest
import hashlib
from types import SimpleNamespace
import numpy as np
import pandas as pd
from run_update_budget_check import CONTROLS,expected_updates,reconstruct


class BudgetChecks(unittest.TestCase):
    def test_declared_update_counts(self):
        self.assertEqual([expected_updates(256,b,e) for _,b,e in CONTROLS],[120,960,960])

    def test_partial_batch_counts_as_update(self):
        self.assertEqual(expected_updates(257,256,120),240)

    def test_reconstruction_order_cutoff_and_boundary(self):
        raw=pd.DataFrame(dict(user_id=['b','excluded','a']))
        end=pd.Timestamp('2022-01-03')
        fit=[hashlib.sha256(('V7-export:'+u).encode()).hexdigest()[:20] for u in ('a','b')]
        split=dict(folds=[dict(fit_users=fit,inner=str(end))],train_target_end=str(end))
        def features(g,cfg):
            u=g.user_id.iloc[0]; y=np.arange(150)+(0 if u=='a' else 1000)
            f=pd.DataFrame(dict(user_id=u,y=y,end=[end]*149+[end+pd.Timedelta(weeks=1)]))
            return f,y[:,None,None],(y*2)[:,None]
        def subset(bundle,mask):
            positions=np.flatnonzero(mask)
            return bundle[0].iloc[positions].reset_index(drop=True),bundle[1][positions],bundle[2][positions]
        worker=SimpleNamespace(ForecastConfig=lambda **kw:kw,clean_data=lambda x:x,make_features=features)
        ns=dict(restrict_history=lambda d,e:d,subset=subset)
        bundle,_,_,_=reconstruct(raw,worker,ns,split)
        expected=np.r_[np.arange(149),1000+np.arange(107)]
        np.testing.assert_array_equal(bundle[0].y,expected)
        np.testing.assert_array_equal(bundle[1][:,0,0],expected)
        np.testing.assert_array_equal(bundle[2][:,0],expected*2)
        self.assertEqual(bundle[0].user_id.tolist(),['a']*149+['b']*107)
        with self.assertRaises(ValueError):reconstruct(raw.loc[raw.user_id.ne('a')],worker,ns,split)
        short=dict(folds=[dict(fit_users=fit[:1],inner=str(end))],train_target_end=str(end))
        with self.assertRaises(ValueError):reconstruct(raw,worker,ns,short)


if __name__=='__main__':unittest.main()
