"""Build V7 from the supplied executed V6, without executing or editing that source."""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
import nbformat

HERE=Path(__file__).resolve().parent
OUTPUT=HERE/'Spending_Model_Upload_V7_R3_Kaggle_Evidence.ipynb'


def source(cell):
    return ''.join(cell.get('source',''))


def selected_definitions(code,names):
    tree=ast.parse(code)
    return '\n\n'.join(ast.get_source_segment(code,n) for n in tree.body
        if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names)


def generalized_forecast(code, fast):
    old='forecast_features_fast' if fast else 'forecast_features_v5'
    name='forecast_fast_config' if fast else 'forecast_reference_config'
    text=selected_definitions(code,{old})
    text=text.replace(f"def {old}(data, variant='pooled'):",f"def {name}(data, lookback, variant='pooled'):")
    # Restrict changes to lookback-dependent shape operations. Recurrence search
    # remains26 weeks; the 4-week summaries and scale definition remain unchanged.
    text=text.replace('len(boundaries)<10','len(boundaries)<lookback+2').replace('len(boundaries) < 10','len(boundaries) < lookback+2')
    for a,b in [('range(8,','range(lookback,'),('i-8','i-lookback'),('i - 8','i - lookback'),
                ('minlength=8','minlength=lookback'),('columns=V5_F_FEATURES','columns=feature_columns(lookback)')]:
        text=text.replace(a,b)
    return text


def historical_audit(nb,v5_path):
    text='\n'.join(''.join(o.get('text','')) for c in nb.cells for o in c.get('outputs',[]) if 'text' in o)
    handoff=json.loads(text.split('SPENDLY_R3_RESULT_START')[1].split('SPENDLY_R3_RESULT_END')[0])
    if handoff.get('final_results'):
        raise ValueError('Source contains final results; do not import them into this development notebook')
    forecasts=handoff['forecast_validation']
    selected=min([r for r in forecasts if r['model'].startswith('lstm')],key=lambda r:r['selection_objective'])
    baseline=min([r for r in forecasts if not r['model'].startswith('lstm')],key=lambda r:r['selection_objective'])
    assert selected['model']=='lstm_0' and selected['rows']==3600 and selected['weeks']==36
    assert abs(selected['WAPE']-.3449432034526241)<1e-10
    # Independent algebraic checks of reported aggregate metrics. Raw prediction
    # re-scoring is not possible without the corresponding V6 row-level archive.
    for r in forecasts:
        assert abs(r['MAE_KES']/r['actual_mean_KES']-r['WAPE'])<1e-10
        assert abs(r['predicted_mean_KES']-r['actual_mean_KES']-r['bias_KES'])<1e-8
    comparison=lambda a,b:dict(WAPE_improvement_pp=100*(b['WAPE']-a['WAPE']),
        WAPE_relative_improvement_percent=100*(b['WAPE']-a['WAPE'])/b['WAPE'],
        MAE_improvement_KES=b['MAE_KES']-a['MAE_KES'],R2_change=a['R2']-b['R2'],
        bias_change_KES=a['bias_KES']-b['bias_KES'],within20_change_pp=100*(a['within_20_percent']-b['within_20_percent']),
        worst_block_improvement_pp=100*(b['worst_block_WAPE']-a['worst_block_WAPE']))
    import csv
    v5=list(csv.DictReader(v5_path.open()))
    v5=min([r for r in v5 if r['model'].startswith('lstm')],key=lambda r:float(r['selection_objective']))
    v5={k:float(v) if k not in ('model','spec','WAPE_goal_met','within_20_goal_met') and v else v for k,v in v5.items()}
    cells=[]
    for i,c in enumerate(nb.cells):
        code=source(c)
        if c.cell_type=='code':
            compile(code,f'V6 cell {i}','exec')
        cells.append(dict(index=i,id=c.get('id'),type=c.cell_type,source_sha256=hashlib.sha256(code.encode()).hexdigest(),
            functions=[n.name for n in ast.walk(ast.parse(code)) if isinstance(n,ast.FunctionDef)] if c.cell_type=='code' else [],
            outputs=len(c.get('outputs',[]))))
    curves=[]
    pattern=r'loss: ([0-9.e+-]+) - val_loss: ([0-9.e+-]+) - val_weighted_mae: ([0-9.e+-]+) - weighted_mae: ([0-9.e+-]+)'
    for match in re.finditer(pattern,text):
        curves.append(list(map(float,match.groups())))
    return dict(source='executed V6 historical evidence, not V7 results',run_id=handoff['run_id'],
        selected=selected,strongest_baseline=baseline,vs_baseline=comparison(selected,baseline),
        selected_v5=v5,vs_v5=comparison(selected,v5),bias_percent=100*selected['bias_KES']/selected['actual_mean_KES'],
        fixed_vs_plateau_pp={r['model']:100*(r['WAPE']-selected['WAPE']) for r in forecasts if r['model'].startswith('lstm')},
        forecast_table=forecasts,cell_inventory=cells,learning_curve_recorded_points=len(curves),
        recorded_curve_first=curves[0],recorded_curve_selected_last=curves[119],
        verification='Source JSON matches printed table; MAE/WAPE/mean/bias identities checked. No V6 row-level predictions supplied for independent rescoring.',
        centering_finding='No mismatch: train target (y-recurring)/scale and prediction residual*scale+recurring both use recurring mean.',
        interpretation=['approximately0.65 WAPE percentage points over recurring median; R2 and bias slightly worse',
            'V5 improvement extremely small; fixed/plateau differences around0.1pp may reflect seed/sampling variation',
            'systematic underprediction demonstrated; underfitting not established by signed bias',
            'no severe classical train-improves/validation-diverges pattern in recorded curves',
            'selected epoch120 equals cap: stopping point not conclusively established',
            'validation cohort influenced V5/V6: reused development benchmark'],
        final_status='source recorded FINAL TEST NOT RUN; no final results imported')


