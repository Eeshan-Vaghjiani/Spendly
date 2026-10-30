"""V8 causality/parity checks on handcrafted fixtures; no production data access."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import nbformat
import numpy as np
import pandas as pd

from test_v7_evidence import fixture

HERE=Path(__file__).resolve().parent


def worker_module(folder):
    nb=nbformat.read(HERE/'Spending_Model_V8_Income_Kaggle.ipynb',as_version=4)
    cell=next(c.source for c in nb.cells if c.cell_type=='code' and 'WORKER_SOURCE =' in c.source)
    tree=ast.parse(cell)
    source=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','')=='WORKER_SOURCE')
    path=folder/'v8_fixture_worker.py'; path.write_text(source,encoding='utf-8')
    spec=importlib.util.spec_from_file_location('v8_fixture_worker',path)
    worker=importlib.util.module_from_spec(spec); sys.modules[spec.name]=worker; spec.loader.exec_module(worker)
    return nb,worker


def income_fixture(worker,users=6,weeks=80,prefix='fixture'):
    expenses=fixture(worker,users=users,weeks=weeks,prefix=prefix)
    receipts=[]
    for user,g in expenses.groupby('user_id'):
        for w in range(0,weeks,4):
            row=g.iloc[0].copy()
            row['transaction_id']=f'{user}_income_{w}'
            row['transaction_timestamp']=g.observation_start.iloc[0]+pd.Timedelta(weeks=w,hours=8)
            row['amount']=5000.; row['category']='Income'; row['merchant']='payer'
            row['transaction_type']='income'; row['label']=0.; row['is_anomaly']=0
            receipts.append(row)
    return pd.concat([expenses,pd.DataFrame(receipts)],ignore_index=True).sort_values(
        ['user_id','transaction_timestamp','transaction_id']).reset_index(drop=True)


class IncomeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(); cls.root=Path(cls.temp.name)
        cls.nb,cls.worker=worker_module(cls.root)
        cls.data=income_fixture(cls.worker,users=1,weeks=52)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def cfg(self):
        return self.worker.ForecastConfig(
            sequence_features=('total','nonrecurring','income_amount','income_receipts','category_food','category_OTHER'),
            context_features=self.worker.ForecastConfig().context_features+self.worker.V8_INCOME_CONTEXT,
            category_vocabulary=('food','OTHER'))

    def test_reference_exact_parity_and_expense_targets(self):
        expenses=self.data.loc[self.data.transaction_type.eq('expense')]
        expected=self.worker._v7_make_features(expenses,self.worker.ForecastConfig())
        actual=self.worker.make_features(self.data,self.worker.ForecastConfig())
        pd.testing.assert_frame_equal(expected[0],actual[0])
        np.testing.assert_array_equal(expected[1],actual[1]); np.testing.assert_array_equal(expected[2],actual[2])
        richer=self.worker.make_features(self.data,self.cfg())
        pd.testing.assert_frame_equal(actual[0],richer[0])

    def test_future_receipts_and_labels_do_not_change_features(self):
        frame,seq,ctx=self.worker.make_features(self.data,self.cfg())
        cutoff=frame.time.iloc[12]; changed=self.data.copy()
        changed.loc[changed.transaction_timestamp.ge(cutoff),'amount']*=19
        changed.loc[changed.transaction_timestamp.ge(cutoff),'category']='future_only'
        changed['label']=1.; changed['is_anomaly']=1; changed['event_id']='never_a_feature'
        _,other_seq,other_ctx=self.worker.make_features(changed,self.cfg())
        mask=frame.time.le(cutoff)
        np.testing.assert_array_equal(seq[mask],other_seq[mask]); np.testing.assert_array_equal(ctx[mask],other_ctx[mask])

    def test_prior_receipt_changes_candidate_not_reference(self):
        cfg=self.cfg(); f,s,c=self.worker.make_features(self.data,cfg)
        changed=self.data.copy(); changed.loc[changed.transaction_type.eq('income'),'amount']*=3
        other,os,oc=self.worker.make_features(changed,cfg)
        pd.testing.assert_frame_equal(f,other)
        self.assertFalse(np.array_equal(s,os)); self.assertFalse(np.array_equal(c,oc))
        base=self.worker.make_features(self.data,self.worker.ForecastConfig())
        updated=self.worker.make_features(changed,self.worker.ForecastConfig())
        np.testing.assert_array_equal(base[1],updated[1]); np.testing.assert_array_equal(base[2],updated[2])

    def test_no_income_and_target_boundary(self):
        expenses=self.data.loc[self.data.transaction_type.eq('expense')].copy()
        frame,seq,ctx=self.worker.make_features(expenses,self.cfg())
        self.assertTrue(np.isfinite(ctx).all())
        self.assertTrue((seq[:,:,2:4]==0).all())
        known_index=self.cfg().context_features.index('income_observed')
        self.assertTrue((ctx[:,known_index]==0).all())
        receipt=expenses.iloc[0].copy(); receipt['transaction_id']='boundary_receipt'
        receipt['transaction_type']='income'; receipt['transaction_timestamp']=frame.time.iloc[5]
        modified=pd.concat([expenses,pd.DataFrame([receipt])],ignore_index=True)
        _,_,other=self.worker.make_features(modified,self.cfg())
        np.testing.assert_array_equal(ctx[:6],other[:6])
        self.assertEqual(other[6,known_index],1.)

    def test_receipt_types_survive_cleaning_and_cache_invalidates(self):
        # Mimic CSV offsets; embedded cleaner strips Nairobi timezone consistently.
        raw=self.data.copy()
        for col in ('transaction_timestamp','observation_start','observation_end'):
            raw[col]=raw[col].map(lambda d:d.isoformat()+'+03:00')
        cleaned=self.worker.clean_data(raw)
        self.assertEqual(cleaned.transaction_type.eq('income').sum(),13)
        one=self.worker.cached_user(self.data,self.cfg(),self.root/'cache','v8')
        changed=self.data.copy(); changed.loc[changed.transaction_type.eq('income'),'amount']+=100
        two=self.worker.cached_user(changed,self.cfg(),self.root/'cache','v8')
        self.assertFalse(np.array_equal(one[2],two[2]))
        self.assertEqual(len(list((self.root/'cache').glob('*/complete.json'))),2)

    def test_notebook_contract(self):
        nbformat.validate(self.nb)
        for c in self.nb.cells:
            if c.cell_type=='code':
                compile(c.source,c.id,'exec'); self.assertFalse(c.outputs)
        search=next(c.source for c in self.nb.cells if 'def v8_search(' in c.source)
        ns={}; exec('from dataclasses import replace',ns)
        exec((HERE/'v8_experiments.py').read_text(encoding='utf-8'),ns)
        self.assertEqual(len(ns['v8_candidates'](self.worker)),5)
        self.assertIn((HERE/'v8_experiments.py').read_text(encoding='utf-8'),search)
        worker_cell=next(c.source for c in self.nb.cells if c.cell_type=='code' and 'WORKER_SOURCE =' in c.source)
        constants={n.targets[0].id:ast.literal_eval(n.value) for n in ast.parse(worker_cell).body
            if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','') in ('WORKER_SOURCE','CODE_HASH')}
        self.assertIn((HERE/'v8_features.py').read_text(encoding='utf-8'),constants['WORKER_SOURCE'])

    def test_income_category_model_training_reload_and_artifact_contract(self):
        import tensorflow as tf
        ns={}
        for cell in self.nb.cells:
            if cell.cell_type=='code' and ('def train_model(' in cell.source or 'def v8_search(' in cell.source):
                exec(cell.source,ns)
        data=income_fixture(self.worker,users=6,weeks=80,prefix='export')
        end=data.observation_start.min()+pd.Timedelta(weeks=61)
        data=ns['restrict_history'](data,end)
        cfg=ns['replace'](ns['v8_candidates'](self.worker)['income_category'],max_epochs=2)
        folder=self.root/'income_export'; folder.mkdir()
        runner=ns['ExperimentRunner'](data,self.worker,folder,self.root/'export_cache','v8-export-test','/CPU:0',1,True)
        result=runner.run('income_category',cfg,'software export path')
        reference_cfg=ns['replace'](self.worker.ForecastConfig(),max_epochs=2)
        reference=runner.run('v6_reference',reference_cfg,'software export reference')
        for seed in (123,2026):
            # Plumbing-only fixtures; no repeated-seed performance claim.
            runner.runs[('income_category',seed,1.)]=result
            runner.runs[('v6_reference',seed,1.)]=reference
        decision=dict(selected='income_category',provisional_winner='income_category',
            material_improvement_demonstrated=False,intervals={},guardrails={})
        fits,lock=ns['lock_and_refit'](runner,{'income_category':cfg,'v6_reference':reference_cfg},decision)
        record=json.loads((folder/'configuration_lock.json').read_text())
        self.assertEqual(record['protocol'],'v8-observed-income-v1')
        self.assertEqual(fits['income_category']['model'].inputs[0].shape[-1],
            4+len(fits['income_category']['config'].category_vocabulary))
        self.assertTrue(json.loads((folder/'reload_parity.json').read_text())['passed'])
        validation=income_fixture(self.worker,users=3,weeks=80,prefix='export_validation')
        rows,measures=ns['evaluate_legacy'](runner,fits,decision,validation,lock)
        self.assertEqual(rows.user_id.nunique(),3)
        self.assertTrue(np.isfinite(rows.prediction).all())
        self.assertEqual(len(rows),len(runner.worker.make_features(validation.loc[
            validation.user_id.eq(sorted(validation.user_id.unique())[0])],fits['income_category']['config'])[0].loc[
                lambda f:f.time.ge(end)])*3)

    def test_income_only_user_excluded_after_cutoff(self):
        data=income_fixture(self.worker,users=6,weeks=52)
        extra=data.loc[data.transaction_type.eq('income')].iloc[:2].copy()
        extra['user_id']='income_only'; extra['transaction_id']=['only1','only2']
        extended=pd.concat([data,extra],ignore_index=True)
        eligible=self.worker.expense_eligible(extended)
        self.assertEqual(set(eligible.user_id),set(data.user_id))
        pd.testing.assert_frame_equal(eligible.reset_index(drop=True),data.reset_index(drop=True))

    def test_vocabulary_uses_fit_expenses_and_multiuser_isolation(self):
        ns={}
        exec(next(c.source for c in self.nb.cells if c.cell_type=='code' and 'def fit_vocabulary(' in c.source),ns)
        exec((HERE/'v8_experiments.py').read_text(encoding='utf-8'),ns)
        data=income_fixture(self.worker,users=2,weeks=52)
        users=sorted(data.user_id.unique()); cutoff=data.observation_start.min()+pd.Timedelta(weeks=30)
        data.loc[data.user_id.eq(users[1]),'category']='HELDOUT_ONLY'
        data.loc[data.user_id.eq(users[0])&data.transaction_type.eq('income'),'category']='INCOME_ONLY'
        cfg=self.worker.ForecastConfig(sequence_features=('total','nonrecurring','category_PENDING'))
        resolved=ns['resolve_config'](cfg,data,[users[0]],cutoff)
        self.assertNotIn('HELDOUT_ONLY',resolved.category_vocabulary)
        self.assertNotIn('INCOME_ONLY',resolved.category_vocabulary)
        f,s,c=self.worker.make_features(data,self.cfg())
        one=data.loc[data.user_id.eq(users[0])]
        of,os,oc=self.worker.make_features(one,self.cfg())
        mask=f.user_id.eq(users[0])
        np.testing.assert_array_equal(s[mask],os); np.testing.assert_array_equal(c[mask],oc)


if __name__=='__main__': unittest.main()
