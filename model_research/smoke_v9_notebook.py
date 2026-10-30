"""End-to-end V9 software run and fresh-namespace recovery on tiny fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from test_v9_checkpoint import modules
from test_v7_evidence import fixture


def main(report):
    with tempfile.TemporaryDirectory(prefix='spendly_v9_smoke_') as temporary:
        root=Path(temporary);inputs=root/'inputs';inputs.mkdir()
        nb,worker,_=modules(root)
        manifest=dict(version='spendly-synthetic-r3-v1',status='complete',currency='KES',
            timezone='Africa/Nairobi',weeks_per_user=80,cohorts={})
        for name,users in [('train',6),('validation',3),('calibration',3)]:
            frame=fixture(worker,users=users,weeks=80,prefix=name)
            for col in ('transaction_timestamp','observation_start','observation_end'):
                frame[col]=frame[col].map(lambda t:t.isoformat()+'+03:00')
            path=inputs/(name+'.csv');frame.to_csv(path,index=False)
            manifest['cohorts'][name]=dict(rows=len(frame),users=users,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        (inputs/'manifest.json').write_text(json.dumps(manifest))
        results=None
        try:
            for resume in (False,True):
                ns={'__name__':'__main__'};done=[]
                for i,c in enumerate(nb.cells):
                    if c.cell_type!='code':continue
                    code=c.source
                    if 'INPUT_ROOT = Path(' in code:
                        code=code.replace("INPUT_ROOT = Path('/kaggle/input')",f'INPUT_ROOT = Path({str(inputs)!r})')
                        code=code.replace("WORK_ROOT = Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()",f'WORK_ROOT = Path({str(root)!r})')
                        code=code.replace('REQUIRE_GPU = True','REQUIRE_GPU = False').replace('SMOKE = False','SMOKE = True')
                        if resume:code=code.replace('RESUME_DIR = None',f'RESUME_DIR = {str(results)!r}')
                    print('V9', 'resume' if resume else 'initial','cell',i,flush=True)
                    exec(compile(code,f'V9 cell {i}','exec'),ns);done.append(i)
                    if resume and 'def make_model(' in code:
                        ns['make_model']=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Replay trained'))
                results=ns['RESULTS']
                assert ns['DECISION']['selected']=='v6_reference' and not ns['DECISION']['evidence_eligible']
                assert len(ns['RUNNER'].runs)==6
                assert {e['cohort'] for e in ns['ACCESSES']}=={'train','validation'}
                for f in ('v9_protocol.json','configuration_lock.json','artifact_manifest.json'):
                    assert json.loads((results/f).read_text())['protocol']=='v9-checkpoint-policy-v1'
            report.write_text(json.dumps(dict(status='passed',completed_code_cells=done,
                fresh_namespace_resume=True,actual_training_device=ns['GPU']['selected_training_device'],
                full_dataset_accuracy_evaluated=False,candidate_seed_runs=6,
                scope='Two-epoch synthetic software check; not forecast improvement evidence'),indent=2),encoding='utf-8')
        finally:
            from joblib.externals.loky import get_reusable_executor
            get_reusable_executor().shutdown(wait=True,kill_workers=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True,type=Path)
    main(parser.parse_args().report)
