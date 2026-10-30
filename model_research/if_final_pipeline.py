"""Development-only IF finalization, verified inputs and trusted-local bundles.

Does not expose a final-holdout loader. A separate approved final evaluation must
be predeclared after development review. Pickle bundles are trusted-local only.
"""
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import platform
import zipfile

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score

from if_final_features import FEATURES, aware_dates, build_features, validate_transactions

PROTOCOL = {
    'version': 'if-finalization-v1', 'dataset': 'spendly-synthetic-r3-v1',
    'training_end': '2023-04-24T00:00:00+03:00',
    'calibration_end': '2023-08-28T00:00:00+03:00',
    'evaluation_end': '2024-01-01T00:00:00+03:00',
    'minimum_history_days': 7, 'fpr_budget': .01, 'seed': 42,
    'fit_policy': 'mixed training expenses; no normal-label filtering',
    'threshold_policy': 'negative-only calibration quantile, no F1 optimization',
    'tie_policy': 'candidate same-user timestamp batch excluded from own history',
    'candidate': {'n_estimators': 500, 'max_samples': 16384, 'max_features': .5},
    'reference': {'n_estimators': 300, 'max_samples': 128, 'max_features': 1.},
    'selection': 'no automatic promotion; paired development report for review',
    'holdouts': 'not accessed; finalization candidate only',
}
COHORTS = ('train', 'calibration', 'validation')


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path = Path(path)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def versions():
    return {'python': platform.python_version(), **{name: importlib.metadata.version(name)
            for name in ('numpy', 'pandas', 'scikit-learn', 'joblib')}}


def source_identity():
    root = Path(__file__).parent
    return {name: digest_bytes((root/name).read_bytes()) for name in
            ('if_final_features.py', 'if_final_pipeline.py', 'if_final_reference.py')}


def load_development(root):
    """Only named development ZIPs are opened, never archive paths extracted."""
    root = Path(root)
    manifest_raw = (root/'manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    if (manifest.get('version') != PROTOCOL['dataset'] or
            manifest.get('synthetic_only') is not True or manifest.get('weeks_per_user') != 156):
        raise ValueError('Expected original synthetic R3 manifest')
    data, identities, users, ids = {}, {}, set(), set()
    for name in COHORTS:
        entry = manifest['cohorts'][name]
        candidates = [p for p in (root/'development'/f'{name}.zip', root/f'{name}.zip') if p.is_file()]
        if len(candidates) != 1:
            raise ValueError(f'Provide exactly one {name}.zip, at root or development/')
        packed = candidates[0].read_bytes()
        if digest_bytes(packed) != entry['zip_sha256']:
            raise ValueError(f'{name} ZIP hash mismatch')
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            files = [i for i in archive.infolist() if not i.is_dir()]
            if len(files) != 1 or files[0].file_size != entry['csv_bytes']:
                raise ValueError(f'{name} archive must contain exactly the declared CSV')
            raw = archive.read(files[0])
        if digest_bytes(raw) != entry['sha256']:
            raise ValueError(f'{name} CSV hash mismatch')
        frame = validate_transactions(pd.read_csv(io.BytesIO(raw)))
        if len(frame) != entry['rows'] or frame.user_id.nunique() != entry['users']:
            raise ValueError(f'{name} counts mismatch')
        if not frame.is_anomaly.isin([0, 1]).all():
            raise ValueError('Explicit binary labels required for evaluation')
        if users & set(frame.user_id) or ids & set(frame.transaction_id):
            raise ValueError('Cohort identity overlap')
        users.update(frame.user_id); ids.update(frame.transaction_id)
        start = aware_dates(frame.observation_start)
        end = aware_dates(frame.observation_end)
        if not start.eq(pd.Timestamp('2021-01-04T00:00:00+03:00')).all() or not end.eq(pd.Timestamp(PROTOCOL['evaluation_end'])).all():
            raise ValueError('Unexpected R3 coverage')
        if not ((frame.transaction_timestamp >= start) & (frame.transaction_timestamp < end)).all():
            raise ValueError('Transaction outside observation coverage')
        data[name] = frame
        identities[name] = entry['sha256']
        print(f'Verified {name}: {len(frame):,} rows / {entry["users"]} users', flush=True)
    return data, {'manifest': digest_bytes(manifest_raw), 'csv': identities}


