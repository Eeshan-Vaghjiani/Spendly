# Spendly V9 — checkpoint-policy comparison

Two fixed configurations test whether the previous predictive stopping rule ended
before a useful checkpoint appeared. This is a hypothesis, not an established
forecast improvement. The tiny-fit diagnostic improved with extra optimizer
updates, but full-data training already takes many updates per epoch. Its23.7%
training-error reduction does not predict a comparable held-out gain.

## What changes

| Configuration | Checkpoint metric | Patience | Max epochs | min_delta |
|---|---|---:|---:|---:|
| V6 reference | regularized val_loss |16|120|0|
| Predictive full budget | val_weighted_mae |121|120|0|

Both restore their best checkpoint. The candidate deliberately runs the complete
120-epoch stopping fit, then refits only through the selected best epoch. The
original architecture, mean-residual target, expense-only8-week features, L2.001,
learning rate.0003, batch256, clipnorm1 and fixed learning-rate schedule remain.
This compares checkpoint policies jointly; it does not isolate a single monitor
or patience parameter. The earlier predictive control with patience10/min_delta1e-4
is historical context, not a newly matched third arm.

## Evaluation

Two configurations ×3 seeds ×3 user-separated chronological folds, each with
stopping and refit phases (up to36 fits plus final refit). Same V7 common row coverage,
train-only vocab/scalers, paired1000-user bootstrap and1pp material improvement
criterion with baseline superiority and bias/coverage/worst-block guards. No gain
retains V6. Internal selection/intervals remain exploratory; reused R3 validation
is not an independent test. Smoke caps fits at2 epochs and cannot claim improvement.

The protocol is fixed before the full run. No960epoch full-data training, feature
search, anomaly retraining or repeated capability/ablation sweep. Exports include
per-seed/fold metrics, predictions, best-vs-last checkpoint comparison, saved model,
preprocessing and recovery archives. The inherited report calls the single full-size
fit fraction a learning-curve plot; it is not a new data-size experiment in V9.

## Kaggle

Import `Spending_Model_V9_Checkpoint_Kaggle.ipynb`, select GPU T4, attach the
original R3 manifest/train/validation inputs. Keep `REQUIRE_GPU=True`, `SMOKE=False`,
`FEATURE_WORKERS=2`, `RESUME_DIR=None`. V9 also accepts the V7 development manifest,
but that is a separate replication and must not be mixed with R3 within a run.
No calibration or final/shifted CSV is read. Download partial backups as they appear
and the final ZIP when complete. V9 uses separate run/cache/module directories.
Only resume your own V9 backup with identical code/data/environment; older V7/V8
checkpoints cannot be reused across this policy change.

Total full-run time remains unmeasured; full-budget fitting can take longer per
candidate, but this avoids another14-configuration search and anomaly processing.
Preserve all original result archives. No model activation follows automatically.
