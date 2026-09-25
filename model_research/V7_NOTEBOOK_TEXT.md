# Spendly V7 — Kaggle LSTM evidence experiment

**Development only. No accuracy improvement is claimed before this notebook runs.**
Forecast **total spending in KES for the next completed Monday–Monday week**. LSTM
remains the principal model; Isolation Forest flags unusual spending; recommendations
remain deterministic. Simple forecasts are comparators only.

## Kaggle GPU setup
1. Open/import this notebook in Kaggle.
2. Open **Notebook Settings / Session Options**.
3. Set **Accelerator → GPU**, preferably **T4 x2** when available.
4. Restart the session if the setting changed.
5. Attach exactly one dataset: original R3 or the separately generated V7 development
   replication (`build_v7_dataset.py`). Attach its `manifest.json`, `train.csv/zip`,
   `validation.csv/zip`, and `calibration.csv/zip`, then **Run All**.

The notebook cannot enable an accelerator. GPU0 trains the LSTM; the second T4 may
remain idle. Raw loading, pandas features, multiprocessing, cache generation,
Isolation Forest and deterministic rules are **expected CPU work**. Progress during
those stages is not evidence of failed GPU setup. No package installation or driver
upgrade is performed. Keep the source V6 and prior evidence unchanged.

Results are new, timestamped `spendly_v7_evidence_*` folders. This is a substantial
research run: up to14 configurations ×3 folds, strongest-two confirmation at three
seeds plus a repeated reference, refits and diagnostics. Each fold may train twice.
Allow hours and inspect measured timings, not a promised duration. Preserve the
numeric feature cache across sessions. Recovery-enabled runs save completed fits and
experiments; incomplete individual fits restart from their declared seed.
`SMOKE=True` caps epochs for software checking only, never a publishable experiment.

### Saving and resuming (#10)
Download the printed `*_latest_checkpoint.zip` regularly and the named selection,
diagnostics and forecast-complete backups before long anomaly work. ZIPs sit beside
the result folder; they do not include the external feature cache. Kaggle temporary
storage can vanish: a local checkpoint without a downloaded/persisted copy is not
durable. Backup creation adds CPU/I/O time and storage overhead.

To resume, restore **your own trusted** recovery ZIP under `/kaggle/working`, set
`RESUME_DIR` to the extracted `spendly_v7_evidence_*` folder, attach exactly the same
input dataset, and Run All. Keep the same notebook code, environment, mode and device.
Completed stages are verified and skipped; changed identity or corrupted files fail
closed. Completed forecasting evaluation is loaded without scoring it again. An
interrupted benchmark with its consumption marker but no verified result is refused,
not silently rerun; retain that record and start a separately documented run if needed.
Older V7 runs without `run_identity.json` cannot use this recovery protocol. Do not
load arbitrary downloaded joblib/model checkpoints: hashes are integrity checks,
not authentication against malicious files.
<!-- CELL -->
## V6 Audit and V7 Improvement Rationale

Primary source: the **executed** `spending-model-upload-v6-r3-kaggle.ipynb`, run
`e805a62ae0142db1ba010f5e`. All32 cells, helper functions, configuration, printed
tables, epoch logs and handoff JSON were inspected; a cell/function inventory and
source SHA256 are embedded below. The recorded environment was TensorFlow2.20.0,
NumPy2.0.2, pandas2.3.3, sklearn1.6.1, Python3.12.13 and Tesla T4 GPU0.

| Historical metric | Selected V6 | Recurring median |
|---|---:|---:|
| MAE (KES) | 2,614.6473 | 2,664.0990 |
| RMSE (KES) | 7,766.9441 | 7,740.7588 |
| WAPE | 34.494320% | 35.146722% |
| R² | .414679 | .418619 |
| Mean bias (KES, prediction−actual) | −1,818.8231 | −1,616.5666 |
| Within20% | 47.8333% | 45.6667% |
| Worst chronological-third WAPE | 35.485270% | 36.301010% |

Selected:32 units, LR.0003, L2.001, **fixed** schedule, epoch120; 3,600
windows across36 weeks and100 validation users. Actual mean KES7,579.93575;
predicted mean KES5,761.11266. The MAE/actual-mean=WAPE and predicted-mean−actual-mean=bias
identities were independently checked. No matching V6 row-level result ZIP was
available, so aggregate consistency is verified, not independently rescored raw
predictions. Historical outputs are evidence inputs, **not new V7 execution results**.

