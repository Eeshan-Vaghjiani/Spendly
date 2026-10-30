"""Preserved five-feature V6 excess view for a matched-protocol comparison.

The function below is copied verbatim from the published V7 WORKER_SOURCE.
Tests compare its source and output to that notebook; no new reference tuning.
"""
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from if_final_features import validate_transactions

A_FEATURES = ['amount_ratio', 'category_ratio', 'category_deviation', 'merchant_ratio', 'count_hour', 'sum_hour_ratio', 'count_day', 'sum_week_ratio', 'duplicate_hour', 'merchants_hour', 'night_rarity', 'category_rarity', 'user_cold', 'merchant_missing']
REFERENCE_COLUMNS = ['category_excess', 'merchant_excess', 'duplicate_hour', 'rare_large', 'burst_amount']


def anomaly_features_fast(data):
    """Same 18 V5 features; integer time windows avoid repeated Timedelta/Pandas work."""
    values=[]
    for _, group in data.groupby('user_id',sort=False):
        group=group.sort_values(['transaction_timestamp','transaction_id'])
        history=deque(maxlen=100)
        categories=defaultdict(lambda:deque(maxlen=40))
        merchants=defaultdict(lambda:deque(maxlen=20))
        recent,category_counts,seen,nights=deque(),defaultdict(int),0,0
        rows=list(group.itertuples())
        times=group.transaction_timestamp.to_numpy(dtype='datetime64[ns]').astype('int64')
        boundaries=np.r_[0,np.flatnonzero(np.diff(times))+1,len(times)]
        hour_ns,day_ns=3600*10**9,86400*10**9
        for left,right in zip(boundaries[:-1],boundaries[1:]):
            stamp=times[left]
            hour_of_day=rows[left].transaction_timestamp.hour
            while recent and recent[0][0] < stamp-7*day_ns:
                recent.popleft()
            hour=[r for r in recent if r[0]>=stamp-hour_ns]
            day=[r for r in recent if r[0]>=stamp-day_ns]
            for row in rows[left:right]:
                a,c,m=row.amount,row.category,row.merchant
                typical=max(float(np.median(history)) if history else 1.,1.)
                cat=categories[c]
                center=max(float(np.median(cat)) if cat else typical,1.)
                spread=max(float(np.median(np.abs(np.asarray(cat)-center)))*1.4826 if cat else 0.,center*.2,1.)
                mc=max(float(np.median(merchants[m])) if m and merchants[m] else center,1.)
                feature=[a/typical,a/center,max(0.,(a-center)/spread),a/mc,len(hour),sum(r[1] for r in hour)/typical,
                    len(day),sum(r[1] for r in recent)/typical,
                    sum(bool(m) and r[2]==m and r[3]==c and abs(r[1]-a)<.01 for r in hour),
                    len({r[2] for r in hour if r[2]}),float(hour_of_day<5 or hour_of_day>=23)*(1-(nights+1)/(seen+2)),
                    1-category_counts[c]/max(1,seen),float(seen<10),float(not m)]
                values.append((row.Index,feature))
            for row in rows[left:right]:
                history.append(row.amount); categories[row.category].append(row.amount)
                if row.merchant:
                    merchants[row.merchant].append(row.amount)
                recent.append((stamp,row.amount,row.merchant,row.category))
                seen+=1; nights+=int(hour_of_day<5 or hour_of_day>=23); category_counts[row.category]+=1
    x=pd.DataFrame([v for _,v in values],index=[i for i,_ in values],columns=A_FEATURES,dtype=float).reindex(data.index)
    x['category_excess']=np.maximum(0.,x.category_ratio-1.)
    x['merchant_excess']=np.maximum(0.,x.merchant_ratio-1.)
    x['rare_large']=x.category_rarity*np.log1p(x.category_excess)*(1-x.user_cold)
    x['burst_amount']=x.count_hour*np.log1p(x.amount_ratio)
    return x


def reference_features(raw):
    data = validate_transactions(raw)
    data = data.loc[data.transaction_type.eq('expense')].reset_index(drop=True)
    data['transaction_timestamp'] = data.transaction_timestamp.dt.tz_localize(None)
    values = np.log1p(anomaly_features_fast(data)[REFERENCE_COLUMNS])
    values.index = data.transaction_id
    return values
