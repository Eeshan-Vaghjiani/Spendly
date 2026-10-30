"""Generate the final submission notebook with aggregate evidence and evaluator.

Default Run All displays the locked results. Final data is never opened unless
the explicit fresh-evaluation switch is enabled and no ledger exists.
"""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE/'Spendly_Final_Isolation_Forest_Submission.ipynb'


def notebook():
    source_names = ['if_final_features.py', 'if_final_reference.py', 'if_final_pipeline.py', 'if_submission.py']
    sources = {name: (HERE/name).read_text(encoding='utf-8') for name in source_names}
    evidence = json.loads((HERE/'evidence/if_submission/final_results.json').read_text())
    lock = json.loads((HERE/'if_submission_lock.json').read_text())
    assert lock['sources'] == {name: hashlib.sha256(source.encode()).hexdigest() for name, source in sources.items()}
    cells = []
    def add(kind, text):
        cell = {'cell_type': kind, 'id': f'if-submission-{len(cells):02d}', 'metadata': {}, 'source': text.splitlines(True)}
        if kind == 'code':
            ast.parse(text)
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    add('markdown', '''# Spendly — Final Isolation Forest submission

## Research status: frozen and evaluated
The retained single excess-view Isolation Forest was evaluated on standard and
shifted synthetic R3 users with no refitting or threshold changes. Mobile
integration is a separate deliverable. Results are final for this protocol;
do not retune on these test outcomes.

300 trees, max_samples128, five causal features, log1p transform, score=-score_samples,
threshold0.6451359189730762. Evaluation interval:2023-04-24 through2024-01-01
(exclusive); earlier personal expenses are context. Normal and anomalous
transactions remain in the historical mixed-data fitting design.

The V2.1-derived candidate was not adopted after a matched development comparison.
See IF_FINALIZATION.md for the design decision and IF_SUBMISSION_RESULTS.md for
the final reporting text. The historical80% precision/recall/F1 aspiration was
not achieved; a completed experiment is not a claim that all targets were met.

**Default Run All reviews recorded aggregate results; it does not rerun tests.**
''')
    add('code', 'import json\nimport pandas as pd\nRESULTS = json.loads('+repr(json.dumps(evidence))+')\nLOCK = json.loads('+repr(json.dumps(lock))+')\n'
        +'''summary = pd.DataFrame({name: {key: result[key] for key in
    ('rows','precision','recall','F1','AP','ROC_AUC','FPR','accuracy','balanced_accuracy','alert_rate')}
    for name, result in RESULTS['results'].items()}).T
display(summary)
''')
    add('code', '''import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for axis, (name, result) in zip(axes, RESULTS['results'].items()):
    matrix = [[result['TN'], result['FP']], [result['FN'], result['TP']]]
    axis.imshow(matrix, cmap='Blues')
    for i in range(2):
        for j in range(2):
            axis.text(j, i, str(matrix[i][j]), ha='center', va='center', color='red')
    axis.set(xticks=[0,1], yticks=[0,1], xticklabels=['Normal','Alert'],
        yticklabels=['Normal','Anomalous'], xlabel='Prediction', ylabel='Actual', title=name)
plt.tight_layout()
plt.show()
families = pd.DataFrame({name: {family: value['recall'] for family, value in result['families'].items()}
    for name, result in RESULTS['results'].items()})
display(families)
families.plot.bar(ylim=(0,1), title='Final transaction recall by synthetic anomaly family')
plt.tight_layout()
plt.show()
for name, result in RESULTS['results'].items():
    print(name, '95% user-cluster intervals:', result['confidence_intervals_95pct'])
''')
    add('markdown', '''## Interpretation and limitations
The model is strongest on duplicate-like, large and burst transactions, and weak
on recurring increases and split transactions. About38% of standard-test alerts
and45% of shifted-test alerts are false positives under the simulator labels.
Alerts mean potential unusual spending requiring review, not confirmed fraud.

These are independent-user synthetic cohorts, not representative real financial
data. Earlier cohort inspection in unrelated external sessions cannot be
independently attested. Bootstrap intervals are conditional on this one frozen
model and simulator. The1% calibration budget is not a guarantee of population FPR.

## Reproducibility and frozen source
The source archive SHA256 and exact dataset manifest, feature definitions,
threshold, source hashes and environment are recorded below. Default execution
does not deserialize an estimator or read any raw dataset.
''')
    add('code', 'print(json.dumps(LOCK, indent=2))\nSOURCES = '+repr(sources)+'\n')
    add('markdown', '''## Optional authorized independent reproduction
For an independently authorized reproduction only, use the pinned original
artifact environment in if_submission_requirements.txt. Supply the original
project-owned alert archive, complete R3 directory and persistent access ledger.
The evaluator refuses repeated access recorded in that ledger. Do not change
the ledger path to bypass an existing evaluation. For routine review, use the
saved scores/metrics instead of consuming the cohorts again.
''')
    add('code', '''RUN_FRESH_AUTHORIZED_EVALUATION = False
if RUN_FRESH_AUTHORIZED_EVALUATION:
    from pathlib import Path
    import hashlib, sys
    module_dir = Path('if_submission_modules')
    module_dir.mkdir(exist_ok=False)
    for name, source in SOURCES.items():
        assert hashlib.sha256(source.encode()).hexdigest() == LOCK['sources'][name]
        (module_dir/name).write_text(source, encoding='utf-8', newline='\n')
    (module_dir/'lock.json').write_text(json.dumps(LOCK), encoding='utf-8')
    sys.path.insert(0, str(module_dir.resolve()))
    if any(name[:-3] in sys.modules for name in SOURCES):
        raise RuntimeError('Use a clean kernel to prevent stale modules')
    from if_submission import run
    DATASET = Path('SET_R3_DIRECTORY')
    ARCHIVE = Path('SET_ORIGINAL_RETAINED_ALERT_ARCHIVE.zip')
    OUTPUT = Path('new_independent_evaluation')
    LEDGER = DATASET/'if_submission_access_ledger'
    run(DATASET, ARCHIVE, OUTPUT, LEDGER, module_dir/'lock.json')
else:
    print('Frozen research complete. Reviewing saved evidence; no holdout inference.')
'''.replace("newline='\n'", "newline='\\n'"))
    return {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'}, 'spendly': {'status': 'frozen_evaluated', 'lock': lock}}, 'cells': cells}


if __name__ == '__main__':
    OUTPUT.write_text(json.dumps(notebook(), indent=2)+'\n', encoding='utf-8', newline='\n')
    print(OUTPUT)