V6 improves WAPE by **0.652402 percentage points (1.856225% relative)** and MAE by
KES49.45166 over the strongest baseline. R² changes by−.003940; bias worsens by
KES202.25652; within20% improves2.166667pp. Bias is about **−23.995% of actual mean**.
Against selected V5 (`lstm_1`, epoch53), WAPE improves only **.045660pp**,
MAE KES3.46096, R² changes−.002720, bias worsens KES62.73916, and within20%
improves.527778pp. These are extremely small changes, not convincing material gains.
Fixed vs32/64-unit plateau differs only.113630/.105877pp, potentially seed or
sampling variation; no repeated-seed evidence was recorded.

**Code correction to the proposed diagnosis:** V6 trains `(y-recurring)/scale` and
reconstructs `residual*scale+recurring`. Both use the recurring **mean**, so there is
no demonstrated centering mismatch. V7 compares consistent median centering as an
alternative; it never adds the validation-derived KES1,818.82 bias as a constant.

Systematic underprediction is demonstrated. Underfitting is **not proven** by
underprediction. Severe classical overfitting is not visible in the recorded curves:
training and stopping metrics mostly plateau rather than strongly diverge. Weighted
metrics use different spending distributions across slices, so their gap is not a
direct train-vs-validation accuracy comparison. Reaching120 means the stopping point
was not conclusively established. V6 monitored regularized `val_loss` despite
logging unregularized `val_weighted_mae`; V7 controls this difference explicitly.

The existing validation users have already influenced V5/V6 development. They are
a **reused development benchmark**, not fresh independent confirmation.
<!-- CELL -->
## Problem, objective and implementation evidence

Question: does an LSTM learn useful temporal information beyond a causal
recurring-spend baseline? The measurable goal is at least **1.0 absolute WAPE pp**
over reproduced V6 with a paired95% user-cluster interval excluding zero, superiority
over recurring median, and no unacceptable practical deterioration. Predeclared
guardrails: worst-block WAPE increases no more than.5pp, absolute bias percentage
increases no more than2pp, and within20% drops no more than2pp.

Selection objective is `(overall WAPE + worst chronological-third WAPE)/2`, averaged
equally across fixed folds and then across seeds. Within20% at actual zero requires
exact zero prediction (tolerance1e-9); percentage error at zero is undefined. WAPE
with zero total actual is undefined, never silently perfect. R² can be negative.

GPU evidence includes TensorFlow build CUDA/cuDNN versions, physical/logical devices,
device names, `nvidia-smi` memory and driver output, and a real matrix operation on
GPU0. Standard documented tanh/sigmoid, no recurrent dropout, no unrolling and bias
permit cuDNN acceleration; no unsupported forcing argument is used. `tf.data`
batching/prefetch, float32, seed controls and environment evidence are recorded.
No multi-GPU synchronization is introduced. Determinism is requested where supported;
cross-version/hardware numerical equivalence is not guaranteed.
<!-- CELL -->
## Configurable causal feature implementation

One immutable `ForecastConfig` owns lookback, sequence/context names, category
vocabulary, target transform/scale, units, L2, LR, batching, epochs and seed. The
numeric cache includes **all feature-defining settings**, source hash, raw-data hash,
NumPy/pandas versions and numeric artifact hashes. Optimizer-only changes reuse the
same features. A metadata mismatch fails rather than silently loading stale arrays.

Features retain optimized CPU process workers without TensorFlow imports. The
original pandas recurrence implementation is embedded as an executable reference;
parity runs at8/13/26 weeks. At8 weeks V6's values are retained. All comparisons
score the same windows after26 weeks of history. The recurring-mean/median baseline
always uses the original eight-week definition even for longer LSTM lookbacks.

Base channels: normalized weekly total and normalized nonrecurring amount, oldest
to newest. Nonrecurring classification uses schedule evidence available at that
forecast origin. Context retains V6 mean4, history standard deviation, due amount,
nonrecurring mean/median/std, log scale, schedule confidence, transaction count4 and
zero fraction. For longer histories, the historically named `std8` context means
standard deviation over the configured lookback (explicit configuration records it).

