"""Snapshot-backed synthetic budget review; no model fitting or upstream writes.

Service-key authorization is a proposed server-to-server boundary. The platform
must authorize the requested household; this key is never a mobile credential.
"""
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import json
import os
from pathlib import Path

from flask import Flask, Response, request

ACTIONS = {
    'Entertainment': 'Review optional entertainment purchases and set a spending limit',
    'Groceries': 'Review grocery purchases and plan a shopping list within the allocation',
    'Airtime and Data': 'Review airtime and data usage and compare available packages',
    'Transport': 'Review optional trips and compare lower-cost transport options',
}


def money(text):
    if isinstance(text, (bool, float)):
        raise ValueError('Use exact decimal amounts')
    try:
        value = Decimal(text)
    except (InvalidOperation, TypeError):
        raise ValueError('Invalid amount') from None
    if not value.is_finite() or value < 0 or value > Decimal('999999999999.99'):
        raise ValueError('Amount outside supported KES range')
    if value != value.quantize(Decimal('.01')):
        raise ValueError('Expected nonnegative KES with at most two decimals')
    return value.quantize(Decimal('.01'))


def json_money(value):
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, dict):
        return '{'+','.join(json.dumps(k)+':'+json_money(v) for k, v in value.items())+'}'
    if isinstance(value, list):
        return '['+','.join(map(json_money, value))+']'
    return json.dumps(value, allow_nan=False)


@dataclass(frozen=True)
class Budget:
    target: str
    owner: str
    month: int
    year: int
    category: str
    allocated: Decimal
    actual: Decimal
    approved: bool


class Snapshot:
    """Immutable, checksum-verified local synthetic snapshot.

Only budget columns needed by the service are kept in memory. Snapshots are
local artifacts; production financial records are outside this implementation.
"""
    def __init__(self, directory):
        directory = Path(directory)
        manifest = json.loads((directory/'snapshot.json').read_text())
        if manifest.get('synthetic') is not True:
            raise ValueError('Synthetic snapshot required')
        payload = (directory/'budget_categories.csv').read_bytes()
        entry = manifest['datasets']['budget_categories']
        if hashlib.sha256(payload).hexdigest() != entry['sha256']:
            raise ValueError('Snapshot checksum mismatch')
        import io
        rows = list(csv.DictReader(io.StringIO(payload.decode('utf-8-sig'))))
        if len(rows) != entry['rows']:
            raise ValueError('Snapshot row count mismatch')
        self.by_period = {}
        targets, periods = set(), set()
        for row in rows:
            record = Budget(row['budget_category_id'], row['user_profile_id'],
                int(row['month']), int(row['year']), row['category'],
                money(row['allocated_kes']), money(row['actual_kes']), row['approval_status']=='APPROVED')
            key = (record.owner, record.month, record.year)
            unique = (*key, record.category)
            if not record.owner or not record.target or not 1 <= record.month <= 12 or record.target in targets or unique in periods:
                raise ValueError('Invalid snapshot identity')
            targets.add(record.target); periods.add(unique)
            self.by_period.setdefault(key, []).append(record)
        self.sha256 = entry['sha256']

    def advice(self, owner, month, year):
        rows = self.by_period.get((owner, month, year))
        if rows is None:
            raise LookupError('No snapshot period available')
        items = []
        for row in rows:
            if not row.approved or row.category not in ACTIONS or row.actual <= row.allocated:
                continue
            difference = row.actual-row.allocated
            items.append({'type':'review_category_budget', 'targetId':row.target,
                'savingKes':difference,
                'reason':f'{ACTIONS[row.category]}. In the synthetic {year}-{month:02d} snapshot, '
                         f'{row.category} spending was KES {row.actual:.2f} against an approved '
                         f'KES {row.allocated:.2f} allocation. Returning to that allocation for a '
                         f'comparable period would reduce spending by KES {difference:.2f}, if feasible. '
                         'This is a retrospective planning scenario, not a forecast or guaranteed saving.'})
        return sorted(items, key=lambda r:(-r['savingKes'],r['targetId']))[:3]


def create_app(snapshot=None, service_key=None):
    source = snapshot or Snapshot(os.environ['SPEND_ADVISOR_SNAPSHOT'])
    key = service_key if service_key is not None else os.environ.get('SPEND_ADVISOR_API_KEY')
    if not isinstance(key, str) or len(key) < 32 or not key.isascii():
        raise ValueError('Configure a private ASCII service key of at least 32 characters')
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 16384

    def respond(body, status=200):
        return Response(json_money(body), status=status, mimetype='application/json')

    @app.get('/health')
    def health():
        return respond({'status':'ok','service':'spend-advisor','isSynthetic':True,
                        'method':'retrospective-approved-budget-gap-v1'})

    @app.post('/recommendations')
    def recommendations():
        supplied = request.headers.get('Authorization', '')
        if not hmac.compare_digest(supplied.encode('utf-8'), ('Bearer '+key).encode('ascii')):
            return respond({'error':'Unauthorized'}, 401)
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {'userId','month','year'}:
            return respond({'error':'Expected userId, month and year'}, 422)
        owner, month, year = body['userId'], body['month'], body['year']
        if (not isinstance(owner, str) or not owner.strip() or len(owner)>128 or owner != owner.strip()
                or type(month) is not int or not 1<=month<=12
                or type(year) is not int or not 2000<=year<=2100):
            return respond({'error':'Invalid household or period'}, 422)
        try:
            items = source.advice(owner, month, year)
        except LookupError:
            return respond({'error':'No snapshot period available'}, 404)
        return respond({'items':items})
    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=8000, debug=False)
