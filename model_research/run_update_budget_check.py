"""Fit-only capability check: fixed architecture, 120 vs 960 optimizer updates.

Imports only repository notebook worker code, never archive pickle/model payloads.
The archive supplies split IDs, source hashes and aggregate diagnostic metadata.
Temporary model artifacts are deleted; only aggregate metrics are retained.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import zipfile

import nbformat
import numpy as np
import pandas as pd

from diagnose_large_weeks import hash_file

HERE=Path(__file__).resolve().parent
CONTROLS=(('batch256_updates120',256,120),('batch32_updates960',32,120),('batch256_updates960',256,960))


def expected_updates(rows,batch_size,epochs):
    return ((rows+batch_size-1)//batch_size)*epochs


def load_worker(folder):
    nb=nbformat.read(HERE/'Spending_Model_V8_Income_Kaggle.ipynb',as_version=4)
    cell=next(c.source for c in nb.cells if c.cell_type=='code' and 'WORKER_SOURCE =' in c.source)
    constants={n.targets[0].id:ast.literal_eval(n.value) for n in ast.parse(cell).body
        if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','') in ('WORKER_SOURCE','CODE_HASH')}
    path=folder/'budget_worker.py'; path.write_text(constants['WORKER_SOURCE'],encoding='utf-8')
    spec=importlib.util.spec_from_file_location('budget_worker',path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
    ns={}
    exec(next(c.source for c in nb.cells if c.cell_type=='code' and 'def train_model(' in c.source),ns)
    ns['CODE_HASH']=constants['CODE_HASH']
    ns['BUDGET_SOURCE_HASHES']=dict(worker=hashlib.sha256(constants['WORKER_SOURCE'].encode()).hexdigest(),
        runtime=hashlib.sha256(next(c.source for c in nb.cells if c.cell_type=='code' and 'def train_model(' in c.source).encode()).hexdigest(),
        runner=hash_file(Path(__file__)))
    return module,ns


def reconstruct(raw,worker,ns,split):
    fit=set(split['folds'][0]['fit_users']); inner=pd.Timestamp(split['folds'][0]['inner'])
    identities={u:hashlib.sha256(('V7-export:'+u).encode()).hexdigest()[:20] for u in raw.user_id.unique()}
    eligible=sorted(u for u,h in identities.items() if h in fit)
    if len(eligible)!=len(fit): raise ValueError('Fit-user identities differ')
    portions=[]; total=0
    cfg=worker.ForecastConfig(monitor='val_loss',patience=16,min_delta=0.)
    for user in eligible:
        g=worker.clean_data(raw.loc[raw.user_id.eq(user)])
        g=ns['restrict_history'](g,pd.Timestamp(split['train_target_end']))
        b=worker.make_features(g,cfg)
        b=ns['subset'](b,b[0].end.le(inner))
        portions.append(b); total+=len(b[0])
        if total>=256: break
    bundle=(pd.concat([b[0] for b in portions],ignore_index=True),
            np.concatenate([b[1] for b in portions]),np.concatenate([b[2] for b in portions]))
    bundle=ns['subset'](bundle,np.arange(len(bundle[0]))<256)
    if len(bundle[0])!=256: raise ValueError('Original tiny slice not reconstructed')
    return bundle,cfg,eligible,inner


def run(archive,train_csv,output):
    import tensorflow as tf
    if output.exists(): raise FileExistsError('Use a new aggregate report path')
    with zipfile.ZipFile(archive) as z:
        prefix=z.namelist()[0].split('/')[0]+'/'
        split=json.loads(z.read(prefix+'data_split_manifest.json'))
        saved=json.loads(z.read(prefix+'memorization_diagnostic.json'))
        saved_identity=json.loads(z.read(prefix+'memorization/fit_identity.json'))
        source_schedule=json.loads(z.read(prefix+'memorization/schedule.json'))
    if split['dataset_version']!='spendly-synthetic-r3-v1': raise ValueError('Expected original R3')
    digest=hash_file(train_csv)
    if digest!=split['permitted_cohorts']['train']['sha256']:raise ValueError('Train hash mismatch')
    # Read one approved cohort only; do not glob input directories.
    raw=pd.read_csv(train_csv,dtype={'user_id':str,'transaction_id':str})
    with tempfile.TemporaryDirectory(prefix='spendly_budget_') as temporary:
        root=Path(temporary); worker,ns=load_worker(root)
        bundle,base,users,inner=reconstruct(raw,worker,ns,split)
        f=bundle[0]
        if f.user_id.nunique()!=saved['metrics']['users']:raise ValueError('Tiny user count differs')
        np.testing.assert_allclose(f.y.mean(),saved['metrics']['actual_mean_KES'],atol=1e-8,rtol=0)
        # Recreate the archived fit identity using its runtime metadata, to verify
        # the full original frame/order/features rather than just mean target.
        original_cfg=ns['replace'](base,l2=0.,learning_rate=.001,batch_size=256,max_epochs=120)
        with zipfile.ZipFile(archive) as z:
            original_tf=json.loads(z.read(prefix+'runtime_environment.json'))['versions']['tensorflow']
            original_numpy=json.loads(z.read(prefix+'runtime_environment.json'))['versions']['numpy']
            # Source hash is V8's declared implementation, not its inherited V6 audit.
            source_hash=ns['CODE_HASH']
        bundle_id=dict(rows=hashlib.sha256(pd.util.hash_pandas_object(f,index=True).values.tobytes()).hexdigest(),
            sequence=hashlib.sha256(bundle[1].tobytes()).hexdigest(),context=hashlib.sha256(bundle[2].tobytes()).hexdigest(),
            shapes=[list(bundle[1].shape),list(bundle[2].shape)])
        recreated=ns['digest'](dict(train=bundle_id,stop=None,config=ns['asdict'](original_cfg),
            users=sorted(users),end=str(inner),replay=None,device=source_schedule['training_device'],
            source=source_hash,tf=original_tf,numpy=original_numpy))
        # Cross-version pandas hashes may differ. Do not claim a byte-identical
        # reconstruction unless the complete archived identity actually agrees.
        exact_identity_match=recreated==saved_identity
        tf.keras.utils.set_random_seed(42)
        device='/CPU:0'
        rows=[]
        for name,batch,epochs in CONTROLS:
            print('CONTROL',name,flush=True)
            cfg=ns['replace'](base,l2=0.,learning_rate=.001,batch_size=batch,max_epochs=epochs)
            fit=ns['train_model'](bundle,None,cfg,root/name,device,users,inner)
            iterations=int(fit['model'].optimizer.iterations.numpy())
            assert iterations==expected_updates(len(f),batch,epochs)
            prediction,_=ns['predict'](fit,bundle,device)
            loaded=tf.keras.models.load_model(root/name/'fitted.keras',compile=False)
            restored,_=ns['predict'](dict(fit,model=loaded),bundle,device)
            np.testing.assert_allclose(prediction,restored,atol=.01,rtol=0)
            baseline=ns['metrics'](f,np.maximum(0.,f.center.to_numpy()))
            measured=ns['metrics'](f,prediction)
            rows.append(dict(control=name,batch_size=batch,epochs=epochs,optimizer_updates=iterations,
                configuration=ns['asdict'](cfg),example_presentations=len(f)*epochs,
                metrics=measured,baseline=baseline,
                final_over_initial_logged_error=fit['history']['weighted_mae'][-1]/fit['history']['weighted_mae'][0],
                final_over_untrained_KES_MAE=measured['MAE_KES']/baseline['MAE_KES'],
                gradient_norm=fit['gradient_norm'],seconds=fit['seconds'],reload_parity=True))
        result=dict(protocol='fit-only-update-budget-v1',train_sha256=digest,source_archive_sha256=hash_file(archive),
            original_fit_identity=saved_identity,rows=len(f),users=f.user_id.nunique(),cutoff=str(inner),
            reconstructed_identity_matches=exact_identity_match,bundle_fingerprints=bundle_id,
            recreated_identity=recreated,executed_source_hashes=ns['BUDGET_SOURCE_HASHES'],
            target_mean_KES=float(f.y.mean()),target_sum_KES=float(f.y.sum()),
            device=device,tensorflow=tf.__version__,numpy=np.__version__,pandas=pd.__version__,
            original_gpu_diagnostic=saved,controls=rows,
            scope='Fixed fit-only windows. CPU replication; not exact Kaggle GPU numerical reproduction or held-out performance.',
            artifacts='Temporary models/scalers removed after checks; aggregate report only retained')
        output.write_text(json.dumps(ns['safe_json'](result),indent=2,allow_nan=False),encoding='utf-8')
        print(pd.DataFrame([dict(control=r['control'],updates=r['optimizer_updates'],MAE=r['metrics']['MAE_KES'],
            WAPE=r['metrics']['WAPE'],error_ratio=r['final_over_untrained_KES_MAE'],seconds=r['seconds']) for r in rows]).to_string(index=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--train-csv',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); run(args.archive,args.train_csv,args.output)