Compact bundle adds weekly transaction count and active-day fraction; history MAD,
recent4/history mean ratio, difference of last4 vs first4 of the latest13 weeks,
target week sine/cosine, and13-week shares of the top3 fit-derived categories plus
OTHER. A modest8-unit context branch is tested. No income/payday assumption,
profile truth, event IDs or anomaly labels enter forecasting features. Monetary
scales are causal per-window mean or MAD with a10%-median/KES1 floor, not statistics
fitted on evaluation labels. All categories come from fold fit users before the
inner cutoff. No target clipping, learned imputation or calibration is hidden.

A separate activity-shape candidate adds weekly mean ticket amount normalized by
the causal scale, largest-transaction share and weekend-spending share, plus count
and active days. All use completed historical weeks; zero-count denominators are
floored at1. These features test whether composition, rather than extra units,
provides useful information. Labels and generator truth remain excluded.
<!-- CELL -->
## Data provenance, composition and leakage controls

R3 is a rules/simulator-generated synthetic dataset, not Kenyan population evidence.
It models heterogeneous hypothetical salaried, irregular and student-like routines,
noisy recurring bills, random activity/amounts, seasonality, sparse histories,
benign large purchases and injected unusual-spending scenarios. Existing generation
protocol/source provenance is preserved; no generator is tuned in this notebook.
Permitted inputs:600 train users/928,077 raw transactions;100 legacy validation
users/153,726;100 IF-calibration users/162,972, with156 weeks each. Runtime verifies
these permitted inputs against the original manifest and exports their actual
counts, coverage, missingness, category composition, income/expense counts and
anomaly prevalence. Individual weeks overlap; they are not independent users.

Optional `spendly-synthetic-v7-dev-v1` inputs use the unchanged R3 simulator with
new fixed development seeds (see `V7_DATA_PROTOCOL.md`). Only train, validation and
calibration are generated. This is a fresh synthetic development replication, not
an untouched final test or real-population validation. Compare V7 and the V6
reference on identical new rows; never attribute differences from historical R3
scores entirely to algorithms. Runtime exports the dataset-specific benchmark role.

Only the first120 covered weeks of the original training cohort are permitted for
model development/refit, matching V6. Three deterministic SHA256 user blocks have
disjoint evaluation users. Rolling origins occur at55%,65%,75% of that permitted
training duration. Each fold evaluates the next12 weeks; stopping users are a
separate deterministic fifth of remaining users, evaluated during the preceding12
weeks. Fit users' target weeks end before stopping starts. Outer refit uses remaining
users before the outer origin; outer-evaluation users never fit any parameter.

Held-out-user past transactions are legitimate **prediction-time history only**.
At each origin, features use timestamps strictly earlier than the target week;
later weeks may use newly observed past weeks as in rolling deployment. They never
use their own target or later transactions. Fold-specific scalers fit only fit rows;
outer-refit scalers fit only outer training rows. Vocabulary learned in the inner
fit remains frozen through that fold's refit. Future-amount/category perturbation,
reference parity, user separation and feature-end/target-start checks are executable.

Final/shifted inputs have no loader route. Only exact permitted filenames are
discovered. The original manifest is read for provenance; only permitted cohort
entries are retained. No holdout labels are loaded, counted, summarized or exported.
<!-- CELL -->
## Predeclared staged comparisons — train users only

Maximum14 selectable configurations before seed confirmation:
1. V6 mean residual,8 weeks,32 units, L2.001/LR.0003, fixed schedule; original
   regularized checkpoint control (patience16/min_delta0).
2. Same architecture, predictive checkpoint (patience10/min_delta1e-4).
3–4. Median-centered residual with mean scale; then MAD scale.
5–6. Best centering/stopping formulation at13 and26 weeks; retain best lookback.
7. Compact causal feature/context-branch bundle.
8–12. One-factor alternatives to the carried model:16 units, L2=0, L2=1e-4,
LR=.001, or plateau schedule. No full Cartesian grid or speculative64-unit expansion.
13–14. Huber residual loss (delta1 in normalized residual units), or activity-shape
channels, each relative to the same carried base. Huber is a hypothesis, not a
bias correction: it changes the objective and can worsen WAPE. Checkpoints and
selection still use weighted MAE and held-out WAPE, not incomparable loss values.

