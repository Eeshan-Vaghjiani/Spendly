"""Build an aggregate-only results notebook. No datasets, models or secrets."""
import ast
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUTPUT=HERE/'Wasaa_Model_Results.ipynb'


def build():
    report=json.loads((HERE/'evidence/wasaa_transfer/results.json').read_text())
    audit=json.loads((HERE/'evidence/wasaa_transfer/audit.json').read_text())
    cells=[]
    def cell(kind,text):
        value={'cell_type':kind,'metadata':{},'id':f'wasaa-results-{len(cells)}','source':text.splitlines(True)}
        if kind=='code':
            ast.parse(text);value.update(outputs=[],execution_count=None)
        cells.append(value)
    cell('markdown', '''# R3-trained models on Wasaa synthetic data

Frozen CPU evaluation,500 households,12 weekly targets. No retraining.
This notebook displays saved aggregate evidence; it does not load models or
access the API. Read WASAA_TRANSFER_RESULTS.md for assumptions and limitations.

Retained total LSTM transfers poorly (75.28% consumption WAPE versus34.52% R3
validation). Category LSTM produces catastrophic outputs on the mapped subset.
IF flags46/39,679 transactions; precision/recall/F1 are unavailable without labels.
''')
    cell('code', 'import json\nimport pandas as pd\nREPORT=json.loads('+repr(json.dumps(report))+')\nAUDIT=json.loads('+repr(json.dumps(audit))+')\n'
         +'''table=pd.DataFrame(REPORT['forecast_metrics']).T
table['WAPE_percent']=100*table['WAPE']
display(table[['rows','WAPE_percent','MAE_KES','RMSE_KES','R2','within20']])
display(pd.DataFrame(AUDIT['forecast_distributions']).T)
''')
    cell('markdown', '''## Reading the numbers
Category mapped WAPE is a ratio of2.069e17, or2.069e19 percent; it is not a
formatting error. Do not silently clip the catastrophic outputs. The mapped
subset covers84.21% of external outflow amount and is not the full spending
target. All nine predicted outputs count in its total.

The reference beats the last-week baseline on WAPE but has substantial downward
bias and lower Within20. R3/Wasaa differ in population, scales, categories and
merchant availability, so cross-dataset deltas do not isolate one cause.
''')
    cell('code', '''display(pd.DataFrame(REPORT['category_metrics']).T)
print(json.dumps(REPORT['alerts'],indent=2))
print(json.dumps(REPORT['coverage'],indent=2))
print(json.dumps(AUDIT['WAPE_95pct_user_cluster_intervals'],indent=2))
''')
    cell('markdown', '''## Interpretation
Over-budget association is not anomaly ground truth. Low alert frequency is not
proof of accurate detection. Findings are conditional on missing-merchant
handling, fixed category mappings and assumed complete internal snapshot weeks.
There are no real-user accuracy or fraud-detection claims.

The frozen evaluation ran on Windows CPU. Kaggle reproduction must use
Accelerator=None; source and artifacts are documented in the report and local
evaluation package. No training or service deployment is part of this notebook.
''')
    return {'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},
             'language_info':{'name':'python'}},'cells':cells}


if __name__=='__main__':
    OUTPUT.write_text(json.dumps(build(),indent=2)+'\n',encoding='utf-8',newline='\n')
