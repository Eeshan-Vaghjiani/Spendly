"""V7 regression checks use newly constructed synthetic fixtures only."""
import ast
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import nbformat
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent


def modules(folder):
    nb=nbformat.read(HERE/'Spending_Model_Upload_V7_R3_Kaggle_Evidence.ipynb',as_version=4)
    cell=next(c.source for c in nb.cells if c.cell_type=='code' and 'WORKER_SOURCE =' in c.source)
    tree=ast.parse(cell)
    constants={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body
               if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)
               and n.targets[0].id in ('WORKER_SOURCE','IF_SOURCE','CODE_HASH')}
    loaded=[]
    for key,name in [('WORKER_SOURCE','v7_fixture_worker'),('IF_SOURCE','v7_fixture_if')]:
        path=folder/(name+'.py'); path.write_text(constants[key],encoding='utf-8')
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module)
        loaded.append(module)
    return nb,*loaded,constants['CODE_HASH']


def fixture(worker, users=9, weeks=80, prefix='software'):
    rng=np.random.default_rng(9851)
    rows=[]; start=pd.Timestamp('2022-01-03')
    for u in range(users):
        for w in range(weeks):
            for day in (0,2,5):
                if w%11==0 and day!=0:
                    continue
                stamp=start+pd.Timedelta(weeks=w,days=day,hours=10)
                rows.append(dict(user_id=f'{prefix}_{u}',transaction_id=f'{prefix}_{u}_{w}_{day}',
                    transaction_timestamp=stamp.isoformat()+'+03:00',amount=float((u+1)*70+rng.uniform(1,100))*(6 if w%17==0 else 1),
                    category='food' if day else 'bill',merchant='shop',transaction_type='expense',
                    is_anomaly=int(w%17==0),event_id=None,anomaly_type='shock' if w%17==0 else 'normal',
                    observation_start=start.isoformat()+'+03:00',
                    observation_end=(start+pd.Timedelta(weeks=weeks)).isoformat()+'+03:00'))
    return worker.clean_data(pd.DataFrame(rows))


