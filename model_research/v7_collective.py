"""Causal companion experiment inspired by BenjaminKakai's Spendly PR #3.

Independent implementation: completed-history baselines, no test-label sweep,
same-merchant/category duplicate windows, and calibrated alert budgets.
These research scores describe unusual spending, not fraud or confirmed duplicates.
"""
from collections import deque

import numpy as np
import pandas as pd


COLLECTIVE_PROTOCOL = dict(
    source='https://github.com/Eeshan-Vaghjiani/Spendly/pull/3',
    baseline_days=90, warmup_days=28, minimum_weekend_days=4,
    duplicate_hours=3, duplicate_tolerance=.02,
    frequency_divisor=4., weekend_divisor=6.,
    rules_budget=.01, combined_component_budget=.005,
    selection='diagnostic comparator only; retain the V6 single forest',
)


def collective_features(data):
    """Score each timestamp batch before updating history; return original row order.

    The current transaction contributes to its own day-to-date total; simultaneous
    peers do not see each other. Completed observed zero days enter rate baselines.
    Matching duplicates must have a nonempty merchant and category, identical for
    both transactions. No labels, event IDs or future totals inform these features.
    """
    required={'user_id','transaction_id','transaction_timestamp','amount','merchant',
              'category','observation_start'}
    if not required <= set(data):
        raise ValueError('Missing collective feature columns')
    if data.transaction_id.duplicated().any():
        raise ValueError('Transaction IDs must be unique')
    amounts=pd.to_numeric(data.amount,errors='coerce')
    if not np.isfinite(amounts).all() or (amounts<=0).any():
        raise ValueError('Expected finite positive expense amounts')
    work=data.copy().reset_index(drop=True)
    work['_position']=np.arange(len(work))
    work['transaction_timestamp']=pd.to_datetime(work.transaction_timestamp)
    work['observation_start']=pd.to_datetime(work.observation_start)
    results=[]
    for _,group in work.groupby('user_id',sort=False):
        if group.observation_start.nunique()!=1:
            raise ValueError('Inconsistent observation start')
        start=group.observation_start.iloc[0]
        if (group.transaction_timestamp<start).any():
            raise ValueError('Transaction precedes observation')
        day=start.normalize()
        counts,weekends,recent=deque(maxlen=90),deque(maxlen=26),deque()
        day_count=0; day_amount=0.
        for stamp,batch in group.groupby('transaction_timestamp',sort=True):
            current=stamp.normalize()
            while day<current:
                # Partial observation-start day is not a complete baseline day.
                if day>=start:
                    counts.append(day_count)
                    if day.weekday()>=5:
                        weekends.append(day_amount)
                day+=pd.Timedelta(days=1); day_count=0; day_amount=0.
            while recent and recent[0][0]<stamp-pd.Timedelta(hours=3):
                recent.popleft()
            eligible=len(counts)>=28
            rate=max(float(np.mean(counts)),1.) if counts else 1.
            weekend_base=max(float(np.median(weekends)),1.) if weekends else 1.
            for row in batch.to_dict('records'):
                merchant=row['merchant']; category=row['category']; amount=float(row['amount'])
                known=(pd.notna(merchant) and pd.notna(category)
                       and bool(str(merchant).strip()) and bool(str(category).strip()))
                matches=sum(1 for _,a,m,c in recent if known and m==merchant and c==category
                            and abs(a-amount)/max(a,amount)<=.02)
                frequency=(day_count+1)/rate if eligible else 0.
                weekend=((day_amount+amount)/weekend_base
                         if eligible and current.weekday()>=5 and len(weekends)>=4 else 0.)
                duplicate=float(matches) if eligible else 0.
                results.append((row['_position'],frequency,weekend,duplicate,eligible,
                                max(frequency/4.,weekend/6.,duplicate)))
            for row in batch.to_dict('records'):
                recent.append((stamp,float(row['amount']),row['merchant'],row['category']))
                day_count+=1; day_amount+=float(row['amount'])
    columns=['position','day_count_ratio','weekend_ratio','duplicate_count','eligible','collective_score']
    out=pd.DataFrame(results,columns=columns).sort_values('position').drop(columns='position')
    out.index=data.index
    return out


def capped_rule_threshold(scores, labels, budget):
    """Tie-safe empirical negative FPR cap, fitted only on calibration labels.

    Positive labels never optimize the threshold. Unknown labels are an error.
    No negatives means disabled (infinity), rather than uncalibrated alerts.
    """
    scores=np.asarray(scores,dtype=float); labels=np.asarray(labels,dtype=float)
    if scores.shape!=labels.shape or not np.isfinite(scores).all():
        raise ValueError('Invalid calibration arrays')
    if not np.isin(labels,[0.,1.]).all() or not 0<budget<1:
        raise ValueError('Explicit binary labels and a fractional budget are required')
    negatives=np.sort(scores[labels==0])
    if not len(negatives):
        return dict(threshold=float('inf'),negative_support=0,budget=budget,
                    calibration_FPR=None,status='disabled: no labelled negatives')
    allowed=int(np.floor(budget*len(negatives)))
    threshold=max(1.,float(np.nextafter(negatives[len(negatives)-allowed-1],np.inf)))
    return dict(threshold=threshold,negative_support=len(negatives),budget=budget,
                calibration_FPR=float(np.mean(negatives>=threshold)),
                status='calibrated' if allowed else 'calibrated: fewer than one allowed false positive')


def collective_diagnostics(rows, flags, model):
    """Descriptive family/event coverage and daily alert burden; never selection."""
    frame=rows.reset_index(drop=True).copy()
    flags=np.asarray(flags,dtype=bool)
    if len(flags)!=len(frame):
        raise ValueError('Prediction alignment mismatch')
    frame['flag']=flags
    frame['day']=pd.to_datetime(frame.time).dt.normalize()
    records=[]
    positives=frame.loc[frame.label.eq(1)]
    for family,part in positives.groupby('family',dropna=False):
        events=part.dropna(subset=['event_id']).groupby(['user_id','event_id']).flag.any()
        records.append(dict(model=model,family=family,positive_transactions=len(part),
            transaction_recall=float(part.flag.mean()),events_with_ids=len(events),
            event_recall=float(events.mean()) if len(events) else None))
    daily=frame.groupby(['user_id','day']).flag.any()
    return records,dict(model=model,transactions=len(frame),alerts=int(flags.sum()),
        active_user_days=len(daily),alerted_user_days=int(daily.sum()),
        fraction_active_days_alerted=float(daily.mean()) if len(daily) else None,
        event_definition='at least one flagged labelled member; absent event IDs excluded',
        daily_denominator='observed days containing evaluated transactions, not all calendar days')
