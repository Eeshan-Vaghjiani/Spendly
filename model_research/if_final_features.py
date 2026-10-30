"""Causal V2.1-derived behavioural features; no labels required for inference.

Equal user timestamps are a batch: none of its transactions can see another.
Timestamps must carry an offset; behavioural time is Africa/Nairobi.
"""
import numpy as np
import pandas as pd

FEATURES = [
    'log_amount', 'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos', 'is_weekend',
    'user_z', 'user_ratio', 'category_z', 'category_ratio', 'merchant_z', 'merchant_ratio',
    'positive_category_increase_ratio', 'log_gap_user_minutes', 'log_gap_category_minutes',
    'log_gap_merchant_minutes', 'log_gap_same_amount_minutes',
    'log_gap_same_merchant_amount_minutes', 'log_gap_same_category_amount_minutes',
    'same_amount_within_1h', 'same_amount_within_7d', 'same_merchant_amount_within_1h',
    'same_category_amount_within_1h', 'same_category_amount_within_7d',
    'ratio_previous_category', 'absolute_log_category_change',
    'log_user_txn_count_prev_1h', 'log_user_txn_count_prev_24h',
    'log_category_txn_count_prev_7d', 'is_recurring_category', 'recurring_amount_change',
    'recurring_increase_ratio', 'log_recurring_gap_days', 'category_prior_share',
    'merchant_prior_share', 'log_history_days', 'amount_vs_user_recent_median_50',
    'amount_vs_user_recent_q90_50', 'amount_vs_category_recent_median_20',
    'amount_vs_category_recent_q90_20',
]


def aware_dates(values):
    """Reject ambiguous naive timestamps, normalize unit and Nairobi timezone."""
    values = pd.Series(values)
    if isinstance(values.dtype, pd.DatetimeTZDtype):
        dates = pd.to_datetime(values, utc=True)
    else:
        text = values.astype(str)
        if not text.str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$', regex=True).all():
            raise ValueError('Every timestamp must include a timezone offset')
        dates = pd.to_datetime(values, utc=True, format='mixed', errors='raise')
    if dates.isna().any():
        raise ValueError('Missing timestamp')
    return dates.astype('datetime64[ns, UTC]').dt.tz_convert('Africa/Nairobi')


def validate_transactions(raw):
    required = {'transaction_id', 'user_id', 'transaction_timestamp', 'amount',
                'category', 'merchant', 'transaction_type'}
    if not required <= set(raw):
        raise ValueError(f'Missing columns: {sorted(required-set(raw))}')
    x = raw.copy()
    for name in ('transaction_id', 'user_id', 'category', 'merchant', 'transaction_type'):
        if x[name].isna().any() or x[name].astype(str).str.strip().eq('').any():
            raise ValueError(f'Missing {name}')
        x[name] = x[name].astype(str)
    if x.transaction_id.duplicated().any():
        raise ValueError('Duplicate transaction IDs')
    if not x.transaction_type.isin(['expense', 'income']).all():
        raise ValueError('Unsupported transaction type')
    x['amount'] = pd.to_numeric(x.amount, errors='raise').astype(float)
    if not np.isfinite(x.amount).all() or x.amount.le(0).any():
        raise ValueError('Amounts must be finite and positive')
    x['transaction_timestamp'] = aware_dates(x.transaction_timestamp)
    return x.sort_values(['user_id', 'transaction_timestamp', 'transaction_id']).reset_index(drop=True)


