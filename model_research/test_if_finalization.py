"""Synthetic-only regression checks for the finalization candidate."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

import build_if_final_notebook as builder
import if_final_pipeline as pipeline
import if_final_reference as reference
from if_final_features import FEATURES, build_features, validate_transactions


def fixture(prefix='fixture', users=2, rows=70):
    result = []
    for user in range(users):
        for i in range(rows):
            result.append(dict(transaction_id=f'{prefix}-{user}-{i:03d}', user_id=f'{prefix}-{user}',
                transaction_timestamp=pd.Timestamp('2021-01-04T00:00:00+03:00')+pd.Timedelta(hours=6*i),
                amount=100.+i%9*7, category='Utilities', merchant='shop', transaction_type='expense',
                is_anomaly=int(i%13==0), anomaly_type='large' if i%13==0 else 'normal',
                event_id=f'{prefix}-{user}-event-{i}' if i%13==0 else None,
                observation_start='2021-01-04T00:00:00+03:00', observation_end='2024-01-01T00:00:00+03:00'))
    return pd.DataFrame(result)


class FeaturesTests(unittest.TestCase):
    def test_units_timezone_and_known_counts(self):
        data = fixture()
        expected = build_features(data)[FEATURES]
        for unit in ('ns', 'us', 'ms'):
            changed = data.copy()
            changed['transaction_timestamp'] = changed.transaction_timestamp.dt.tz_convert('UTC').astype(f'datetime64[{unit}, UTC]')
            pd.testing.assert_frame_equal(build_features(changed)[FEATURES], expected)
        self.assertEqual(expected.loc[10, 'log_user_txn_count_prev_1h'], 0)
        self.assertAlmostEqual(np.expm1(expected.loc[10, 'log_user_txn_count_prev_24h']), 4)
        self.assertEqual(expected.loc[0, 'hour_cos'], 1.)

    def test_future_labels_income_and_order_invariance(self):
        data = fixture()
        result = build_features(data).set_index('transaction_id')[FEATURES]
        prefix = data.groupby('user_id').head(50)
        got = build_features(prefix).set_index('transaction_id')[FEATURES]
        pd.testing.assert_frame_equal(got, result.loc[got.index])
        modified = data.assign(is_anomaly=0, anomaly_type='changed', event_id=None)
        income = data.iloc[[0]].assign(transaction_id='income', transaction_type='income', amount=1e8)
        modified = pd.concat([modified, income]).sample(frac=1, random_state=3)
        pd.testing.assert_frame_equal(build_features(modified).set_index('transaction_id')[FEATURES], result)
        bare = data.drop(columns=['is_anomaly', 'anomaly_type', 'event_id'])
        pd.testing.assert_frame_equal(build_features(bare).set_index('transaction_id')[FEATURES], result)

    def test_simultaneous_transactions_cannot_see_one_another(self):
        data = fixture(users=1)
        target = data.iloc[[50]]
        addition = target.assign(transaction_id='000-first-at-tie', amount=999999)
        baseline = build_features(data).set_index('transaction_id')
        combined = build_features(pd.concat([data, addition])).set_index('transaction_id')
        pd.testing.assert_series_equal(baseline.loc[target.transaction_id.iloc[0], FEATURES],
                                       combined.loc[target.transaction_id.iloc[0], FEATURES])
        self.assertEqual(combined.loc['000-first-at-tie', 'log_user_txn_count_prev_1h'], 0)

    def test_invalid_input_rejected(self):
        data = fixture()
        for column, value in [('amount', -1), ('amount', np.inf), ('merchant', ''),
                              ('transaction_type', 'unknown'), ('user_id', None)]:
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                validate_transactions(data.assign(**{column: value}))
        with self.assertRaises(ValueError):
            validate_transactions(pd.concat([data, data.iloc[[0]]]))
        with self.assertRaises(ValueError):
            validate_transactions(data.assign(transaction_timestamp='2021-01-01'))

    def test_reference_is_preserved_published_source(self):
        nb = json.loads((builder.HERE/'Spending_Model_Upload_V7_R3_Kaggle_Evidence.ipynb').read_text(encoding='utf-8'))
        published = None
        for cell in nb['cells']:
            if cell['cell_type'] != 'code':
                continue
            for node in ast.parse(''.join(cell['source'])).body:
                if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'WORKER_SOURCE':
                    published = ast.parse(ast.literal_eval(node.value))
        original = next(n for n in published.body if isinstance(n, ast.FunctionDef) and n.name == 'anomaly_features_fast')
        current = next(n for n in ast.parse(Path(reference.__file__).read_text()).body if isinstance(n, ast.FunctionDef) and n.name == original.name)
        self.assertEqual(ast.dump(original), ast.dump(current))
        ns = {'np': np, 'pd': pd, 'deque': reference.deque, 'defaultdict': reference.defaultdict, 'A_FEATURES': reference.A_FEATURES}
        exec(compile(ast.Module(body=[original], type_ignores=[]), 'published reference', 'exec'), ns)
        frame = validate_transactions(fixture())
        frame['transaction_timestamp'] = frame.transaction_timestamp.dt.tz_localize(None)
        expected = np.log1p(ns['anomaly_features_fast'](frame)[reference.REFERENCE_COLUMNS])
        expected.index = frame.transaction_id
        pd.testing.assert_frame_equal(reference.reference_features(fixture()), expected)


class PipelineTests(unittest.TestCase):
    def test_threshold_ties_and_positive_scores_do_not_choose_cutoff(self):
        labels = np.array([0]*100+[1]*10)
        scores = np.array([1.]*10+[0.]*90+[.5]*10)
        cutoff = pipeline.capped_threshold(labels, scores, .01)
        self.assertEqual(int((scores[:100] >= cutoff).sum()), 0)
        scores[100:] = 999
        self.assertEqual(cutoff, pipeline.capped_threshold(labels, scores, .01))
        with self.assertRaises(ValueError):
            pipeline.capped_threshold([1], [.4], .01)

    def test_metrics_event_and_paired_interval(self):
        rows = fixture(users=1, rows=4).assign(is_anomaly=[1, 1, 0, 0], event_id=['event', 'event', None, None])
        result = pipeline.measures(rows, [.8, .7, .6, .1], .65)
        self.assertEqual((result['TP'], result['FP'], result['FN'], result['TN']), (2, 0, 0, 2))
        self.assertEqual(result['event_support'], 1)
        self.assertEqual(result['event_recall'], 1.)
        flags = np.array([True, True, False, False])
        interval = pipeline.paired_interval(rows, flags, flags, repetitions=10)
        self.assertEqual(interval['candidate_minus_reference_F1_95pct'], [0., 0.])

    def test_bundle_parity_tamper_and_overwrite(self):
        x = build_features(fixture())[FEATURES]
        model = make_pipeline(SimpleImputer(add_indicator=True), IsolationForest(n_estimators=5, random_state=42)).fit(x)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)/'bundle'
            pipeline.save_bundle(folder, model, FEATURES, .5, {'synthetic': True}, x.iloc[:10])
            with self.assertRaises(PermissionError):
                pipeline.load_bundle(folder)
            with self.assertRaises(FileExistsError):
                pipeline.save_bundle(folder, model, FEATURES, .5, {}, x.iloc[:10])
            (folder/'pipeline.joblib').write_bytes(b'corrupt')
            with patch.object(pipeline.joblib, 'load', side_effect=AssertionError('must not deserialize')):
                with self.assertRaises(ValueError):
                    pipeline.load_bundle(folder, trusted=True)

    def test_verified_loader_hashes_and_development_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = {'version': pipeline.PROTOCOL['dataset'], 'synthetic_only': True, 'weeks_per_user': 156, 'cohorts': {}}
            for name in pipeline.COHORTS:
                frame = fixture(prefix=name)
                raw = frame.to_csv(index=False).encode()
                with zipfile.ZipFile(root/f'{name}.zip', 'w') as archive:
                    archive.writestr(f'{name}.csv', raw)
                manifest['cohorts'][name] = {'rows': len(frame), 'users': 2, 'csv_bytes': len(raw),
                    'sha256': hashlib.sha256(raw).hexdigest(), 'zip_sha256': hashlib.sha256((root/f'{name}.zip').read_bytes()).hexdigest()}
            (root/'manifest.json').write_text(json.dumps(manifest))
            (root/'test.zip').write_bytes(b'not a zip: must not read')
            data, _ = pipeline.load_development(root)
            self.assertEqual(set(data), set(pipeline.COHORTS))
            (root/'train.zip').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                pipeline.load_development(root)

    def test_notebook_rebuild_no_outputs_or_network(self):
        nb = builder.notebook()
        checked = json.loads(builder.OUTPUT.read_text())
        self.assertEqual(nb, checked)
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                code = ''.join(cell['source'])
                ast.parse(code)
                self.assertFalse(cell['outputs'])
                self.assertNotIn('gdown', code)
        self.assertNotIn('RUN_STANDARD_TEST', json.dumps(nb))

    def test_full_development_orchestration_synthetic_only(self):
        data = {}
        for name in pipeline.COHORTS:
            frame = fixture(prefix=name, rows=70)
            if name != 'train':
                origin = pd.Timestamp(pipeline.PROTOCOL['training_end'] if name == 'calibration'
                                      else pipeline.PROTOCOL['calibration_end'])
                frame['transaction_timestamp'] += origin-pd.Timestamp('2021-01-04T00:00:00+03:00')
            data[name] = frame
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'run'
            with patch.object(pipeline, 'load_development', return_value=(data, {'synthetic_test': True})):
                report = pipeline.run_development('unused', output)
            self.assertEqual(report['decision'], 'review_required_no_automatic_promotion')
            self.assertEqual(report['common_rows']['validation'], 84)
            scores = pd.read_csv(output/'development_predictions.csv')
            self.assertEqual(len(scores), 84)
            for name in ('candidate', 'reference'):
                self.assertEqual(report['metrics'][name]['validation']['rows'], len(scores))
            with self.assertRaises(FileExistsError):
                pipeline.run_development('unused', output)

    def test_published_aggregate_arithmetic_and_source_identity(self):
        root = builder.HERE/'evidence/if_finalization'
        report = json.loads((root/'comparison.json').read_text())
        for name in ('candidate', 'reference'):
            metadata = json.loads((root/f'{name}_manifest.json').read_text())
            self.assertEqual(metadata['sources'], pipeline.source_identity())
            for cohort in ('calibration', 'validation'):
                m = report['metrics'][name][cohort]
                tp, fp, fn, tn = (m[k] for k in ('TP', 'FP', 'FN', 'TN'))
                self.assertEqual(tp+fp+fn+tn, m['rows'])
                self.assertAlmostEqual(m['F1'], 2*tp/(2*tp+fp+fn))
                self.assertAlmostEqual(m['precision'], tp/(tp+fp))
                self.assertAlmostEqual(m['recall'], tp/(tp+fn))
                self.assertEqual(sum(f['support'] for f in m['families'].values()), tp+fn)
                self.assertEqual(sum(f['detected'] for f in m['families'].values()), tp)


if __name__ == '__main__':
    unittest.main()
