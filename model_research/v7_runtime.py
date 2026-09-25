"""V7 evidence runner. Embedded verbatim in standalone notebook; no work on import."""
import os, sys, json, hashlib, time, platform, subprocess, importlib.metadata, zipfile
from pathlib import Path
from contextlib import contextmanager
from dataclasses import asdict, replace
from collections import defaultdict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
import joblib

RUN_FINAL_HOLDOUTS = False
ALLOWED_COHORTS = ('train', 'validation', 'calibration')
TIMINGS = defaultdict(float)
STARTED = time.perf_counter()
ACCESSES = []


def safe_json(value):
    if isinstance(value, dict):
        return {str(k):safe_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):
        return [safe_json(v) for v in value]
    if isinstance(value,(np.integer,np.bool_)):
        return value.item()
    if isinstance(value,(float,np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value,(Path,pd.Timestamp)):
        return str(value)
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(safe_json(value),indent=2,sort_keys=True,allow_nan=False),encoding='utf-8')


def digest(value):
    return hashlib.sha256(json.dumps(safe_json(value),sort_keys=True).encode()).hexdigest()


@contextmanager
def timed(stage):
    start=time.perf_counter()
    try:
        yield
    finally:
        TIMINGS[stage]+=time.perf_counter()-start


def gpu_preflight(result_dir, require_gpu=True):
    import tensorflow as tf
    evidence=dict(tensorflow=tf.__version__,python=sys.version,build=tf.sysconfig.get_build_info())
    try:
        evidence['nvidia_smi']=subprocess.run(['nvidia-smi'],capture_output=True,text=True,timeout=20).stdout
        evidence['gpu_memory']=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used,driver_version',
            '--format=csv'],capture_output=True,text=True,timeout=20).stdout
    except (OSError,subprocess.SubprocessError) as error:
        evidence['nvidia_smi_unavailable']=type(error).__name__
    physical=tf.config.list_physical_devices('GPU')
    evidence['physical_gpus']=[dict(device=d.name,details=tf.config.experimental.get_device_details(d)) for d in physical]
    for device in physical:
        try:
            tf.config.experimental.set_memory_growth(device,True)
        except RuntimeError:
            pass
    evidence['logical_gpus']=[d.name for d in tf.config.list_logical_devices('GPU')]
    evidence['selected_training_device']='/GPU:0' if physical else '/CPU:0'
    evidence['gpu_required']=require_gpu
    write_json(result_dir/'gpu_evidence.json',evidence)
    if require_gpu and not physical:
        raise RuntimeError('Kaggle: open Notebook Settings / Session Options > Accelerator > GPU (T4 x2), '
            'restart the session, then Run All. This notebook cannot enable a Kaggle accelerator itself.')
    previous=tf.config.get_soft_device_placement()
    try:
        tf.config.set_soft_device_placement(False)
        with tf.device(evidence['selected_training_device']):
            result=tf.matmul(tf.ones((64,64)),tf.ones((64,64)))
            result.numpy()
        evidence['matrix_result_device']=result.device
        assert not physical or 'GPU:0' in result.device.upper()
    finally:
        tf.config.set_soft_device_placement(previous)
    # Some cuDNN GPU kernels remain version/hardware sensitive despite seeds.
    try:
        tf.config.experimental.enable_op_determinism()
        evidence['determinism_requested']=True
    except (AttributeError,RuntimeError):
        evidence['determinism_requested']=False
    write_json(result_dir/'gpu_evidence.json',evidence)
    versions={name:importlib.metadata.version(name) for name in
              ('numpy','pandas','tensorflow','keras','scikit-learn','joblib','matplotlib')}
    write_json(result_dir/'runtime_environment.json',dict(python=sys.version,platform=platform.platform(),
        cpu_count=os.cpu_count(),versions=versions,precision='float32',
        limitations='GPU results can differ across CUDA/cuDNN, TF/Keras and hardware versions'))
    print('LSTM device:',evidence['selected_training_device'], '| all feature/IF/rule stages are CPU')
    return evidence


def assert_permitted(cohort):
    if cohort not in ALLOWED_COHORTS:
        raise PermissionError('Development-only notebook: requested cohort is prohibited')
    if RUN_FINAL_HOLDOUTS is not False:
        raise PermissionError('Final holdouts are locked; this notebook has no final evaluator')