def build_features(raw):
    x = validate_transactions(raw)
    x = x.loc[x.transaction_type.eq('expense')].reset_index(drop=True)
    out = x.copy()
    amount = x.amount
    stamp = x.transaction_timestamp
    x['_square'] = amount**2
    x['_amount_key'] = amount.round(2)

    batch_indices = {}

    def batch_prior(series, keys):
        # Preserve NaNs: groupby.first() would skip them and leak another row.
        key = tuple(keys)
        if key not in batch_indices:
            groupers = [x[k] for k in keys] + [stamp]
            batch_indices[key] = pd.Series(np.arange(len(x))).groupby(groupers, sort=False).transform('min').to_numpy()
        return series.iloc[batch_indices[key]].reset_index(drop=True)

    def previous_count(keys):
        return batch_prior(x.groupby(keys, sort=False).cumcount().astype(float), keys)

    for prefix, keys in [('user', ['user_id']), ('category', ['user_id', 'category']),
                         ('merchant', ['user_id', 'merchant'])]:
        group = x.groupby(keys, sort=False)
        count = previous_count(keys)
        total = batch_prior(group.amount.cumsum()-amount, keys)
        square = batch_prior(group['_square'].cumsum()-x['_square'], keys)
        mean = total/count.replace(0, np.nan)
        variance = (square-total**2/count.replace(0, np.nan))/(count-1).where(count.gt(1))
        out[prefix+'_z'] = ((amount-mean)/(np.sqrt(variance.clip(lower=0))+1e-6)).clip(-20, 20)
        out[prefix+'_ratio'] = (amount/(mean+1)).clip(0, 50)

    prior_category = batch_prior(x.groupby(['user_id', 'category']).amount.shift(), ['user_id', 'category'])
    ratio = (amount+1)/(prior_category+1)
    out['ratio_previous_category'] = ratio.clip(0, 50)
    out['absolute_log_category_change'] = np.abs(np.log(ratio.clip(1e-4, 100))).clip(0, 5)
    out['positive_category_increase_ratio'] = (ratio-1).clip(0, 10)
    for prefix, keys, window, minimum in [('user', ['user_id'], 50, 10),
                                           ('category', ['user_id', 'category'], 20, 5)]:
        group = x.groupby(keys, sort=False).amount
        median = group.transform(lambda s: s.shift().rolling(window, min_periods=minimum).median())
        q90 = group.transform(lambda s: s.shift().rolling(window, min_periods=minimum).quantile(.9))
        for name, reference in [('median', median), ('q90', q90)]:
            out[f'amount_vs_{prefix}_recent_{name}_{window}'] = (amount/(batch_prior(reference, keys)+1)).clip(0, 50)

    def gap(keys, name):
        prior = batch_prior(x.groupby(keys, sort=False).transaction_timestamp.shift(), keys)
        minutes = (stamp-prior).dt.total_seconds()/60
        out[f'log_gap_{name}_minutes'] = np.log1p(minutes.clip(lower=0))
        return minutes

    gap(['user_id'], 'user')
    category_gap = gap(['user_id', 'category'], 'category')
    gap(['user_id', 'merchant'], 'merchant')
    for name, keys in [('same_amount', ['user_id', '_amount_key']),
                       ('same_merchant_amount', ['user_id', 'merchant', '_amount_key']),
                       ('same_category_amount', ['user_id', 'category', '_amount_key'])]:
        minutes = gap(keys, name)
        out[name+'_within_1h'] = minutes.le(60).astype(int)
        if name != 'same_merchant_amount':
            out[name+'_within_7d'] = minutes.le(7*24*60).astype(int)

    # Explicit nanoseconds; counts exclude every transaction in the current batch.
    ns = stamp.astype('datetime64[ns, Africa/Nairobi]').astype('int64').to_numpy()
    for name, keys, minutes in [('user_txn_count_prev_1h', ['user_id'], 60),
                               ('user_txn_count_prev_24h', ['user_id'], 1440),
                               ('category_txn_count_prev_7d', ['user_id', 'category'], 10080)]:
        counts = np.zeros(len(x))
        for positions in x.groupby(keys, sort=False).indices.values():
            t = ns[positions]
            counts[positions] = np.searchsorted(t, t, side='left')-np.searchsorted(t, t-minutes*60*10**9, side='left')
        out['log_'+name] = np.log1p(counts)

    hour = stamp.dt.hour+stamp.dt.minute/60
    dow = stamp.dt.dayofweek
    out['log_amount'] = np.log1p(amount)
    for name, values, period in [('hour', hour, 24), ('dow', dow, 7)]:
        out[name+'_sin'] = np.sin(2*np.pi*values/period)
        out[name+'_cos'] = np.cos(2*np.pi*values/period)
    out['is_weekend'] = dow.ge(5).astype(int)
    out['history_days'] = (stamp-x.groupby('user_id').transaction_timestamp.transform('min')).dt.total_seconds()/86400
    out['log_history_days'] = np.log1p(out.history_days)
    recurring = x.category.str.casefold().isin(['rent', 'utilities', 'subscriptions']).astype(int)
    out['is_recurring_category'] = recurring
    out['recurring_amount_change'] = out.absolute_log_category_change*recurring
    out['recurring_increase_ratio'] = out.positive_category_increase_ratio*recurring
    out['log_recurring_gap_days'] = np.log1p(category_gap/1440)*recurring
    for key in ('category', 'merchant'):
        out[key+'_prior_share'] = previous_count(['user_id', key])/(previous_count(['user_id'])+1)
    if np.isinf(out[FEATURES].to_numpy()).any():
        raise ValueError('Non-finite feature overflow')
    return out
