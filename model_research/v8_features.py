"""V8 observed-income features layered over the unchanged V7 expense reference.

Embedded after V7 worker definitions. No income is added to expense targets,
recurrence discovery, scaling, or baseline reconstruction. Future receipts and
generator profile/label fields are never feature inputs.
"""

V8_INCOME_CONTEXT = (
    'income_observed', 'income_recent', 'income_age', 'income_last_amount',
    'income_mean26', 'income_to_expense8', 'income_cadence', 'income_cadence_mad',
    'income_cadence_known', 'income_phase', 'month_sin', 'month_cos',
)
V8_INCOME_SEQUENCE = ('income_amount', 'income_receipts')
_v7_expense_clean = clean_data
_v7_make_features = make_features


def expense_eligible(data):
    """Retain receipts only for users with observed expenses in this permitted slice."""
    users=set(data.loc[data.transaction_type.eq('expense'),'user_id'])
    return data.loc[data.user_id.isin(users)].copy().reset_index(drop=True)


def clean_data(raw, blank_normal=False):
    """Validate all transactions via the existing cleaner, retaining receipt type."""
    if 'transaction_id' not in raw:
        raise ValueError('V8 input requires explicit transaction IDs')
    kinds = raw.get('transaction_type', pd.Series('expense', index=raw.index)).astype(str).str.strip().str.lower()
    if not kinds.isin(['expense', 'income']).all():
        raise ValueError('transaction_type must be expense or income')
    types = pd.Series(kinds.to_numpy(), index=raw.transaction_id.astype(str).str.strip())
    validated = _v7_expense_clean(raw.assign(transaction_type='expense'), blank_normal)
    validated['transaction_type'] = validated.transaction_id.map(types)
    if not validated.transaction_type.eq('expense').any():
        raise ValueError('No expense records found')
    return expense_eligible(validated)


def make_features(data, config, reference=False):
    """Build V6-identical expense tensors, then append declared observed channels."""
    expenses = data.loc[data.transaction_type.eq('expense')].copy()
    extra_seq = tuple(n for n in config.sequence_features if n in V8_INCOME_SEQUENCE or n.startswith('category_'))
    extra_ctx = tuple(n for n in config.context_features if n in V8_INCOME_CONTEXT)
    base = replace(config,
        sequence_features=tuple(n for n in config.sequence_features if n not in extra_seq),
        context_features=tuple(n for n in config.context_features if n not in extra_ctx))
    frame, sequence, context = _v7_make_features(expenses, base, reference)
    if not extra_seq and not extra_ctx:
        return frame, sequence, context
    if any(n=='category_PENDING' for n in extra_seq):
        raise ValueError('Resolve category vocabulary on fit users before feature generation')
    seq_extra = np.zeros((len(frame),config.lookback,len(extra_seq)),dtype='float32')
    ctx_extra = np.zeros((len(frame),len(extra_ctx)),dtype='float32')
    for user, positions in frame.groupby('user_id',sort=False).indices.items():
        group = data.loc[data.user_id.eq(user)]
        income = group.loc[group.transaction_type.eq('income')].sort_values('transaction_timestamp')
        expense = expenses.loc[expenses.user_id.eq(user)]
        # Merge receipts sharing a timestamp to avoid artificial zero-length cadence.
        receipts = income.groupby('transaction_timestamp').amount.agg(['sum','size'])
        for position in positions:
            row = frame.iloc[position]; origin = row.time
            earlier = receipts.loc[receipts.index<origin]
            history = earlier.loc[earlier.index>=origin-pd.Timedelta(weeks=26)]
            recent = history.loc[history.index>=origin-pd.Timedelta(weeks=8)]
            scale = float(row.scale)
            age = min((origin-earlier.index[-1]).total_seconds()/86400.,182.) if len(earlier) else 182.
            dates = history.index.normalize().unique()
            gaps = np.diff(dates.to_numpy())/np.timedelta64(1,'D')
            known = len(gaps)>=2
            cadence = float(np.median(gaps)) if known else 0.
            spread = float(np.median(np.abs(gaps-cadence))) if known else 0.
            past_expense = expense.loc[expense.transaction_timestamp.ge(origin-pd.Timedelta(weeks=8))
                                       & expense.transaction_timestamp.lt(origin),'amount'].sum()
            # Last observed receipt only; no generated/assumed future paycheck.
            values = dict(income_observed=float(len(earlier)>0),income_recent=float(len(history)>0),
                income_age=age/182.,income_last_amount=float(history['sum'].iloc[-1])/scale if len(history) else 0.,
                income_mean26=float(history['sum'].sum())/26./scale,
                income_to_expense8=float(recent['sum'].sum())/max(float(past_expense),1.),
                income_cadence=cadence/31.,income_cadence_mad=spread/31.,income_cadence_known=float(known),
                income_phase=min(age/max(cadence,1.),4.)/4. if known else 0.,
                month_sin=float(np.sin(2*np.pi*(origin.day-1)/origin.days_in_month)),
                month_cos=float(np.cos(2*np.pi*(origin.day-1)/origin.days_in_month)))
            ctx_extra[position] = [values[n] for n in extra_ctx]
            boundaries = pd.date_range(origin-pd.Timedelta(weeks=config.lookback),origin,freq='7D')
            for week in range(config.lookback):
                left,right = boundaries[week],boundaries[week+1]
                observed = history.loc[(history.index>=left)&(history.index<right)]
                spending = expense.loc[expense.transaction_timestamp.ge(left)&expense.transaction_timestamp.lt(right)]
                for j,name in enumerate(extra_seq):
                    if name=='income_amount': value=float(observed['sum'].sum())/scale
                    elif name=='income_receipts': value=float(observed['size'].sum())
                    else:
                        category=name.removeprefix('category_')
                        mask=~spending.category.isin(config.category_vocabulary[:-1]) if category=='OTHER' else spending.category.eq(category)
                        value=float(spending.loc[mask,'amount'].sum())/scale
                    seq_extra[position,week,j]=value
    if not np.isfinite(seq_extra).all() or not np.isfinite(ctx_extra).all():
        raise ValueError('Nonfinite income/category features')
    # Configurations append extras; refuse ambiguous feature-order contracts.
    if config.sequence_features!=base.sequence_features+extra_seq or config.context_features!=base.context_features+extra_ctx:
        raise ValueError('V8 extra features must be appended in configured order')
    return frame,np.concatenate([sequence,seq_extra],axis=-1),np.concatenate([context,ctx_extra],axis=1)
