"""Verified local research checkpoints; restore only your own trusted run folders.

Hashes detect corruption and incompatible inputs, not maliciously replaced bundles.
Joblib/model checkpoints must never be loaded from untrusted sources.
"""
import hashlib
import json
import os
from pathlib import Path
import time
import zipfile

import joblib


def recovery_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, value):
    path=Path(path); temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(temporary,path)


def seal_checkpoint(directory, identity, names):
    directory=Path(directory)
    atomic_json(directory/'complete.json',dict(identity=identity,
        files={name:recovery_hash(directory/name) for name in names}))


def verify_checkpoint(directory, identity):
    directory=Path(directory); marker=directory/'complete.json'
    if not marker.exists():
        return False
    record=json.loads(marker.read_text(encoding='utf-8'))
    if record['identity']!=identity:
        raise ValueError('Checkpoint identity mismatch; use a new run for changed code/data/configuration')
    for name,expected in record['files'].items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid checkpoint path')
        if recovery_hash(directory/relative)!=expected:
            raise ValueError('Checkpoint artifact hash mismatch: '+name)
    return True


def bind_run(directory, identity):
    """Bind before training; refuse old/unbound nonempty experiment directories."""
    directory=Path(directory); path=directory/'run_identity.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=identity:
            raise ValueError('Run identity mismatch; do not mix datasets, modes or environments')
        return
    if (directory/'experiments').exists() or (directory/'configuration_lock.json').exists():
        raise ValueError('Older run has no recovery identity; preserve it and start a new run')
    atomic_json(path,identity)


def backup_run(directory, label):
    """Atomic partial archive of evidence/checkpoints; excludes feature cache outside run."""
    directory=Path(directory)
    if not label.replace('_','').isalnum():
        raise ValueError('Invalid backup label')
    archive=directory.parent/(directory.name+'_'+label+'.zip')
    temporary=archive.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for path in sorted(directory.rglob('*')):
            if path.is_file() and not path.name.endswith('.tmp'):
                z.write(path,Path(directory.name)/path.relative_to(directory))
    os.replace(temporary,archive)
    print('PARTIAL RECOVERY BACKUP:',archive,flush=True)
    print('Download/persist this ZIP now; temporary Kaggle storage can disappear.',flush=True)
    return archive


def runner_snapshot(runner):
    """Two-slot atomic state saves keep the previous valid generation on interruption."""
    root=runner.directory/'recovery'; root.mkdir(exist_ok=True)
    pointer=root/'current.json'
    old=json.loads(pointer.read_text())['slot'] if pointer.exists() else 1
    slot=1-old; folder=root/str(slot); folder.mkdir(exist_ok=True)
    (folder/'complete.json').unlink(missing_ok=True)
    joblib.dump(dict(registry=runner.registry,fold_metrics=runner.fold_metrics,
        runs=runner.runs,histories=runner.histories),folder/'state.joblib')
    seal_checkpoint(folder,runner.identity,['state.joblib'])
    atomic_json(pointer,dict(slot=slot))


def restore_runner(runner):
    root=runner.directory/'recovery'; pointer=root/'current.json'
    if not pointer.exists():
        return
    slot=json.loads(pointer.read_text())['slot']
    if slot not in (0,1):
        raise ValueError('Invalid recovery slot')
    folder=root/str(slot)
    if not verify_checkpoint(folder,runner.identity):
        raise ValueError('Incomplete published runner snapshot')
    saved=joblib.load(folder/'state.joblib')
    for name in ('registry','fold_metrics','runs','histories'):
        setattr(runner,name,saved[name])
    print(f'RESUMED: {len(runner.runs)} completed candidate/seed/fraction experiments',flush=True)


def seal_outputs(directory, names):
    return {name:recovery_hash(Path(directory)/name) for name in names}


def verify_outputs(directory, record):
    for name,expected in record.items():
        if recovery_hash(Path(directory)/name)!=expected:
            raise ValueError('Published evidence changed: '+name)


def checkpoint_stage(runner, name, operation, outputs, inputs=None):
    """Skip a completed stage only after verifying all its named outputs."""
    marker=runner.directory/('stage_'+name); marker.mkdir(exist_ok=True)
    identity=dict(run=runner.identity,inputs=inputs)
    if verify_checkpoint(marker,identity):
        record=json.loads((marker/'outputs.json').read_text())
        for filename,expected in record.items():
            if recovery_hash(runner.directory/filename)!=expected:
                raise ValueError('Stage output changed: '+filename)
        print('RESUMED completed stage:',name,flush=True)
        return
    atomic_json(marker/'status.json',dict(state='running',started=time.time()))
    try:
        operation()
        atomic_json(marker/'outputs.json',{f:recovery_hash(runner.directory/f) for f in outputs})
        seal_checkpoint(marker,identity,['outputs.json'])
        atomic_json(marker/'status.json',dict(state='completed'))
    except Exception as error:
        atomic_json(marker/'status.json',dict(state='failed',error_type=type(error).__name__))
        raise
