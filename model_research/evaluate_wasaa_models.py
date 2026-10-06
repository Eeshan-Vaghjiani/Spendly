"""Frozen CPU transfer evaluation on a hash-pinned synthetic Wasaa snapshot.

Explicit scenarios rather than claiming unknown category/merchant equivalence.
No fit, thresholds, calibration, candidate search or upstream requests.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

import numpy as np
import pandas as pd

SPEND_SHA = 'ce7d857048c6ede0844e33084ad0358011a619ee962406b7a367c104126741da'
BUDGET_SHA = '78673fe0dd5b0786c015ede22ad6d0029a760330dc5dd572fda6e2af50f87cac'
WEIGHTS_SHA = '6fcf6b12c5c0c00ad5057c126e2054588858b5b5bba10d6f10417ea6bf146538'
MAP = {'Groceries':'Food', 'Medical':'Healthcare', 'School Fees':'Education',
       'Entertainment':'Entertainment', 'Rent':'Rent', 'Transport':'Transport', 'Utilities':'Utilities'}
PROTOCOL = {
    'id':'wasaa-frozen-transfer-v1', 'synthetic':True, 'training':'none',
    'history_start':'2025-04-07', 'evaluation_start':'2026-07-06', 'evaluation_end_exclusive':'2026-09-28',
    'timezone':'Africa/Nairobi', 'coverage':'assume internal snapshot weeks fully recorded; exclude first/last partial weeks',
    'scenarios':{'consumption':'all categories except Savings', 'all_outflows':'all categories including Savings',
                 'mapped_subset':'only seven mapped categories; both LSTMs scored on these identical targets'},
    'category_mapping':MAP, 'excluded_from_category_model':['Savings','Household Help','Airtime and Data'],
    'merchant':'empty string activates retained missing-merchant behavior; not fabricated merchant identity',
    'anomaly_labels':'unavailable; precision/recall/F1/AP/AUC not estimable',
    'budget_analysis':'retrospective association only; over-budget is not anomaly ground truth',
    'comparison':'report all scenarios; no changes after results; same fixed twelve weekly targets per household',
    'primary_forecast_metrics':['WAPE','MAE_KES','RMSE_KES','R2','bias_KES','within20'],
    'threshold':'original portable IF threshold 0.6451359189730762',
}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_aligned(directory):
    """Load only reviewed feature and portable inference sources, no app startup."""
    name = '_wasaa_frozen_aligned'
    package = types.ModuleType(name); package.__path__ = [str(directory)]
    sys.modules[name] = package
    result = []
    for part in ('features','portable'):
        spec = importlib.util.spec_from_file_location(name+'.'+part, Path(directory)/(part+'.py'))
        module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module
        spec.loader.exec_module(module); result.append(module)
    return result


def metric(actual, prediction):
    y, p = np.asarray(actual,float), np.asarray(prediction,float)
    if len(y)==0 or y.shape!=p.shape or not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError('Invalid forecast arrays')
    error = p-y; denominator = y.sum(); variance = ((y-y.mean())**2).sum()
    return dict(rows=len(y), WAPE=float(abs(error).sum()/denominator) if denominator else None,
                MAE_KES=float(abs(error).mean()), RMSE_KES=float(np.sqrt((error**2).mean())),
                R2=float(1-(error**2).sum()/variance) if variance else None,
                bias_KES=float(error.mean()), within20=float((abs(error)<=np.where(y>0,.2*y,1e-9)).mean()))


def adapt(spending):
    result = spending.rename(columns={'spending_record_id':'transaction_id','user_profile_id':'user_id',
        'amount_kes':'amount','transaction_date':'transaction_timestamp'}).copy()
    result['transaction_timestamp'] = pd.to_datetime(result.transaction_timestamp,utc=True).dt.tz_convert('Africa/Nairobi').dt.tz_localize(None)
    result['merchant'] = ''
    result['transaction_type'] = 'expense'
    return result.sort_values(['user_id','transaction_timestamp','transaction_id']).reset_index(drop=True)


def category_panel(data, owner, start, end, categories):
    weeks = pd.date_range(start,end-pd.Timedelta(weeks=1),freq='7D')
    x = data.copy()
    x['week'] = x.transaction_timestamp.dt.to_period('W-SUN').dt.start_time
    panel = pd.DataFrame({'user_id':owner,'week':weeks})
    for i, category in enumerate(categories):
        g = x.loc[x.category.eq(category)].groupby('week').amount
        panel[f'spend_{i}'] = g.sum().reindex(weeks,fill_value=0).to_numpy()
        panel[f'count_{i}'] = g.size().reindex(weeks,fill_value=0).to_numpy()
    panel['total_spend'] = panel[[f'spend_{i}' for i in range(len(categories))]].sum(axis=1)
    panel['total_count'] = panel[[f'count_{i}' for i in range(len(categories))]].sum(axis=1)
    return panel


def run(args):
    output = Path(args.output)
    if output.exists(): raise FileExistsError('Use a new output directory; preserve prior evidence')
    snapshot, aligned = Path(args.snapshot), Path(args.aligned_source)
    if sha(snapshot/'spending_records.csv')!=SPEND_SHA or sha(snapshot/'budget_categories.csv')!=BUDGET_SHA:
        raise ValueError('Snapshot differs from locked inputs')
    if sha(Path(args.portable_bundle)/'weights.npz')!=WEIGHTS_SHA:
        raise ValueError('Wrong retained model')
    source_paths=[aligned/'features.py',aligned/'portable.py',Path(__file__)]
    source_paths += [Path(args.category_source)/n for n in ('category_lstm_frozen.py','category_lstm_features.py')]
    identity = {'protocol':PROTOCOL,'sources':{str(p.name):sha(p) for p in source_paths},
                'inputs':{'spending':SPEND_SHA,'budgets':BUDGET_SHA},'portable_weights':WEIGHTS_SHA}
    if args.lock_only:
        output.mkdir()
        (output/'protocol.json').write_text(json.dumps(identity,indent=2),encoding='utf-8')
        return
    if not args.lock or json.loads(Path(args.lock).read_text())!=identity:
        raise ValueError('Explicit unchanged pre-run lock required')
    output.mkdir()
    (output/'protocol.json').write_text(json.dumps(identity,indent=2),encoding='utf-8')
    feature, portable = load_aligned(aligned)
    reference = portable.PortableSelectedModel(args.portable_bundle)
    sys.path.insert(0,str(args.category_source))
    from category_lstm_frozen import FrozenCategoryLSTM, CATEGORIES, FEATURES
    from category_lstm_features import add_model_features
    candidate = FrozenCategoryLSTM(args.category_bundle,trusted=True)
    spending=pd.read_csv(snapshot/'spending_records.csv'); budgets=pd.read_csv(snapshot/'budget_categories.csv')
    data=adapt(spending)
    history_start=pd.Timestamp(PROTOCOL['history_start']); end=pd.Timestamp(PROTOCOL['evaluation_end_exclusive'])
    origins=pd.date_range(PROTOCOL['evaluation_start'],end-pd.Timedelta(weeks=1),freq='7D')
    data=data.loc[data.transaction_timestamp.ge(history_start)&data.transaction_timestamp.lt(end)].copy()
    rows=[]; alert_rows=[]; category_rows=[]
    checkpoint=output/'household_checkpoints'; checkpoint.mkdir()
    for number,(owner,household) in enumerate(data.groupby('user_id',sort=True),1):
        starts=(len(rows),len(alert_rows),len(category_rows))
        scoped={'consumption':household.loc[household.category.ne('Savings')].copy(),
                'all_outflows':household.copy(), 'mapped_subset':household.loc[household.category.isin(MAP)].copy()}
        for scenario, frame in scoped.items():
            if scenario=='mapped_subset': frame['category']=frame.category.map(MAP)
            matrices=[]; contexts=[]
            for origin in origins:
                past=frame.loc[frame.transaction_timestamp.lt(origin)].copy()
                context,values=feature.next_week_features(past[['user_id','transaction_id','transaction_timestamp','amount','category','merchant']],
                    origin,observed_from=history_start,observed_through=origin)
                matrices.append(values); contexts.append(context)
            contexts=pd.concat(contexts,ignore_index=True); matrices=pd.concat(matrices,ignore_index=True)
            predicted=reference.predict_features(matrices,contexts.scale,contexts.recurring)
            for i,origin in enumerate(origins):
                actual=frame.loc[frame.transaction_timestamp.ge(origin)&frame.transaction_timestamp.lt(origin+pd.Timedelta(weeks=1)),'amount'].sum()
                prev=frame.loc[frame.transaction_timestamp.ge(origin-pd.Timedelta(weeks=1))&frame.transaction_timestamp.lt(origin),'amount'].sum()
                rows.append(dict(user_id=owner,target_week=str(origin.date()),scenario=scenario,model='retained_lstm',actual=float(actual),prediction=float(predicted[i]),last_week=float(prev)))
            if scenario=='mapped_subset':
                panel=category_panel(frame,owner,history_start,end,CATEGORIES)
                feats,cols=add_model_features(panel)
                assert cols==FEATURES
                tensors=[]; targets=[]
                for origin in origins:
                    pos=int(np.flatnonzero(panel.week.eq(origin))[0])
                    tensors.append(candidate.x_scaler.transform(feats[FEATURES].iloc[pos-26:pos].to_numpy(np.float32)).astype(np.float32))
                    targets.append(panel.loc[pos,[f'spend_{i}' for i in range(9)]].to_numpy(float))
                predictions=candidate.predict_tensor(np.stack(tensors))
                # All nine outputs contribute to total; spurious absent-category predictions count as error.
                for i,origin in enumerate(origins):
                    rows.append(dict(user_id=owner,target_week=str(origin.date()),scenario=scenario,model='category_lstm',
                        actual=float(sum(targets[i])),prediction=float(predictions[i].astype(float).sum()),last_week=None))
                    for c,cat in enumerate(CATEGORIES):
                        category_rows.append(dict(user_id=owner,target_week=str(origin.date()),category=cat,actual=float(targets[i][c]),prediction=float(predictions[i][c])))
            if scenario=='consumption':
                features=feature.anomaly_features(frame[['user_id','transaction_id','transaction_timestamp','amount','category','merchant']])
                mask=frame.transaction_timestamp.ge(origins[0])
                selected=frame.loc[mask]
                scores=reference.anomaly_scores(features.loc[mask])
                for (_,r),score in zip(selected.iterrows(),scores):
                    alert_rows.append(dict(transaction_id=r.transaction_id,user_id=owner,budget_category_id=r.budget_category_id,
                        category=r.category,score=float(score),flag=bool(score>=reference.threshold)))
        pd.DataFrame(rows[starts[0]:]).to_csv(checkpoint/f'{number:04d}_forecasts.csv',index=False)
        pd.DataFrame(alert_rows[starts[1]:]).to_csv(checkpoint/f'{number:04d}_alerts.csv',index=False)
        pd.DataFrame(category_rows[starts[2]:]).to_csv(checkpoint/f'{number:04d}_categories.csv',index=False)
        if number%25==0: print(f'Completed {number}/500 households',flush=True)
    forecasts=pd.DataFrame(rows); alerts=pd.DataFrame(alert_rows); cats=pd.DataFrame(category_rows)
    forecasts.to_csv(output/'forecasts.csv',index=False); alerts.to_csv(output/'alerts.csv',index=False); cats.to_csv(output/'categories.csv',index=False)
    results={}
    for (scenario,model),g in forecasts.groupby(['scenario','model']):
        results[f'{scenario}/{model}']=metric(g.actual,g.prediction)
        if model=='retained_lstm': results[f'{scenario}/last_week']=metric(g.actual,g.last_week)
    joined=alerts.merge(budgets[['budget_category_id','allocated_kes','actual_kes']],on='budget_category_id',validate='many_to_one')
    joined['over_budget']=joined.actual_kes>joined.allocated_kes
    alert_summary={'rows':len(alerts),'alerts':int(alerts.flag.sum()),'alert_rate':float(alerts.flag.mean()),
        'households_alerted':int(alerts.loc[alerts.flag,'user_id'].nunique()),'threshold':reference.threshold,
        'precision':None,'recall':None,'F1':None,'reason':'no independent anomaly labels',
        'over_budget_association':{str(k):{'rows':len(g),'alert_rate':float(g.flag.mean())} for k,g in joined.groupby('over_budget')}}
    evaluation=data.loc[data.transaction_timestamp.ge(origins[0])]
    included=evaluation.category.isin(MAP)
    coverage={'evaluation_records':len(evaluation),'mapped_records':int(included.sum()),
        'mapped_amount_share_all_outflows':float(evaluation.loc[included,'amount'].sum()/evaluation.amount.sum()),
        'excluded_amount_by_category':evaluation.loc[~included].groupby('category').amount.sum().to_dict()}
    report={'protocol':PROTOCOL,'forecast_metrics':results,'category_metrics':{k:metric(g.actual,g.prediction) for k,g in cats.groupby('category')},
        'alerts':alert_summary,'coverage':coverage,'runtime_versions':candidate.versions,
        'category_artifacts':candidate.metadata['selected_config'],'training_performed':False}
    (output/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    (output/'hashes.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('snapshot','aligned-source','portable-bundle','category-source','category-bundle','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--lock',type=Path);p.add_argument('--lock-only',action='store_true')
    run(p.parse_args())