def capped_threshold(labels, scores, budget):
    """Tied scores cannot exceed budget; positives never select the cutoff."""
    labels, scores = np.asarray(labels), np.asarray(scores, dtype=float)
    if not 0 < budget < 1 or len(labels) != len(scores) or not np.isfinite(scores).all():
        raise ValueError('Invalid calibration')
    negative = np.sort(scores[labels == 0])[::-1]
    if not len(negative):
        raise ValueError('Calibration requires normal observations')
    allowed = int(np.floor(budget*len(negative)))
    threshold = float(np.nextafter(negative[allowed], np.inf))
    assert (negative >= threshold).sum() <= allowed
    return threshold


def measures(rows, scores, threshold):
    y = rows.is_anomaly.to_numpy(dtype=int)
    scores = np.asarray(scores)
    if len(y) != len(scores) or not len(y) or not np.isfinite(scores).all():
        raise ValueError('Invalid evaluation scores')
    flags = scores >= threshold
    tn, fp, fn, tp = map(int, confusion_matrix(y, flags, labels=[0, 1]).ravel())
    both = len(np.unique(y)) == 2
    precision = tp/(tp+fp) if tp+fp else 0.
    recall = tp/(tp+fn) if tp+fn else None
    fpr = fp/(fp+tn) if fp+tn else None
    families = {}
    for name, group in rows.assign(flag=flags).loc[rows.is_anomaly.eq(1)].groupby('anomaly_type'):
        families[str(name)] = {'support': len(group), 'detected': int(group.flag.sum()), 'recall': float(group.flag.mean())}
    positive = rows.assign(flag=flags).loc[rows.is_anomaly.eq(1)]
    events = positive.dropna(subset=['event_id']).groupby(['user_id', 'event_id']).flag.max()
    days = pd.DataFrame({'user': rows.user_id, 'date': rows.transaction_timestamp.dt.date, 'flag': flags}).groupby(['user', 'date']).flag.sum()
    return {'rows': len(rows), 'TP': tp, 'FP': fp, 'FN': fn, 'TN': tn,
            'precision': precision, 'recall': recall, 'F1': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,
            'FPR': fpr, 'accuracy': (tp+tn)/len(y),
            'balanced_accuracy': (recall+1-fpr)/2 if both else None,
            'AP': float(average_precision_score(y, scores)) if both else None,
            'ROC_AUC': float(roc_auc_score(y, scores)) if both else None,
            'alert_rate': float(flags.mean()), 'families': families,
            'event_support': len(events), 'event_recall': float(events.mean()) if len(events) else None,
            'positive_rows_without_event_id': int(positive.event_id.isna().sum()),
            'active_user_days': len(days), 'alerted_user_days': int(days.gt(0).sum()),
            'max_alerts_per_active_user_day': int(days.max())}


def paired_interval(rows, candidate, reference, repetitions=1000):
    """Paired user-cluster bootstrap; reused-development uncertainty only."""
    labels = rows.is_anomaly.to_numpy(dtype=bool)
    columns = []
    for flags in (candidate, reference):
        columns.extend([labels & flags, ~labels & flags, labels & ~flags])
    counts = pd.DataFrame(np.array(columns).T.astype(int)).assign(user=rows.user_id.to_numpy()).groupby('user').sum().to_numpy()
    rng = np.random.default_rng(42)
    differences = []
    for _ in range(repetitions):
        summed = counts[rng.integers(0, len(counts), size=len(counts))].sum(axis=0)
        f1 = lambda v: 2*v[0]/max(1, 2*v[0]+v[1]+v[2])
        differences.append(f1(summed[:3])-f1(summed[3:]))
    return {'method': 'paired user-cluster bootstrap', 'replicates': repetitions,
            'candidate_minus_reference_F1_95pct': np.quantile(differences, [.025, .975]).tolist()}


def save_bundle(directory, pipeline, columns, threshold, identity, probe):
    directory = Path(directory)
    directory.mkdir(exist_ok=False)
    target = directory/'pipeline.joblib'
    joblib.dump(pipeline, target)
    manifest = {'protocol': PROTOCOL, 'versions': versions(), 'sources': source_identity(),
                'inputs': identity, 'features': columns, 'threshold': threshold,
                'sha256': digest_bytes(target.read_bytes()), 'status': 'development_candidate_not_promoted'}
    write_json(directory/'manifest.json', manifest)
    loaded, metadata = load_bundle(directory, trusted=True)
    before = -pipeline.score_samples(probe)
    after = -loaded.score_samples(probe)
    np.testing.assert_array_equal(before, after)
    write_json(directory/'reload_parity.json', {'rows': len(probe), 'max_abs_error': float(np.max(np.abs(before-after))),
                                             'model_sha256': metadata['sha256']})


