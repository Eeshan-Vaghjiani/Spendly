"""Attribute saved forecast errors using only the hash-verified R3 train cohort.

Scenario labels and bill categories are descriptive diagnostics, never model
inputs or grounds to exclude difficult weeks from the reported evaluation.
No models, pickle files, validation CSVs or final/shifted datasets are loaded.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

BILL_CATEGORIES = ('Rent', 'Utilities', 'Subscriptions')
KEYS = ['user_id', 'target_week']


def hash_file(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for part in iter(lambda: handle.read(1024*1024), b''):
            result.update(part)
    return result.hexdigest()


def aggregate_weeks(raw, cutoff):
    required = {'user_id','transaction_id','transaction_timestamp','transaction_type',
                'amount','category','is_anomaly','anomaly_type'}
    if not required <= set(raw):
        raise ValueError('Missing diagnostic columns')
    frame = raw.copy()
    frame['time'] = pd.to_datetime(frame.transaction_timestamp, utc=True).dt.tz_convert('Africa/Nairobi').dt.tz_localize(None)
    frame = frame.loc[frame.time.lt(pd.Timestamp(cutoff)) & frame.transaction_type.eq('expense')].copy()
    if not frame.is_anomaly.isin([0,1]).all():
        raise ValueError('Explicit binary scenario labels required')
    if not np.isfinite(frame.amount).all() or frame.amount.lt(0).any():
        raise ValueError('Invalid spending amounts')
    frame['target_week'] = frame.time.dt.normalize()-pd.to_timedelta(frame.time.dt.weekday,unit='D')
    frame['user_id'] = frame.user_id.astype(str).map(lambda u:hashlib.sha256(('V7-export:'+u).encode()).hexdigest()[:20])
    injected = frame.is_anomaly.eq(1)
    bill = frame.category.isin(BILL_CATEGORIES)
    frame['injected_spend'] = frame.amount.where(injected,0.)
    frame['ordinary_spend'] = frame.amount.where(~injected,0.)
    frame['bill_spend'] = frame.amount.where(bill,0.)
    frame['ordinary_bill_spend'] = frame.amount.where(bill & ~injected,0.)
    frame['ordinary_nonbill_spend'] = frame.amount.where(~bill & ~injected,0.)
    frame['injected_transactions'] = injected.astype(int)
    for family in ('large','burst','duplicate','recurring_increase','split'):
        frame['scenario_'+family] = frame.amount.where(injected & frame.anomaly_type.eq(family),0.)
    sums = ['amount','injected_spend','ordinary_spend','bill_spend','ordinary_bill_spend',
            'ordinary_nonbill_spend','injected_transactions']+[c for c in frame if c.startswith('scenario_')]
    return frame.groupby(KEYS)[sums].sum().reset_index()


def average_predictions(predictions, cutoff):
    reference=predictions[0][KEYS+['fold','actual','recurring','recurring_median','recurring_share']].copy()
    for p in predictions:
        if p.duplicated(KEYS).any(): raise ValueError('Duplicate prediction windows')
        if not np.isfinite(p[['actual','prediction']].to_numpy(float)).all():
            raise ValueError('Nonfinite saved predictions')
        times=pd.to_datetime(p.target_week)
        if not (times+pd.Timedelta(weeks=1)).le(pd.Timestamp(cutoff)).all():
            raise ValueError('Prediction target extends beyond permitted training history')
        if not times.dt.weekday.eq(0).all() or not times.eq(times.dt.normalize()).all():
            raise ValueError('Expected completed Monday-week targets')
    for index,p in enumerate(predictions):
        incoming=p[KEYS+['fold','actual','prediction']].rename(columns={'fold':f'fold_{index}',
            'actual':f'actual_{index}','prediction':f'prediction_{index}'})
        reference=reference.merge(incoming,on=KEYS,how='outer',validate='one_to_one',indicator=True)
        if not reference['_merge'].eq('both').all():raise ValueError('Seed prediction windows differ')
        reference=reference.drop(columns='_merge')
        np.testing.assert_array_equal(reference.fold,reference[f'fold_{index}'])
        np.testing.assert_allclose(reference.actual,reference[f'actual_{index}'])
    reference['prediction']=reference[[f'prediction_{i}' for i in range(len(predictions))]].mean(axis=1)
    return reference


def join_predictions(predictions, weekly):
    if predictions.duplicated(KEYS).any() or weekly.duplicated(KEYS).any():
        raise ValueError('Duplicate user/week rows')
    joined = predictions.merge(weekly,on=KEYS,how='left',validate='one_to_one')
    for col in weekly.columns.difference(KEYS):
        joined[col] = pd.to_numeric(joined[col]).fillna(0.)
    if not np.allclose(joined.actual,joined.amount,atol=.01,rtol=0):
        raise ValueError('Saved targets do not match hash-verified expense weeks')
    joined['error'] = joined.prediction-joined.actual
    joined['absolute_error'] = joined.error.abs()
    return joined


def summarize(frame, total_error):
    actual = float(frame.actual.sum()); error = float(frame.absolute_error.sum())
    if frame.empty:
        return dict(rows=0)
    return dict(rows=len(frame),users=frame.user_id.nunique(),
        WAPE=error/actual if actual else None,MAE_KES=error/len(frame),
        recurring_median_WAPE=float(np.abs(frame.recurring_median-frame.actual).sum()/actual) if actual else None,
        bias_KES=float(frame.error.mean()),share_total_error=error/total_error,
        actual_spend=actual,injected_spend=float(frame.injected_spend.sum()),
        injected_share=float(frame.injected_spend.sum()/actual) if actual else None,
        ordinary_bill_spend=float(frame.ordinary_bill_spend.sum()),
        ordinary_nonbill_spend=float(frame.ordinary_nonbill_spend.sum()),
        underpredicted_fraction=float(frame.error.lt(0).mean()))


def diagnose(archive, train_csv):
    with zipfile.ZipFile(archive) as z:
        roots={n.split('/')[0] for n in z.namelist()}
        if len(roots)!=1: raise ValueError('Expected one run folder')
        prefix=next(iter(roots))+'/'
        read_json=lambda name:json.loads(z.read(prefix+name))
        split=read_json('data_split_manifest.json')
        if split.get('dataset_version')!='spendly-synthetic-r3-v1':
            raise ValueError('This diagnosis is declared for the original R3 train cohort')
        expected=split['permitted_cohorts']['train']
        actual_hash=hash_file(train_csv)
        if actual_hash!=expected['sha256']: raise ValueError('Training CSV hash mismatch')
        predictions=[]
        for seed in (42,123,2026):
            p=pd.read_csv(io.BytesIO(z.read(prefix+f'v6_reference_seed_{seed}_fraction_1.0_predictions.csv')))
            p['target_week']=pd.to_datetime(p.target_week)
            if p.duplicated(KEYS).any(): raise ValueError('Duplicate prediction windows')
            predictions.append(p)
        # Attribution uses the mean forecast, explicitly distinct from mean-seed MAE.
        reference=average_predictions(predictions,split['train_target_end'])
        parts=[]; count=0; users=set()
        for chunk in pd.read_csv(train_csv,dtype={'user_id':str},chunksize=100000):
            count+=len(chunk); users.update(chunk.user_id.unique())
            parts.append(aggregate_weeks(chunk,split['train_target_end']))
        if count!=expected['rows'] or len(users)!=expected['users']: raise ValueError('Cohort size mismatch')
        weekly=pd.concat(parts,ignore_index=True).groupby(KEYS).sum().reset_index()
        result=join_predictions(reference,weekly)
        total=float(result.absolute_error.sum())
        groups={
            'all':result,
            'weeks_with_injected_events':result.loc[result.injected_transactions.gt(0)],
            'weeks_without_injected_events':result.loc[result.injected_transactions.eq(0)],
            'no_injection_with_bill_categories':result.loc[result.injected_transactions.eq(0)&result.bill_spend.gt(0)],
            'no_injection_without_bill_categories':result.loc[result.injected_transactions.eq(0)&result.bill_spend.eq(0)],
        }
        for q in (.9,.95,.99):
            top=result.loc[result.actual.ge(result.actual.quantile(q))]
            groups[f'top_{q}']=top
            groups[f'top_{q}_with_injection']=top.loc[top.injected_transactions.gt(0)]
            groups[f'top_{q}_without_injection']=top.loc[top.injected_transactions.eq(0)]
        families={c.removeprefix('scenario_'):summarize(result.loc[result[c].gt(0)],total)
                  for c in weekly.columns if c.startswith('scenario_')}
        # Known category proxy is not the detector's recurrence assignment.
        result['due_proxy']=result.recurring_share*result.recurring
        ordinary=result.loc[result.injected_transactions.eq(0)]
        bill_proxy=dict(rows=len(ordinary),
            due_minus_bill_MAE_KES=float((ordinary.due_proxy-ordinary.bill_spend).abs().mean()),
            due_minus_bill_bias_KES=float((ordinary.due_proxy-ordinary.bill_spend).mean()),
            meaning='Causal scheduled-due estimate vs named bill categories; includes category/schedule definition differences, not pure timing error')
        schedule=read_json('memorization/schedule.json')
        tiny=read_json('memorization_diagnostic.json'); history=pd.read_csv(io.BytesIO(z.read(prefix+'memorization/history.csv')))
        batch=schedule['configuration']['batch_size']; epochs=len(history)
        # Final diagnostic update has checkpointed history; no need to load saved model.
        capability=dict(rows=tiny['rows'],users=tiny['metrics']['users'],batch_size=batch,epochs=epochs,
            optimizer_updates=math.ceil(tiny['rows']/batch)*epochs,
            first_weighted_MAE=float(history.weighted_mae.iloc[0]),last_weighted_MAE=float(history.weighted_mae.iloc[-1]),
            reduction_percent=100*(1-tiny['final_over_initial_error']),training_seconds=schedule['train_seconds'],
            caveat='One batch per epoch means only120 optimizer updates; weak memorization does not establish a model/data ceiling')
        return dict(protocol='v8-large-week-diagnosis-v1',archive_sha256=hash_file(archive),
            train_sha256=actual_hash,train_raw_rows=count,training_cutoff=split['train_target_end'],
            prediction_scope=f'{len(reference)} outer training-user windows; mean of three reference predictions, not mean-seed metrics',
            groups={name:summarize(g,total) for name,g in groups.items()},families=families,
            bill_proxy=bill_proxy,capability=capability,
            access='Only hash-verified train.csv read; no validation/calibration/final/shifted dataset files read',
            limitations=['Association not causal attribution','Injected labels describe simulation scenarios, not fraud',
                'Bill categories are a proxy for schedules','No model training or candidate selection performed'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--train-csv',required=True,type=Path); parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(); report=diagnose(args.archive,args.train_csv)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(report,indent=2))