def discover(name, root):
    # Whitelist exact filenames. Never recursively open arbitrary CSVs/archives.
    if name not in ('manifest.json', *[c+s for c in ALLOWED_COHORTS for s in ('.csv','.zip')]):
        raise PermissionError('Input name is not permitted')
    matches=sorted(Path(root).rglob(name))
    if len(matches)!=1:
        raise FileNotFoundError(f'Attach exactly one {name} under Kaggle Input; found {len(matches)}')
    return matches[0]


def load_manifest(root):
    # Dataset manifest contains aggregate provenance, not labels. Retain permitted entries only.
    raw=json.loads(discover('manifest.json',root).read_text())
    if raw.get('version') not in ('spendly-synthetic-r3-v1','spendly-synthetic-v7-dev-v1') or raw.get('status')!='complete':
        raise ValueError('Expected completed synthetic R3 or V7 development manifest')
    if raw.get('version')=='spendly-synthetic-v7-dev-v1' and set(raw.get('cohorts',{}))!=set(ALLOWED_COHORTS):
        raise ValueError('V7 development manifest must contain only permitted cohorts')
    return dict(version=raw['version'],currency=raw['currency'],timezone=raw['timezone'],
        benchmark_role='fresh synthetic development replication' if raw['version']=='spendly-synthetic-v7-dev-v1' else 'legacy reused development benchmark',
        weeks_per_user=raw['weeks_per_user'],cohorts={k:raw['cohorts'][k] for k in ALLOWED_COHORTS})


def load_cohort(cohort, root, manifest, worker, result_dir):
    assert_permitted(cohort)
    if cohort=='validation' and not (result_dir/'configuration_lock.json').exists():
        raise PermissionError('Legacy validation cannot open until configuration is locked')
    with timed('data_loading'):
        try:
            path=discover(cohort+'.csv',root)
        except FileNotFoundError:
            path=discover(cohort+'.zip',root)
        if path.suffix=='.zip':
            with zipfile.ZipFile(path) as z:
                if z.namelist()!=[cohort+'.csv']:
                    raise ValueError('Attach a single-cohort ZIP containing only '+cohort+'.csv')
                contents=z.read(cohort+'.csv')
        else:
            contents=path.read_bytes()
        if hashlib.sha256(contents).hexdigest()!=manifest['cohorts'][cohort]['sha256']:
            raise ValueError('R3 data hash mismatch')
        import io
        raw=pd.read_csv(io.BytesIO(contents),dtype={'user_id':str,'transaction_id':str})
        if len(raw)!=manifest['cohorts'][cohort]['rows'] or raw.user_id.nunique()!=manifest['cohorts'][cohort]['users']:
            raise ValueError('Permitted cohort composition mismatch')
        data=worker.clean_data(raw)
        ACCESSES.append(dict(cohort=cohort,sha256=manifest['cohorts'][cohort]['sha256'],raw_rows=len(raw),
            users=data.user_id.nunique(),expense_rows=len(data),income_rows=int(raw.transaction_type.eq('income').sum()),
            missing_cells=int(raw.isna().sum().sum()),anomaly_prevalence=float(data.label.mean()),
            category_counts=data.category.value_counts().to_dict(),start=str(data.observation_start.min()),end=str(data.observation_end.max())))
        return data


def restrict_history(data, end):
    result=data.loc[data.transaction_timestamp.lt(end)].copy()
    result['observation_end']=end
    return result


def features(data, config, worker, cache, code_hash, workers=2):
    assert 1<=workers<=4
    from joblib import Parallel, delayed, parallel_config
    with timed('feature_generation'):
        print(f'CPU features: {data.user_id.nunique()} users; lookback={config.lookback}; workers={workers}',flush=True)
        begun=time.perf_counter()
        with parallel_config(backend='loky',n_jobs=workers,inner_max_num_threads=1):
            results=Parallel(return_as='generator',pre_dispatch=workers,batch_size=1)(
                delayed(worker.cached_user)(g,config,str(cache),code_hash) for _,g in data.groupby('user_id',sort=True))
            parts=[]
            for i,part in enumerate(results,1):
                parts.append(part)
                if i==1 or i%25==0:
                    print(f'  {i} users ready; {(time.perf_counter()-begun)/60:.1f} CPU-stage minutes',flush=True)
        return (pd.concat([v[0] for v in parts],ignore_index=True),
                np.concatenate([v[1] for v in parts]),np.concatenate([v[2] for v in parts]))


