"""Actual frozen-artifact CPU readiness check on generated histories only."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from category_lstm_frozen import FrozenCategoryLSTM, HASHES, history_panel


def fixture(weeks=80):
    rows = []
    start = pd.Timestamp('2024-01-01T00:00:00+03:00')
    for week in range(weeks):
        # Deliberate leading/trailing quiet weeks, zero categories and regular bills.
        if week in (0, weeks-1):
            continue
        for day, category, amount in [(1, 'Food', 700.+week%5*100), (3, 'Transport', 350.)]:
            rows.append(dict(user_id='synthetic', transaction_id=f'{week}-{day}',
                transaction_timestamp=(start+pd.Timedelta(weeks=week, days=day, hours=12)).isoformat(),
                transaction_type='expense', category=category, amount=amount))
        if week%4 == 0:
            rows.append(dict(user_id='synthetic', transaction_id=f'{week}-bill',
                transaction_timestamp=(start+pd.Timedelta(weeks=week, days=2, hours=9)).isoformat(),
                transaction_type='expense', category='Rent', amount=12000.))
    return pd.DataFrame(rows), dict(owner='synthetic', observed_from=start,
        target_start=start+pd.Timedelta(weeks=weeks), as_of=start+pd.Timedelta(weeks=weeks, days=2),
        history_complete=True)


def check(directory):
    adapter = FrozenCategoryLSTM(directory, trusted=True)
    tensors = []
    for weeks in (26, 52, 80):
        records, coverage = fixture(weeks)
        panel = history_panel(records, **coverage)
        assert len(panel) == weeks and panel.total_spend.iloc[-1] == 0
        tensors.append(adapter.feature_tensor(panel))
    tensors = np.concatenate(tensors)
    batch = adapter.predict_tensor(tensors)
    individual = np.concatenate([adapter.predict_tensor(x[None, ...]) for x in tensors])
    # CPU batch kernels may differ in rounding; explicit KES tolerance.
    np.testing.assert_allclose(batch, individual, atol=.02, rtol=1e-5)
    loaded = FrozenCategoryLSTM(directory, trusted=True)
    reload = loaded.predict_tensor(tensors)
    np.testing.assert_array_equal(batch, reload)
    result = {'status': 'passed', 'scope': 'generated fixture inference only; no external quality evaluation',
              'CPU_only': True, 'model_input': [None,26,76], 'model_output': [None,9],
              'history_lengths_weeks': [26,52,80], 'forecast_rows': 3,
              'category_outputs': 27, 'max_batch_single_difference_KES': float(np.max(abs(batch-individual))),
              'max_reload_difference_KES': float(np.max(abs(batch-reload))),
              'artifact_hashes': HASHES, 'versions': adapter.versions,
              'scaler_fit_rows': {'input': int(adapter.x_scaler.n_samples_seen_),
                                  'target': int(adapter.y_scaler.n_samples_seen_)},
              'source_hashes': {name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                                for name in ('category_lstm_features.py','category_lstm_frozen.py')}}
    return result, batch


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--compare-run', type=Path)
    args = p.parse_args()
    result, batch = check(args.bundle)
    result['synthetic_forecasts_KES'] = batch.tolist()
    if args.compare_run:
        previous = json.loads(args.compare_run.read_text())
        np.testing.assert_allclose(batch, previous['synthetic_forecasts_KES'], atol=.02, rtol=1e-5)
        result['fresh_process_max_difference_KES'] = float(np.max(abs(batch-np.array(previous['synthetic_forecasts_KES']))))
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps(result, indent=2))
