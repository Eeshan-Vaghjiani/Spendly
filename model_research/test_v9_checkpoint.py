import ast
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import nbformat
import numpy as np
import pandas as pd
from test_v7_evidence import fixture

HERE=Path(__file__).resolve().parent


def modules(folder):
    nb=nbformat.read(HERE/'Spending_Model_V9_Checkpoint_Kaggle.ipynb',as_version=4)
    cell=next(c.source for c in nb.cells if c.cell_type=='code' and 'WORKER_SOURCE =' in c.source)
    worker_source=next(ast.literal_eval(n.value) for n in ast.parse(cell).body
        if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','')=='WORKER_SOURCE')
    path=folder/'v9_test_worker.py';path.write_text(worker_source,encoding='utf-8')
    spec=importlib.util.spec_from_file_location('v9_test_worker',path)
    worker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=worker;spec.loader.exec_module(worker)
    ns={}
    for c in nb.cells:
        if c.cell_type=='code' and ('def train_model(' in c.source or 'def v9_search(' in c.source):exec(c.source,ns)
    return nb,worker,ns


class CheckpointChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.nb,cls.worker,cls.ns=modules(cls.root)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_only_checkpoint_policy_differs(self):
        configs=self.ns['v9_candidates'](self.worker)
        self.assertEqual(len(configs),2)
        a,b=[self.ns['asdict'](c) for c in configs.values()]
        self.assertEqual({k for k in a if a[k]!=b[k]},{'monitor','patience'})
        self.assertEqual(b['patience'],121);self.assertEqual(b['max_epochs'],120)
        self.assertEqual(b['min_delta'],0.)

    def test_full_budget_restores_earlier_best(self):
        cfg=self.ns['replace'](self.ns['v9_candidates'](self.worker)['predictive_full_budget'],l2=0.,max_epochs=4)
        data=fixture(self.worker,users=1,weeks=40)
        bundle=self.worker.make_features(data,cfg)
        bundle[0]['y']=bundle[0].center
        train=self.ns['subset'](bundle,np.arange(len(bundle[0]))<16)
        stop=self.ns['subset'](bundle,np.arange(len(bundle[0]))>=16)
        fit=self.ns['train_model'](train,stop,cfg,self.root/'fit','/CPU:0',list(data.user_id.unique()),pd.Timestamp('2030-01-01'))
        self.assertEqual(len(fit['history']['loss']),4)
        self.assertEqual(fit['best_epoch'],1)
        self.assertEqual(len(fit['rates']),1)
        p,_=self.ns['predict'](fit,stop,'/CPU:0')
        np.testing.assert_allclose(p,stop[0].center,atol=.01)

    def test_notebook_and_source_contract(self):
        nbformat.validate(self.nb)
        for c in self.nb.cells:
            if c.cell_type=='code':compile(c.source,c.id,'exec');self.assertFalse(c.outputs)
        code='\n'.join(c.source for c in self.nb.cells if c.cell_type=='code')
        self.assertIn((HERE/'v9_checkpoint.py').read_text(encoding='utf-8'),code)
        self.assertNotIn("CALIBRATION=load_cohort",code)

    def test_best_weights_replace_changed_last_weights(self):
        import tensorflow as tf
        cfg=self.ns['replace'](self.ns['v9_candidates'](self.worker)['predictive_full_budget'],l2=0.,max_epochs=3)
        data=fixture(self.worker,users=1,weeks=40)
        bundle=self.worker.make_features(data,cfg)
        bundle[0]['y']=bundle[0].center
        train=self.ns['subset'](bundle,np.arange(len(bundle[0]))<16)
        stop=self.ns['subset'](bundle,np.arange(len(bundle[0]))>=16)
        last={}
        class ControlledDeterioration(tf.keras.callbacks.Callback):
            def on_epoch_end(self,epoch,logs=None):
                logs[cfg.monitor]=float(epoch)
                if epoch>0:
                    weights=self.model.get_weights();weights[-1]=np.ones_like(weights[-1])*5
                    self.model.set_weights(weights)
                    last['weights']=self.model.get_weights()
        original=tf.keras.Model.fit
        def fit_with_probe(model,*args,**kwargs):
            kwargs['callbacks']=[ControlledDeterioration()]+kwargs['callbacks']
            return original(model,*args,**kwargs)
        with patch.object(tf.keras.Model,'fit',fit_with_probe):
            result=self.ns['train_model'](train,stop,cfg,self.root/'changed_weights','/CPU:0',
                list(data.user_id.unique()),pd.Timestamp('2030-01-01'))
        self.assertEqual(result['best_epoch'],1)
        p,_=self.ns['predict'](result,stop,'/CPU:0')
        np.testing.assert_allclose(p,stop[0].center,atol=.01)
        result['model'].set_weights(last['weights'])
        later,_=self.ns['predict'](result,stop,'/CPU:0')
        self.assertGreater(float(np.mean(np.abs(later-p))),1.)


if __name__=='__main__':unittest.main()
