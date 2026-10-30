"""Verify the local two-table synthetic snapshot; publish aggregate QA only."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd


def audit(directory):
    root = Path(directory)
    manifest = json.loads((root/'snapshot.json').read_text())
    if manifest.get('synthetic') is not True:
        raise ValueError('Synthetic snapshot required')
    tables = {}
    for name in ('spending_records','budget_categories'):
        raw = (root/f'{name}.csv').read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest['datasets'][name]['sha256']:
            raise ValueError('Snapshot identity changed')
        import io
        tables[name] = pd.read_csv(io.BytesIO(raw))
    s, b = tables['spending_records'], tables['budget_categories']
    t = pd.to_datetime(s.transaction_date, utc=True, errors='raise')
    joined = s.merge(b, on='budget_category_id', suffixes=('_spend','_budget'), how='left', validate='many_to_one', indicator=True)
    totals = s.groupby('budget_category_id').amount_kes.sum()
    difference = b.set_index('budget_category_id').actual_kes-totals.reindex(b.budget_category_id,fill_value=0).to_numpy()
    return {'synthetic':True, 'snapshot':manifest,
        'households': {'spending':s.user_profile_id.nunique(),'budgets':b.user_profile_id.nunique()},
        'categories':sorted(s.category.unique()), 'start_utc':str(t.min()), 'end_utc':str(t.max()),
        'duplicate_spending_ids':int(s.spending_record_id.duplicated().sum()),
        'duplicate_budget_periods':int(b.duplicated(['user_profile_id','year','month','category']).sum()),
        'unmatched_budget_links':int(joined['_merge'].ne('both').sum()),
        'owner_mismatches':int(joined.user_profile_id_spend.ne(joined.user_profile_id_budget).sum()),
        'category_mismatches':int(joined.category_spend.ne(joined.category_budget).sum()),
        'period_mismatches':int(((t.dt.month.to_numpy()!=joined.month.to_numpy()) | (t.dt.year.to_numpy()!=joined.year.to_numpy())).sum()),
        'max_actual_reconciliation_difference_KES':float(difference.abs().max()),
        'over_budget_category_months':int(b.actual_kes.gt(b.allocated_kes).sum()),
        'over_budget_fraction':float(b.actual_kes.gt(b.allocated_kes).mean()),
        'approval_status':b.approval_status.value_counts().to_dict(),
        'compatibility': {'anomaly_labels':False, 'merchant_field':False,
            'category_mapping_required':['Groceries','Medical','School Fees','Airtime and Data','Household Help','Savings'],
            'coverage_attestation_required':True,
            'model_evaluation':'blocked pending semantic mapping; no retraining'}}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--snapshot', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = audit(a.snapshot)
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k!='snapshot'},indent=2))
