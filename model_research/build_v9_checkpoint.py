"""Build V9 from the unchanged V7 worker/runtime and shared five-seed-safe selection logic."""
import ast
import hashlib
from pathlib import Path
import nbformat

HERE=Path(__file__).resolve().parent


def build():
    nb=nbformat.read(HERE/'Spending_Model_Upload_V7_R3_Kaggle_Evidence.ipynb',as_version=4)
    cells={c.id:c.source for c in nb.cells}
    constants={n.targets[0].id:ast.literal_eval(n.value) for n in ast.parse(cells['v7-07']).body
        if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','') in ('WORKER_SOURCE','IF_SOURCE','CODE_HASH')}
    selection=(HERE/'v8_experiments.py').read_text(encoding='utf-8')
    tree=ast.parse(selection)
    selection=next(ast.get_source_segment(selection,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='v8_search')
    selection=selection.replace('v8_search','v9_search').replace('v8_selection_complete','v9_selection_complete').replace('v8_candidates','v9_candidates')
    selection=selection.replace('V8 observed information','V9 checkpoint policy').replace('five fixed configurations','two fixed checkpoint policies')
    experiment=cells['v7-08']+'\n\n'+(HERE/'v9_checkpoint.py').read_text(encoding='utf-8')+'\n\n'+selection
    experiment=experiment.replace("protocol='spendly-v7-evidence-v1'","protocol='v9-checkpoint-policy-v1'")
    experiment=experiment.replace("required=['v6_audit.json'","required=['v9_protocol.json','checkpoint_comparison.csv','v6_audit.json'")
    runtime=cells['v7-04']
    worker=constants['WORKER_SOURCE']
    # Bind inherited executable orchestration and this builder as well as helpers.
    # Otherwise a changed benchmark/export call could silently reuse old state.
    code_hash=hashlib.sha256((worker+runtime+experiment+
        '\n'.join(c.source for c in nb.cells if c.cell_type=='code')+
        Path(__file__).read_text(encoding='utf-8')).encode()).hexdigest()
    imports='WORKER_SOURCE = '+repr(worker)+'\nIF_SOURCE = '+repr(constants['IF_SOURCE'])+'\nCODE_HASH = '+repr(code_hash)+'\n'+cells['v7-07'][cells['v7-07'].index('import importlib'):]
    imports=imports.replace('spendly_v7_modules','spendly_v9_modules').replace('spendly_v7_worker_','spendly_v9_worker_').replace('spendly_v7_if_','spendly_v9_if_')
    setup=cells['v7-05'].replace('spendly_v7','spendly_v9')
    data=cells['v7-10']+'''
write_json(RESULTS/'v9_protocol.json',dict(protocol='v9-checkpoint-policy-v1',dataset_version=DATASET['version'],
    configurations={n:asdict(c) for n,c in v9_candidates(WORKER).items()},seeds=[42,123,2026],
    selection='Original grouped train folds and material-gain guards; benchmark after lock only',
    scope='Forecast-only; no anomaly retraining, new features, final evaluation or960epoch cap'))
'''
    finish='''checkpoint_diagnostics(RUNNER,DECISION)
write_figures(RUNNER,LEGACY_ROWS,LEGACY_METRICS,DECISION)
write_json(RESULTS/'data_composition.json',ACCESSES)
ARCHIVE=package_results(RESULTS,CODE_HASH)
print('V9 FORECAST COMPARISON COMPLETE:',ARCHIVE)
'''
    codes=[cells['v7-02'],runtime,setup,imports,experiment,data,
        'CANDIDATES, DECISION = v9_search(RUNNER)\nprint(DECISION)',cells['v7-16'],finish,
        cells['v7-24'].replace('exists in V7','exists in V9')]
    out=[nbformat.v4.new_markdown_cell((HERE/'V9_PROTOCOL.md').read_text(encoding='utf-8'))]+[nbformat.v4.new_code_cell(c) for c in codes]
    for i,c in enumerate(out):
        c.id=f'v9-{i:02d}'
        if c.cell_type=='code':compile(c.source,c.id,'exec')
    result=nbformat.v4.new_notebook(cells=out,metadata=dict(kernelspec=dict(name='python3',language='python',display_name='Python 3'),
        spendly=dict(protocol='v9-checkpoint-policy-v1',code_hash=code_hash,reference_code_hash=constants['CODE_HASH'])))
    nbformat.validate(result)
    path=HERE/'Spending_Model_V9_Checkpoint_Kaggle.ipynb'
    path.write_text(nbformat.writes(result),encoding='utf-8')
    print('Built',path.name, 'with',len(codes),'code cells')


if __name__=='__main__':build()
