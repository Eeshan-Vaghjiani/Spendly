"""CPU-only V7 features. Reference functions are supplied by the notebook builder."""
from dataclasses import dataclass, asdict, replace
import time


@dataclass(frozen=True)
class ForecastConfig:
    lookback: int = 8
    sequence_features: tuple = ('total', 'nonrecurring')
    context_features: tuple = ('mean4', 'std8', 'recurring', 'nonrecurring',
        'log_scale', 'nonrec_median', 'nonrec_std', 'due_confidence', 'count4', 'zero_fraction')
    category_vocabulary: tuple = ()
    target_transform: str = 'mean_residual'
    scale_method: str = 'mean'
    units: int = 32
    l2: float = .001
    learning_rate: float = .0003
    batch_size: int = 256
    max_epochs: int = 120
    seed: int = 42
    schedule: str = 'fixed'
    monitor: str = 'val_weighted_mae'
    patience: int = 10
    min_delta: float = 1e-4
    ablation: str = 'full'
    context_branch: bool = False
    clipnorm: float = 1.
    loss: str = 'mae'

    def validate(self):
        assert self.lookback in (8, 13, 26)
        assert self.target_transform in ('mean_residual', 'median_residual')
        assert self.scale_method in ('mean', 'mad')
        assert len(set(self.sequence_features)) == len(self.sequence_features)
        assert len(set(self.context_features)) == len(self.context_features)
        assert self.ablation in ('full', 'sequence_only', 'context_only', 'shuffled')
        assert self.schedule in ('fixed', 'plateau')
        assert self.loss in ('mae', 'huber')
        assert self.units > 0 and self.batch_size > 0 and self.max_epochs > 0
        return self


def feature_columns(lookback):
    return ([f'lag{i}' for i in range(1, lookback+1)] +
            [f'nonrec_lag{i}' for i in range(1, lookback+1)] +
            list(ForecastConfig().context_features))


def make_features(data, config, reference=False):
    """Causal schedules use [cutoff-26 weeks,cutoff); target is [cutoff,cutoff+7d).

    Nonrecurring lag amounts are classified using information at that forecast
    cutoff, not the subsequent target. Sequence is ordered oldest -> newest.
    All alternatives retain the original eight-week baseline for comparisons.
    """
    config.validate()
    fun = forecast_reference_config if reference else forecast_fast_config
    f, x, skipped = fun(data, config.lookback)
    if f.empty:
        raise ValueError('Insufficient complete history; no fabricated target windows')
    if config.lookback != 8:
        original, _, _ = fun(data, 8)
        aligned = original.set_index(['user_id','time']).loc[pd.MultiIndex.from_frame(f[['user_id','time']])]
        for name in ('recurring','robust_recurring','due','nonrec_mean','last','mean4'):
            f[name] = aligned[name].to_numpy()
    seqs, contexts, diagnostics = [], [], []
    for uid, positions in f.groupby('user_id', sort=False).indices.items():
        group = data.loc[data.user_id.eq(uid)]
        start, end = group.observation_start.iloc[0], group.observation_end.iloc[0]
        first = start.normalize() + pd.Timedelta(days=(-start.weekday()) % 7)
        last = end.normalize()-pd.Timedelta(days=end.weekday())
        boundaries = pd.date_range(first, last, freq='7D')
        week = group.transaction_timestamp.dt.normalize()-pd.to_timedelta(group.transaction_timestamp.dt.weekday,unit='D')
        totals = group.groupby(week).amount.sum().reindex(boundaries[:-1],fill_value=0.).to_numpy()
        counts = group.groupby(week).size().reindex(boundaries[:-1],fill_value=0.).to_numpy()
        days = group.assign(day=group.transaction_timestamp.dt.normalize()).groupby(week).day.nunique().reindex(boundaries[:-1],fill_value=0.).to_numpy()
        largest = group.groupby(week).amount.max().reindex(boundaries[:-1],fill_value=0.).to_numpy()
        weekend_mask=group.transaction_timestamp.dt.weekday.ge(5)
        weekend_totals=group.loc[weekend_mask].groupby(week[weekend_mask]).amount.sum().reindex(boundaries[:-1],fill_value=0.).to_numpy()
        cats = {}
        for cat in config.category_vocabulary:
            chosen = ~group.category.isin(config.category_vocabulary[:-1]) if cat == 'OTHER' else group.category.eq(cat)
            cats[cat] = group.loc[chosen].groupby(week[chosen]).amount.sum().reindex(boundaries[:-1],fill_value=0.).to_numpy()
        for pos in positions:
            row, base = f.iloc[pos], x.iloc[pos]
            i = boundaries.get_loc(row.time)
            past = totals[i-config.lookback:i]
            mean_scale = float(row.scale)
            median = float(np.median(past))
            mad = float(np.median(np.abs(past-median))) * 1.4826
            scale = mean_scale if config.scale_method == 'mean' else max(mad, median*.1, 1.)
            total = np.asarray([base[f'lag{k}'] for k in range(config.lookback,0,-1)]) * mean_scale
            nonrec = np.asarray([base[f'nonrec_lag{k}'] for k in range(config.lookback,0,-1)]) * mean_scale
            channels = dict(total=total/scale, nonrecurring=nonrec/scale,
                            count=counts[i-config.lookback:i], active_days=days[i-config.lookback:i]/7.,
                            ticket_mean=totals[i-config.lookback:i]/np.maximum(counts[i-config.lookback:i],1.)/scale,
                            largest_share=largest[i-config.lookback:i]/np.maximum(totals[i-config.lookback:i],1.),
                            weekend_share=weekend_totals[i-config.lookback:i]/np.maximum(totals[i-config.lookback:i],1.))
            context = base.to_dict()
            # Keep V6 context values exactly for control; alternative robust scale is
            # explicit and affects only normalized monetary quantities.
            for name in ('mean4','std8','recurring','nonrecurring','nonrec_median','nonrec_std'):
                context[name] *= mean_scale/scale
            context['log_scale'] = np.log(scale)
            recent = totals[max(0,i-13):i]
            context.update(rolling_median=median/scale, rolling_mad=mad/scale,
                recent_ratio=float(past[-4:].mean()/max(past.mean(),1.)),
                trend13=float((recent[-4:].mean()-recent[:4].mean())/scale),
                week_sin=np.sin(2*np.pi*row.time.isocalendar().week/52.1775),
                week_cos=np.cos(2*np.pi*row.time.isocalendar().week/52.1775))
            denominator=max(float(totals[max(0,i-13):i].sum()),1.)
            for cat, values in cats.items():
                context['share_'+cat] = float(values[max(0,i-13):i].sum()/denominator)
            seqs.append((pos,np.stack([channels[n] for n in config.sequence_features],axis=-1)))
            contexts.append((pos,[context[n] for n in config.context_features]))
            diagnostics.append((pos,dict(volatility=float(past.std()/max(past.mean(),1.)),
                activity=float(counts[i-config.lookback:i].mean()), zero_fraction=float(np.mean(past==0)),
                recurring_share=float(row.due/max(row.recurring,1.)), scale=scale,
                feature_end=row.time-pd.Timedelta(nanoseconds=1))))
    sequence=np.asarray([v for _,v in sorted(seqs)],dtype='float32')
    context=np.asarray([v for _,v in sorted(contexts)],dtype='float32')
    details=pd.DataFrame([v for _,v in sorted(diagnostics)])
    for col in details:
        f[col]=details[col].to_numpy()
    f['center']=f.recurring if config.target_transform=='mean_residual' else f.robust_recurring
    assert (f.feature_end < f.time).all(), 'Target dates overlap feature dates'
    assert (f.end == f.time+pd.Timedelta(weeks=1)).all()
    assert np.isfinite(sequence).all() and np.isfinite(context).all()
    return f, sequence, context