def subset(bundle, mask):
    positions=np.flatnonzero(np.asarray(mask))
    return bundle[0].iloc[positions].reset_index(drop=True),bundle[1][positions],bundle[2][positions]


def fixed_folds(data, smoke=False):
    users=sorted(data.user_id.unique(),key=lambda u:hashlib.sha256(('V7:'+u).encode()).hexdigest())
    if len(users)<6:
        raise ValueError('At least six training users required for separated fit/stopping/evaluation blocks')
    blocks=[list(v) for v in np.array_split(users,3)]
    origin=data.observation_start.min()
    duration=int((data.observation_end.min()-origin)/pd.Timedelta(weeks=1))
    folds=[]
    for i in range(3):
        outer=int(duration*(.55+.10*i))
        # Stopping targets are strictly earlier than outer evaluation targets.
        inner=max(28,outer-12)
        train=[u for u in users if u not in blocks[i]]
        stop=train[::5]
        fit=[u for u in train if u not in stop]
        folds.append(dict(fold=i,fit_users=fit,stop_users=stop,eval_users=blocks[i],refit_users=train,
            inner=str(origin+pd.Timedelta(weeks=inner)),outer=str(origin+pd.Timedelta(weeks=outer)),
            end=str(origin+pd.Timedelta(weeks=min(outer+12,duration)))))
    return folds


def fit_vocabulary(data, fit_users, end, count=3):
    portion=data.loc[data.user_id.isin(fit_users)&data.transaction_timestamp.lt(end)]
    ranks=portion.groupby('category').amount.sum().sort_values(ascending=False,kind='stable')
    return tuple(ranks.index[:count])+('OTHER',)


def resolve_config(config, data, users, end):
    if not any(n.startswith('share_') for n in config.context_features):
        return config
    vocab=fit_vocabulary(data,users,end)
    ctx=tuple(n for n in config.context_features if not n.startswith('share_'))+tuple('share_'+v for v in vocab)
    return replace(config,category_vocabulary=vocab,context_features=ctx)


def fit_preprocessing(bundle, allowed_users, end):
    f,s,c=bundle
    assert set(f.user_id)<=set(allowed_users), 'Preprocessing fitted with nontraining users'
    assert f.end.le(pd.Timestamp(end)).all(), 'Preprocessing fitted with future targets'
    if not len(f):
        raise ValueError('Empty fit slice')
    return dict(sequence=StandardScaler().fit(s.reshape(-1,s.shape[-1])),context=StandardScaler().fit(c),
        fit_users=sorted(set(f.user_id)),fit_end=str(end),rows=len(f),feature_shape=list(s.shape[1:]))


def model_inputs(bundle, scales, cfg):
    _,s,c=bundle
    if list(s.shape[1:])!=scales['feature_shape']:
        raise ValueError('Preprocessing/configuration shape mismatch')
    seq=scales['sequence'].transform(s.reshape(-1,s.shape[-1])).reshape(s.shape).astype('float32')
    ctx=scales['context'].transform(c).astype('float32')
    if cfg.ablation=='shuffled':
        seq=seq.copy()
        rng=np.random.default_rng(cfg.seed)
        for row in seq:
            rng.shuffle(row,axis=0)
    return (seq,ctx)


