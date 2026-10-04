"""Frozen 26-week category LSTM adapter for CPU-only evaluation.

No fit, recalibration or raw-data download. Explicit observed coverage is required.
Artifact hashes identify the reviewed Drive final bundle, not the earlier
development checkpoint. Joblib loading requires explicit trusted-artifact consent.
"""
import os
# Must be set before importing TensorFlow, including in the generated notebook.
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import hashlib
import importlib.metadata
import json
from pathlib import Path
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.preprocessing import StandardScaler

from category_lstm_features import add_model_features, SPEND_COLS, COUNT_COLS

HASHES = {
    'model.keras': 'd6250e19063756465bfd9b24760ee368c284ab30b5c4db272480c39263f78e1e',
    'input_scaler.pkl': '33acd1d92c6ea76275eedfd747b0133fcdef352a2a542242159b0493377417cd',
    'target_scaler.pkl': '50e2c03beaa3f665922a3c2ff50ac926c737ab38a1f0d8137b63f4a7cf1cbc0a',
    'metadata.json': '8b51ebe16e6c8725c7f1707bd825e7bd183fc3006a6e3edcedc45dc2033a140c',
}
CATEGORIES = ['Education', 'Entertainment', 'Food', 'Healthcare', 'Rent', 'Shopping',
              'Subscriptions', 'Transport', 'Utilities']
FEATURES = [name for i in range(9) for name in
            (f'log_spend_{i}', f'log_count_{i}', f'share_{i}', f'prior_active_rate4_{i}',
             f'prior_active_rate8_{i}', f'prior_active_rate13_{i}', f'log_spend_lag52_{i}',
             f'log_prior_mean13_{i}')]+['log_total_spend', 'log_total_count', 'week_sin', 'week_cos']


def version_record():
    return {name: importlib.metadata.version(name) for name in
            ('tensorflow', 'keras', 'numpy', 'pandas', 'scikit-learn', 'joblib')}


def timestamp(value):
    result = pd.Timestamp(value)
    if pd.isna(result) or result.tzinfo is None:
        raise ValueError('Timezone-aware timestamp required')
    return result.tz_convert('Africa/Nairobi')


def week_boundary(value):
    result = timestamp(value)
    if result.dayofweek != 0 or result != result.normalize():
        raise ValueError('Expected Monday midnight in Africa/Nairobi')
    return result


def history_panel(records, *, owner, observed_from, target_start, as_of, history_complete):
    """Construct only completed, explicitly observed weeks before target_start.

History must include all available covered transactions. Never use the target
week, fill unconfirmed gaps, or silently discard invalid/unmapped expense rows.
"""
    if history_complete is not True:
        raise ValueError('Complete recorded-history attestation required')
    start, target, now = week_boundary(observed_from), week_boundary(target_start), timestamp(as_of)
    weeks = (target-start).days//7
    if weeks < 26 or target > now:
        raise ValueError('At least 26 complete observed weeks before an available target required')
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError('Explicit household identity required')
    required = {'user_id', 'transaction_id', 'transaction_timestamp', 'transaction_type', 'amount', 'category'}
    if not isinstance(records, pd.DataFrame) or not required <= set(records):
        raise ValueError('Missing transaction fields')
    data = records.copy()
    if data[list(required)].isna().any().any():
        raise ValueError('Missing transaction values')
    if not data.user_id.astype(str).eq(owner).all():
        raise ValueError('History contains another household')
    if data.transaction_id.astype(str).str.strip().eq('').any() or data.transaction_id.duplicated().any():
        raise ValueError('Nonblank unique transaction IDs required')
    if not data.transaction_type.isin(['expense', 'income']).all():
        raise ValueError('Unknown transaction type')
    data['amount'] = pd.to_numeric(data.amount, errors='raise')
    if pd.api.types.is_bool_dtype(data.amount) or not np.isfinite(data.amount).all() or data.amount.lt(0).any():
        raise ValueError('Finite nonnegative KES required')
    data['transaction_timestamp'] = pd.to_datetime(
        [timestamp(value) for value in data.transaction_timestamp], utc=True).tz_convert('Africa/Nairobi')
    times = data.transaction_timestamp
    if (times < start).any() or (times >= target).any():
        raise ValueError('History rows must lie in the attested pre-target interval')
    expense = data.loc[data.transaction_type.eq('expense')].copy()
    if not expense.category.isin(CATEGORIES).all():
        raise ValueError('Unmapped expense category')
    dates = pd.date_range(start.tz_localize(None), periods=weeks, freq='7D')
    panel = pd.DataFrame({'user_id': owner, 'week': dates})
    for i, category in enumerate(CATEGORIES):
        subset = expense.loc[expense.category.eq(category)].copy()
        local = subset.transaction_timestamp.dt.tz_localize(None)
        subset['week'] = local.dt.to_period('W-SUN').dt.start_time
        grouped = subset.groupby('week').amount
        panel[f'spend_{i}'] = grouped.sum().reindex(dates, fill_value=0).to_numpy()
        panel[f'count_{i}'] = grouped.size().reindex(dates, fill_value=0).to_numpy()
    panel['total_spend'] = panel[SPEND_COLS].sum(axis=1)
    panel['total_count'] = panel[COUNT_COLS].sum(axis=1)
    return panel


