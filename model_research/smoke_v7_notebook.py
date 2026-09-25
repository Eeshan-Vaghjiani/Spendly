"""Execute every generated cell on disposable handcrafted synthetic data, real CPU ML.

No R3 files or production seeds are opened. Outputs explicitly aren't accuracy evidence.
"""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path
import nbformat
import pandas as pd
from test_v7_evidence import modules, fixture, HERE


def main(report):
    with tempfile.TemporaryDirectory(prefix='spendly_v7_software_') as temporary:
        root=Path(temporary); inputs=root/'inputs'; inputs.mkdir()
        _,worker,_,_=modules(root)
        manifest=dict(version='spendly-synthetic-v7-dev-v1',status='complete',currency='KES',
            timezone='Africa/Nairobi',weeks_per_user=80,cohorts={})
        for cohort,users in [('train',6),('validation',3),('calibration',3)]:
            data=fixture(worker,users=users,weeks=80,prefix='software_'+cohort)
            for col in ('transaction_timestamp','observation_start','observation_end'):
                data[col]=data[col].map(lambda t:t.isoformat()+'+03:00')
            path=inputs/(cohort+'.csv'); data.to_csv(path,index=False)
            manifest['cohorts'][cohort]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                rows=len(data),users=users)
        (inputs/'manifest.json').write_text(json.dumps(manifest))
        nb=nbformat.read(HERE/'Spending_Model_Upload_V7_R3_Kaggle_Evidence.ipynb',as_version=4)
        ns={'__name__':'__main__'}; completed=[]
        try:
            for i,cell in enumerate(nb.cells):
                if cell.cell_type!='code':
                    continue
                code=cell.source
                if 'INPUT_ROOT = Path(' in code:
                    code=code.replace("INPUT_ROOT = Path('/kaggle/input')",f'INPUT_ROOT = Path({str(inputs)!r})')
                    code=code.replace("WORK_ROOT = Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()",f'WORK_ROOT = Path({str(root)!r})')
                    code=code.replace('REQUIRE_GPU = True','REQUIRE_GPU = False').replace('SMOKE = False','SMOKE = True')
                print(f'EXECUTING GENERATED CELL {i}',flush=True)
                exec(compile(code,f'generated V7 cell {i}','exec'),ns)
                completed.append(i)
            assert ns['DATASET']['benchmark_role']=='fresh synthetic development replication'
            assert pd.read_csv(ns['RESULTS']/'anomaly_metrics.csv').benchmark_role.eq(ns['DATASET']['benchmark_role']).all()
            original_results=ns['RESULTS']
            resumed={'__name__':'__main__'}
            for i,cell in enumerate(nb.cells):
                if cell.cell_type!='code':
                    continue
                code=cell.source
                if 'INPUT_ROOT = Path(' in code:
                    code=code.replace("INPUT_ROOT = Path('/kaggle/input')",f'INPUT_ROOT = Path({str(inputs)!r})')
                    code=code.replace("WORK_ROOT = Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()",f'WORK_ROOT = Path({str(root)!r})')
                    code=code.replace('REQUIRE_GPU = True','REQUIRE_GPU = False').replace('SMOKE = False','SMOKE = True')
                    code=code.replace('RESUME_DIR = None',f'RESUME_DIR = {str(original_results)!r}')
                print(f'RESUMING GENERATED CELL {i}',flush=True)
                exec(compile(code,f'resumed V7 cell {i}','exec'),resumed)
                if 'def train_model(' in code:
                    resumed['make_model']=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('Resume must not train'))
            summary=dict(status='passed',completed_code_cells=completed,mode='CPU synthetic software verification',
                full_fresh_namespace_resume=True,resume_retraining=False,
                dataset_version=ns['DATASET']['version'],benchmark_role=ns['DATASET']['benchmark_role'],
                real_training=True,production_data_accessed=False,gpu_execution=False,
                registry_rows=len(ns['RUNNER'].registry),
                selected=ns['DECISION']['selected'],
                artifacts=sorted(p.name for p in ns['RESULTS'].iterdir() if p.is_file()),
                archive_bytes=ns['ARCHIVE'].stat().st_size,timings=dict(ns['TIMINGS']))
            report.write_text(json.dumps(summary,indent=2),encoding='utf-8')
            print('V7 generated notebook software smoke PASSED')
        finally:
            from joblib.externals.loky import get_reusable_executor
            get_reusable_executor().shutdown(wait=True,kill_workers=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--report',required=True,type=Path)
    main(parser.parse_args().report)
