# Spendly V8 — observed-income forecasting experiment

**Hypothesis, not a claimed improvement:** past income receipts and category
histories provide useful information that V7's expense-only inputs omit.
The earlier R2 payday proxy inferred timing from spending peaks and did not help;
V8 instead uses payments actually observed before the forecast origin.

## Run

Import `Spending_Model_V8_Income_Kaggle.ipynb`. Enable GPU T4, retain
`REQUIRE_GPU=True`, `SMOKE=False`, `FEATURE_WORKERS=2`, `RESUME_DIR=None` for a new
run. Attach exactly one R3 or V7-development manifest plus train/validation files
from that dataset (calibration is not read). Data must contain transaction types.
Do not attach protected final/shifted inputs. This experiment does not retrain the
anomaly detectors; V7's final alert results need separate review.

Outputs use separate `spendly_v8_*` folders. Download partial checkpoint ZIPs
regularly and the final evidence ZIP. Resume only your own trusted V8 checkpoints
using their extracted result folder and identical inputs/configuration/environment.
V7 checkpoints cannot be resumed as V8. Feature caches are outside backup ZIPs.

## Five declared configurations

1. V6 reference: same expense targets/features/scaling and original checkpoint rule.
2. Predictive-stopping control: same inputs, predictive MAE checkpoint policy.
3. Income context: control plus last observed income age/amount, 26-week average
   receipts, 8-week income/spending ratio, observed receipt cadence and variation,
   missing/recent-income indicators, and known target-calendar month phase.
4. Income sequence: income context plus weekly receipt amount/count channels.
5. Category sequence: income sequence plus weekly spending for the three largest
   expense categories of fit users and an OTHER channel.

All use 8 weeks,32 LSTM units, L2.001, LR.0003, MAE, batch256, cap120. No broad
architecture search, loss tuning or generator changes. Every configuration runs
seeds42/123/2026 on the same three grouped chronological folds. This is15
candidate/seed runs, each with3 folds and stopping/refit phases; it is not a quick
single fit and may still take hours. Diagnostic comparisons are separate.

## Leakage and ownership

Income is retained as an observable input, never added to expense targets, expense
normalization or recurring-spend baselines. Receipt timestamps must be strictly
earlier than the forecast origin. No future payments, profile truth, anomaly
labels or event IDs inform features. Receipts at the same timestamp are aggregated
for cadence; calendar-day ties do not create zero-day cadence. Category vocabulary
uses only fold-fit expenses before the inner cutoff and stays fixed through refit.

No-income users have explicit missing indicators and zero receipt channels; no
salary date or income amount is fabricated. Last-income age is capped at182 days,
and recent monetary context uses at most26 weeks. All features are deterministic
functions of permitted observation history. The reference and candidates evaluate
identical user/week targets and baseline values.

## Selection and interpretation

Reuse V7's mean-fold objective, repeated seeds, paired user-cluster bootstrap,
1pp minimum WAPE improvement, baseline-superiority criterion and practical guards.
No qualifying gain retains the V6 reference. Smoke always forces fallback and is
software evidence only. Category, income and calendar effects are bundled at the
specified stages; a gain does not identify one feature as its cause.

The original R3 benchmark has already influenced development. The new V7 dataset
is same-simulator development replication. Neither is independent real-population
confirmation. Keep reused benchmark labels out of selection and don't retune after
the lock. Report all candidates and subgroup errors, including expensive weeks.
The tiny-fit, branch/order and epoch-cap diagnostics are not selectable candidates.

This protocol is declared before a full V8 run. A large improvement is not assured:
unexpected purchases may remain unpredictable from recorded history. V8 remains
a research export and app integration remains on hold.

## Local verification

Nine V8 regression tests passed, including exact expense-reference parity, future
receipt/label invariance, missing-income behavior, receipt-sensitive cache identity,
fit-only vocabulary, user isolation, and real CPU income/category training,
refitting and saved-model prediction parity. The category export path is forced
only in its software test and is not a claimed winning configuration.

All11 notebook code cells executed on disposable income/expense fixtures with
two-epoch CPU training for all5 configurations and3 seeds, then completed a
fresh-namespace replay with model creation forbidden. Output:
`evidence/v7_source_audit/v8_software_smoke.json`. The final lock-message wording
was corrected afterward; no numerical code changed. Independent read-only review
found no remaining actionable defects in the scoped follow-up.

These checks establish software behavior only. Full-dataset accuracy, actual V8
GPU execution, interrupted V8 recovery and clean-process relocated checkpoint
restoration are not established. Temporary fixtures/models/archives were removed.
No training on protected cohorts, model activation, commit or push was performed
for this V8 implementation.
