# Generalization Research V3

Open `Spending_Model_Generalization_Research_V3.ipynb` in Google Colab. It is a
standalone experiment, not a replacement for the models used by the application.
Existing notebooks and application artifacts are unchanged.

## Run In Colab

1. Upload the notebook to Colab and use a Python CPU runtime. No GPU is required.
2. Leave `MODE` as `quick` in the configuration cell and choose **Runtime > Run all**.
3. Review validation rankings, threshold feasibility, then the known-user-future
   and unseen-user evaluation tables. Final evaluation is disabled by default.
4. Change `MODE` to `full` for larger experiments or `smoke` for correctness checks.
   Configure precision/FPR requirements before training, not after seeing test results.
5. Once the method is settled, set `RUN_FINAL = True` in the final-gate cell and
   run that cell once. This tests every reserved seed and both synthetic processes.
   Do not change the configuration or model after freezing without rerunning development.

Standard Colab already includes the dependencies. The notebook reports actual
Python/package versions and does not upgrade libraries inside a running session.
No CSV, ZIP, repository checkout, credentials, or previous models are required.

## What Changed

- Forecasting compares last-week, four-week mean, inferred-recurring baseline,
  regularized Ridge, and histogram gradient boosting with raw versus normalized targets.
- Monetary inputs use past-only scaling, with absolute scale retained so the raw-target
  comparison is not deprived of information. Monthly recurrence uses longer history
  and includes Sunday evening in the target week.
- Anomaly detection compares rules, Isolation Forest, and a hybrid. Every comparator
  gets a separately calibrated threshold and is evaluated on identical held-out rows.
- Two rolling validation folds select models. A separate later calibration period
  fixes anomaly thresholds. Users reserved for transfer evaluation never enter fitting.
- Events crossing selection boundaries are purged from label-based selection masks,
  not from the causal feature stream. Event recall distinguishes already-started events.
- Synthetic environments include benign repeats, nightlife, shopping bursts, and large
  planned purchases, not just easy normal-versus-injected examples. Final shifted data
  also contains anomaly families absent from development and lower anomaly prevalence.
- Correctness tests check future-data invariance, label blindness, independent generator
  streams, recurrence boundaries, full-week coverage, event separation, and absent classes.

## Read The Results

Forecasting reports MAE/RMSE in **KES**, WAPE as a **fraction** (`0.30` means 30%),
R-squared, and signed bias. Classification accuracy is not a forecast metric.

Anomaly results include accuracy, balanced accuracy, precision, recall, F1, average
precision, ROC AUC, false-positive rate, confusion counts, alert rate, per-family
recall, event recall, and detection delay. High ordinary accuracy can be misleading
when most transactions are normal.

Default threshold selection maximizes calibration recall subject to precision at
least `0.80` and false-positive rate at most `0.02`. These are measured constraints,
not guarantees on future data. If none is feasible, the notebook explicitly reports
failure and falls back to no alerts. It does not manufacture a high precision score.

User-cluster bootstrap intervals quantify evaluation uncertainty conditional on the
fitted model. Seed summaries report both `count` (defined values) and `size` (total
rows); missing-class metrics remain undefined instead of being silently scored zero.
Transaction evaluation includes ongoing events; event recall excludes left-censored
events. No paired statistical superiority claim is made from separate intervals.

## Continuous Research

Repeat development experiments and keep their manifests/results. Once you have looked
at an evaluation result and used it to change the method, it is development evidence,
not a fresh test. Reserve a new seed batch before a later final evaluation and report
every seed, not just the best. Switching mode or output folder does not refresh a seed.

The final gate verifies the saved model bytes, configuration, and implementation,
then marks the batch consumed before generating data. This local guard is not a
cross-session registry: keep your own research log across Colab sessions.

Outputs appear in `research_v3_outputs/`: validation/evaluation CSVs, predictions,
per-family/event results, feature order, runtime and model manifests, reference score
distributions, and frozen research models. Set `SPENDLY_EXPORT_ZIP=1` for the optional
archive cell and `SPENDLY_COLAB_DOWNLOAD=1` to request its download. Colab storage is
temporary, so download results before ending the session. Only load trusted joblib files.

This is a new, harder synthetic benchmark, not an exact V2 artifact replay. Its scores
cannot be placed directly beside old V2 scores as a fair improvement comparison. The
new generator is simplified and does not reproduce all eleven application categories,
income transactions, budgets, or missing-observation patterns. Positive expenses remain
positive; there is no inferred real-world fraud label. Real-world recall needs independent
labels, including missed cases. Better synthetic metrics do not establish real-user accuracy.

## Local Verification

The final revised quick configuration completed locally in approximately 178 seconds
on Python 3.13.2, NumPy 2.4.6, pandas 3.0.3, and scikit-learn 1.6.1. Colab timing and
results may differ with its runtime versions. Full mode and the reserved final seeds
have not been evaluated. An isolated smoke run exercised the final path with disposable
seeds instead; those checks are software verification, not final model evidence.

Quick selected raw-target histogram gradient boosting and Isolation Forest using
validation only. The following are equal-weight means over the two development seeds,
not independent final results:

| Evaluation group | Forecast WAPE | Recurring baseline WAPE | Anomaly precision | Anomaly recall |
|---|---:|---:|---:|---:|
| Known users, future, baseline process | 38.23% | 47.83% | 78.24% | 57.35% |
| Known users, future, shifted process | 49.35% | 53.75% | 50.00% | 37.33% |
| Unseen users, baseline process | 41.91% | 50.76% | 83.82% | 63.27% |
| Unseen users, shifted process | 45.75% | 50.80% | 77.72% | 66.20% |

This supports further research, not a claim that V3 beats the deployed V1/V2 models.
In particular, precision constraints met on calibration did not consistently survive
evaluation, and selected Isolation Forest did not consistently beat the other anomaly
comparators. Do not discard those failures or tune on the reserved final batch.