def make_model(cfg, device):
    import tensorflow as tf
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(cfg.seed)
    with tf.device(device):
        seq=tf.keras.Input((cfg.lookback,len(cfg.sequence_features)),name='weekly_sequence')
        context=tf.keras.Input((len(cfg.context_features),),name='causal_context')
        # No unsupported use_cudnn flag; these documented options permit the fast path.
        encoded=tf.keras.layers.LSTM(cfg.units,activation='tanh',recurrent_activation='sigmoid',
            recurrent_dropout=0.,dropout=0.,unroll=False,use_bias=True,
            kernel_regularizer=tf.keras.regularizers.l2(cfg.l2))(seq)
        contextual=tf.keras.layers.Dense(8,activation='relu')(context) if cfg.context_branch else context
        if cfg.ablation=='sequence_only':
            contextual=tf.keras.layers.Rescaling(0.)(contextual)
        if cfg.ablation=='context_only':
            encoded=tf.keras.layers.Rescaling(0.)(encoded)
        hidden=tf.keras.layers.Dense(16,activation='relu')(tf.keras.layers.Concatenate()([encoded,contextual]))
        out=tf.keras.layers.Dense(1,kernel_initializer='zeros',bias_initializer='zeros')(hidden)
        model=tf.keras.Model([seq,context],out)
        loss='mae' if cfg.loss=='mae' else tf.keras.losses.Huber(delta=1.)
        model.compile(optimizer=tf.keras.optimizers.Adam(cfg.learning_rate,clipnorm=cfg.clipnorm),loss=loss,
            weighted_metrics=[tf.keras.metrics.MeanAbsoluteError(name='weighted_mae')],jit_compile=False)
        probe=model([tf.zeros((2,cfg.lookback,len(cfg.sequence_features))),
                     tf.zeros((2,len(cfg.context_features)))],training=False)
        probe.numpy()
        if 'GPU' in device.upper() and 'GPU:0' not in probe.device.upper():
            raise RuntimeError('LSTM output did not execute on GPU0; refusing silent fallback')
    return model


def training_dataset(bundle, scales, cfg, denominator, shuffle=False):
    import tensorflow as tf
    f=bundle[0]
    target=((f.y-f.center)/f.scale).to_numpy('float32').reshape(-1,1)
    weights=(f.scale/denominator).to_numpy('float32')
    ds=tf.data.Dataset.from_tensor_slices((model_inputs(bundle,scales,cfg),target,weights))
    if shuffle:
        ds=ds.shuffle(len(f),seed=cfg.seed,reshuffle_each_iteration=True)
    options=tf.data.Options(); options.threading.private_threadpool_size=2
    return ds.batch(cfg.batch_size).with_options(options).prefetch(tf.data.AUTOTUNE)