The two strongest are confirmed with42,123,2026; the reference is repeated at those
seeds too for paired comparisons. Report individual/mean/std, not a lucky best seed.
The final model uses predeclared seed42 and a deterministic representative training
duration/schedule from train-only folds. Controls retain Adam clipnorm1 for V6
comparability; post-fit gradient norms are diagnostic, not a retrospective claim
that clipping was necessary. No calibrator is investigated in this budget.

For improved candidates, the correctly sample-weighted unregularized normalized MAE
is monitored. Weights are causal scale divided by the fit-slice mean scale; this
is proportional to KES MAE for a fixed evaluation set. One min_delta-aware callback
saves/restores the best weights and controls early stopping; LR scheduling monitors
the same predictive metric. The V6 reference deliberately retains val_loss stopping
so the checkpoint-policy change is measured rather than concealed.

Changes relative to exact V6 replay: grouped nested folds, common26-week row coverage
for controlled comparisons, seed repeats and current installed libraries. Final V6
refit uses its full8-week-onward permitted training history. Do not expect exact
historical weights/scores. All LSTM parameters train from scratch; no pretrained
component or baseline parameters are silently frozen into a learned replacement.
<!-- CELL -->
## Capability, ablation and data-size diagnostics

Diagnostics are separately registered and cannot enter selection. Compare full,
sequence-only, context-only (LSTM contribution zeroed), shuffled-order and the strongest
simple baseline on identical fixed folds. Context-only is an ablation, not a proposed
standalone production forecast. Zeroing the branch retains comparable parameter
accounting, although effective active capacity differs. Similar shuffled/full scores
mean useful order sensitivity is **not demonstrated**; rich context can make order
redundant. Do not force the desired conclusion.

A deterministic subset of at most256 fit windows trains without L2 for a capability
check. Report initial/final error and investigate weak reduction; memorization is
not deployment evidence. Fit-user learning curves use25%,50%,100% with fixed stopping
and evaluation users. Interpret training and held-out errors together. Poor errors
on both can indicate weak features/noise/underfitting; a large gap suggests
overfitting; improvements with users suggest data limitation; a plateau alone proves
no universal ceiling.

Only the final selected architecture receives a120/160 epoch-cap sensitivity check.
Continuation must improve beyond min_delta across at least three late observations
in each fold. This is diagnostic; even a positive result requires repeated-seed
confirmation in a future preregistered run, not automatic adoption here. If fallback
V6 is retained, a separate predictive-metric120 control isolates the cap comparison
without changing the retained reference. Loss and unregularized histories are exported.
<!-- CELL -->
## Lock, refit, then one Legacy development benchmark

Write the configuration/schedule/selection lock **before opening validation**.
Refit on the complete permitted training cohort, save the selected LSTM/scalers,
verify reload parity, then evaluate once on legacy users after week120 (36 weeks).
A create-only evaluation marker prevents accidental repetition in the same results
folder. New folders do not make previously viewed users independent; do not alter
the configuration after viewing this benchmark.

Report MAE, RMSE, WAPE, R², signed bias and bias percentage, within20%, three-block
worst WAPE, parameter count and timing. Export pseudonymized row-level predictions
with matched reproduced-V6/baseline predictions, target week, fold, seed and causal
subgroups. User-cluster bootstrap uses1,000 complete-user resamples for candidate
WAPE and paired differences. Repeated-seed rows remain clustered within their user,
not treated as independent people. Intervals are conditional on selected models,
not selection-adjusted hypothesis tests; internal selection is adaptive. A better
legacy result may be promising, not independent confirmation.
<!-- CELL -->
## Isolation Forest, causal collective companion, and recommendations

Preserve V6's chosen **single excess-view IF, max_samples128,300 trees**, log1p
features and1% labelled-negative FPR threshold selection. Keep the original fixed
excess128/rhythm512 union with.5% per-component budgets as a comparator. The separate
calibration users set thresholds, not LSTM architecture or scalers. The small
protocol compatibility correction is to freeze the previously selected IF
architecture rather than rank it on the legacy validation labels again. Original
event-boundary purging and boolean-union undefined AP/AUC semantics remain.

