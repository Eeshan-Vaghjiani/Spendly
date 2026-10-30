"""Build a standalone, output-free CPU notebook from reviewed research modules."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE/'Spending_Isolation_Forest_Finalization.ipynb'
MODULES = ('if_final_features.py', 'if_final_reference.py', 'if_final_pipeline.py')


def notebook():
    modules = {name: (HERE/name).read_text(encoding='utf-8') for name in MODULES}
    hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in modules.items()}
    code = '''from pathlib import Path
import hashlib, sys
MODULES = '''+repr(modules)+'''
EXPECTED = '''+repr(hashes)+'''
MODULE_DIR = Path('/kaggle/working/if_finalization_modules') if Path('/kaggle').exists() else Path('if_finalization_modules')
MODULE_DIR.mkdir(exist_ok=True)
for name, source in MODULES.items():
    assert hashlib.sha256(source.encode()).hexdigest() == EXPECTED[name]
    path = MODULE_DIR/name
    if path.exists() and path.read_text(encoding='utf-8') != source:
        raise RuntimeError('Existing module differs; use a new clean session/folder')
    path.write_text(source, encoding='utf-8')
sys.path.insert(0, str(MODULE_DIR.resolve()))
for name in ('if_final_features', 'if_final_reference', 'if_final_pipeline'):
    if name in sys.modules:
        raise RuntimeError('Restart kernel before rerunning setup to prevent stale imports')
from if_final_pipeline import PROTOCOL, run_development, versions
print(versions())
print(PROTOCOL)
'''
    cells = []
    def add(kind, text):
        c = {'cell_type': kind, 'id': f'if-final-{len(cells):02d}', 'metadata': {}, 'source': text.splitlines(True)}
        if kind == 'code':
            ast.parse(text)
            c.update(execution_count=None, outputs=[])
        cells.append(c)
    add('markdown', '''# Spendly — Isolation Forest finalization candidate

Builds on the supplied V2.1 behavioural feature design. This is a **development
comparison and freeze workflow**, not a claim of final-test superiority.

## Run on Kaggle or Colab (CPU)
The verified Windows run used Python3.10.6, numpy1.26.4, pandas2.3.3,
scikit-learn1.7.2 and joblib1.6.0 (see if_final_requirements.txt).
No TensorFlow, GPU or downloads in code. Other runtimes must record their versions;
cross-platform byte-identical artifacts are not promised.
Attach original R3 manifest.json and development train.zip, calibration.zip,
validation.zip. They may be together or ZIPs in a development/ subfolder.
Set INPUT_ROOT to that directory. Do not attach final/shifted test files.

Both estimators fit identical mixed-label training rows before2023-04-24.
Calibration users during2023-04-24–2023-08-28 set a negative-only1% FPR cutoff.
Validation users during2023-08-28–2024-01-01 provide the later comparison.
Past-only user history is available for features; evaluation labels never choose
the threshold. The reference is the preserved V6 excess feature view under this
new common protocol, not a reproduction of its old metric table.

The candidate uses Nairobi time, normalized nanoseconds and simultaneous-batch
exclusion. Predictions are saved for auditing and paired user-bootstrap intervals.
These are reused synthetic development cohorts, not new independent evidence.
''')
    add('code', code)
    add('code', '''# Set paths explicitly. The output must not exist (protects prior runs).
INPUT_ROOT = Path('/kaggle/input/YOUR_R3_DATASET')
OUTPUT_ROOT = Path('/kaggle/working/if_finalization_run') if Path('/kaggle').exists() else Path('if_finalization_run')
RUN_DEVELOPMENT = False  # set True after checking the displayed protocol and paths
if RUN_DEVELOPMENT:
    report = run_development(INPUT_ROOT, OUTPUT_ROOT)
else:
    print('Configured only. Set INPUT_ROOT and RUN_DEVELOPMENT=True to run.')
''')
    add('markdown', '''## Preserve evidence and review
Download the entire run folder (or use the ZIP cell below). It includes the
protocol/source/environment identities, input hashes, both frozen pipelines,
reload parity, metrics, family/event burden, row scores and paired uncertainty.
Row predictions are synthetic audit evidence; do not commit them or model binaries.

Promotion is manual after reviewing gains, false-positive burden and family
trade-offs. No final-test reader is included: approve and lock that separate
evaluation only after this comparison. Do not tune using final-test outcomes.
Joblib is executable serialization: reload only your own trusted artifacts.
''')
    add('code', '''import shutil
if RUN_DEVELOPMENT:
    archive = OUTPUT_ROOT.with_suffix('.zip')
    if archive.exists():
        raise FileExistsError(archive)
    shutil.make_archive(str(OUTPUT_ROOT), 'zip', OUTPUT_ROOT)
    print('Download:', archive)
''')
    return {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'}, 'spendly': {'module_hashes': hashes}}, 'cells': cells}


if __name__ == '__main__':
    OUTPUT.write_text(json.dumps(notebook(), indent=2)+'\n', encoding='utf-8')
    print(OUTPUT)