def cached_user(raw, config, cache_dir, code_hash):
    """Only self-created numeric NPZ/CSV caches; configuration and content verified."""
    feature_keys=('lookback','sequence_features','context_features','category_vocabulary','target_transform','scale_method')
    metadata=dict(config={k:asdict(config)[k] for k in feature_keys}, code=code_hash, numpy=np.__version__, pandas=pd.__version__,
        data=hashlib.sha256(pd.util.hash_pandas_object(raw,index=True).values.tobytes()).hexdigest())
    metadata=json.loads(json.dumps(metadata,sort_keys=True))
    key=hashlib.sha256(json.dumps(metadata,sort_keys=True).encode()).hexdigest()
    folder=Path(cache_dir)/key
    marker=folder/'complete.json'
    if marker.exists():
        saved=json.loads(marker.read_text())
        if saved['metadata'] != metadata:
            raise ValueError('Cached metadata differs from active feature configuration')
        for name,digest in saved['hashes'].items():
            if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Corrupt feature cache')
    else:
        f,s,c=make_features(raw,config)
        folder.mkdir(parents=True,exist_ok=True)
        f.to_csv(folder/'rows.csv',index=False)
        np.savez_compressed(folder/'features.npz',sequence=s,context=c)
        hashes={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in ('rows.csv','features.npz')}
        marker.write_text(json.dumps(dict(metadata=metadata,hashes=hashes),sort_keys=True))
    f=pd.read_csv(folder/'rows.csv',dtype={'user_id':str},parse_dates=['time','end','feature_end'])
    with np.load(folder/'features.npz',allow_pickle=False) as arrays:
        return f,arrays['sequence'],arrays['context']


def check_causal_parity(data):
    """Deterministic sample, all lookbacks, unequal ties, future amount/category edits."""
    sample=data.loc[data.user_id.eq(sorted(data.user_id.unique())[0])].copy()
    for lookback in (8,13,26):
        cfg=ForecastConfig(lookback=lookback)
        f,s,c=make_features(sample,cfg)
        rf,rs,rc=make_features(sample,cfg,reference=True)
        pd.testing.assert_frame_equal(f,rf,check_exact=False,rtol=1e-9,atol=1e-7)
        np.testing.assert_allclose(s,rs,rtol=1e-6,atol=1e-6)
        np.testing.assert_allclose(c,rc,rtol=1e-6,atol=1e-6)
        cutoff=f.time.iloc[len(f)//2]
        edited=sample.copy()
        future=edited.transaction_timestamp.ge(cutoff)
        edited.loc[future,'amount']=edited.loc[future,'amount']*17+123
        edited.loc[future,'category']='FUTURE_ONLY'
        ef,es,ec=make_features(edited,cfg)
        before=f.time.le(cutoff).to_numpy()
        np.testing.assert_allclose(s[before],es[before],rtol=0,atol=0)
        np.testing.assert_allclose(c[before],ec[before],rtol=0,atol=0)
        np.testing.assert_allclose(f.loc[before,'center'],ef.loc[before,'center'],rtol=0,atol=0)
    return dict(status='passed',lookbacks=[8,13,26],float32_tolerance=1e-6,
                future_invariance='exact',reference='original pandas implementation generalized only for lookback')