class FrozenCategoryLSTM:
    def __init__(self, directory, *, trusted=False):
        if not trusted:
            raise PermissionError('Load only the verified project-owned model/scaler bundle')
        directory = Path(directory)
        for name, expected in HASHES.items():
            if hashlib.sha256((directory/name).read_bytes()).hexdigest() != expected:
                raise ValueError(f'Artifact hash mismatch: {name}')
        self.metadata = json.loads((directory/'metadata.json').read_text())
        if (self.metadata['categories'] != CATEGORIES or self.metadata['feature_columns'] != FEATURES
                or self.metadata['sequence_window_weeks'] != 26):
            raise ValueError('Unsupported category/feature contract')
        versions = version_record()
        for package, expected in {'tensorflow': '2.20.0', 'keras': '3.13.2', 'scikit-learn': '1.6.1'}.items():
            if versions[package] != expected:
                raise ValueError(f'Expected {package} {expected}, found {versions[package]}')
        import tensorflow as tf
        # Fail rather than use an initialized accelerator supplied by another cell.
        tf.config.set_visible_devices([], 'GPU')
        if tf.config.get_visible_devices('GPU'):
            raise RuntimeError('CPU-only execution required')
        with tf.device('/CPU:0'):
            self.model = tf.keras.models.load_model(directory/'model.keras', compile=False, safe_mode=True)
        if tuple(self.model.input_shape) != (None, 26, 76) or tuple(self.model.output_shape) != (None, 9):
            raise ValueError('Unexpected model dimensions')
        with warnings.catch_warnings():
            warnings.simplefilter('error', InconsistentVersionWarning)
            self.x_scaler = joblib.load(directory/'input_scaler.pkl')
            self.y_scaler = joblib.load(directory/'target_scaler.pkl')
        for scaler, dimension in ((self.x_scaler, 76), (self.y_scaler, 9)):
            if type(scaler) is not StandardScaler or scaler.n_features_in_ != dimension:
                raise ValueError('Unexpected scaler type/dimension')
            if not np.isfinite(scaler.mean_).all() or not np.isfinite(scaler.scale_).all() or (scaler.scale_ <= 0).any():
                raise ValueError('Invalid frozen scaler statistics')
        self.versions = versions

    def feature_tensor(self, panel):
        features, columns = add_model_features(panel)
        if columns != FEATURES or len(features) < 26:
            raise ValueError('Invalid feature input')
        values = features[FEATURES].tail(26).to_numpy(dtype=np.float32)
        if not np.isfinite(values).all():
            raise ValueError('Nonfinite feature input')
        tensor = self.x_scaler.transform(values).astype(np.float32)[None, ...]
        if not np.isfinite(tensor).all():
            raise ValueError('Nonfinite scaled feature input')
        return tensor

    def predict_tensor(self, tensor):
        import tensorflow as tf
        tensor = np.asarray(tensor, dtype=np.float32)
        if tensor.ndim != 3 or tensor.shape[1:] != (26, 76) or not np.isfinite(tensor).all():
            raise ValueError('Expected finite N x 26 x 76 input')
        with tf.device('/CPU:0'):
            scaled = self.model(tensor, training=False).numpy()
        with np.errstate(over='raise', invalid='raise'):
            amounts = np.maximum(0., np.expm1(self.y_scaler.inverse_transform(scaled)))
        if not np.isfinite(amounts).all():
            raise ValueError('Nonfinite forecast output')
        return amounts

    def forecast(self, records, **coverage):
        panel = history_panel(records, **coverage)
        amounts = self.predict_tensor(self.feature_tensor(panel))[0]
        return {'target_start': week_boundary(coverage['target_start']).isoformat(),
                'category_forecasts_KES': dict(zip(CATEGORIES, map(float, amounts))),
                'total_forecast_KES': float(amounts.astype(float).sum()),
                'history_weeks': len(panel), 'model': HASHES['model.keras'],
                'quality_status': 'final_refit_external_evaluation_pending'}
