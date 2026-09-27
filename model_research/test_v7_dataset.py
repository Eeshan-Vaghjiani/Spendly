"""Bounded software checks: only newly generated temporary development fixtures."""
import ast
from collections import defaultdict
from contextlib import contextmanager, redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

import pandas as pd

import build_v7_dataset as builder
import synthetic_r3_data as r3

HERE = Path(__file__).resolve().parent
SMALL_COUNTS = dict(train=2, validation=1, calibration=1)


def loader_functions():
    """Execute actual loader source without unrelated ML/plotting dependencies."""
    names = {'timed', 'assert_permitted', 'discover', 'load_manifest', 'load_cohort'}
    tree = ast.parse((HERE / 'v7_runtime.py').read_text(encoding='utf-8'))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in nodes} != names:
        raise AssertionError('V7 loader contract functions changed')
    ns = dict(Path=Path, hashlib=hashlib, json=json, pd=pd, zipfile=zipfile,
              time=time, contextmanager=contextmanager, TIMINGS=defaultdict(float),
              ACCESSES=[], ALLOWED_COHORTS=builder.ALLOWED_COHORTS, RUN_FINAL_HOLDOUTS=False)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'v7_runtime.py', 'exec'), ns)
    return ns


class FixtureCleaner:
    """Only the cleaner interface needed by load_cohort; no model work."""
    @staticmethod
    def clean_data(raw):
        return raw.loc[raw.transaction_type.eq('expense')].assign(
            label=lambda frame: frame.is_anomaly)