def build(source_path,pdf_path=None,audit_path=None):
    original=source_path.read_bytes()
    nb=nbformat.reads(original.decode(),as_version=4)
    cells={c.id:source(c) for c in nb.cells}
    if audit_path is not None:
        audit=json.loads(audit_path.read_text(encoding='utf-8'))
        inventory=audit['cell_inventory']
        if len(inventory)!=len(nb.cells):
            raise ValueError('V6 source differs from audited cell inventory')
        for cell,entry in zip(nb.cells,inventory):
            if (cell.id!=entry['id'] or cell.cell_type!=entry['type'] or
                    hashlib.sha256(source(cell).encode()).hexdigest()!=entry['source_sha256']):
                raise ValueError('V6 source cell differs from recorded audit: '+cell.id)
        if audit['final_status']!='source recorded FINAL TEST NOT RUN; no final results imported':
            raise ValueError('Expected development-only V6 audit')
    else:
        if pdf_path is None:
            raise ValueError('Supply --guidance with an executed source, or use --audit')
        audit=historical_audit(nb,HERE/'evidence/colab_abf57185_review_checked/forecast_validation.csv')
        audit['source_sha256']=hashlib.sha256(original).hexdigest()
        audit['guidance_pdf_sha256']=hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    worker_node=ast.parse(cells['v6-worker-setup'])
    embedded=next(ast.literal_eval(n.value) for n in worker_node.body if isinstance(n,ast.Assign)
                  and any(isinstance(t,ast.Name) and t.id=='worker_source' for t in n.targets))
    # Preserve every audited original helper required for parity and IF, but remove
    # V6 shard writer. V7 uses its own fully configuration-keyed numeric cache.
    tree=ast.parse(embedded)
    embedded='\n\n'.join(ast.get_source_segment(embedded,n) for n in tree.body
        if not isinstance(n,ast.FunctionDef) or n.name!='worker_shard')
    worker=embedded+'\n\n'+selected_definitions(cells['forecast-functions'],{'infer_schedule','schedule_features','forecast_features_v5'})
    worker+='\n\n'+(HERE/'v7_features.py').read_text(encoding='utf-8')
    collective=(HERE/'v7_collective.py').read_text(encoding='utf-8')
    worker+='\n\n'+collective
    worker+='\n\n'+generalized_forecast(embedded,True)+'\n\n'+generalized_forecast(cells['forecast-functions'],False)
    worker+='''

def anomaly_bundle(data):
    x=anomaly_features_fast(data).join(rhythm_features(data)).join(collective_features(data))
    a=data[['user_id','transaction_id','transaction_timestamp','label','event_id','family']].rename(columns={'transaction_timestamp':'time'})
    return a,x
'''
    ref='''import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_recall_curve, average_precision_score, roc_auc_score
GOAL=.80
'''
    ref+=selected_definitions(cells['rhythm-features'],{'rhythm_views'})+'\nRHythm_PLACEHOLDER\n'
    ref=ref.replace('RHythm_PLACEHOLDER',"RHYTHM_FEATURES=['day_count_excess','week_count_excess','gap_compression','recurring_increase','recurring_known']")
    ref+='\n\n'+selected_definitions(cells['metrics-helpers'],{'classification_metrics'})
    ref+='\n\n'+selected_definitions(cells['calibration'],{'false_positive_floor','fpr_capped_threshold'})
    ref+='\n\n'+selected_definitions(cells['colab-r3-workflow'],{'event_contained','forest_score','fit_forest','calibrate_forest'})
    ref+='\n\n'+collective
    runtime=(HERE/'v7_recovery.py').read_text(encoding='utf-8')+'\n\n'+(HERE/'v7_runtime.py').read_text(encoding='utf-8')
    experiments=(HERE/'v7_experiments.py').read_text(encoding='utf-8')
    code_hash=hashlib.sha256((worker+ref+runtime+experiments+cells['recommendation-rules']).encode()).hexdigest()
    audit['v7_code_hash']=code_hash
    doc=(HERE/'V7_NOTEBOOK_TEXT.md').read_text(encoding='utf-8').split('\n<!-- CELL -->\n')
    out=[]
    def md(s): out.append(nbformat.v4.new_markdown_cell(s))
    def py(s): out.append(nbformat.v4.new_code_cell(s))
    md(doc[0]); md(doc[1])
    py('V6_AUDIT = '+repr(audit)+"\nprint('Historical V6 comparison:', V6_AUDIT['vs_baseline'])\nprint('Historical V5 comparison:',V6_AUDIT['vs_v5'])")
    md(doc[2]); py(runtime)
    py('''# Edit input root only for a local software fixture; Kaggle discovers attached permitted inputs.
INPUT_ROOT = Path('/kaggle/input')
WORK_ROOT = Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()
REQUIRE_GPU = True
SMOKE = False  # software verification only; never evidence of predictive performance
FEATURE_WORKERS = 2
RESUME_DIR = None  # absolute path to YOUR restored trusted result folder, otherwise new run
RESULTS = Path(RESUME_DIR) if RESUME_DIR else WORK_ROOT / ('spendly_v7_evidence_' + time.strftime('%Y%m%d_%H%M%S'))
if RESUME_DIR:
    if not (RESULTS/'run_identity.json').is_file():
        raise ValueError('Resume requires a saved recovery-enabled result folder')
else:
    RESULTS.mkdir(parents=True, exist_ok=False)
CACHE = WORK_ROOT / 'spendly_v7_feature_cache'
ATTEMPT = WORK_ROOT / ('spendly_v7_resume_attempt_' + str(time.time_ns())) if RESUME_DIR else RESULTS
if RESUME_DIR:
    ATTEMPT.mkdir(exist_ok=False)
write_json(ATTEMPT/'v6_audit.json',V6_AUDIT)
GPU = gpu_preflight(ATTEMPT, REQUIRE_GPU)
''')
    md(doc[3])
    py('WORKER_SOURCE = '+repr(worker)+'\nIF_SOURCE = '+repr(ref)+'\nCODE_HASH = '+repr(code_hash)+'''
import importlib
MODULE_DIR=WORK_ROOT/'spendly_v7_modules'
MODULE_DIR.mkdir(exist_ok=True)
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0,str(MODULE_DIR))
WORKER_NAME='spendly_v7_worker_'+CODE_HASH[:12]
IF_NAME='spendly_v7_if_'+CODE_HASH[:12]
(MODULE_DIR/(WORKER_NAME+'.py')).write_text(WORKER_SOURCE,encoding='utf-8')
(MODULE_DIR/(IF_NAME+'.py')).write_text(IF_SOURCE,encoding='utf-8')
WORKER=importlib.import_module(WORKER_NAME)
IF_REFERENCE=importlib.import_module(IF_NAME)
''')
    py(experiments)
    md(doc[4])
    py('''DATASET=load_manifest(INPUT_ROOT)
TRAIN_RAW=load_cohort('train',INPUT_ROOT,DATASET,WORKER,RESULTS)
ORIGIN=TRAIN_RAW.observation_start.min()
TRAIN_END=ORIGIN+pd.Timedelta(weeks=int(DATASET['weeks_per_user']*.77))
TRAIN=restrict_history(TRAIN_RAW,TRAIN_END)
del TRAIN_RAW
PARITY=WORKER.check_causal_parity(TRAIN)
write_json(ATTEMPT/'causal_parity_tests.json',PARITY)
RUNNER=ExperimentRunner(TRAIN,WORKER,RESULTS,CACHE,CODE_HASH,GPU['selected_training_device'],FEATURE_WORKERS,SMOKE,DATASET['benchmark_role'])
# No raw IDs in report; complete-user lists are pseudonymized in the split manifest.
split_folds=[]
for fold in RUNNER.folds:
    split_folds.append({k:([hashlib.sha256(('V7-export:'+u).encode()).hexdigest()[:20] for u in v]
        if k.endswith('users') else v) for k,v in fold.items()})
write_json(ATTEMPT/'data_split_manifest.json',dict(permitted_cohorts=DATASET['cohorts'],folds=split_folds,
    train_target_end=str(TRAIN_END),minimum_common_history_weeks=26,
    history_policy='Held-out users supply only history strictly earlier than each target. No held-out-user rows fit parameters/scalers/vocabulary.',
    vocabulary_policy='fit users before inner cutoff; frozen through fold refit',
    benchmark_role=DATASET['benchmark_role'],dataset_version=DATASET['version'],related_observations='overlapping weekly windows clustered by user'))
if RESUME_DIR:
    import shutil
    RESUME_ATTEMPT_ID=ATTEMPT.name
    shutil.copytree(ATTEMPT,RESULTS/'resume_attempts'/RESUME_ATTEMPT_ID)
''')
    md(doc[5]); py('CANDIDATES, STAGE_RESULTS, DECISION = stage_experiments(RUNNER)\nprint(DECISION)')
    md(doc[6]); py("checkpoint_stage(RUNNER,'diagnostics',lambda:diagnostics(RUNNER,CANDIDATES,DECISION),\n    ['memorization_diagnostic.json','epoch_cap_sensitivity.json','diagnostic_interpretation.json'])\nbackup_run(RESULTS,'diagnostics_complete')")
    md(doc[7]); py('''FITS, LOCK_HASH=lock_and_refit(RUNNER,CANDIDATES,DECISION)
VALIDATION=load_cohort('validation',INPUT_ROOT,DATASET,WORKER,RESULTS)
LEGACY_ROWS, LEGACY_METRICS=evaluate_legacy(RUNNER,FITS,DECISION,VALIDATION,LOCK_HASH)
print(DATASET['benchmark_role'] + ' (locked, no retuning):')
print(pd.DataFrame(LEGACY_METRICS).to_string(index=False))
''')
    md(doc[8]); py('''CALIBRATION=load_cohort('calibration',INPUT_ROOT,DATASET,WORKER,RESULTS)
checkpoint_stage(RUNNER,'anomalies',lambda:anomaly_pipeline(RUNNER,CALIBRATION,VALIDATION,IF_REFERENCE),
    ['anomaly_metrics.csv','collective_protocol.json','anomaly_per_type_events.csv',
     'anomaly_alert_burden.json','isolation_forests.joblib','anomaly_protocol.json'],
    inputs={k:DATASET['cohorts'][k]['sha256'] for k in ('calibration','validation')})
backup_run(RESULTS,'anomalies_complete')
''')
    py(cells['recommendation-rules'])
    py('''# Existing deterministic rules, unchanged. Synthetic demonstration is not user evidence.
demo=RecommendationContext(history_periods=26,forecasted_spending=6000.,budget_amount=5000.,unusual_spending_detected=True)
write_json(RESULTS/'recommendation_demo.json',[r.to_dict() for r in RecommendationEngine().evaluate(demo)])
''')
    md(doc[9]); py('''write_figures(RUNNER,LEGACY_ROWS,LEGACY_METRICS,DECISION)
write_json(RESULTS/'data_composition.json',ACCESSES)
ARCHIVE=package_results(RESULTS,CODE_HASH)
print('Download the existing ZIP and executed notebook from Kaggle Output.')
''')
    md(doc[10]); py("assert RUN_FINAL_HOLDOUTS is False\nprint('LOCKED: no final or shifted-test loader/evaluator exists in V7.')")
    new=nbformat.v4.new_notebook(cells=out,metadata=dict(kernelspec=dict(name='python3',language='python',display_name='Python 3'),
        language_info=dict(name='python',version='3.12'),spendly=dict(protocol='v7-evidence-v1',source_sha256=audit['source_sha256'],code_hash=code_hash)))
    for i,c in enumerate(new.cells):
        c.id=f'v7-{i:02d}'
        if c.cell_type=='code': compile(c.source,f'V7 cell {i}','exec')
    nbformat.validate(new)
    OUTPUT.write_text(nbformat.writes(new),encoding='utf-8')
    write=HERE/'evidence/v7_source_audit/v6_verified_audit.json'
    write.write_text(json.dumps(audit,indent=2),encoding='utf-8')
    assert source_path.read_bytes()==original, 'Original V6 changed'
    print(f'Created {OUTPUT.name}: {len(new.cells)} cells; nbformat and Python compilation passed')
    print(json.dumps(dict(vs_baseline=audit['vs_baseline'],vs_v5=audit['vs_v5'],bias_percent=audit['bias_percent']),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=HERE/'Spending_Model_Upload_V6_R3_Kaggle.ipynb')
    parser.add_argument('--guidance',type=Path)
    parser.add_argument('--audit',type=Path,help='Reuse recorded historical audit after verifying every source-cell hash')
    args=parser.parse_args()
    build(args.source,args.guidance,args.audit)
