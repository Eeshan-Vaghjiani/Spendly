"""One-time frozen retained-forest evaluation. No fit, selection or calibration.

Only the SHA256-pinned project-owned archive is deserialized. Input paths are
explicit; holdout access is recorded before opening either cohort ZIP.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd

from if_final_features import aware_dates, validate_transactions
from if_final_reference import REFERENCE_COLUMNS, reference_features
from if_final_pipeline import measures, versions, write_json

ARCHIVE_SHA = '98617ac130c456a5ee8917100e39451c63224ebe99877d7adb1db23c46dc4c42'
MANIFEST_SHA = '0280b31519bf89515e5d1c105612f8f2a660880e695a903a68a814af25b0b8f5'
THRESHOLD = 0.6451359189730762
ENVIRONMENT = {'numpy': '2.0.2', 'pandas': '2.3.3', 'scikit-learn': '1.6.1', 'joblib': '1.5.3'}
PROTOCOL = {
    'id': 'spendly-if-submission-v1', 'selected': 'retained_single_excess128',
    'artifact_sha256': ARCHIVE_SHA, 'dataset_manifest_sha256': MANIFEST_SHA,
    'threshold': THRESHOLD, 'score': '-sklearn.score_samples(log1p(five_excess_features))',
    'comparison': 'score >= threshold', 'trees': 300, 'max_samples': 128,
    'features': REFERENCE_COLUMNS, 'environment': ENVIRONMENT,
    'training_end': '2023-04-24T00:00:00+03:00',
    'evaluation_start': '2023-04-24T00:00:00+03:00',
    'evaluation_end': '2024-01-01T00:00:00+03:00',
    'eligibility': 'all expense rows in final36weeks; earlier same-user expenses are causal context only',
    'warmup': 'no new eligibility filter; preserve historical retained-model evaluation',
    'cohorts': ['test', 'test_shifted'], 'primary': ['precision', 'recall', 'F1'],
    'supplementary': ['AP', 'ROC_AUC', 'FPR', 'alert_rate', 'families', 'events', 'daily_burden'],
    'uncertainty': '2000 paired-within-user cluster bootstrap replicates; fixed seed42',
    'target': 'report historical 0.80 precision/recall/F1 aspiration, not an agreed supervisor gate',
    'decision': 'no retraining, recalibration, candidate scoring or test-driven selection',
    'scope': 'synthetic held-out-user evaluation; independent real-user quality unestablished',
    'prior_access': 'project records indicate no prior model evaluation; unrelated external sessions cannot be independently attested',
    'authorization': 'user requested complete final submission evaluation; mobile integration excluded',
}
SOURCES = ('if_submission.py', 'if_final_features.py', 'if_final_reference.py', 'if_final_pipeline.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_hashes():
    return {name: sha((Path(__file__).parent/name).read_bytes()) for name in SOURCES}


def read_archive(path):
    raw = Path(path).read_bytes()
    if sha(raw) != ARCHIVE_SHA:
        raise ValueError('Not the frozen project-owned alert archive')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        manifests = [n for n in names if n.endswith('/artifact_manifest.json')]
        if len(manifests) != 1 or len(names) != len(set(names)):
            raise ValueError('Invalid artifact archive')
        prefix = manifests[0][:-len('artifact_manifest.json')]
        manifest = json.loads(archive.read(manifests[0]))
        if manifest.get('execution_mode') != 'full_development' or manifest.get('evidence_eligible') is not True:
            raise ValueError('Not a full-development artifact')
        for name, digest in manifest['files'].items():
            if sha(archive.read(prefix+name)) != digest:
                raise ValueError('Artifact member checksum mismatch')
        lock = json.loads(archive.read(prefix+'configuration_lock.json'))
        if lock['versions'] != ENVIRONMENT or any(versions()[k] != v for k, v in ENVIRONMENT.items()):
            raise ValueError('Use the frozen isolated artifact environment')
        forests = joblib.load(io.BytesIO(archive.read(prefix+'isolation_forests.joblib')))
        chosen = [v for v in forests if v['name'] == 'single']
        if len(chosen) != 1:
            raise ValueError('Expected one retained single forest')
        selected = chosen[0]
        if selected['columns'] != REFERENCE_COLUMNS or selected['threshold']['threshold'] != THRESHOLD:
            raise ValueError('Feature/threshold mismatch')
        model = selected['model']
        if type(model).__name__ != 'IsolationForest' or len(model.estimators_) != 300 or model.max_samples_ != 128 or model.n_features_in_ != 5:
            raise ValueError('Unexpected retained architecture')
        return model, manifest, raw


def verified_csv(root, manifest, cohort):
    entry = manifest['cohorts'][cohort]
    relative = entry['zip'].replace('\\', '/')
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Invalid dataset path')
    raw = (Path(root)/relative).read_bytes()
    if sha(raw) != entry['zip_sha256']:
        raise ValueError(f'{cohort} archive hash mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [m for m in archive.infolist() if not m.is_dir()]
        if len(members) != 1 or members[0].file_size != entry['csv_bytes']:
            raise ValueError('Unexpected CSV member/size')
        csv = archive.read(members[0])
    if sha(csv) != entry['sha256']:
        raise ValueError('CSV hash mismatch')
    return csv


def validate_cohort(raw, entry, existing_users, existing_ids):
    frame = validate_transactions(pd.read_csv(io.BytesIO(raw)))
    if len(frame) != entry['rows'] or frame.user_id.nunique() != entry['users']:
        raise ValueError('Cohort counts differ')
    if existing_users & set(frame.user_id) or existing_ids & set(frame.transaction_id):
        raise ValueError('Holdout ownership overlaps an earlier cohort')
    if not frame.is_anomaly.isin([0, 1]).all():
        raise ValueError('Explicit binary labels required')
    start, end = aware_dates(frame.observation_start), aware_dates(frame.observation_end)
    if not start.eq(pd.Timestamp('2021-01-04T00:00:00+03:00')).all() or not end.eq(pd.Timestamp(PROTOCOL['evaluation_end'])).all():
        raise ValueError('Unexpected observation bounds')
    if not ((frame.transaction_timestamp >= start) & (frame.transaction_timestamp < end)).all():
        raise ValueError('Transaction outside observation bounds')
    return frame


def begin_access(ledger, cohort, identity):
    """Exclusive durable marker BEFORE reading. Failed attempts remain consumed."""
    ledger = Path(ledger)
    ledger.mkdir(parents=True, exist_ok=True)
    write_json(ledger/f'{cohort}.access.json', {
        'state': 'access_started_do_not_repeat', 'cohort': cohort,
        'at_utc': datetime.now(timezone.utc).isoformat(), 'identity': identity})


def confidence_intervals(rows, flags):
    y = rows.is_anomaly.to_numpy(dtype=bool)
    counts = pd.DataFrame({'user': rows.user_id.to_numpy(), 'tp': y & flags,
                          'fp': ~y & flags, 'fn': y & ~flags, 'tn': ~y & ~flags}).groupby('user').sum().to_numpy(dtype=float)
    rng = np.random.default_rng(42)
    samples = []
    for _ in range(2000):
        tp, fp, fn, tn = counts[rng.integers(0, len(counts), len(counts))].sum(axis=0)
        samples.append([tp/max(1, tp+fp), tp/max(1, tp+fn), 2*tp/max(1, 2*tp+fp+fn), fp/max(1, fp+tn)])
    return {name: np.quantile(np.asarray(samples)[:, i], [.025, .975]).tolist()
            for i, name in enumerate(['precision', 'recall', 'F1', 'FPR'])}


def evaluate_frame(model, frame, threshold=THRESHOLD):
    values = reference_features(frame)
    rows = frame.loc[frame.transaction_type.eq('expense')].set_index('transaction_id').loc[values.index]
    mask = rows.transaction_timestamp.ge(pd.Timestamp(PROTOCOL['evaluation_start'])) & rows.transaction_timestamp.lt(pd.Timestamp(PROTOCOL['evaluation_end']))
    rows, values = rows.loc[mask], values.loc[mask]
    if rows.empty:
        raise ValueError('No eligible test expenses')
    scores = -model.score_samples(values)
    result = measures(rows, scores, threshold)
    flags = scores >= threshold
    result['confidence_intervals_95pct'] = confidence_intervals(rows, flags)
    result['historical_80pct_aspiration_met'] = all(result[k] >= .8 for k in ('precision', 'recall', 'F1'))
    prediction = rows[['user_id', 'transaction_timestamp', 'is_anomaly', 'anomaly_type', 'event_id']].copy()
    prediction['score'], prediction['flag'] = scores, flags
    return result, prediction, values.iloc[:128]


def run(root, archive, output, ledger, lock):
    """Requires a previously written exact protocol/source lock."""
    output, root, ledger = Path(output), Path(root), Path(ledger)
    expected = {'protocol': PROTOCOL, 'sources': source_hashes(), 'versions': versions()}
    if json.loads(Path(lock).read_text()) != expected:
        raise ValueError('Pre-evaluation lock differs; do not proceed')
    if any((ledger/f'{name}.access.json').exists() for name in PROTOCOL['cohorts']):
        raise FileExistsError('Final cohort access already recorded; analyze saved predictions instead')
    manifest_raw = (root/'manifest.json').read_bytes()
    if sha(manifest_raw) != MANIFEST_SHA:
        raise ValueError('Wrong R3 manifest')
    manifest = json.loads(manifest_raw)
    model, artifact_manifest, archive_raw = read_archive(archive)
    # Establish ownership without reading any held-out rows.
    users, ids = set(), set()
    for name in ('train', 'validation', 'calibration'):
        raw = verified_csv(root, manifest, name)
        frame = pd.read_csv(io.BytesIO(raw), usecols=['user_id', 'transaction_id'])
        if users & set(frame.user_id) or ids & set(frame.transaction_id):
            raise ValueError('Development cohort overlap')
        users.update(frame.user_id); ids.update(frame.transaction_id)
    output.mkdir(exist_ok=False)
    write_json(output/'protocol_lock.json', expected)
    (output/'retained_alert_source.zip').write_bytes(archive_raw)
    write_json(output/'source_artifact_manifest.json', artifact_manifest)
    results = {}
    for name in PROTOCOL['cohorts']:
        print(f'Starting locked {name} evaluation', flush=True)
        begin_access(ledger, name, {'protocol_lock': sha(Path(lock).read_bytes()), 'model': ARCHIVE_SHA,
                                    'csv': manifest['cohorts'][name]['sha256']})
        raw = verified_csv(root, manifest, name)
        frame = validate_cohort(raw, manifest['cohorts'][name], users, ids)
        result, predictions, probe = evaluate_frame(model, frame)
        reloaded, _, _ = read_archive(archive)
        np.testing.assert_array_equal(model.score_samples(probe), reloaded.score_samples(probe))
        result.update(cohort=name, reload_parity_rows=len(probe), reload_max_abs_error=0.,
                      threshold=THRESHOLD, source_csv_sha256=manifest['cohorts'][name]['sha256'])
        predictions.to_csv(output/f'{name}_predictions.csv')
        write_json(output/f'{name}_metrics.json', result)
        write_json(ledger/f'{name}.completed.json', {'metrics_sha256': sha((output/f'{name}_metrics.json').read_bytes()),
                   'predictions_sha256': sha((output/f'{name}_predictions.csv').read_bytes())})
        users.update(frame.user_id); ids.update(frame.transaction_id)
        results[name] = result
        print(json.dumps(result, indent=2), flush=True)
    write_json(output/'final_results.json', {'protocol': PROTOCOL, 'results': results,
        'decision': 'retained model evaluated without changes; research frozen; integration separate'})
    write_json(output/'artifact_hashes.json', {p.name: sha(p.read_bytes()) for p in output.iterdir() if p.is_file()})
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write-lock', type=Path)
    parser.add_argument('--lock', type=Path)
    parser.add_argument('--dataset', type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--ledger', type=Path)
    args = parser.parse_args()
    if args.write_lock:
        write_json(args.write_lock, {'protocol': PROTOCOL, 'sources': source_hashes(), 'versions': versions()})
    elif all((args.lock, args.dataset, args.archive, args.output, args.ledger)):
        run(args.dataset, args.archive, args.output, args.ledger, args.lock)
    else:
        parser.error('Write a lock first, or provide --lock --dataset --archive --output --ledger')
