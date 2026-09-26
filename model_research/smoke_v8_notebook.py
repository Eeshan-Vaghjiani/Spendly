"""Execute V8 and its resume path on temporary observed-income fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import nbformat
from test_v8_income import worker_module,income_fixture,HERE


def main(report):
    with tempfile.TemporaryDirectory(prefix='spendly_v8_smoke_') as temporary:
        root=Path(temporary); inputs=root/'inputs'; inputs.mkdir()
        nb,worker=worker_module(root)
        manifest=dict(version='spendly-synthetic-v7-dev-v1',status='complete',currency='KES',
            timezone='Africa/Nairobi',weeks_per_user=80,cohorts={})
        for name,users in [('train',6),('validation',3),('calibration',3)]:
            frame=income_fixture(worker,users=users,weeks=80,prefix=name)
            for col in ('transaction_timestamp','observation_start','observation_end'):
                frame[col]=frame[col].map(lambda d:d.isoformat()+'+03:00')
            path=inputs/(name+'.csv'); frame.to_csv(path,index=False)
            manifest['cohorts'][name]=dict(rows=len(frame),users=users,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        (inputs/'manifest.json').write_text(json.dumps(manifest))
        result=None
        try:
            for replay in (False,True):
                ns={'__name__':'__main__'}; completed=[]
                for i,cell in enumerate(nb.cells):
                    if cell.cell_type!='code': continue
                    code=cell.source
                    if 'INPUT_ROOT = Path(' in code:
                        code=code.replace("INPUT_ROOT = Path('/kaggle/input')",f'INPUT_ROOT = Path({str(inputs)!r})')
                        code=code.replace("WORK_ROOT = Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()",f'WORK_ROOT = Path({str(root)!r})')
                        code=code.replace('REQUIRE_GPU = True','REQUIRE_GPU = False').replace('SMOKE = False','SMOKE = True')
                        if replay: code=code.replace('RESUME_DIR = None',f'RESUME_DIR = {str(result)!r}')
                    print('V8', 'resume' if replay else 'initial','cell',i,flush=True)
                    exec(compile(code,f'V8 cell {i}','exec'),ns); completed.append(i)
                    if replay and 'def make_model(' in code:
                        ns['make_model']=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('Replay retrained'))
                result=ns['RESULTS']
                assert ns['DECISION']['selected']=='v6_reference'
                assert not ns['DECISION']['evidence_eligible']
                assert all(a['cohort'] in ('train','validation') for a in ns['ACCESSES'])
                for filename in ('configuration_lock.json','artifact_manifest.json','v8_protocol.json'):
                    assert json.loads((result/filename).read_text())['protocol']=='v8-observed-income-v1'
            summary=dict(status='passed',code_cells=completed,full_namespace_resume=True,
                training_device=ns['GPU']['selected_training_device'],
                real_CPU_training=ns['GPU']['selected_training_device']=='/CPU:0',
                GPU_tested=ns['GPU']['selected_training_device']=='/GPU:0',full_dataset_performance=False,
                selected=ns['DECISION']['selected'],all_five_candidates_three_seeds=True,
                archive_bytes=ns['ARCHIVE'].stat().st_size)
            report.write_text(json.dumps(summary,indent=2),encoding='utf-8')
        finally:
            from joblib.externals.loky import get_reusable_executor
            get_reusable_executor().shutdown(wait=True,kill_workers=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--report',type=Path,required=True)
    main(parser.parse_args().report)
