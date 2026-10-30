import unittest

import pandas as pd

from analyze_v7_checkpoint import validate_prediction_rows, metrics


class AuditChecks(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame(dict(user_id=['a','a','b'],target_week=['2024-01-01','2024-01-08','2024-01-01'],
            fold=[0,0,1],actual=[10.,20.,30.],prediction=[9.,18.,27.],residual=[-1.,-2.,-3.],absolute_error=[1.,2.,3.]))

    def test_known_metrics(self):
        frame=self.fixture(); validate_prediction_rows(frame)
        measured=metrics(frame)
        self.assertAlmostEqual(measured['WAPE'],.1)
        self.assertAlmostEqual(measured['MAE_KES'],2.)
        self.assertAlmostEqual(measured['bias_KES'],-2.)

    def test_overlap_across_folds_rejected(self):
        frame=self.fixture()
        frame=pd.concat([frame,frame.iloc[:1].assign(fold=2)],ignore_index=True)
        with self.assertRaises(ValueError): validate_prediction_rows(frame)

    def test_disjoint_weeks_same_user_other_fold_rejected(self):
        frame=self.fixture(); frame.loc[1,'fold']=2
        with self.assertRaises(ValueError): validate_prediction_rows(frame)

    def test_wrong_residual_rejected(self):
        frame=self.fixture(); frame['residual']*=-1
        with self.assertRaises(AssertionError): validate_prediction_rows(frame)


if __name__=='__main__': unittest.main()