def train_model(train, stop, cfg, directory, device, allowed_users, end, replay=None, require_completed=False):
    import tensorflow as tf
    directory.mkdir(parents=True,exist_ok=True)
    def bundle_identity(bundle):
        if bundle is None:
            return None
        frame,sequence,context=bundle
        return dict(rows=hashlib.sha256(pd.util.hash_pandas_object(frame,index=True).values.tobytes()).hexdigest(),
            sequence=hashlib.sha256(sequence.tobytes()).hexdigest(),context=hashlib.sha256(context.tobytes()).hexdigest(),
            shapes=[list(sequence.shape),list(context.shape)])
    identity=digest(dict(train=bundle_identity(train),stop=bundle_identity(stop),config=asdict(cfg),
        users=sorted(allowed_users),end=str(end),replay=replay,device=device,
        source=globals().get('CODE_HASH','local-fixture'),tf=tf.__version__,numpy=np.__version__))
    if verify_checkpoint(directory,identity):
        saved=joblib.load(directory/'fit_state.joblib')
        model=tf.keras.models.load_model(directory/'fitted.keras',compile=False)
        print('RESUMED completed fit:',directory.name,flush=True)
        return dict(saved,model=model,config=cfg)
    if require_completed:
        raise PermissionError('Benchmark already consumed: missing completed refit; retraining forbidden')
    identity_path=directory/'fit_identity.json'
    if identity_path.exists() and json.loads(identity_path.read_text())!=identity:
        raise ValueError('Incomplete fit belongs to different inputs/configuration')
    atomic_json(identity_path,identity)
    scales=fit_preprocessing(train,allowed_users,end)
    model=make_model(cfg,device)
    denominator=float(train[0].scale.mean())
    rates=[]
    class RateRecorder(tf.keras.callbacks.Callback):
        def on_epoch_begin(self,epoch,logs=None):
            if replay is not None:
                self.model.optimizer.learning_rate.assign(replay[epoch])
            rates.append(float(self.model.optimizer.learning_rate.numpy()))
        def on_epoch_end(self,epoch,logs=None):
            logs['learning_rate_used']=rates[-1]
            if epoch==0 or (epoch+1)%10==0:
                print(f'  {directory.name}: epoch {epoch+1}, weighted MAE {logs.get("weighted_mae",float("nan")):.6f}',flush=True)
    callbacks=[RateRecorder(),tf.keras.callbacks.TerminateOnNaN(),tf.keras.callbacks.CSVLogger(str(directory/'history.csv'))]
    best_tracker=None
    if stop is not None:
        # One checkpoint criterion, including min_delta, controls save, restore and duration.
        class PredictiveCheckpoint(tf.keras.callbacks.Callback):
            def __init__(self):
                super().__init__(); self.best=np.inf; self.epoch=0; self.wait=0
            def on_epoch_end(self,epoch,logs=None):
                current=float(logs[cfg.monitor])
                if current < self.best-cfg.min_delta:
                    self.best=current; self.epoch=epoch+1; self.wait=0
                    self.model.save_weights(directory/'best.weights.h5')
                else:
                    self.wait+=1
                    if self.wait>=cfg.patience:
                        self.model.stop_training=True
            def on_train_end(self,logs=None):
                if self.epoch==0:
                    raise FloatingPointError('No finite checkpoint')
                self.model.load_weights(directory/'best.weights.h5')
        best_tracker=PredictiveCheckpoint()
        callbacks.append(best_tracker)
        if cfg.schedule=='plateau':
            callbacks.append(tf.keras.callbacks.ReduceLROnPlateau(monitor=cfg.monitor,mode='min',factor=.5,
                patience=4,min_delta=cfg.min_delta,cooldown=1,min_lr=1e-5))
    start=time.perf_counter()
    with timed('model_training'),tf.device(device):
        history=model.fit(training_dataset(train,scales,cfg,denominator,True),
            validation_data=training_dataset(stop,scales,cfg,denominator) if stop is not None else None,
            epochs=len(replay) if replay is not None else cfg.max_epochs,callbacks=callbacks,verbose=0)
    seconds=time.perf_counter()-start
    for key,values in history.history.items():
        if not np.isfinite(values).all():
            raise FloatingPointError('Nonfinite '+key)
    best=best_tracker.epoch if best_tracker is not None else len(history.history['loss'])
    joblib.dump(scales,directory/'preprocessing.joblib')
    write_json(directory/'schedule.json',dict(best_epoch=best,rates=rates[:best],configuration=asdict(cfg),
        checkpoint_metric=cfg.monitor,train_seconds=seconds,parameters=model.count_params(),training_device=device))
    # Useful gradient diagnostic, measured without parameter updates.
    batch=next(iter(training_dataset(train,scales,cfg,denominator)))
    with tf.GradientTape() as tape:
        output=model(batch[0],training=False)
        loss=tf.reduce_mean(tf.abs(output-batch[1])*batch[2][:,None])
    grads=tape.gradient(loss,model.trainable_weights)
    gradient_norm=float(tf.linalg.global_norm([g for g in grads if g is not None]).numpy())
    saved=dict(scales=scales,rates=rates[:best],history=history.history,
                 best_epoch=best,seconds=seconds,parameters=model.count_params(),gradient_norm=gradient_norm)
    model.save(directory/'fitted.keras')
    joblib.dump(saved,directory/'fit_state.joblib')
    seal_checkpoint(directory,identity,['fitted.keras','fit_state.joblib','schedule.json','preprocessing.joblib'])
    return dict(saved,model=model,config=cfg)


def predict(fit, bundle, device):
    import tensorflow as tf
    begun=time.perf_counter()
    with timed('prediction'),tf.device(device):
        inputs=model_inputs(bundle,fit['scales'],fit['config'])
        ds=tf.data.Dataset.from_tensor_slices(inputs).batch(fit['config'].batch_size).prefetch(tf.data.AUTOTUNE)
        values=np.concatenate([fit['model'](batch,training=False).numpy().ravel() for batch in ds])
        prediction=np.maximum(0.,values*bundle[0].scale.to_numpy()+bundle[0].center.to_numpy())
    return prediction,time.perf_counter()-begun