BenjaminKakai's merged [PR #3](https://github.com/Eeshan-Vaghjiani/Spendly/pull/3)
motivates an independent causal companion implementation. It uses the current
transaction plus earlier day activity against completed historical days (including
observed zero days), completed-weekend medians, and same-merchant/category matching
amounts across a three-hour window. Simultaneous rows never see each other; the
first28 complete days are warmup. The normalized max score uses fixed divisors4/6
for frequency/weekend and the prior duplicate count. No feature uses labels.

Rules-only gets a1% empirical negative FPR budget. A forest/rules union allocates
.5% to each component; the union bound applies on calibration, not guaranteed on
unseen data. Thresholds handle score ties conservatively, use calibration negatives
only, and are saved before companion benchmark scoring. No threshold sweep uses
benchmark labels. Both are diagnostic comparators; the single forest remains selected
until a future declared confirmation experiment supports promotion. Per-family
transaction recall, event recall (any labelled member detected), and active-user-day
alert burden expose weak scenario support and excessive alerting. Missing event IDs
are excluded from event denominators, not fabricated.

The existing recommendation code is embedded unchanged. Its minimum-eight-period
history rule remains an application convention; V7 is a research export, not a
replacement serving contract for longer lookbacks. The demonstration uses explicit
synthetic budget values. Alerts are unusual-spending signals, not fraud findings.
<!-- CELL -->
## Experimental evidence and report-ready outputs

Figures and tables include epoch histories, fixed-user learning curves, baseline
comparison, residuals by actual/predicted spending deciles, causal volatility,
transaction activity, zero-heavy histories, recurring share and forecast quarter.
Quantile groups are descriptive, never fitted into a subsequent model. Representative
large under/overpredictions omit user IDs. No synthetic profile truth is required.
Additional exports: `collective_protocol.json`, `anomaly_per_type_events.csv`, and
`anomaly_alert_burden.json`. The older PR's test-tuned metrics are not V7 evidence.

Use `selection_decision.md` as the result statement. Unless the declared material
criterion and guardrails pass, explicitly report **“a material improvement was not
demonstrated”** and retain the reference. Reducing mean bias can increase WAPE:
absolute error favours conditional medians, not necessarily mean-unbiased forecasts.

The result ZIP includes the audit, GPU/build evidence, environment, splits, feature
configuration, registry, fold/seed metrics, legacy metrics, row predictions,
bootstrap intervals, summaries, histories, figures, scaler/preprocessing/model,
decision and SHA256 artifact manifest. Raw transactions and feature caches remain
outside it. CPU peak memory is main-process-only where available; GPU allocator
peak and `nvidia-smi` snapshots have different meanings. Timing separates data
loading, features, training, prediction, evaluation, anomalies and overall execution.

### Research-writing alignment
The supplied **Research Writing for CS 2 Projects – 2026 (2).pdf**, internally titled
*ML Fundamentals – Deep Dive*, supplies methodological guidance, not measured
Spendly results. Its lessons2,6,8,9,10 and CS Project II checklist (p36) motivate
train-fitted preprocessing, related-observation splits, simple baselines, sample-size
learning curves, repeated trials, difficult-case reporting, and honest synthetic-only
limitations. Traceability: objective → causal LSTM features → fixed train-user folds
→ locked model → reused benchmark → uncertainty/diagnostic/compute evidence.
<!-- CELL -->
## Limitations, responsible use and visibly locked final holdouts

**RUN_FINAL_HOLDOUTS = False.** There is no final-evaluation implementation here.
Ordinary Run All cannot access final/shifted labels, even if their files are attached.
Their future assessment requires a separately frozen evaluation protocol.

Synthetic-only results do not establish performance for real Spendly users or the
Kenyan population. Hundreds of overlapping windows are not hundreds of independent
users. Generator assumptions, limited independent groups, adaptive development,
GPU/version variation and the reused validation cohort constrain claims. Historical
R3 provenance notes document earlier generator correctness fixtures; this V7 work
does not consume protected cohorts or claim a cryptographic guarantee about prior
human access.

Initial real-world use should be **shadow mode**. Sparse, new, irregular or suddenly
changing users can defeat the forecast. Predictions should support decisions rather
than automatically control finances. Deployment needs privacy controls, monitoring,
consent where applicable and human oversight; ethically obtained real-world or
shadow-deployment validation remains future work. No real-user evidence is invented.
Review dataset suitability, acceptance criteria and claims with the supervisor.
