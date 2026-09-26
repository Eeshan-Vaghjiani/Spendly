"""Verify alert-reproduction reports using counts only; never unpickle forests."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile
import numpy as np
import pandas as pd


def event_counts(family):
    support=family.events_with_ids.to_numpy(float)
    recall=family.event_recall.to_numpy(float)
    if not np.isfinite(support).all() or (support<0).any() or not np.equal(support,np.floor(support)).all():
        raise ValueError('Invalid event support')
    known=support>0
    if not np.isfinite(recall[known]).all() or ((recall[known]<0)|(recall[known]>1)).any():
        raise ValueError('Invalid event recall')
    result=np.zeros_like(support); result[known]=recall[known]*support[known]
    np.testing.assert_allclose(result,np.round(result),atol=1e-10)
    return result


def analyze(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        assert len(names)==len(set(names)) and z.testzip() is None
        roots={n.split('/')[0] for n in names}; assert len(roots)==1
        root=next(iter(roots))+'/'
        js=lambda f:json.loads(z.read(root+f))
        csv=lambda f:pd.read_csv(io.BytesIO(z.read(root+f)))
        manifest=js('artifact_manifest.json')
        assert manifest['protocol']=='v7-alert-reproduction-v1'
        for name,h in manifest['files'].items():
            p=PurePosixPath(name)
            assert not p.is_absolute() and '..' not in p.parts
            assert hashlib.sha256(z.read(root+name)).hexdigest()==h
        table=csv('anomaly_metrics.csv');families=csv('anomaly_per_type_events.csv')
        burden=js('anomaly_alert_burden.json');diagnostics=[]
        expected={'single','union_excess','union_rhythm','two_if_union','collective_rules','forest_collective_union'}
        assert len(table)==len(expected) and set(table.model)==expected
        for r in table.itertuples():
            assert r.TP+r.FN==r.positive_support and r.FP+r.TN==r.negative_support
            assert r.TP+r.FP+r.TN+r.FN==r.rows==r.labelled_rows
            calculated=dict(precision=r.TP/(r.TP+r.FP),recall=r.TP/(r.TP+r.FN),
                F1=2*r.TP/(2*r.TP+r.FP+r.FN),FPR=r.FP/(r.FP+r.TN),
                accuracy=(r.TP+r.TN)/r.rows,alert_rate=(r.TP+r.FP)/r.rows,
                balanced_accuracy=(r.TP/(r.TP+r.FN)+r.TN/(r.TN+r.FP))/2)
            for k,v in calculated.items():np.testing.assert_allclose(v,getattr(r,k),atol=1e-12)
            family=families.loc[families.model.eq(r.model)]
            assert family.family.is_unique and len(family)==5
            assert family.positive_transactions.sum()==r.positive_support
            counts=family.transaction_recall*family.positive_transactions
            np.testing.assert_allclose(counts,np.round(counts),atol=1e-10)
            np.testing.assert_allclose(counts.sum(),r.TP,atol=1e-10)
            events=event_counts(family)
            b=next(b for b in burden if b['model']==r.model)
            assert b['alerts']==r.TP+r.FP
            np.testing.assert_allclose(b['fraction_active_days_alerted'],b['alerted_user_days']/b['active_user_days'])
            diagnostics.append(dict(model=r.model,event_support=int(family.events_with_ids.sum()),
                detected_events=int(round(events.sum())),**calculated))
        t=table.set_index('model')
        return dict(archive_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            verified_file_hashes=len(manifest['files']),verified_model_summaries=len(table),
            metrics=table.where(pd.notna(table),None).to_dict(orient='records'),
            event_summary=diagnostics,per_type=families.to_dict(orient='records'),burden=burden,
            collective_increment_vs_strict_forest=dict(TP=int(t.loc['forest_collective_union','TP']-t.loc['union_excess','TP']),
                FP=int(t.loc['forest_collective_union','FP']-t.loc['union_excess','FP'])),
            protocol=js('anomaly_protocol.json'),collective_protocol=js('collective_protocol.json'),
            elapsed_seconds=js('timings.json')['seconds']['anomaly_detection'],
            limitation='Integrity and arithmetic consistency checked; archive has no row scores/flags for independent inference or AP/AUC rescoring.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--archive',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();result=analyze(args.archive)
    # Convert pandas/numpy NaNs to JSON null for the deliberately undefined union AUCs.
    result=json.loads(pd.Series(result).to_json())
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('verified_file_hashes','verified_model_summaries','event_summary','collective_increment_vs_strict_forest')},indent=2))
