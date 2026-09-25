"""Interrupted-write and restart integrity checks on disposable synthetic state."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import v7_recovery as recovery


class RecoveryChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.run=self.root/'run'; self.run.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def runner(self):
        return SimpleNamespace(directory=self.run,identity='bound-run',code_hash='code',
            registry=[],fold_metrics=[],runs={},histories=[])

    def test_identity_and_tampering_fail_closed(self):
        recovery.bind_run(self.run,'original')
        with self.assertRaises(ValueError): recovery.bind_run(self.run,'different')
        folder=self.run/'fit'; folder.mkdir(); (folder/'model').write_bytes(b'own fixture')
        recovery.seal_checkpoint(folder,'identity',['model'])
        self.assertTrue(recovery.verify_checkpoint(folder,'identity'))
        with self.assertRaises(ValueError): recovery.verify_checkpoint(folder,'changed')
        (folder/'model').write_bytes(b'corrupted')
        with self.assertRaises(ValueError): recovery.verify_checkpoint(folder,'identity')

    def test_interrupted_snapshot_preserves_previous_generation(self):
        runner=self.runner(); runner.runs={'completed':1}; recovery.runner_snapshot(runner)
        runner.runs['new']=2
        with patch.object(recovery,'seal_checkpoint',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError): recovery.runner_snapshot(runner)
        restored=self.runner(); recovery.restore_runner(restored)
        self.assertEqual(restored.runs,{'completed':1})

    def test_stage_skips_completed_and_rejects_changed_inputs(self):
        runner=self.runner(); calls=[]
        def work():
            calls.append(1); (self.run/'metrics.json').write_text('{}')
        recovery.checkpoint_stage(runner,'anomaly',work,['metrics.json'],inputs={'data':'a'})
        recovery.checkpoint_stage(runner,'anomaly',work,['metrics.json'],inputs={'data':'a'})
        self.assertEqual(len(calls),1)
        with self.assertRaises(ValueError):
            recovery.checkpoint_stage(runner,'anomaly',work,['metrics.json'],inputs={'data':'b'})
        (self.run/'metrics.json').write_text('changed')
        with self.assertRaises(ValueError):
            recovery.checkpoint_stage(runner,'anomaly',work,['metrics.json'],inputs={'data':'a'})

    def test_failed_stage_is_not_marked_complete(self):
        runner=self.runner()
        with self.assertRaises(RuntimeError):
            recovery.checkpoint_stage(runner,'anomaly',lambda:(_ for _ in ()).throw(RuntimeError('fail')),[])
        self.assertFalse((self.run/'stage_anomaly'/'complete.json').exists())
        self.assertEqual(json.loads((self.run/'stage_anomaly'/'status.json').read_text())['state'],'failed')

    def test_backup_round_trip_contains_state_not_external_cache(self):
        recovery.bind_run(self.run,'same')
        runner=self.runner(); runner.runs={'candidate':42}; recovery.runner_snapshot(runner)
        (self.root/'feature_cache').mkdir(); (self.root/'feature_cache'/'raw').write_text('excluded')
        archive=recovery.backup_run(self.run,'latest_checkpoint')
        restored=self.root/'restored'; restored.mkdir()
        with zipfile.ZipFile(archive) as z:
            self.assertTrue(all(n.startswith('run/') for n in z.namelist()))
            z.extractall(restored)
        recovered=self.runner(); recovered.directory=restored/'run'
        recovery.bind_run(recovered.directory,'same'); recovery.restore_runner(recovered)
        self.assertEqual(recovered.runs,{'candidate':42})

    def test_old_unbound_run_refused(self):
        (self.run/'configuration_lock.json').write_text('{}')
        with self.assertRaises(ValueError): recovery.bind_run(self.run,'new')

    def test_snapshot_cannot_cross_dataset_identity(self):
        runner=self.runner(); recovery.runner_snapshot(runner)
        other=self.runner(); other.identity='different-data'
        with self.assertRaises(ValueError): recovery.restore_runner(other)
        self.assertEqual(other.runs,{})


if __name__=='__main__': unittest.main()
