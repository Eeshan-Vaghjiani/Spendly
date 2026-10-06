import unittest
import numpy as np
import pandas as pd
from audit_wasaa_results import metrics, validate_forecasts, compare_record, distribution


def fixture():
    return pd.DataFrame([dict(user_id='a',target_week='2026-07-06',scenario=scenario,model=model,actual=100.,prediction=110.)
        for scenario,model in [('consumption','retained_lstm'),('all_outflows','retained_lstm'),
                               ('mapped_subset','retained_lstm'),('mapped_subset','category_lstm')]])


class AuditTests(unittest.TestCase):
    def test_known_metric_and_zero_target(self):
        result=metrics([100,200],[110,180])
        self.assertEqual(result['MAE_KES'],15.)
        self.assertEqual(result['WAPE'],.1)
        self.assertIsNone(metrics([0,0],[1,0])['WAPE'])
        with self.assertRaises(ValueError): metrics([100],[np.inf])

    def test_paired_identity_validation(self):
        data=fixture(); validate_forecasts(data)
        with self.assertRaises(ValueError): validate_forecasts(pd.concat([data,data.iloc[[0]]]))
        changed=data.copy(); changed.loc[3,'actual']=200
        with self.assertRaises(AssertionError): validate_forecasts(changed)
        changed=data.copy(); changed.loc[3,'target_week']='2026-07-13'
        with self.assertRaises(ValueError): validate_forecasts(changed)

    def test_extreme_predictions_are_not_clipped(self):
        data=pd.DataFrame({'actual':[100.,100.],'prediction':[100.,1e20]})
        result=distribution(data)
        self.assertEqual(result['maximum_prediction_KES'],1e20)
        self.assertEqual(result['predictions_above_1billion_KES'],1)
        self.assertGreater(metrics(data.actual,data.prediction)['WAPE'],1e10)

    def test_metric_mismatch_rejected(self):
        correct=metrics([1,2],[1,2]); bad=dict(correct,WAPE=.5)
        with self.assertRaises(AssertionError): compare_record(correct,bad)

    def test_results_notebook_rebuild(self):
        import json
        import build_wasaa_results_notebook as builder
        notebook=builder.build()
        self.assertEqual(notebook,json.loads(builder.OUTPUT.read_text()))
        for cell in notebook['cells']:
            if cell['cell_type']=='code':
                compile(''.join(cell['source']),cell['id'],'exec')
                self.assertFalse(cell['outputs'])


if __name__=='__main__': unittest.main()
