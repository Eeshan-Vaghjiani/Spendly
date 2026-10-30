"""Build a standalone forecast-only V8 notebook from the checked V7 implementation."""
import ast
import hashlib
from pathlib import Path
import nbformat

HERE=Path(__file__).resolve().parent


def build():
    original=nbformat.read(HERE/'Spending_Model_Upload_V7_R3_Kaggle_Evidence.ipynb',as_version=4)
    cells={c.id:c.source for c in original.cells}
    tree=ast.parse(cells['v7-07'])
    constants={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)
        and n.targets[0].id in ('WORKER_SOURCE','IF_SOURCE','CODE_HASH')}
    worker=constants['WORKER_SOURCE']+'\n\n'+(HERE/'v8_features.py').read_text(encoding='utf-8')
    runtime=cells['v7-04']
    # V8 retains receipts but reports expense composition explicitly.
    runtime=runtime.replace('expense_rows=len(data)',"expense_rows=int(data.transaction_type.eq('expense').sum())")
    runtime=runtime.replace('anomaly_prevalence=float(data.label.mean())',"anomaly_prevalence=float(data.loc[data.transaction_type.eq('expense'),'label'].mean())")
    experiments=cells['v7-08']+'\n\n'+(HERE/'v8_experiments.py').read_text(encoding='utf-8')
    experiments=experiments.replace("protocol='spendly-v7-evidence-v1'","protocol='v8-observed-income-v1'")
    experiments=experiments.replace("required=['v6_audit.json'","required=['v8_protocol.json','v6_audit.json'")
    code_hash=hashlib.sha256((worker+runtime+experiments).encode()).hexdigest()
    setup=cells['v7-05'].replace('spendly_v7','spendly_v8')
    imports=cells['v7-07']
    start=imports.index('import importlib')
    imports='WORKER_SOURCE = '+repr(worker)+'\nIF_SOURCE = '+repr(constants['IF_SOURCE'])+'\nCODE_HASH = '+repr(code_hash)+'\n'+imports[start:]
    imports=imports.replace("WORK_ROOT/'spendly_v7_modules'","WORK_ROOT/'spendly_v8_modules'").replace("'spendly_v7_worker_'","'spendly_v8_worker_'").replace("'spendly_v7_if_'","'spendly_v8_if_'")
    data=cells['v7-10']
    data=data.replace('TRAIN=restrict_history(TRAIN_RAW,TRAIN_END)',
        "TRAIN=WORKER.expense_eligible(restrict_history(TRAIN_RAW,TRAIN_END))\nprint('Eligible training users with expenses:',TRAIN.user_id.nunique())")
    data += '''
write_json(RESULTS/'v8_protocol.json',dict(protocol='v8-observed-income-v1',dataset_version=DATASET['version'],
    candidate_names=list(v8_candidates(WORKER)),seeds=[42,123,2026],income_policy='observed before origin only',
    scope='forecast-only development experiment; no anomaly retraining or final evaluation',
    income_rows=int(TRAIN.transaction_type.eq('income').sum()),
    users_with_income=int(TRAIN.loc[TRAIN.transaction_type.eq('income'),'user_id'].nunique())))
print('V8 expense users:',TRAIN.loc[TRAIN.transaction_type.eq('expense'),'user_id'].nunique(),
      '| users with observed income:',TRAIN.loc[TRAIN.transaction_type.eq('income'),'user_id'].nunique())
'''
    export='''write_figures(RUNNER,LEGACY_ROWS,LEGACY_METRICS,DECISION)
write_json(RESULTS/'data_composition.json',ACCESSES)
ARCHIVE=package_results(RESULTS,CODE_HASH)
print('FORECAST EXPERIMENT COMPLETE:',ARCHIVE)
print('Download the ZIP. Do not deploy until results are reviewed.')
'''
    introduction=(HERE/'V8_PROTOCOL.md').read_text(encoding='utf-8')
    out=[nbformat.v4.new_markdown_cell(introduction)]
    for code in (cells['v7-02'],runtime,setup,imports,experiments,data,
                 'CANDIDATES, DECISION = v8_search(RUNNER)\nprint(DECISION)',cells['v7-14'],cells['v7-16'],export,cells['v7-24'].replace('exists in V7','exists in V8')):
        out.append(nbformat.v4.new_code_cell(code))
    for i,cell in enumerate(out):
        cell.id=f'v8-{i:02d}'
        if cell.cell_type=='code': compile(cell.source,cell.id,'exec')
    nb=nbformat.v4.new_notebook(cells=out,metadata=dict(kernelspec=dict(name='python3',language='python',display_name='Python 3'),
        spendly=dict(protocol='v8-observed-income-v1',code_hash=code_hash,reference_code_hash=constants['CODE_HASH'])))
    nbformat.validate(nb)
    output=HERE/'Spending_Model_V8_Income_Kaggle.ipynb'
    output.write_text(nbformat.writes(nb),encoding='utf-8')
    print('Built',output.name,'with',len(out)-1,'code cells')


if __name__=='__main__': build()
