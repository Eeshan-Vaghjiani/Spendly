"""Execute the alert-only notebook twice on small fixtures, without TensorFlow."""
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import nbformat
from test_v7_evidence import modules,fixture,HERE


class AlertReviewChecks(unittest.TestCase):
    def test_full_notebook_and_completed_stage_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);inputs=root/'inputs';inputs.mkdir()
            _,worker,_,_=modules(root)
            manifest=dict(version='spendly-synthetic-r3-v1',status='complete',currency='KES',
                timezone='Africa/Nairobi',weeks_per_user=40,cohorts={})
            for name in ('train','validation','calibration'):
                frame=fixture(worker,users=2,weeks=40,prefix='alerts_'+name)
                for col in ('transaction_timestamp','observation_start','observation_end'):
                    frame[col]=frame[col].map(lambda t:t.isoformat()+'+03:00')
                path=inputs/(name+'.csv');frame.to_csv(path,index=False)
                manifest['cohorts'][name]=dict(rows=len(frame),users=2,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            (inputs/'manifest.json').write_text(json.dumps(manifest))
            nb=nbformat.read(HERE/'Spending_Alerts_Review_Kaggle.ipynb',as_version=4)
            original=None
            try:
                for resume in (False,True):
                    ns={'__name__':'__main__'}
                    # Any import of TensorFlow fails, even if installed locally.
                    with patch.dict(sys.modules,{'tensorflow':None}):
                        for c in nb.cells:
                            if c.cell_type!='code':continue
                            code=c.source.replace("INPUT_ROOT=Path('/kaggle/input')",f'INPUT_ROOT=Path({str(inputs)!r})')
                            code=code.replace("WORK_ROOT=Path('/kaggle/working')",f'WORK_ROOT=Path({str(root)!r})')
                            code=code.replace('SMOKE=False','SMOKE=True')
                            if resume:code=code.replace('RESUME_DIR=None',f'RESUME_DIR={str(original)!r}')
                            exec(compile(code,c.id,'exec'),ns)
                            if resume and 'def anomaly_pipeline(' in code:
                                ns['anomaly_pipeline']=lambda *a:(_ for _ in ()).throw(AssertionError('Repeated completed anomaly fit'))
                    original=ns['RESULTS']
                    self.assertTrue(ns['ARCHIVE'].exists())
                    artifact=json.loads((original/'artifact_manifest.json').read_text())
                    self.assertFalse(artifact['evidence_eligible'])
                    self.assertFalse(artifact['forecast_training'])
                    self.assertEqual({a['cohort'] for a in ns['ACCESSES']},{'train','validation','calibration'})
                    for forbidden in ('test','test_shifted'):
                        with self.assertRaises(PermissionError):ns['assert_permitted'](forbidden)
                manifest['weeks_per_user']=44
                (inputs/'manifest.json').write_text(json.dumps(manifest))
                ns['ACCESSES'].clear()
                data_cell=next(c.source for c in nb.cells if c.cell_type=='code' and 'DATASET=load_manifest' in c.source)
                with self.assertRaisesRegex(ValueError,'identity mismatch'):
                    exec(compile(data_cell,'changed manifest','exec'),ns)
                self.assertEqual(ns['ACCESSES'],[])
            finally:
                from joblib.externals.loky import get_reusable_executor
                get_reusable_executor().shutdown(wait=True,kill_workers=True)


if __name__=='__main__':unittest.main()
