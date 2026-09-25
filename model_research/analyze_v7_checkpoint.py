"""Read-only ZIP/notebook audit; never imports notebook code or unpickles models.

Writes aggregate evidence only. Does not train, tune or open raw/holdout datasets.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd


def validate_prediction_rows(frame):
    # Every exported experiment evaluates each user in just one outer fold.
    if frame.duplicated(['user_id','target_week']).any():
        raise ValueError('Repeated user/week across outer folds')
    if frame.groupby('user_id').fold.nunique().gt(1).any():
        raise ValueError('Outer evaluation user appears in multiple folds')
    np.testing.assert_allclose(frame.residual,frame.prediction-frame.actual,atol=1e-8,rtol=1e-12)
    np.testing.assert_allclose(frame.absolute_error,np.abs(frame.prediction-frame.actual),atol=1e-8,rtol=1e-12)


def metrics(frame, column='prediction'):
    y=frame.actual.to_numpy(float); p=frame[column].to_numpy(float)
    assert len(y) and np.isfinite(y).all() and np.isfinite(p).all()
    error=p-y; denominator=y.sum()
    wape=lambda g: float(np.abs(g[column]-g.actual).sum()/g.actual.sum())
    blocks=np.array_split(sorted(frame.target_week.unique()),3)
    worst=max(wape(frame.loc[frame.target_week.isin(b)]) for b in blocks if len(b))
    overall=float(np.abs(error).sum()/denominator)
    return dict(rows=len(y),users=frame.user_id.nunique(),MAE_KES=float(np.abs(error).mean()),
        RMSE_KES=float(np.sqrt(np.mean(error**2))),WAPE=overall,
        R2=float(1-np.sum(error**2)/np.sum((y-y.mean())**2)),bias_KES=float(error.mean()),
        bias_percent=float(100*error.sum()/denominator),
        within_20_percent=float(np.mean(np.where(y>0,np.abs(error)<=.2*y,np.abs(error)<=1e-9))),
        worst_block_WAPE=worst,selection_objective=(overall+worst)/2)


def paired_bootstrap(frame):
    values=frame.assign(denom=frame.actual,
        candidate_error=np.abs(frame.prediction-frame.actual),
        reference_error=np.abs(frame.reference-frame.actual),
        baseline_error=np.abs(frame.recurring_median-frame.actual))
    grouped=values.groupby('user_id',sort=True)[['denom','candidate_error','reference_error','baseline_error']].sum().to_numpy()
    rng=np.random.default_rng(2026); draws=[]
    for _ in range(1000):
        totals=grouped[rng.integers(0,len(grouped),len(grouped))].sum(axis=0)
        draws.append(totals[1:]/totals[0])
    draws=np.asarray(draws)
    ci=lambda a: np.quantile(a,[.025,.975]).tolist()
    return dict(candidate_WAPE_95=ci(draws[:,0]),
        candidate_minus_v6_pp_95=ci(100*(draws[:,0]-draws[:,1])),
        candidate_minus_baseline_pp_95=ci(100*(draws[:,0]-draws[:,2])))


def analyze(archive, notebook):
    nb=json.loads(notebook.read_text(encoding='utf-8'))
    text=lambda x: ''.join(x) if isinstance(x,list) else x
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        names=z.namelist(); assert len(names)==len(set(names))
        roots={n.split('/')[0] for n in names}; assert len(roots)==1
        root=next(iter(roots))+'/'
        csv=lambda n: pd.read_csv(io.BytesIO(z.read(root+n)))
        js=lambda n: json.loads(z.read(root+n))
        checks=0
        for path in names:
            if path.endswith('/complete.json'):
                marker=json.loads(z.read(path)); folder=path.rsplit('/',1)[0]+'/'
                for relative,h in marker.get('files',{}).items():
                    assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
                    assert hashlib.sha256(z.read(folder+relative)).hexdigest()==h
                    checks+=1
        # Selection JSON/CSV records are separately bound to the saved selection.
        for path in names:
            if path.endswith('/outputs.json'):
                for relative,h in json.loads(z.read(path)).items():
                    assert hashlib.sha256(z.read(root+relative)).hexdigest()==h
        folds=csv('fold_metrics.csv'); registry=csv('experiment_registry.csv')
        assert not folds.duplicated(['candidate','seed','fold','fraction']).any()
        predictions={}; discrepancies=[]; summaries=[]; checked_folds=0
        for path in sorted(names):
            name=path[len(root):]
            if '/' in name or not name.endswith('_predictions.csv'):
                continue
            candidate,remainder=name.rsplit('_seed_',1)
            seed,fraction=remainder.removesuffix('_predictions.csv').split('_fraction_')
            seed=int(seed); fraction=float(fraction); frame=csv(name)
            validate_prediction_rows(frame)
            assert not frame.duplicated(['user_id','target_week','fold','seed']).any()
            assert frame.seed.eq(seed).all() and frame.candidate.eq(candidate).all()
            assert np.allclose(frame.absolute_error,np.abs(frame.prediction-frame.actual))
            predictions[candidate,seed,fraction]=frame
            measured=metrics(frame)
            selected=folds.loc[folds.candidate.eq(candidate)&folds.seed.eq(seed)&folds.fraction.eq(fraction)]
            assert len(selected)==3
            for fold,part in frame.groupby('fold'):
                for suffix,column in [('', 'prediction'),('::recurring_median','recurring_median'),
                                      ('::recurring_mean','recurring'),('::last_week','last'),('::mean4','mean4')]:
                    record=folds.loc[folds.candidate.eq(candidate+suffix)&folds.seed.eq(seed)&
                        folds.fraction.eq(fraction)&folds.fold.eq(fold)].iloc[0]
                    for key,value in metrics(part,column).items():
                        if not np.isclose(value,record[key],atol=1e-7,rtol=1e-9):
                            discrepancies.append(dict(candidate=candidate+suffix,seed=seed,fold=int(fold),metric=key))
                    checked_folds+=1
            summaries.append(dict(candidate=candidate,seed=seed,fraction=fraction,**measured,
                mean_fold_objective=float(selected.selection_objective.mean()),
                mean_train_WAPE=float(selected.train_WAPE.mean()),
                best_epochs=selected.best_epoch.astype(int).tolist()))
        assert not discrepancies,discrepancies
        reference=predictions['v6_reference',42,1.]
        keys=['user_id','target_week','fold','seed']
        for (candidate,seed,fraction),frame in predictions.items():
            match=reference.drop(columns='seed').merge(frame,on=keys[:-1],validate='one_to_one',suffixes=('_ref',''))
            assert len(match)==len(reference)==len(frame)
            for col in ('actual','recurring_median','recurring','last','mean4'):
                np.testing.assert_allclose(match[col],match[col+'_ref'],rtol=1e-12,atol=1e-8)
        decision=js('train_selection_evidence.json'); winner=decision['provisional_winner']
        pairs=[]
        for seed in (42,123,2026):
            p=predictions[winner,seed,1.]; ref=predictions['v6_reference',seed,1.]
            pairs.append(p.merge(ref[keys+['prediction']].rename(columns={'prediction':'reference'}),on=keys,validate='one_to_one'))
        pairs=pd.concat(pairs,ignore_index=True); intervals=paired_bootstrap(pairs)
        for key,interval in intervals.items():
            np.testing.assert_allclose(interval,decision['intervals'][key],rtol=1e-9,atol=1e-9)
        subgroups=[]
        for col in ('actual','volatility','activity','recurring_share','zero_fraction'):
            for label,g in reference.groupby(pd.qcut(reference[col],4,duplicates='drop'),observed=True):
                subgroups.append(dict(feature=col,group=str(label),**metrics(g),
                    fraction_absolute_error=float(g.absolute_error.sum()/reference.absolute_error.sum()),
                    baseline_WAPE=metrics(g,'recurring_median')['WAPE']))
        tail=[]
        for quantile in (.9,.95,.99):
            threshold=reference.actual.quantile(quantile); g=reference.loc[reference.actual.ge(threshold)]
            tail.append(dict(quantile=quantile,threshold_KES=float(threshold),**metrics(g),
                fraction_absolute_error=float(g.absolute_error.sum()/reference.absolute_error.sum())))
        user_error=reference.assign(baseline_error=np.abs(reference.recurring_median-reference.actual))
        user_sums=user_error.groupby('user_id')[['absolute_error','baseline_error','actual']].sum()
        curves=[]; total_seconds=0.
        for path in names:
            if path.endswith('/schedule.json'):
                schedule=json.loads(z.read(path)); total_seconds+=schedule['train_seconds']
            if path.endswith('/stopping/history.csv'):
                parts=path[len(root):].split('/')
                if parts[1] not in ('v6_reference','predictive_stop','diagnostic_cap120','diagnostic_cap160'):
                    continue
                h=pd.read_csv(io.BytesIO(z.read(path))); schedule=json.loads(z.read(path.rsplit('/',1)[0]+'/schedule.json'))
                curves.append(dict(candidate=parts[1],seed=parts[2],fold_fraction=parts[3],epochs=len(h),
                    best_epoch=schedule['best_epoch'],first_train=float(h.weighted_mae.iloc[0]),
                    last_train=float(h.weighted_mae.iloc[-1]),first_stop=float(h.val_weighted_mae.iloc[0]),
                    last_stop=float(h.val_weighted_mae.iloc[-1])))
        result=dict(zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            notebook_sha256=hashlib.sha256(notebook.read_bytes()).hexdigest(),
            zip_entries=len(names),verified_checkpoint_hashes=checks,verified_fold_metric_rows=checked_folds,
            prediction_files=len(predictions),unique_evaluation_windows=len(reference),
            rescore_discrepancies=discrepancies,decision=decision,bootstrap_rescored=intervals,
            candidate_metrics=summaries,baselines={c:metrics(reference,c) for c in ('recurring_median','recurring','last','mean4')},
            subgroup_metrics=subgroups,tail_error=tail,training_curves=curves,
            users_beating_median=int((user_sums.absolute_error<user_sums.baseline_error).sum()),
            users_underpredicting=int(reference.assign(recomputed_residual=reference.prediction-reference.actual).groupby('user_id').recomputed_residual.mean().lt(0).sum()),
            memorization=js('memorization_diagnostic.json'),persisted_training_hours=total_seconds/3600,
            dataset_version=js('data_split_manifest.json')['dataset_version'],
            missing_reports=[f for f in ('configuration_lock.json','validation_metrics.json','row_level_predictions.csv',
                'epoch_cap_sensitivity.json','diagnostic_interpretation.json','anomaly_metrics.csv',
                'anomaly_per_type_events.csv','anomaly_alert_burden.json','artifact_manifest.json') if root+f not in names],
            notebook_cells=[dict(id=c.get('id'),execution=c.get('execution_count'),
                errors=[dict(name=o.get('ename'),message=o.get('evalue')) for o in c.get('outputs',[]) if o.get('output_type')=='error'])
                for c in nb['cells'] if c['cell_type']=='code'],
            notebook_final_export=any('Evidence ZIP:' in text(o.get('text','')) for c in nb['cells'] for o in c.get('outputs',[])))
        return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--notebook',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); result=analyze(args.archive,args.notebook)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    table=pd.DataFrame(result['candidate_metrics'])
    print('SEED42 FULL-FRACTION COMPARISONS:')
    print(table.loc[table.seed.eq(42)&table.fraction.eq(1),['candidate','WAPE','MAE_KES','R2','bias_KES','within_20_percent','mean_fold_objective','best_epochs']].sort_values('mean_fold_objective').to_string(index=False))
    print('LEARNING CURVE:',table.loc[table.candidate.eq('v6_reference')&table.seed.eq(42),['fraction','WAPE','mean_train_WAPE','mean_fold_objective']].to_string(index=False))
    print('VERIFICATION:',result['verified_checkpoint_hashes'],'hashes;',result['verified_fold_metric_rows'],'fold records;',result['prediction_files'],'prediction files; no discrepancies')
    print('BOOTSTRAP:',result['bootstrap_rescored'])
    print('TAIL:',result['tail_error'])
    print('USERS:',result['users_beating_median'],'beat median;',result['users_underpredicting'],'underpredict')
    print('PERSISTED FIT HOURS:',result['persisted_training_hours'])
