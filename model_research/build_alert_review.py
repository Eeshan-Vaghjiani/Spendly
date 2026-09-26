"""Build a CPU-only reproduction of V7's completed, subsequently lost alert run."""
import ast
import hashlib
from pathlib import Path
import nbformat

HERE=Path(__file__).resolve().parent


def build():
    v7=nbformat.read(HERE/'Spending_Model_Upload_V7_R3_Kaggle_Evidence.ipynb',as_version=4)
    cells={c.id:c.source for c in v7.cells}
    nodes=ast.parse(cells['v7-07']).body
    constants={n.targets[0].id:ast.literal_eval(n.value) for n in nodes
        if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','') in ('WORKER_SOURCE','IF_SOURCE')}
    runtime_names={'safe_json','write_json','digest','timed','assert_permitted','discover','load_manifest','load_cohort','restrict_history'}
    runtime_tree=ast.parse(cells['v7-04'])
    selected='\n\n'.join(('@contextmanager\n' if n.name=='timed' else '')+ast.get_source_segment(cells['v7-04'],n) for n in runtime_tree.body
        if isinstance(n,ast.FunctionDef) and n.name in runtime_names)
    experiment_tree=ast.parse(cells['v7-08'])
    anomaly=next(ast.get_source_segment(cells['v7-08'],n) for n in experiment_tree.body
        if isinstance(n,ast.FunctionDef) and n.name=='anomaly_pipeline')
    recovery=(HERE/'v7_recovery.py').read_text(encoding='utf-8')
    header='''import sys, json, hashlib, time, platform, importlib, importlib.metadata, zipfile
from pathlib import Path
from contextlib import contextmanager
from collections import defaultdict
from types import SimpleNamespace
import numpy as np
import pandas as pd
import joblib
RUN_FINAL_HOLDOUTS=False
ALLOWED_COHORTS=('train','validation','calibration')
TIMINGS=defaultdict(float)
ACCESSES=[]
'''
    setup='''# CPU-only. Keep the original R3 dataset attached; no LSTM training is run.
INPUT_ROOT=Path('/kaggle/input')
WORK_ROOT=Path('/kaggle/working')
SMOKE=False
FEATURE_WORKERS=2
RESUME_DIR=None  # restore only your own alert-review result folder
RESULTS=Path(RESUME_DIR) if RESUME_DIR else WORK_ROOT/('spendly_alert_review_'+time.strftime('%Y%m%d_%H%M%S'))
if RESUME_DIR:
    if not (RESULTS/'run_identity.json').is_file():
        raise ValueError('No alert-review recovery identity in this folder')
else:
    RESULTS.mkdir(parents=True,exist_ok=False)
'''
    source_cells=[header+recovery+'\n'+selected+'\n'+anomaly,setup]
    source_cells.append('WORKER_SOURCE='+repr(constants['WORKER_SOURCE'])+'\nIF_SOURCE='+repr(constants['IF_SOURCE'])+'''
MODULE_DIR=WORK_ROOT/'spendly_alert_review_modules'
MODULE_DIR.mkdir(exist_ok=True)
if str(MODULE_DIR) not in sys.path: sys.path.insert(0,str(MODULE_DIR))
WORKER_NAME='spendly_alert_worker_'+CODE_HASH[:12]
IF_NAME='spendly_alert_if_'+CODE_HASH[:12]
for name,source in [(WORKER_NAME,WORKER_SOURCE),(IF_NAME,IF_SOURCE)]:
    (MODULE_DIR/(name+'.py')).write_text(source,encoding='utf-8')
WORKER=importlib.import_module(WORKER_NAME)
IF_REFERENCE=importlib.import_module(IF_NAME)
''')
    source_cells.append('''DATASET=load_manifest(INPUT_ROOT)
if DATASET['version']!='spendly-synthetic-r3-v1':
    raise ValueError('Use original R3 for this reproduction, not a different dataset')
versions={n:importlib.metadata.version(n) for n in ('numpy','pandas','scikit-learn','joblib')}
identity=digest(dict(code=CODE_HASH,inputs={k:v['sha256'] for k,v in DATASET['cohorts'].items()},
    manifest=DATASET,mode='software_smoke' if SMOKE else 'full_development',versions=versions))
bind_run(RESULTS,identity)
lock=dict(protocol='v7-alert-reproduction-v1',code_hash=CODE_HASH,run_identity=identity,
    model='frozen V7 single IF plus diagnostic comparators',scope='reproduction, not recovered historical results',
    inputs={k:v['sha256'] for k,v in DATASET['cohorts'].items()},versions=versions,
    manifest=DATASET,
    execution_mode='software_smoke' if SMOKE else 'full_development')
lock_path=RESULTS/'configuration_lock.json'
if lock_path.exists():
    if json.loads(lock_path.read_text())!=lock: raise ValueError('Existing alert configuration differs')
else: atomic_json(lock_path,lock)
TRAIN_RAW=load_cohort('train',INPUT_ROOT,DATASET,WORKER,RESULTS)
END=TRAIN_RAW.observation_start.min()+pd.Timedelta(weeks=int(DATASET['weeks_per_user']*.77))
TRAIN=restrict_history(TRAIN_RAW,END)
split_record=dict(training_start=str(TRAIN.observation_start.min()),training_end=str(END),
    evaluation_start=str(END),weeks_per_user=DATASET['weeks_per_user'],run_identity=identity)
split_path=RESULTS/'data_split_manifest.json'
if split_path.exists():
    if json.loads(split_path.read_text())!=split_record: raise ValueError('Saved evaluation boundary differs')
else: atomic_json(split_path,split_record)
del TRAIN_RAW
CALIBRATION=load_cohort('calibration',INPUT_ROOT,DATASET,WORKER,RESULTS)
VALIDATION=load_cohort('validation',INPUT_ROOT,DATASET,WORKER,RESULTS)
if set(TRAIN.user_id)&set(VALIDATION.user_id): raise ValueError('Train/validation users overlap')
RUNNER=SimpleNamespace(data=TRAIN,worker=WORKER,directory=RESULTS,workers=FEATURE_WORKERS,
    smoke=SMOKE,code_hash=CODE_HASH,identity=identity,benchmark_role=DATASET['benchmark_role'])
''')
    source_cells.append('''OUTPUTS=['anomaly_metrics.csv','collective_protocol.json','anomaly_per_type_events.csv',
    'anomaly_alert_burden.json','isolation_forests.joblib','anomaly_protocol.json']
checkpoint_stage(RUNNER,'anomalies',lambda:anomaly_pipeline(RUNNER,CALIBRATION,VALIDATION,IF_REFERENCE),
    OUTPUTS,inputs=lock['inputs'])
print(pd.read_csv(RESULTS/'anomaly_metrics.csv').to_string(index=False))
print('Per-type and event results:')
print(pd.read_csv(RESULTS/'anomaly_per_type_events.csv').to_string(index=False))
write_json(RESULTS/'input_access_log.json',ACCESSES)
timing_path=RESULTS/('resume_timings_'+str(time.time_ns())+'.json') if (RESULTS/'timings.json').exists() else RESULTS/'timings.json'
write_json(timing_path,dict(seconds=dict(TIMINGS),scope='current process only; resumed completed stage is skipped'))
write_json(RESULTS/'artifact_manifest.json',dict(protocol='v7-alert-reproduction-v1',code_hash=CODE_HASH,
    files={p.relative_to(RESULTS).as_posix():recovery_hash(p) for p in RESULTS.rglob('*')
        if p.is_file() and p.name!='artifact_manifest.json'},
    execution_mode=lock['execution_mode'],evidence_eligible=not SMOKE,
    forecast_training=False,holdouts_accessed=False))
ARCHIVE=backup_run(RESULTS,'results')
print('ALERT REVIEW COMPLETE. Download this ZIP:',ARCHIVE)
''')
    digest=hashlib.sha256(('\n'.join(source_cells)+Path(__file__).read_text(encoding='utf-8')).encode()).hexdigest()
    source_cells[0]='CODE_HASH='+repr(digest)+'\n'+source_cells[0]
    intro='''# Spendly — reproduce V7 spending-alert results

The original V7 alert output was lost. This notebook repeats only its frozen
Isolation Forest and collective-rule comparisons. It does **not** train the LSTM
or claim to recover the original artifacts. Record these results as a new
reproduction on reused synthetic R3 development data.

## Run
1. Attach original R3 `manifest.json`, `train.csv/zip`, `validation.csv/zip`, and
   `calibration.csv/zip`. Attach only one dataset version.
2. CPU is sufficient; GPU can be disabled. Keep `SMOKE=False`, `FEATURE_WORKERS=2`.
3. Run All. Progress shows completed users and forest stages.
4. Download the printed `spendly_alert_review_*_results.zip` **and executed notebook**.

No new hyperparameter search or labels used as features. The same V7 architecture,
budgets, causal features and evaluation boundary are preserved. Library differences
can alter results; versions are recorded. Final/shifted cohorts are not loaded.
An incomplete anomaly stage restarts; a completed, verified stage can be reused by
setting `RESUME_DIR` to your own restored alert-review folder. V7/V8/V9 checkpoint
folders are not compatible. The previous full V7 anomaly stage took about42 minutes;
this is context, not a runtime guarantee. Save/download outputs before leaving.

The collective approach is credited to PR #3. Its usefulness must be assessed
against false alerts, per-type support, event recall and daily alert burden.
Alerts are unusual-spending signals, not fraud findings. No app model is activated.
'''
    cells_out=[nbformat.v4.new_markdown_cell(intro)]+[nbformat.v4.new_code_cell(s) for s in source_cells]
    for i,c in enumerate(cells_out):
        c.id=f'alerts-{i}'
        if c.cell_type=='code':compile(c.source,c.id,'exec')
    result=nbformat.v4.new_notebook(cells=cells_out,metadata=dict(kernelspec=dict(name='python3',display_name='Python 3',language='python'),
        spendly=dict(protocol='v7-alert-reproduction-v1',code_hash=digest)))
    nbformat.validate(result)
    output=HERE/'Spending_Alerts_Review_Kaggle.ipynb'
    output.write_text(nbformat.writes(result),encoding='utf-8')
    print(output)


if __name__=='__main__':build()
