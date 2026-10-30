"""Verify V9 final archive and recompute its saved metrics without loading models."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

import numpy as np
import pandas as pd
from analyze_v7_checkpoint import metrics,paired_bootstrap,validate_prediction_rows


def validate_final_records(records,expected):
    names=[r['candidate'] for r in records]
    if len(names)!=len(expected) or set(names)!=set(expected):
        raise ValueError('Expected exactly one final validation record per comparator')
    return len(records)


def analyze(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or z.testzip() is not None:
            raise ValueError('Invalid ZIP')
        for name in names:
            p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name:raise ValueError('Unsafe ZIP path')
        js=lambda name:json.loads(z.read(name))
        csv=lambda name:pd.read_csv(io.BytesIO(z.read(name)))
        manifest=js('artifact_manifest.json')
        if manifest['protocol']!='v9-checkpoint-policy-v1':raise ValueError('Expected V9 final archive')
        for name,h in manifest['files'].items():
            if hashlib.sha256(z.read(name)).hexdigest()!=h:raise ValueError('Hash mismatch: '+name)
        folds=csv('fold_metrics.csv');seeds=csv('seed_metrics.csv');decision=js('train_selection_evidence.json')
        if folds.duplicated(['candidate','seed','fold','fraction']).any():raise ValueError('Repeated fold metrics')
        checked=0;paired=[]
        keys=['user_id','target_week','fold','seed']
        for seed in (42,123,2026):
            frames={}
            for candidate in ('v6_reference','predictive_full_budget'):
                p=csv(f'{candidate}_seed_{seed}_fraction_1.0_predictions.csv')
                validate_prediction_rows(p); frames[candidate]=p
                record=seeds.loc[seeds.candidate.eq(candidate)&seeds.seed.eq(seed)]
                assert len(record)==1
                for key,value in metrics(p).items():
                    if key in record:np.testing.assert_allclose(value,record[key].iloc[0],atol=1e-7,rtol=1e-9)
                for fold,g in p.groupby('fold'):
                    for suffix,column in (('','prediction'),('::recurring_median','recurring_median'),
                        ('::recurring_mean','recurring'),('::last_week','last'),('::mean4','mean4')):
                        r=folds.loc[folds.candidate.eq(candidate+suffix)&folds.seed.eq(seed)&folds.fold.eq(fold)]
                        assert len(r)==1
                        for key,value in metrics(g,column).items():np.testing.assert_allclose(value,r[key].iloc[0],atol=1e-7,rtol=1e-9)
                        checked+=1
            ref=frames['v6_reference']
            p=frames['predictive_full_budget'].merge(ref[keys+['actual','prediction']].rename(
                columns={'prediction':'reference','actual':'reference_actual'}),on=keys,how='outer',validate='one_to_one',indicator=True)
            assert p['_merge'].eq('both').all()
            np.testing.assert_allclose(p.actual,p.reference_actual)
            paired.append(p)
        paired=pd.concat(paired,ignore_index=True)
        intervals=paired_bootstrap(paired)
        for key,value in intervals.items():np.testing.assert_allclose(value,decision['intervals'][key],atol=1e-9)
        final=csv('row_level_predictions.csv');validate_prediction_rows(final)
        columns=dict(v6_reference='prediction',recurring_median='recurring_median',recurring_mean='recurring',last_week='last',mean4='mean4')
        final_records=js('validation_metrics.json')['metrics']
        final_count=validate_final_records(final_records,columns)
        for record in final_records:
            for key,value in metrics(final,columns[record['candidate']]).items():
                np.testing.assert_allclose(value,record[key],atol=1e-7,rtol=1e-9)
        ck=csv('checkpoint_comparison.csv')
        for row in ck.itertuples():
            folder=f'experiments/{row.candidate}/seed_{row.seed}/fold_{row.fold}_fraction_1.0/stopping/'
            history=csv(folder+'history.csv');schedule=js(folder+'schedule.json')
            assert len(history)==row.trained_epochs and schedule['best_epoch']==row.restored_epoch
            assert row.restored_epoch==int(np.argmin(history[row.checkpoint_metric]))+1
            np.testing.assert_allclose(history[row.checkpoint_metric].iloc[row.restored_epoch-1],row.restored_metric)
        change=paired.assign(candidate_error=np.abs(paired.prediction-paired.actual),reference_error=np.abs(paired.reference-paired.actual))
        users=change.groupby('user_id')[['candidate_error','reference_error']].sum()
        actuals=change.actual
        tails=[]
        for q in (.9,.95,.99):
            g=change.loc[actuals.ge(actuals.quantile(q))]
            tails.append(dict(quantile=q,candidate_WAPE=float(g.candidate_error.sum()/g.actual.sum()),
                reference_WAPE=float(g.reference_error.sum()/g.actual.sum())))
        totals=seeds.groupby('candidate')[['WAPE','MAE_KES','RMSE_KES','R2','bias_KES','within_20_percent','objective']].mean()
        duration=folds.loc[~folds.candidate.str.contains('::')].groupby('candidate').train_seconds.sum()
        return dict(archive_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),verified_manifest_files=len(manifest['files']),
            fold_records_rescored=checked,seed_records_rescored=len(seeds),validation_records_rescored=final_count,
            checkpoint_records_verified=len(ck),decision=decision,bootstrap_recomputed=intervals,
            mean_results=totals.to_dict(orient='index'),seed_results=seeds[['candidate','seed','WAPE','MAE_KES']].to_dict(orient='records'),
            comparison_training_seconds=duration.to_dict(),users_with_lower_error=int(users.candidate_error.lt(users.reference_error).sum()),
            users_with_equal_error=int(np.isclose(users.candidate_error,users.reference_error,atol=1e-9,rtol=0).sum()),
            tail_metrics=tails,checkpoint_records=ck.to_dict(orient='records'),
            final_validation=js('validation_metrics.json'),timing=js('timings.json'),
            reload_parity_report=js('reload_parity.json'),
            scope='Read-only CSV/JSON audit; no model execution, raw data access or independent population evaluation')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--archive',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();result=analyze(args.archive)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('verified_manifest_files','fold_records_rescored','checkpoint_records_verified','mean_results','comparison_training_seconds','users_with_lower_error','users_with_equal_error','tail_metrics')},indent=2))
