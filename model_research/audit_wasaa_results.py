"""Audit saved Wasaa model outputs; no model imports, training or inference.

Recompute metrics, cross-check checkpoint rows and quantify extreme outputs.
Only aggregate output is suitable for Git publication.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def metrics(actual, prediction):
    y, p = np.asarray(actual, dtype=float), np.asarray(prediction, dtype=float)
    if not len(y) or y.shape != p.shape or not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError('Expected paired finite predictions')
    if (y < 0).any() or (p < 0).any():
        raise ValueError('Negative expenditure')
    return {'rows': len(y), 'WAPE': float(np.abs(y-p).sum()/y.sum()) if y.sum() else None,
            'MAE_KES': float(mean_absolute_error(y, p)),
            'RMSE_KES': float(np.sqrt(mean_squared_error(y, p))),
            'R2': float(r2_score(y, p)) if np.unique(y).size > 1 else None,
            'bias_KES': float((p-y).mean()),
            'within20': float(np.mean(np.abs(y-p) <= np.where(y > 0, .2*y, 1e-9)))}


def validate_forecasts(frame):
    keys = ['user_id', 'target_week', 'scenario', 'model']
    if frame[keys].isna().any().any() or frame.duplicated(keys).any():
        raise ValueError('Missing or repeated forecast identity')
    expected = {('consumption', 'retained_lstm'), ('all_outflows', 'retained_lstm'),
                ('mapped_subset', 'retained_lstm'), ('mapped_subset', 'category_lstm')}
    if set(frame[['scenario', 'model']].itertuples(index=False, name=None)) != expected:
        raise ValueError('Unexpected scenario/model set')
    reference_keys = None
    for _, group in frame.groupby(['scenario', 'model']):
        metrics(group.actual, group.prediction)
        current = set(group[['user_id', 'target_week']].itertuples(index=False, name=None))
        if reference_keys is not None and current != reference_keys:
            raise ValueError('Scenario target coverage mismatch')
        reference_keys = current
    subset = frame.loc[frame.scenario.eq('mapped_subset')]
    pivot = subset.pivot(index=['user_id', 'target_week'], columns='model', values='actual')
    np.testing.assert_allclose(pivot.category_lstm, pivot.retained_lstm, atol=1e-6, rtol=1e-12)


def compare_record(actual, expected):
    if set(actual) != set(expected):
        raise ValueError('Metric fields differ')
    for key in actual:
        if actual[key] is None or expected[key] is None:
            if actual[key] != expected[key]:
                raise ValueError(f'Undefined metric mismatch: {key}')
        else:
            np.testing.assert_allclose(actual[key], expected[key], atol=1e-7, rtol=1e-10)


def bootstrap(frame, draws=1000):
    totals = frame.assign(error=np.abs(frame.prediction-frame.actual)).groupby('user_id')[['actual', 'error']].sum().to_numpy()
    rng = np.random.default_rng(2026)
    ratios = []
    for _ in range(draws):
        sample = totals[rng.integers(0, len(totals), len(totals))].sum(axis=0)
        if sample[0] <= 0:
            raise ValueError('Bootstrap denominator is zero')
        ratios.append(sample[1]/sample[0])
    return np.quantile(ratios, [.025, .975]).tolist()


def distribution(frame):
    error = np.abs(frame.prediction-frame.actual).to_numpy()
    order = np.sort(error)[::-1]
    return {'median_actual_KES': float(frame.actual.median()),
            'median_prediction_KES': float(frame.prediction.median()),
            'maximum_prediction_KES': float(frame.prediction.max()),
            'maximum_actual_KES': float(frame.actual.max()),
            'predictions_above_1million_KES': int(frame.prediction.gt(1e6).sum()),
            'predictions_above_1billion_KES': int(frame.prediction.gt(1e9).sum()),
            'top_one_row_fraction_absolute_error': float(order[0]/error.sum()) if error.sum() else 0.,
            'top_ten_rows_fraction_absolute_error': float(order[:10].sum()/error.sum()) if error.sum() else 0.}


def audit(directory):
    root = Path(directory)
    recorded_hashes = json.loads((root/'hashes.json').read_text())
    for name, expected in recorded_hashes.items():
        if Path(name).name != name or hashlib.sha256((root/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Result hash mismatch')
    recorded = json.loads((root/'results.json').read_text())
    forecasts = pd.read_csv(root/'forecasts.csv')
    categories = pd.read_csv(root/'categories.csv')
    alerts = pd.read_csv(root/'alerts.csv')
    validate_forecasts(forecasts)
    expected_dates = set(pd.date_range('2026-07-06', '2026-09-21', freq='7D').strftime('%Y-%m-%d'))
    if forecasts.user_id.nunique() != 500 or set(forecasts.target_week) != expected_dates:
        raise ValueError('Expected 500 households and twelve fixed weeks')
    if not forecasts.groupby(['scenario', 'model', 'user_id']).size().eq(12).all():
        raise ValueError('Incomplete household coverage')
    checked, distributions, intervals = 0, {}, {}
    for (scenario, model), group in forecasts.groupby(['scenario', 'model']):
        key = scenario+'/'+model
        compare_record(metrics(group.actual, group.prediction), recorded['forecast_metrics'][key])
        checked += 1
        distributions[key] = distribution(group)
        intervals[key] = bootstrap(group)
        if model == 'retained_lstm':
            compare_record(metrics(group.actual, group.last_week), recorded['forecast_metrics'][scenario+'/last_week'])
            checked += 1
    if categories.duplicated(['user_id', 'target_week', 'category']).any():
        raise ValueError('Repeated category target')
    if not categories.groupby(['user_id', 'target_week']).size().eq(9).all():
        raise ValueError('Category coverage incomplete')
    for name, group in categories.groupby('category'):
        compare_record(metrics(group.actual, group.prediction), recorded['category_metrics'][name])
        checked += 1
    sums = categories.groupby(['user_id', 'target_week'])[['actual', 'prediction']].sum().sort_index()
    overall = forecasts.loc[forecasts.model.eq('category_lstm')].set_index(['user_id', 'target_week']).sort_index()
    np.testing.assert_allclose(sums, overall[['actual', 'prediction']], atol=1e-6, rtol=1e-12)
    if alerts.transaction_id.duplicated().any() or not np.isfinite(alerts.score).all():
        raise ValueError('Invalid alert rows')
    np.testing.assert_array_equal(alerts.flag, alerts.score.ge(recorded['alerts']['threshold']))
    if len(alerts) != recorded['alerts']['rows'] or int(alerts.flag.sum()) != recorded['alerts']['alerts']:
        raise ValueError('Alert count mismatch')
    for kind, final in [('forecasts', forecasts), ('categories', categories), ('alerts', alerts)]:
        paths = sorted((root/'household_checkpoints').glob(f'*_{kind}.csv'))
        if len(paths) != 500:
            raise ValueError('Missing household checkpoint')
        combined = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
        pd.testing.assert_frame_equal(combined, final, check_exact=False, rtol=1e-12, atol=1e-6)
    return {'status': 'verified', 'method': 'saved-output rescore; no model inference',
            'result_hashes_verified': len(recorded_hashes), 'household_checkpoint_files_checked': 1500,
            'forecast_rows': len(forecasts), 'category_rows': len(categories), 'alert_rows': len(alerts),
            'metric_records_recomputed': checked, 'forecast_distributions': distributions,
            'WAPE_95pct_user_cluster_intervals': intervals,
            'interval_scope': 'post-run descriptive uncertainty, 1000 resamples seed2026; conditional on fixed models/scenario assumptions',
            'alert_score_range': [float(alerts.score.min()), float(alerts.score.max())],
            'extreme_outputs_preserved': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.results)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(result, indent=2))
