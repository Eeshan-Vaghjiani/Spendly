"""Standalone CPU-only frozen artifact check; never trains or downloads data."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE/'LSTM_Demo_Readiness_CPU.ipynb'


def build():
    sources = {name: (HERE/name).read_text(encoding='utf-8') for name in
               ('category_lstm_features.py', 'category_lstm_frozen.py', 'check_category_lstm.py')}
    hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in sources.items()}
    cells = []
    def add(kind, source):
        cell = dict(cell_type=kind, id=f'lstm-ready-{len(cells)}', metadata={}, source=source.splitlines(True))
        if kind == 'code':
            ast.parse(source); cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    add('markdown', '''# Category LSTM — CPU evaluation readiness

In Kaggle choose **Accelerator: None**. GPU is not used. Attach the frozen local
bundle containing model.keras, input_scaler.pkl, target_scaler.pkl, metadata.json.
This notebook verifies hashes and runs generated-history inference. It does not
train, download records, or establish external accuracy.

Use a compatible CPU environment: tensorflow2.20.0, keras3.13.2,
scikit-learn1.6.1. The recorded verification environment also used numpy2.0.2,
pandas2.3.3 and joblib1.5.3. Package installation is deliberately separate.

Important finding: sparse synthetic histories produced very large utilities
forecasts despite no utilities history. Preserve those outputs during evaluation;
do not treat artifact loading success as model-quality approval.
''')
    add('code', '''import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
import sys, hashlib, json
SOURCES = '''+repr(sources)+'''\nHASHES = '''+repr(hashes)+'''
MODULE_DIR = Path('/kaggle/working/lstm_readiness_modules') if Path('/kaggle').exists() else Path('lstm_readiness_modules')
MODULE_DIR.mkdir(exist_ok=True)
if any(name[:-3] in sys.modules for name in SOURCES):
    raise RuntimeError('Restart kernel before rerunning setup to avoid stale imports')
for name, source in SOURCES.items():
    assert hashlib.sha256(source.encode()).hexdigest() == HASHES[name]
    path = MODULE_DIR/name
    if path.exists() and path.read_text(encoding='utf-8') != source:
        raise ValueError('Existing source differs')
    with path.open('w', encoding='utf-8', newline='\\n') as f:
        f.write(source)
sys.path.insert(0, str(MODULE_DIR.resolve()))
from check_category_lstm import check
''')
    add('code', '''BUNDLE = Path('/kaggle/input/YOUR_PRIVATE_MODEL_DATASET/category_lstm_frozen')
RUN_CHECK = False  # Set True after choosing the bundle path and CPU runtime.
if RUN_CHECK:
    report, forecasts = check(BUNDLE)
    report['synthetic_forecasts_KES'] = forecasts.tolist()
    OUTPUT = Path('/kaggle/working/lstm_readiness.json') if Path('/kaggle').exists() else Path('lstm_readiness.json')
    with OUTPUT.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, allow_nan=False)
    print(json.dumps(report, indent=2))
else:
    print('Configured only. No model loaded or records read.')
''')
    add('markdown', '''## External evaluation boundary

The adapter requires an explicit household, confirmed complete observed history,
Monday-start target and as-of time. At least26 complete weeks are required; retain
all available history for the52-week features. It rejects target-week rows,
unknown expense categories, duplicate IDs, missing values and ambiguous dates.
Income is excluded; confirmed quiet weeks are included.

Wasaa schema mapping remains separate. Evaluate both frozen LSTMs on common
eligible origins if both input contracts can be supported, with a predeclared
comparison. Do not fit scalers, optimize thresholds, or train on external data.
The category bundle is the final all-development refit: its stored development
scores belong to an earlier checkpoint and are not independent scores for this
artifact. The retained total LSTM and finalized Isolation Forest remain unchanged.
''')
    return dict(nbformat=4, nbformat_minor=5, cells=cells, metadata={
        'kernelspec': {'display_name':'Python 3','language':'python','name':'python3'},
        'language_info': {'name':'python'}, 'spendly': {'CPU_only':True,'source_hashes':hashes}})


if __name__ == '__main__':
    OUTPUT.write_text(json.dumps(build(), indent=2)+'\n', encoding='utf-8', newline='\n')