def load_bundle(directory, *, trusted=False):
    if not trusted:
        raise PermissionError('Only load your own trusted local joblib artifact')
    directory = Path(directory)
    meta = json.loads((directory/'manifest.json').read_text())
    if meta['versions'] != versions() or meta['sources'] != source_identity() or meta['protocol'] != PROTOCOL:
        raise ValueError('Frozen environment/source/protocol mismatch')
    path = directory/'pipeline.joblib'
    if digest_bytes(path.read_bytes()) != meta['sha256']:
        raise ValueError('Model hash mismatch')
    return joblib.load(path), meta


def run_development(input_root, output):
    from sklearn.pipeline import make_pipeline
    from if_final_reference import reference_features
    output = Path(output)
    output.mkdir(exist_ok=False)
    write_json(output/'protocol.json', {'protocol': PROTOCOL, 'sources': source_identity(), 'versions': versions()})
    data, identity = load_development(input_root)
    candidate, reference = {}, {}
    for name, frame in data.items():
        if name == 'train':
            frame = frame.loc[frame.transaction_timestamp < pd.Timestamp(PROTOCOL['training_end'])].copy()
        print(f'Building {name} feature views', flush=True)
        candidate[name] = build_features(frame)
        reference[name] = reference_features(frame)
    # Common eligibility including reference warm-up, identical IDs in both views.
    selected = {}
    for name in COHORTS:
        c = candidate[name]
        mask = c.history_days.ge(PROTOCOL['minimum_history_days'])
        t = c.transaction_timestamp
        if name == 'train':
            mask &= t.lt(pd.Timestamp(PROTOCOL['training_end']))
        elif name == 'calibration':
            mask &= t.ge(pd.Timestamp(PROTOCOL['training_end'])) & t.lt(pd.Timestamp(PROTOCOL['calibration_end']))
        else:
            mask &= t.ge(pd.Timestamp(PROTOCOL['calibration_end'])) & t.lt(pd.Timestamp(PROTOCOL['evaluation_end']))
        shared = set(reference[name].index)
        c = c.loc[mask & c.transaction_id.isin(shared)].set_index('transaction_id')
        if c.empty:
            raise ValueError(f'No common eligible {name} rows')
        selected[name] = c
        reference[name] = reference[name].loc[c.index]
    write_json(output/'input_identity.json', identity)
    reports, flags, all_scores = {}, {}, {}
    for name in ('reference', 'candidate'):
        matrices = ({k: v[FEATURES] for k, v in selected.items()} if name == 'candidate' else reference)
        params = PROTOCOL[name]
        pipeline = make_pipeline(SimpleImputer(strategy='median', add_indicator=True),
            IsolationForest(**params, contamination='auto', random_state=42, n_jobs=2)) if name == 'candidate' else make_pipeline(
                IsolationForest(**params, contamination='auto', random_state=42, n_jobs=2))
        print(f'Fitting {name}: {len(matrices["train"]):,} common rows', flush=True)
        pipeline.fit(matrices['train'])
        calibration_scores = -pipeline.score_samples(matrices['calibration'])
        threshold = capped_threshold(selected['calibration'].is_anomaly, calibration_scores, PROTOCOL['fpr_budget'])
        scores = -pipeline.score_samples(matrices['validation'])
        reports[name] = {'threshold': threshold, 'calibration': measures(selected['calibration'], calibration_scores, threshold),
                         'validation': measures(selected['validation'], scores, threshold)}
        flags[name] = scores >= threshold
        all_scores[name] = scores
        save_bundle(output/name, pipeline, list(matrices['train']), threshold, identity, matrices['validation'].iloc[:128])
        write_json(output/f'{name}_metrics.json', reports[name])
    rows = selected['validation']
    prediction_rows = rows[['user_id', 'transaction_timestamp', 'is_anomaly', 'anomaly_type', 'event_id']].copy()
    for name in flags:
        prediction_rows[name+'_score'] = all_scores[name]
        prediction_rows[name+'_flag'] = flags[name]
    prediction_rows.to_csv(output/'development_predictions.csv')
    report = {'scope': 'reused synthetic development comparison; not final test', 'protocol': PROTOCOL,
              'metrics': reports, 'uncertainty': paired_interval(rows, flags['candidate'], flags['reference']),
              'decision': 'review_required_no_automatic_promotion',
              'common_rows': {k: len(v) for k, v in selected.items()}}
    write_json(output/'comparison.json', report)
    write_json(output/'artifacts.json', {str(p.relative_to(output)): digest_bytes(p.read_bytes())
                                      for p in output.rglob('*') if p.is_file()})
    print(json.dumps(report, indent=2))
    return report
