"""Predeclared equal-weight seed-ensemble diagnostic on saved train-fold rows.

No model loading, fitting, weight selection, raw data, validation CSV or holdout
access. Reads only three reference CSVs after checking the pinned archive/hash.
Historical folds are reused exploratory evidence, not an independent test.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from analyze_v7_checkpoint import metrics, validate_prediction_rows

ARCHIVE_SHA256 = 'e3c3b893a51d9f29976a0245a290699a829cb4c65d49a793a985f9c18972089e'
SEEDS = (42, 123, 2026)
KEYS = ['user_id', 'target_week', 'fold']
PROTOCOL = {
    'name': 'lstm-equal-seed-ensemble-diagnostic-v1',
    'sources': 'three saved v6_reference train-fold prediction CSVs from pinned V9 archive',
    'candidate': 'unweighted arithmetic mean of seed42/123/2026 predictions',
    'comparator': 'seed42 reference fixed before this diagnostic; also report all seeds',
    'selection': 'no optimized weights, offsets, clipping changes or candidate search',
    'material_gain_WAPE_pp': 1.0,
    'uncertainty': '1000 paired user-cluster resamples, seed2026; conditional on reused folds',
    'scope': 'exploratory development diagnostic only; no promotion or independent quality claim',
}


def align(frames):
    if set(frames) != set(SEEDS):
        raise ValueError('Require exactly the three predeclared seeds')
    base = None
    for seed in SEEDS:
        frame = frames[seed].copy()
        required = set(KEYS + ['actual', 'prediction', 'residual', 'absolute_error',
                              'recurring_median', 'seed', 'candidate'])
        if not required <= set(frame) or frame.empty:
            raise ValueError('Missing or empty prediction columns')
        if frame[KEYS].isna().any().any() or not frame.seed.eq(seed).all() or not frame.candidate.eq('v6_reference').all():
            raise ValueError('Invalid prediction identity')
        validate_prediction_rows(frame)
        if not np.isfinite(frame[['actual', 'prediction', 'recurring_median']].to_numpy()).all() or frame.actual.lt(0).any():
            raise ValueError('Non-finite or negative target')
        frame['target_week'] = pd.to_datetime(frame.target_week, errors='raise')
        if frame.target_week.isna().any():
            raise ValueError('Missing target week')
        frame = frame.sort_values(KEYS).reset_index(drop=True)
        if base is None:
            base = frame.copy()
        else:
            if not frame[KEYS].equals(base[KEYS]):
                raise ValueError('Seed user/week/fold coverage differs')
            for column in ('actual', 'recurring_median'):
                np.testing.assert_allclose(frame[column], base[column], rtol=0, atol=1e-8)
        base[f'seed_{seed}'] = frame.prediction.to_numpy()
    base['ensemble'] = base[[f'seed_{seed}' for seed in SEEDS]].mean(axis=1)
    return base


def compare(frames):
    data = align(frames)
    if data.actual.sum() <= 0:
        raise ValueError('Positive pooled actual spending required for WAPE')
    report = {'protocol': PROTOCOL, 'rows': len(data), 'users': data.user_id.nunique(),
              'first_target_week': str(data.target_week.min()), 'last_target_week': str(data.target_week.max()),
              'metrics': {name: metrics(data, name) for name in
                          [f'seed_{seed}' for seed in SEEDS]+['ensemble', 'recurring_median']}}
    errors = pd.DataFrame({'user_id': data.user_id, 'actual': data.actual,
                          'ensemble': abs(data.ensemble-data.actual),
                          'reference': abs(data.seed_42-data.actual)})
    grouped = errors.groupby('user_id', sort=True)[['actual', 'ensemble', 'reference']].sum().to_numpy()
    rng = np.random.default_rng(2026)
    differences = []
    for _ in range(1000):
        total = grouped[rng.integers(0, len(grouped), len(grouped))].sum(axis=0)
        if total[0] <= 0:
            raise ValueError('Bootstrap sample has zero denominator')
        differences.append(100*(total[1]-total[2])/total[0])
    report['ensemble_minus_seed42_WAPE_pp_95'] = np.quantile(differences, [.025, .975]).tolist()
    report['gain_vs_seed42_WAPE_pp'] = 100*(report['metrics']['seed_42']['WAPE']-report['metrics']['ensemble']['WAPE'])
    report['material_gain_met'] = report['gain_vs_seed42_WAPE_pp'] >= PROTOCOL['material_gain_WAPE_pp']
    report['fold_metrics'] = {str(fold): {name: metrics(part, name) for name in ('seed_42', 'ensemble')}
                              for fold, part in data.groupby('fold')}
    report['users_lower_error'] = int((grouped[:, 1] < grouped[:, 2]).sum())
    report['users_higher_error'] = int((grouped[:, 1] > grouped[:, 2]).sum())
    report['users_equal_error'] = int((grouped[:, 1] == grouped[:, 2]).sum())
    report['decision'] = 'no_model_promotion_from_reused_diagnostic'
    return report


def analyze(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('Unexpected archive; use the verified final V9 export')
    accessed = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive members')
        manifest = json.loads(archive.read('artifact_manifest.json'))
        accessed.append('artifact_manifest.json')
        frames = {}
        for seed in SEEDS:
            name = f'v6_reference_seed_{seed}_fraction_1.0_predictions.csv'
            content = archive.read(name)
            accessed.append(name)
            if hashlib.sha256(content).hexdigest() != manifest['files'][name]:
                raise ValueError('Prediction hash mismatch')
            frames[seed] = pd.read_csv(io.BytesIO(content))
    result = compare(frames)
    # These are training-user outer folds, not the final validation export.
    if result['rows'] != 7200 or result['users'] != 600 or any(
            pd.to_datetime(frame.target_week).max() >= pd.Timestamp('2023-04-24') for frame in frames.values()):
        raise ValueError('Unexpected development coverage')
    result.update(archive_sha256=ARCHIVE_SHA256, verified_prediction_files=3,
                  members_parsed=accessed, raw_data_opened=False, model_loaded=False,
                  validation_or_final_prediction_files_parsed=False)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = analyze(args.archive)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2, allow_nan=False)
    print(json.dumps(result, indent=2))
