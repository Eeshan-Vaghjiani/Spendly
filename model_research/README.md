# Model research

Spendly's forecasting and unusual-spending experiments. These models are research
candidates; they do not replace the app's deployed artifacts.

## Current result

The completed V7 Kaggle run compared 14 forecast configurations and repeated the
strongest candidates across three seeds. It did not demonstrate a reliable gain
over the V6 reference, which was retained. Mean train-fold WAPE was **32.3585%**
for the reference and **32.3857%** for the no-L2 candidate.

See [V7 results](V7_KAGGLE_RESULTS_REVIEW.md) for the verified comparisons and
limitations. The supplied checkpoint predates the final anomaly reports; their
analysis is still pending. All datasets are synthetic and amounts are in KES.

## Run on Kaggle

1. Import `Spending_Model_Upload_V7_R3_Kaggle_Evidence.ipynb`.
2. Select GPU T4 and restart the session if needed.
3. Attach exactly one supported dataset: its `manifest.json`, `train.csv`,
   `validation.csv`, and `calibration.csv` (single-cohort ZIPs also work).
4. Keep `REQUIRE_GPU=True`, `SMOKE=False`, `FEATURE_WORKERS=2` and
   `RESUME_DIR=None` for a new run. Run all cells in order.
5. Download checkpoint ZIPs during the run and the final results ZIP when finished.

The notebook is standalone. Feature preparation and Isolation Forest use CPU;
LSTM training uses GPU0. The second GPU may stay idle.

To resume, extract **your own trusted** checkpoint ZIP into `/kaggle/working` and
set `RESUME_DIR` to its result folder. Use the same notebook, inputs and compatible
environment. Completed fits are verified and reused. An incomplete individual fit
restarts; an interrupted benchmark without a completed result fails closed.
Kaggle temporary storage is not a backup: download or persist the ZIPs.

## Files

| File | Purpose |
|---|---|
| `Spending_Model_Upload_V6_R3_Kaggle.ipynb` | Historical source implementation, outputs removed |
| `Spending_Model_Upload_V7_R3_Kaggle_Evidence.ipynb` | Current standalone experiment |
| `v7_features.py`, `v7_runtime.py`, `v7_experiments.py` | Feature construction, training and comparisons |
| `v7_collective.py` | Causal group-level anomaly experiment, inspired by [PR #3](https://github.com/Eeshan-Vaghjiani/Spendly/pull/3) |
| `v7_recovery.py` | Checkpoint validation, backups and recovery |
| `build_v7_evidence.py`, `V7_NOTEBOOK_TEXT.md` | Notebook builder and methodology text |
| `build_v7_dataset.py`, `synthetic_r3_data.py` | Development-only replication with fixed new seeds |
| `analyze_v7_checkpoint.py` | CSV/JSON-only checkpoint audit; no model unpickling |
| `evidence/v7_source_audit/` | Aggregate historical audit and verification summaries |

Data generation is documented in [V7_DATA_PROTOCOL.md](V7_DATA_PROTOCOL.md), with
simulator assumptions in [R3_DATA_PROTOCOL.md](R3_DATA_PROTOCOL.md). The new V7
dataset is a separate development replication; the completed run used original R3.
The older `Spending_Model_Trial.ipynb` and combined-data builder are retained from
the original folder and are not the V7 pipeline.

## Local checks

Use an isolated Python environment with `requirements.txt`. Kaggle's recorded run
used Python3.12.13, TensorFlow2.20.0, Keras3.13.2, NumPy2.0.2, pandas2.3.3 and
scikit-learn1.6.1. The dependency ranges are not a guarantee of identical results;
the notebook exports the actual environment for every run.

From the repository root:

```powershell
python -m unittest discover -s model_research -p "test_v7_*.py" -v
python -m unittest discover -s model_research -p test_analyze_v7_checkpoint.py -v
python model_research/build_v7_evidence.py --audit model_research/evidence/v7_source_audit/v6_verified_audit.json
python model_research/smoke_v7_notebook.py --report model_research/evidence/v7_source_audit/software_smoke.json
```

The builder verifies the output-free V6 source against the recorded cell hashes.
The historical executed-source/PDF hashes stay in the audit; those private inputs
are not needed to rebuild using `--audit`. To redo the historical audit, supply
`--source <executed-V6.ipynb> --guidance <research-guidance.pdf>` instead.

Tests create temporary synthetic fixtures. The smoke runs real, short CPU training
and verifies fresh-namespace recovery; it is not predictive-performance evidence.
Raw datasets, checkpoints and generated models are excluded from this update.
Issues [#6](https://github.com/Eeshan-Vaghjiani/Spendly/issues/6) and
[#7](https://github.com/Eeshan-Vaghjiani/Spendly/issues/7) track the remaining result review.