class V7Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(); cls.root=Path(cls.temp.name)
        cls.nb,cls.worker,cls.ifref,cls.code_hash=modules(cls.root)
        sys.path.insert(0,str(cls.root))
        cls.data=fixture(cls.worker)
        cls.ns={}
        exec((HERE/'v7_recovery.py').read_text(),cls.ns)
        exec((HERE/'v7_runtime.py').read_text(),cls.ns)
        exec((HERE/'v7_experiments.py').read_text(),cls.ns)

    @classmethod
    def tearDownClass(cls):
        from joblib.externals.loky import get_reusable_executor
        get_reusable_executor().shutdown(wait=True,kill_workers=True)
        sys.path.remove(str(cls.root))
        cls.temp.cleanup()

    def test_notebook_valid_and_no_outputs(self):
        nbformat.validate(self.nb)
        for c in self.nb.cells:
            if c.cell_type=='code':
                compile(c.source,c.id,'exec')
                self.assertFalse(c.outputs)
        all_code='\n'.join(c.source for c in self.nb.cells if c.cell_type=='code')
        self.assertNotIn('FINAL_CONFIRMATION',all_code)
        self.assertNotIn('test_shifted.csv',all_code)
        self.assertNotIn('In Colab select',all_code)
        self.assertNotIn("use_cudnn",self.ns['make_model'].__code__.co_names)
        self.assertIn((HERE/'v7_runtime.py').read_text(encoding='utf-8'),all_code)
        self.assertIn((HERE/'v7_experiments.py').read_text(encoding='utf-8'),all_code)

    def test_original_parity_and_future_invariance(self):
        result=self.worker.check_causal_parity(self.data)
        self.assertEqual(result['status'],'passed')
        one=self.data.loc[self.data.user_id.eq('software_0')]
        f,x,_=self.worker.forecast_features_v5(one)
        result,s,c=self.worker.make_features(one,self.worker.ForecastConfig())
        np.testing.assert_allclose(result.y,f.y)
        np.testing.assert_allclose(c,x.iloc[:,16:],rtol=1e-6,atol=1e-6)
        cfg=self.worker.ForecastConfig(lookback=26,target_transform='median_residual',scale_method='mad',
            sequence_features=('total','nonrecurring','count','active_days','ticket_mean','largest_share','weekend_share'),category_vocabulary=('food','OTHER'),
            context_features=('rolling_mad','recent_ratio','trend13','week_sin','week_cos','share_food','share_OTHER'))
        frame,seq,ctx=self.worker.make_features(one,cfg)
        cutoff=frame.time.iloc[5]; changed=one.copy(); future=changed.transaction_timestamp.ge(cutoff)
        changed.loc[future,'amount']*=91; changed.loc[future,'category']='future'
        ef,es,ec=self.worker.make_features(changed,cfg)
        before=frame.time.le(cutoff)
        np.testing.assert_array_equal(seq[before],es[before]); np.testing.assert_array_equal(ctx[before],ec[before])
        np.testing.assert_array_equal(frame.center,frame.robust_recurring)

    def test_huber_training_and_reload(self):
        import tensorflow as tf
        cfg=self.worker.ForecastConfig(loss='huber',max_epochs=2)
        bundle=self.worker.make_features(self.data.loc[self.data.user_id.eq('software_0')],cfg)
        fit=self.ns['train_model'](bundle,None,cfg,self.root/'huber','/CPU:0',
            ['software_0'],pd.Timestamp('2030-01-01'))
        self.assertTrue(np.isfinite(fit['history']['loss']).all())
        self.assertIn('weighted_mae',fit['history'])
        path=self.root/'huber_reload.keras'; fit['model'].save(path)
        loaded=tf.keras.models.load_model(path,compile=False)
        expected,_=self.ns['predict'](fit,bundle,'/CPU:0')
        actual,_=self.ns['predict'](dict(fit,model=loaded),bundle,'/CPU:0')
        np.testing.assert_allclose(actual,expected,atol=.01,rtol=0)
        with patch.dict(self.ns,make_model=lambda *args: (_ for _ in ()).throw(AssertionError('must not train'))):
            resumed=self.ns['train_model'](bundle,None,cfg,self.root/'huber','/CPU:0',
                ['software_0'],pd.Timestamp('2030-01-01'))
        again,_=self.ns['predict'](resumed,bundle,'/CPU:0')
        np.testing.assert_allclose(again,expected,atol=.01,rtol=0)
        with self.assertRaises(ValueError):
            self.ns['train_model'](bundle,None,self.ns['replace'](cfg,l2=.1),self.root/'huber','/CPU:0',
                ['software_0'],pd.Timestamp('2030-01-01'))
        (self.root/'huber'/'complete.json').unlink()
        with patch.dict(self.ns,make_model=lambda *args: (_ for _ in ()).throw(AssertionError('must not train'))):
            with self.assertRaises(PermissionError):
                self.ns['train_model'](bundle,None,cfg,self.root/'huber','/CPU:0',
                    ['software_0'],pd.Timestamp('2030-01-01'),require_completed=True)

    def test_cache_shape_identity_and_tamper(self):
        cache=self.root/'cache_test'
        one=self.data.loc[self.data.user_id.eq('software_0')]
        for length in (8,13):
            f,s,c=self.worker.cached_user(one,self.worker.ForecastConfig(lookback=length),cache,'source')
            self.assertEqual(s.shape[1],length)
        markers=list(cache.glob('*/complete.json'))
        self.assertEqual(len(markers),2)
        marker=markers[0]; meta=json.loads(marker.read_text()); meta['metadata']['config']['lookback']=99
        marker.write_text(json.dumps(meta))
        caught=False
        for length in (8,13):
            try: self.worker.cached_user(one,self.worker.ForecastConfig(lookback=length),cache,'source')
            except ValueError: caught=True
        self.assertTrue(caught)

    def test_holdouts_denied_before_path_access(self):
        for name in ('test','test_shifted','hidden','final'):
            with self.assertRaises(PermissionError):
                self.ns['load_cohort'](name,Path('nonexistent'),{},self.worker,self.root)
        with self.assertRaises(PermissionError):
            self.ns['load_cohort']('validation',Path('nonexistent'),{},self.worker,self.root)

    def test_user_folds_and_train_only_preprocessing(self):
        folds=self.ns['fixed_folds'](self.data)
        held=[]
        for fold in folds:
            held+=fold['eval_users']
            self.assertFalse(set(fold['fit_users'])&set(fold['eval_users']))
            self.assertFalse(set(fold['stop_users'])&set(fold['eval_users']))
            self.assertLess(pd.Timestamp(fold['inner']),pd.Timestamp(fold['outer']))
        self.assertEqual(len(held),len(set(held)))
        cfg=self.worker.ForecastConfig()
        b=self.worker.make_features(self.data.loc[self.data.user_id.eq('software_0')],cfg)
        with self.assertRaises(AssertionError):
            self.ns['fit_preprocessing'](b,['legacy_user'],pd.Timestamp('2030-01-01'))
        with self.assertRaises(AssertionError):
            self.ns['fit_preprocessing'](b,['software_0'],pd.Timestamp('2022-01-01'))

    def test_cluster_bootstrap_pairing(self):
        frame=pd.DataFrame(dict(user_id=np.repeat(['a','b','c'],4),actual=np.tile([10.,20.,40.,100.],3)))
        frame['prediction']=frame.actual*.95; frame['reproduced_v6']=frame.actual*.8
        frame['recurring_median']=frame.actual*.7
        result=self.ns['bootstrap'](frame)
        self.assertLess(result['candidate_minus_v6_pp_95'][1],0)
        self.assertAlmostEqual(result['candidate_WAPE_95'][0],.05)
        with self.assertRaises(AssertionError): self.ns['bootstrap'](frame,10)

    def test_worst_block_guard_and_smoke_non_evidence(self):
        reference=pd.DataFrame(dict(worst_block_WAPE=[.4]*9,bias_percent=[-10.]*9,within_20_percent=[.5]*9))
        winner=reference.copy(); winner['worst_block_WAPE']=.42
        self.assertFalse(self.ns['practical_guardrails'](winner,reference)['worst_block'])
        self.assertFalse(self.ns['evidence_decision'](True,True))
        self.assertTrue(self.ns['evidence_decision'](True,False))

    def test_predictive_plateau_checkpoint_and_exact_replay(self):
        cfg=self.worker.ForecastConfig(l2=0.,schedule='plateau',patience=6,max_epochs=9)
        bundle=self.worker.make_features(self.data.loc[self.data.user_id.eq('software_0')],cfg)
        # Perfect zero residual creates a genuine constant predictive metric. The
        # initial checkpoint is best; patience and plateau must operate independently.
        bundle[0]['y']=bundle[0].center
        train=self.ns['subset'](bundle,np.arange(len(bundle[0]))<20)
        stop=self.ns['subset'](bundle,np.arange(len(bundle[0]))>=20)
        fit=self.ns['train_model'](train,stop,cfg,self.root/'plateau_real','/CPU:0',
            ['software_0'],pd.Timestamp('2030-01-01'))
        self.assertEqual(fit['best_epoch'],1)
        self.assertEqual(len(fit['history']['loss']),7)
        self.assertLess(fit['history']['learning_rate_used'][-1],cfg.learning_rate)
        rates=[.0003,.00015,.000075]
        refit=self.ns['train_model'](train,None,cfg,self.root/'plateau_replay','/CPU:0',
            ['software_0'],pd.Timestamp('2030-01-01'),replay=rates)
        np.testing.assert_allclose(refit['history']['learning_rate_used'],rates,rtol=1e-6)

    def test_real_training_fold_refit_prediction_and_if(self):
        folder=self.root/'real_smoke'; folder.mkdir()
        data=self.ns['restrict_history'](self.data,pd.Timestamp('2022-01-03')+pd.Timedelta(weeks=64))
        runner=self.ns['ExperimentRunner'](data,self.worker,folder,self.root/'smoke_cache',self.code_hash,'/CPU:0',1,True)
        original_train=self.ns['train_model']; calls=[]
        def interrupted(*args,**kwargs):
            calls.append(1)
            if len(calls)==3:
                raise RuntimeError('synthetic interruption at second fold')
            return original_train(*args,**kwargs)
        with patch.dict(self.ns,train_model=interrupted):
            with self.assertRaises(RuntimeError):
                runner.run('v6_reference',self.worker.ForecastConfig(),'software smoke')
        result=runner.run('v6_reference',self.worker.ForecastConfig(),'software smoke')
        self.assertEqual(len(result['metrics']),3)
        own=[r for r in runner.fold_metrics if r['candidate']=='v6_reference']
        self.assertEqual(len(own),3)
        self.assertEqual(len(runner.histories),3)
        self.assertTrue(np.isfinite(result['rows'].prediction).all())
        for seed in (123,2026):
            # Production repeats real training; this fixture tests downstream plumbing
            # with explicitly duplicated fixtures, not claimed seed evidence.
            runner.runs[('v6_reference',seed,1.)]=result
        decision=dict(selected='v6_reference',provisional_winner='v6_reference',material_improvement_demonstrated=False,
            intervals={},guardrails={})
        fits,lock=self.ns['lock_and_refit'](runner,{'v6_reference':self.worker.ForecastConfig()},decision)
        validation=fixture(self.worker,users=3,weeks=80,prefix='legacy_fixture')
        rows,measures=self.ns['evaluate_legacy'](runner,fits,decision,validation,lock)
        self.assertEqual(rows.user_id.nunique(),3)
        recovered,_=self.ns['evaluate_legacy'](runner,fits,decision,validation,lock)
        pd.testing.assert_frame_equal(recovered,rows)
        original=(folder/'validation_metrics.json').read_bytes()
        (folder/'validation_metrics.json').write_text('{}')
        with self.assertRaises(ValueError):
            self.ns['evaluate_legacy'](runner,fits,decision,validation,lock)
        (folder/'validation_metrics.json').write_bytes(original)
        with self.assertRaises(PermissionError):
            runner.run('forbidden_after_lock',self.worker.ForecastConfig(),'illegal')
        calibration=fixture(self.worker,users=3,weeks=80,prefix='calibration_fixture')
        self.ns['anomaly_pipeline'](runner,calibration,validation,self.ifref)
        anomaly=pd.read_csv(folder/'anomaly_metrics.csv')
        self.assertIn('forest_collective_union',set(anomaly.model))
        protocol=json.loads((folder/'collective_protocol.json').read_text())
        self.assertFalse(protocol['adopted'])
        self.assertEqual(protocol['execution_mode'],'software_smoke')
        self.assertTrue((folder/'anomaly_per_type_events.csv').exists())
        (folder/'fold_metrics.csv').write_text('corrupted')
        (folder/'experiment_registry.csv').unlink()
        self.ns['write_figures'](runner,rows,measures,decision)
        self.assertEqual(len(pd.read_csv(folder/'fold_metrics.csv')),len(runner.fold_metrics))
        self.assertEqual(len(pd.read_csv(folder/'experiment_registry.csv')),len(runner.registry))
        self.assertTrue((folder/'residual_diagnostics.png').exists())


if __name__=='__main__':
    unittest.main()
