"""Pre-holdout evaluator checks use generated fixtures, never actual holdouts."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

import if_submission as final
from if_final_reference import reference_features


def fixture():
    rows = []
    start = pd.Timestamp('2023-04-01T12:00:00+03:00')
    for user in range(3):
        for i in range(50):
            label = int(i % 7 == 0)
            rows.append(dict(user_id=f'fixture{user}', transaction_id=f'fixture{user}-{i}',
                transaction_timestamp=start+pd.Timedelta(days=i), amount=900. if label else 100.,
                category='Food', merchant='fixture', transaction_type='expense', is_anomaly=label,
                anomaly_type='large' if label else 'normal', event_id=f'event{user}-{i}' if label else None,
                observation_start='2021-01-04T00:00:00+03:00', observation_end='2024-01-01T00:00:00+03:00'))
    return pd.DataFrame(rows)


class SubmissionTests(unittest.TestCase):
    def test_exclusive_access_record_survives_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            final.begin_access(tmp, 'test', {'fixture': True})
            with self.assertRaises(FileExistsError):
                final.begin_access(tmp, 'test', {'fixture': True})
            marker = json.loads((Path(tmp)/'test.access.json').read_text())
            self.assertEqual(marker['state'], 'access_started_do_not_repeat')

    def test_wrong_archive_rejected_before_pickle(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'bad.zip'
            path.write_bytes(b'not trusted')
            with patch.object(final.joblib, 'load', side_effect=AssertionError('no deserialization')):
                with self.assertRaises(ValueError):
                    final.read_archive(path)

    def test_checksum_and_ownership(self):
        frame = fixture()
        raw = frame.to_csv(index=False).encode()
        entry = {'rows': len(frame), 'users': 3, 'csv_bytes': len(raw), 'sha256': final.sha(raw), 'zip': 'test.zip'}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(root/'test.zip', 'w') as archive:
                archive.writestr('test.csv', raw)
            entry['zip_sha256'] = final.sha((root/'test.zip').read_bytes())
            got = final.verified_csv(root, {'cohorts': {'test': entry}}, 'test')
            result = final.validate_cohort(got, entry, set(), set())
            self.assertEqual(len(result), 150)
            with self.assertRaises(ValueError):
                final.validate_cohort(got, entry, {'fixture0'}, set())
            with self.assertRaises(ValueError):
                final.validate_cohort(got, entry, set(), {'fixture0-0'})
            (root/'test.zip').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                final.verified_csv(root, {'cohorts': {'test': entry}}, 'test')

    def test_frozen_scoring_boundary_and_repeatability(self):
        frame = final.validate_transactions(fixture())
        model = IsolationForest(n_estimators=10, random_state=42).fit(reference_features(frame))
        with patch.object(model, 'fit', side_effect=AssertionError('never fit in evaluator')):
            metrics, predictions, probe = final.evaluate_frame(model, frame)
            self.assertEqual(len(predictions), 81)
            self.assertTrue(predictions.transaction_timestamp.ge(pd.Timestamp(final.PROTOCOL['evaluation_start'])).all())
            self.assertEqual(metrics['rows'], 81)
            self.assertEqual(sum(metrics[k] for k in ('TP', 'FP', 'FN', 'TN')), 81)
            flags = predictions.flag.to_numpy()
            self.assertEqual(final.confidence_intervals(predictions, flags), metrics['confidence_intervals_95pct'])
            self.assertTrue(np.isfinite(probe).all().all())

    def test_changed_lock_and_consumed_ledger_stop_before_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = root/'lock.json'
            lock.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'lock differs'):
                final.run(root/'missing', root/'missing', root/'out', root/'ledger', lock)
            lock.write_text(json.dumps({'protocol': final.PROTOCOL, 'sources': final.source_hashes(), 'versions': final.versions()}))
            final.begin_access(root/'ledger', 'test', {})
            with self.assertRaises(FileExistsError):
                final.run(root/'missing', root/'missing', root/'out', root/'ledger', lock)

    def test_final_evidence_and_source_lock(self):
        root = Path(__file__).parent
        lock = json.loads((root/'if_submission_lock.json').read_text())
        self.assertEqual(lock['sources'], final.source_hashes())
        self.assertEqual(lock['protocol'], final.PROTOCOL)
        report = json.loads((root/'evidence/if_submission/final_results.json').read_text())
        self.assertEqual(set(report['results']), {'test', 'test_shifted'})
        for name, metrics in report['results'].items():
            tp, fp, fn, tn = [metrics[k] for k in ('TP', 'FP', 'FN', 'TN')]
            self.assertEqual(tp+fp+fn+tn, metrics['rows'])
            self.assertAlmostEqual(metrics['F1'], 2*tp/(2*tp+fp+fn))
            self.assertEqual(sum(v['detected'] for v in metrics['families'].values()), tp)
            self.assertEqual(metrics['threshold'], final.THRESHOLD)
            self.assertFalse(metrics['historical_80pct_aspiration_met'])
            marker = json.loads((root/f'evidence/if_submission/{name}.access.json').read_text())
            self.assertEqual(marker['identity']['model'], final.ARCHIVE_SHA)

    def test_submission_notebook_matches_builder(self):
        import build_if_submission_notebook as builder
        notebook = builder.notebook()
        self.assertEqual(notebook, json.loads(builder.OUTPUT.read_text()))
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), cell['id'], 'exec')
                self.assertEqual(cell['outputs'], [])
        self.assertIn('RUN_FRESH_AUTHORIZED_EVALUATION = False', json.dumps(notebook))


if __name__ == '__main__':
    unittest.main()
