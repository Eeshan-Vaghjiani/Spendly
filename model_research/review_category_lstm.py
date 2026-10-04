"""Inspect a hash-identified notebook as evidence, not an executable workflow.

Only named, manually reviewed pure preprocessing/metric functions are extracted
for synthetic probes. No installation, Drive access, training or model loading.
"""
import argparse
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

NOTEBOOK_SHA = 'e760268cb1d1fd0dfc40bf8c632cfcb2485040d4c6e44172cee37472b5601a6f'
FUNCTIONS = {'prepare_expense_transactions', 'build_weekly_user_matrix',
             'add_model_features', 'make_sequences', 'smape', 'wape',
             'basic_metrics', 'multioutput_metrics', 'inverse_targets'}


def inspect(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != NOTEBOOK_SHA:
        raise ValueError('Notebook differs from the reviewed version')
    nb = json.loads(raw)
    nodes = []
    parsed = 0
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] != 'code':
            continue
        tree = ast.parse(''.join(cell['source']), filename=f'cell_{i}')
        parsed += 1
        nodes.extend(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in FUNCTIONS)
    if {n.name for n in nodes} != FUNCTIONS or len(nodes) != len(FUNCTIONS):
        raise ValueError('Unexpected function inventory')
    ns = dict(np=np, pd=pd, StandardScaler=StandardScaler, mean_absolute_error=mean_absolute_error,
              mean_squared_error=mean_squared_error, r2_score=r2_score, USER_COL='user_id',
              DATE_COL='transaction_timestamp', AMOUNT_COL='amount', CATEGORY_COL='category',
              TYPE_COL='transaction_type', EXPENSE_VALUE='expense', DROP_EXACT_DUPLICATES=False,
              SPEND_COLS=['spend_0'], COUNT_COLS=['count_0'], manifest={'weeks_per_user': 60})
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'reviewed_notebook_functions', 'exec'), ns)
    return nb, ns, parsed


def fixture():
    parts = []
    for user in ('a', 'b'):
        for week in range(60):
            value = float(100+week)
            parts.append({'user_id': user, 'week': pd.Timestamp('2021-01-04')+pd.Timedelta(weeks=week),
                          'spend_0': value, 'count_0': 1., 'total_spend': value, 'total_count': 1.})
    return pd.DataFrame(parts)


def probe(ns):
    panel = fixture()
    features, columns = ns['add_model_features'](panel)
    ns.update(FEATURE_COLS=columns, TARGET_COLS=['spend_0'])
    xs = StandardScaler().fit(features[columns].to_numpy(dtype=np.float32))
    ys = StandardScaler().fit(np.log1p(features[['spend_0']].to_numpy(dtype=np.float32)))
    x, y, meta = ns['make_sequences'](features, 16, xs, ys)
    changed = panel.copy()
    changed.loc[changed.week >= pd.Timestamp('2021-10-04'), 'spend_0'] *= 20
    changed['total_spend'] = changed.spend_0
    changed_features, _ = ns['add_model_features'](changed)
    xx, _, changed_meta = ns['make_sequences'](changed_features, 16, xs, ys)
    same = meta.target_week <= pd.Timestamp('2021-10-04')
    np.testing.assert_array_equal(x[same], xx[same])
    pd.testing.assert_frame_equal(meta, changed_meta)
    np.testing.assert_allclose(ns['inverse_targets'](y, ys).ravel(),
                               features.loc[features.groupby('user_id').cumcount().ge(16), 'spend_0'], atol=.001)
    _, _, long_meta = ns['make_sequences'](features, 26, xs, ys)
    income = pd.DataFrame({'user_id': ['a'], 'transaction_timestamp': ['2021-01-04T12:00:00+03:00'],
                           'amount': [1000.], 'category': ['Income'], 'transaction_type': ['income']})
    with contextlib.redirect_stdout(io.StringIO()):
        retained_income = ns['prepare_expense_transactions'](income, 'fixture')
        expense = income.assign(category='Food', transaction_type='expense')
        span = pd.concat([expense, expense.assign(transaction_timestamp='2021-01-18T12:00:00+03:00')], ignore_index=True)
        span['observation_start'] = '2020-12-28T00:00:00+03:00'
        span['observation_end'] = '2021-02-01T00:00:00+03:00'
        span = ns['prepare_expense_transactions'](span, 'fixture')
        weekly, _, _ = ns['build_weekly_user_matrix'](span, ['Food'], 'fixture')
    smape = ns['smape']([0., 100.], [0., 0.])
    return {
        'causal_sequence_future_invariance': True,
        'target_inverse_round_trip_atol_KES': .001,
        'lookback16_rows': len(meta), 'lookback26_rows': len(long_meta),
        'lookback_comparison_changes_target_population': len(meta) != len(long_meta),
        'income_only_rows_retained_as_expenses': len(retained_income),
        'declared_coverage_weeks': 5, 'emitted_weeks': len(weekly),
        'first_emitted_week': str(weekly.week.min()), 'last_emitted_week': str(weekly.week.max()),
        'smape_excluding_joint_zeros': smape, 'smape_including_joint_zeros_as_zero': 100.,
        'scope': 'generated fixtures only; no saved estimator executed',
    }


def review(path):
    nb, ns, parsed = inspect(path)
    # The selected metrics are printed JSON in the development-search output.
    text = ''.join(''.join(o.get('text', [])) for o in nb['cells'][33].get('outputs', []))
    marker = 'Selected validation metrics:\n'
    selected = json.JSONDecoder().raw_decode(text.split(marker)[1].lstrip())[0]
    if selected['Total WAPE (%)'] > selected['Category WAPE (%)']:
        raise ValueError('Category/total absolute-error inequality violated')
    tests = probe(ns)
    return {'notebook_sha256': NOTEBOOK_SHA, 'cells': len(nb['cells']), 'code_cells_parsed': parsed,
            'selected_validation_metrics_reported': selected, 'probes': tests,
            'metrics_recomputed_from_saved_predictions': False,
            'selected_model': 'LSTM_128_MAE / window26 / 76 features / 9 outputs',
            'decision': 'retain existing total forecaster; category candidate needs matched development validation',
            'no_training_or_external_data_access': True}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--notebook', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = review(args.notebook)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps(result, indent=2))
