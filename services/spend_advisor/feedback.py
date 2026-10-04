"""Persistent versioned recommendation delivery and feedback, without raw records."""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3


class StaleOffer(Exception):
    pass


class FeedbackStore:
    def __init__(self, path):
        self.path = str(Path(path).resolve())
        if not Path(self.path).parent.is_dir():
            raise ValueError('Feedback database parent must exist')
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS offers (
                    offer_id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    month INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    target TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    first_delivered TEXT NOT NULL,
                    last_delivered TEXT NOT NULL,
                    shown_at TEXT,
                    decision INTEGER CHECK(decision IN (0,1)),
                    decided_at TEXT,
                    active INTEGER NOT NULL CHECK(active IN (0,1)),
                    revision INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS offers_period ON offers(owner, month, year);
                CREATE TABLE IF NOT EXISTS source_state (id INTEGER PRIMARY KEY CHECK(id=1), identity TEXT NOT NULL);
            ''')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(offers)')}
            if 'revision' not in columns:
                db.execute('ALTER TABLE offers ADD COLUMN revision INTEGER NOT NULL DEFAULT 0')

    def activate_source(self, identity):
        with self.connect() as db:
            db.execute('INSERT INTO source_state VALUES (1,?) ON CONFLICT(id) DO UPDATE SET identity=excluded.identity', (identity,))

    @staticmethod
    def offer_id(key, item, serialize):
        # Whole-snapshot provenance is tracked separately, never part of identity.
        identity = json.dumps([*key, item['targetId'], serialize(item)], separators=(',', ':'))
        return hashlib.sha256(identity.encode()).hexdigest()

    @staticmethod
    def check_source(db, identity):
        current = db.execute('SELECT identity FROM source_state WHERE id=1').fetchone()
        if current is None or current['identity'] != identity:
            raise StaleOffer('Snapshot version changed; restart this worker')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def issue(self, key, items, serialize, *, source_identity):
        """Unique version per household/period/target/content/source; retries dedupe.

        A new response deactivates withdrawn/replaced offers in that period. Old
        decisions remain historical evidence, never transfer to changed offers.
        Delivery means prepared by the service, not proof of client receipt/view.
        """
        owner, month, year = key
        result = []
        now = self.now()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.check_source(db, source_identity)
            db.execute('UPDATE offers SET active=0 WHERE owner=? AND month=? AND year=?', key)
            for item in items:
                payload = serialize(item)
                offer_id = self.offer_id(key, item, serialize)
                db.execute('''INSERT INTO offers
                    (offer_id,owner,month,year,target,payload,first_delivered,last_delivered,active)
                    VALUES (?,?,?,?,?,?,?,?,1)
                    ON CONFLICT(offer_id) DO UPDATE SET last_delivered=excluded.last_delivered,active=1''',
                    (offer_id, owner, month, year, item['targetId'], payload, now, now))
                revision = db.execute('SELECT revision FROM offers WHERE offer_id=?', (offer_id,)).fetchone()['revision']
                result.append({'offerId': offer_id, 'revision': revision, 'item': item})
        return result

    def feedback(self, key, offer_id, *, shown=False, accepted=None, expected_revision=0, source_identity):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.check_source(db, source_identity)
            offer = db.execute('SELECT active,revision,decision FROM offers WHERE offer_id=? AND owner=? AND month=? AND year=?',
                               (offer_id, *key)).fetchone()
            if offer is None:
                raise LookupError('Offer not found for this household and period')
            if not offer['active']:
                raise StaleOffer('Offer has been replaced or withdrawn')
            if accepted is not None and offer['revision'] != expected_revision:
                raise StaleOffer('Decision changed; refresh the offer revision')
            now = self.now()
            if shown or accepted is not None:
                db.execute('UPDATE offers SET shown_at=COALESCE(shown_at,?) WHERE offer_id=?', (now, offer_id))
            if accepted is not None:
                # The latest explicit decision wins; retrying never increments counts.
                db.execute('''UPDATE offers SET decision=?,decided_at=?,revision=revision+1
                              WHERE offer_id=? AND (decision IS NULL OR decision!=?)''',
                           (int(accepted), now, offer_id, int(accepted)))

    def metrics(self, key):
        with self.connect() as db:
            row = db.execute('''SELECT COUNT(*) AS delivered,
                COALESCE(SUM(shown_at IS NOT NULL),0) AS shown,
                COALESCE(SUM(decision IS NOT NULL),0) AS responded,
                COALESCE(SUM(decision=1),0) AS accepted,
                COALESCE(SUM(active),0) AS active
                FROM offers WHERE owner=? AND month=? AND year=?''', key).fetchone()
        counts = dict(row)
        rate = lambda denominator: (Decimal(counts['accepted'])/Decimal(denominator)).quantize(Decimal('.0001')) if denominator else None
        return {**counts, 'acceptRate': rate(counts['delivered']),
                'shownAcceptRate': rate(counts['shown']),
                'definition': 'Accepted unique offer versions / all unique delivered offer versions in this household and budget period; unanswered and superseded versions remain in the denominator.',
                'deliveryDefinition': 'Prepared by the service; does not prove client receipt or display.',
                'shownDefinition': 'Explicit display acknowledgement or decision; never inferred from a recommendation request.',
                'periodDefinition': 'Budget month/year, not event timestamp window.',
                'isSynthetic': True}