class V7DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        # Resolved because macOS hands back /var/folders/..., a symlink to
        # /private/var/folders/.... The read-boundary guard below compares a
        # resolved path against this root, so an unresolved root fails there
        # on macOS while passing on Linux.
        cls.root = Path(cls.temp.name).resolve()
        cls.output = cls.root / 'first'
        with patch.object(builder, 'generate_user', wraps=r3.generate_user) as calls:
            cls.manifest = builder.build(cls.output, weeks=24, counts=SMALL_COUNTS)
            cls.generation_calls = calls.call_args_list

    def test_fixed_defaults_and_disjoint_seeds(self):
        self.assertEqual(builder.VERSION, 'spendly-synthetic-v7-dev-v1')
        self.assertEqual(dict(builder.DEFAULT_COUNTS), dict(train=600, validation=100, calibration=100))
        self.assertEqual(dict(builder.SEEDS), dict(train=170306173, validation=170417239, calibration=170528307))
        self.assertEqual(len(set(builder.SEEDS.values())), 3)
        self.assertFalse(set(builder.SEEDS.values()) & {v[0] for v in r3.COHORTS.values()})
        self.assertEqual(builder.build.__defaults__[0], 156)
        self.assertIs(builder.generate_user, r3.generate_user)
        self.assertIs(builder.audit_user, r3.audit_user)

    def test_only_development_generated_and_exported(self):
        self.assertEqual(len(self.generation_calls), 4)
        self.assertEqual({c.args[2] for c in self.generation_calls}, set(builder.ALLOWED_COHORTS))
        for call in self.generation_calls:
            self.assertEqual(call.args[0], builder.SEEDS[call.args[2]])
            self.assertEqual(call.kwargs, dict(weeks=24, shifted=False, inject=True))
        expected = {'manifest.json'}
        for cohort in builder.ALLOWED_COHORTS:
            expected.add(f'development/{cohort}.csv')
            for suffix in ('user_audit.csv', 'diagnostic_profiles.csv', 'aggregate_qa.json'):
                expected.add(f'diagnostics_DO_NOT_TRAIN/{cohort}_{suffix}')
        actual = {p.relative_to(self.output).as_posix() for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(actual, expected)
        self.assertEqual(set(self.manifest['cohorts']), set(builder.ALLOWED_COHORTS))

    def test_byte_reproducibility(self):
        second = self.root / 'repeat'
        manifest = builder.build(second, weeks=24, counts=dict(reversed(list(SMALL_COUNTS.items()))))
        self.assertEqual(manifest, self.manifest)
        for source in self.output.rglob('*'):
            if source.is_file():
                self.assertEqual(source.read_bytes(), (second / source.relative_to(self.output)).read_bytes())

    def test_count_extension_preserves_users_and_unchanged_generator_rows(self):
        one = self.root / 'one_each'
        builder.build(one, weeks=24, counts={name: 1 for name in builder.ALLOWED_COHORTS})
        original, *_ = r3.generate_user(builder.SEEDS['train'], 0, 'train', weeks=24, shifted=False, inject=True)
        exported = pd.read_csv(one / 'development/train.csv')
        expected = pd.read_csv(io.StringIO(original.assign(source_dataset=builder.VERSION).to_csv(index=False)))
        pd.testing.assert_frame_equal(exported, expected)
        extended = pd.read_csv(self.output / 'development/train.csv')
        pd.testing.assert_frame_equal(exported, extended.loc[extended.user_id.eq(exported.user_id.iloc[0])].reset_index(drop=True))

    def test_manifest_schema_hashes_and_provenance(self):
        manifest = json.loads((self.output / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest, self.manifest)
        for key, value in dict(version=builder.VERSION, status='complete', currency='KES',
                               timezone='Africa/Nairobi', weeks_per_user=24, development_only=True,
                               synthetic_only=True, holdout_model_evaluations=0).items():
            self.assertEqual(manifest[key], value)
        self.assertFalse(manifest['provenance']['independent_real_population_evidence'])
        self.assertFalse(manifest['provenance']['existing_dataset_rows_accessed'])
        for name in builder.SOURCE_FILES:
            self.assertEqual(manifest['sources'][name], hashlib.sha256((HERE / name).read_bytes()).hexdigest())
        self.assertEqual(manifest['protocol_sha256'], manifest['sources']['V7_DATA_PROTOCOL.md'])
        self.assertEqual(manifest['total_rows'], sum(c['rows'] for c in manifest['cohorts'].values()))
        ids = set()
        for cohort, entry in manifest['cohorts'].items():
            csv = self.output / entry['csv']
            frame = pd.read_csv(csv)
            self.assertEqual(entry['sha256'], hashlib.sha256(csv.read_bytes()).hexdigest())
            self.assertEqual(entry['rows'], len(frame))
            self.assertEqual(entry['users'], frame.user_id.nunique())
            self.assertEqual(entry['users'], SMALL_COUNTS[cohort])
            self.assertEqual(tuple(frame.columns), builder.MODEL_COLUMNS)
            self.assertTrue(frame.source_dataset.eq(builder.VERSION).all())
            self.assertTrue(frame.transaction_id.is_unique)
            self.assertFalse(ids & set(frame.user_id))
            ids.update(frame.user_id)
            self.assertTrue(frame.event_id.notna().equals(frame.is_anomaly.eq(1)))
            for table in entry['diagnostic_tables'].values():
                path = self.output / table['csv']
                self.assertEqual(table['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(len(pd.read_csv(path)), table['rows'])
            qa = self.output / entry['aggregate_qa']['json']
            self.assertEqual(entry['aggregate_qa']['sha256'], hashlib.sha256(qa.read_bytes()).hexdigest())
            self.assertEqual(json.loads(qa.read_text()), entry['audit'])

    def test_coverage_qa_matches_generated_rows(self):
        for entry in self.manifest['cohorts'].values():
            frame = pd.read_csv(self.output / entry['csv'])
            audit = pd.read_csv(self.output / entry['diagnostic_tables']['user_audit']['csv'])
            coverage = entry['audit']['observation_coverage']
            expected_days = entry['users'] * 24 * 7
            self.assertEqual(coverage['expected_user_days'], expected_days)
            self.assertEqual(coverage['observed_user_days'], expected_days)
            self.assertEqual(coverage['complete_users'], entry['users'])
            active = sum(pd.to_datetime(g.transaction_timestamp, utc=True).dt.tz_convert('Africa/Nairobi').dt.date.nunique()
                         for _, g in frame.groupby('user_id'))
            self.assertEqual(coverage['transaction_days'], active)
            self.assertEqual(coverage['zero_transaction_days'], expected_days - active)
            self.assertGreaterEqual(coverage['zero_expense_days'], coverage['zero_transaction_days'])
            self.assertEqual(int(audit.rows.sum()), len(frame))
            self.assertEqual(int(audit.days.sum()), expected_days)
            profiles = pd.read_csv(self.output / entry['diagnostic_tables']['diagnostic_profiles']['csv'])
            self.assertEqual(set(profiles.user_id), set(frame.user_id))
            self.assertIn('rho', profiles)
            self.assertNotIn('rho', frame)
            self.assertNotIn('conditional_ordinary_noise_ratio', frame)

    def test_invalid_config_fails_before_creating_any_directory(self):
        invalid = [dict(weeks=v) for v in (23, 0, -1, True, 24.5, '156', None, 10**12)]
        invalid += [dict(counts=v) for v in ({}, [], {'train': 1},
                    dict(SMALL_COUNTS, test=1), dict(SMALL_COUNTS, final=1),
                    dict(SMALL_COUNTS, test_shifted=1))]
        invalid += [dict(counts=dict(SMALL_COUNTS, train=v)) for v in (0, -1, True, 1.5, '2', None)]
        for index, kwargs in enumerate(invalid):
            with self.subTest(kwargs=kwargs):
                parent = self.root / f'invalid_{index}'
                with patch.object(builder, 'generate_user') as generate:
                    with self.assertRaises(ValueError):
                        builder.build(parent / 'data', **kwargs)
                    generate.assert_not_called()
                self.assertFalse(parent.exists())
        for output in ('', '   ', None):
            with self.subTest(output=output), self.assertRaises(ValueError):
                builder.build(output, weeks=24, counts=SMALL_COUNTS)

    def test_existing_output_never_overwritten_or_read(self):
        empty = self.root / 'existing_empty'
        empty.mkdir()
        file = self.root / 'existing_file'
        file.write_bytes(b'preserve fixture')
        before = {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        for output in (self.output, empty, file):
            with patch.object(builder, 'generate_user') as generate, patch.object(builder, 'sha256') as digest:
                with self.assertRaises(FileExistsError):
                    builder.build(output, weeks=24, counts=SMALL_COUNTS)
                generate.assert_not_called()
                digest.assert_not_called()
        self.assertEqual(file.read_bytes(), b'preserve fixture')
        self.assertEqual(list(empty.iterdir()), [])
        self.assertEqual(before, {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob('*') if p.is_file()})
        with self.assertRaises(ValueError):
            builder.build(file / 'nested/data', weeks=24, counts=SMALL_COUNTS)

    def test_failure_does_not_publish_completed_manifest_or_allow_resume(self):
        output = self.root / 'interrupted'
        with patch.object(builder, 'generate_user', side_effect=RuntimeError('fixture interruption')):
            with self.assertRaisesRegex(RuntimeError, 'fixture interruption'):
                builder.build(output, weeks=24, counts=SMALL_COUNTS)
        self.assertFalse((output / 'manifest.json').exists())
        with self.assertRaises(FileExistsError):
            builder.build(output, weeks=24, counts=SMALL_COUNTS)

    def test_incomplete_coverage_is_rejected(self):
        output = self.root / 'bad_coverage'

        def missing_day(*args, **kwargs):
            frame, profile, daily, origins = r3.generate_user(*args, **kwargs)
            return frame, profile, daily.iloc[:-1], origins

        with patch.object(builder, 'generate_user', side_effect=missing_day):
            with self.assertRaisesRegex(ValueError, 'Observation coverage violation'):
                builder.build(output, weeks=24, counts=SMALL_COUNTS)
        self.assertFalse((output / 'manifest.json').exists())

    def test_build_reads_only_provenance_sources_and_new_artifacts(self):
        output = self.root / 'read_boundary'
        allowed_sources = {HERE / name for name in builder.SOURCE_FILES}
        original_open = Path.open
        reads = []

        def guarded_open(path, mode='r', *args, **kwargs):
            if 'r' in mode or '+' in mode:
                resolved = path.resolve()
                self.assertTrue(resolved in allowed_sources or resolved.is_relative_to(output))
                reads.append(resolved)
            return original_open(path, mode, *args, **kwargs)

        with patch.object(Path, 'open', guarded_open):
            builder.build(output, weeks=24, counts={name: 1 for name in builder.ALLOWED_COHORTS})
        self.assertTrue(allowed_sources <= set(reads))

    def test_cli_invalid_and_prohibited_options_do_not_create_directories(self):
        for index, option in enumerate(('--test-users', '--final-users', '--shifted-test-users', '--seed', '--cohorts', '--weeks')):
            parent = self.root / f'bad_cli_{index}'
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                builder.main(['--output', str(parent / 'dataset'), option, '0'])
            self.assertEqual(error.exception.code, 2)
            self.assertFalse(parent.exists())

    def test_existing_load_cohort_accepts_manifest_and_enforces_integrity(self):
        ns = loader_functions()
        results = self.root / 'loader_results'
        results.mkdir()
        (results / 'configuration_lock.json').write_text('{}')
        for cohort in builder.ALLOWED_COHORTS:
            data = ns['load_cohort'](cohort, self.output, self.manifest, FixtureCleaner, results)
            self.assertEqual(data.user_id.nunique(), SMALL_COUNTS[cohort])
        for field, value in (('sha256', '0' * 64), ('rows', 1), ('users', 999)):
            bad = json.loads(json.dumps(self.manifest))
            bad['cohorts']['train'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                ns['load_cohort']('train', self.output, bad, FixtureCleaner, results)
        for cohort in ('test', 'test_shifted', 'final'):
            with self.assertRaises(PermissionError):
                ns['load_cohort'](cohort, self.root / 'absent', {}, FixtureCleaner, results)
        with self.assertRaises(PermissionError):
            ns['load_cohort']('validation', self.output, self.manifest, FixtureCleaner, self.root / 'unlocked')
        loaded=ns['load_manifest'](self.output)
        self.assertEqual(loaded['version'],builder.VERSION)
        self.assertEqual(loaded['benchmark_role'],'fresh synthetic development replication')
        self.assertEqual(set(loaded['cohorts']),set(builder.ALLOWED_COHORTS))


if __name__ == '__main__':
    unittest.main()