def metrics(frame, prediction):
    with timed('evaluation'):
        y=frame.y.to_numpy(float); p=np.asarray(prediction,float)
        assert len(y)==len(p) and len(y)>0 and np.isfinite(p).all()
        error=p-y
        denominator=y.sum()
        wape=float(np.abs(error).sum()/denominator) if denominator>0 else np.nan
        blocks=np.array_split(sorted(frame.time.unique()),3)
        block=[]
        for dates in blocks:
            m=frame.time.isin(dates).to_numpy()
            if m.any() and y[m].sum()>0:
                block.append(float(np.abs(error[m]).sum()/y[m].sum()))
        worst=max(block) if block else np.nan
        return dict(rows=len(y),users=frame.user_id.nunique(),weeks=frame.time.nunique(),MAE_KES=np.abs(error).mean(),
            RMSE_KES=np.sqrt(np.mean(error**2)),WAPE=wape,R2=r2_score(y,p) if np.var(y)>0 else np.nan,
            bias_KES=error.mean(),bias_percent=100*error.mean()/y.mean() if y.mean()>0 else np.nan,
            actual_mean_KES=y.mean(),predicted_mean_KES=p.mean(),within_20_percent=np.mean(np.abs(error)<=.2*y+1e-9),
            worst_block_WAPE=worst,selection_objective=(wape+worst)/2)


def row_predictions(frame,prediction,candidate,fold,seed):
    out=frame[['user_id','time','y','robust_recurring','recurring','last','mean4','volatility','activity','zero_fraction','recurring_share']].copy()
    out['user_id']=out.user_id.map(lambda u:hashlib.sha256(('V7-export:'+u).encode()).hexdigest()[:20])
    out=out.rename(columns={'time':'target_week','y':'actual','robust_recurring':'recurring_median'})
    out['prediction']=prediction; out['candidate']=candidate; out['fold']=fold; out['seed']=seed
    out['residual']=out.prediction-out.actual; out['absolute_error']=np.abs(out.residual)
    out['percentage_error']=np.where(out.actual.gt(0),out.absolute_error/np.maximum(out.actual,1e-12),np.nan)
    out['within_20_valid']=np.where(out.actual.gt(0),out.percentage_error.le(.2),np.nan)
    out['activity_subgroup']=np.where(out.zero_fraction.ge(.5),'zero-heavy','active')
    return out


def bootstrap(rows, resamples=1000, seed=2026):
    assert resamples>=1000
    columns=['prediction','reproduced_v6','recurring_median']
    groups=[]
    for _,g in rows.groupby('user_id',sort=True):
        groups.append([g.actual.sum(),*[np.abs(g[c]-g.actual).sum() for c in columns]])
    a=np.asarray(groups,float)
    if len(a)<2:
        raise ValueError('Cluster bootstrap requires multiple independent users')
    rng=np.random.default_rng(seed)
    trials=[]
    for _ in range(resamples):
        sums=a[rng.integers(0,len(a),size=len(a))].sum(axis=0)
        if sums[0]>0:
            trials.append(sums[1:]/sums[0])
    draws=np.asarray(trials)
    if len(draws)<.95*resamples:
        raise ValueError('Too many zero-denominator bootstrap samples')
    ci=lambda x:np.quantile(x,[.025,.975]).tolist()
    point=np.abs(rows.prediction-rows.actual).sum()/rows.actual.sum()
    return dict(resamples=resamples,users=len(a),WAPE=float(point),candidate_WAPE_95=ci(draws[:,0]),
        candidate_minus_v6_pp_95=ci(100*(draws[:,0]-draws[:,1])),
        candidate_minus_baseline_pp_95=ci(100*(draws[:,0]-draws[:,2])),
        scope='complete-user paired percentile bootstrap; conditional on chosen models; not selection-adjusted; seeds not independent users')


def paired_rows(rows, reference):
    keys=['user_id','target_week','fold','seed']
    assert not reference.duplicated(keys).any() and not rows.duplicated(keys).any()
    result=rows.merge(reference[keys+['prediction']].rename(columns={'prediction':'reproduced_v6'}),on=keys,validate='one_to_one')
    if len(result)!=len(rows):
        raise ValueError('Comparator evaluation rows differ')
    return result
