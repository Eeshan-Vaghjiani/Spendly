# V7 resumed Kaggle results review

## Verdict and evidence boundary

The executed notebook `notebook73bc3e27af (2).ipynb` records successful completion:
10 prior experiments resumed, full selection, diagnostics, final forecast refit and
benchmark, anomaly processing, recommendations, final ZIP, and holdout-lock assertion.
No saved exceptions. Original code cells match the recovery-enabled notebook except
the intended RESUME_DIR setting. Added user setup cells do not change algorithms.

The supplied `latest_checkpoint (4).zip` is **not the final evidence ZIP**. It was
last refreshed inside the final diagnostic experiment, before diagnostic summaries,
configuration lock, final refit, benchmark, anomaly reports and final manifest.
The notebook subsequently printed these files but did not embed their contents.
Download `spendly_v7_evidence_20260925_054840.zip` from Kaggle Output; no rerun is
required if that existing file remains available. Current Downloads contains only
latest-checkpoint ZIP variants, not that final ZIP.

Notebook SHA256: `1ea2e40cd3ac8ce16574d4cf053b523fbe5fe3411241395fa1864e8b85782adb`.
Checkpoint SHA256: `46792de4b7922645e348455070b9135ce285c2e58d16a0467af130f4c60353c5`.
Code hash: `aeedc4984516268147077a6d26f2855be4fbfa406512ac6013db6fee1a577fa8`.

## Independent verification performed

`analyze_v7_checkpoint.py` reads ZIP JSON/CSV and notebook JSON only: no notebook
execution, unpickling, model loading, training or raw/holdout dataset access.

- ZIP CRC passed; all **656 checkpoint-referenced file hashes** matched.
- Selection evidence hashes matched their checkpoint output record.
- Independently recomputed **405 fold metric records**, including simple baselines,
  from **27 prediction CSVs**: no discrepancies within stated numeric tolerances.
- Verified identical targets/baselines across candidates and no repeated user/week
  or cross-fold evaluation-user overlap. Each experiment has 7,200 unique windows,
  600 evaluation users, each user contributing 12 weeks in one of three folds.
- Reproduced the reported 1,000 complete-user paired bootstrap intervals exactly
  within floating-point tolerance. Seeds remain grouped within users.
- Four audit regression tests passed: known metrics, overlapping windows,
  cross-fold users and incorrect residuals. Independent review identified the last
  two validation gaps; both were corrected before rescoring again.

Aggregate machine-readable evidence:
`evidence/v7_source_audit/kaggle_checkpoint4_analysis.json`.
Hashes establish internal consistency, not third-party authentication or model
inference parity. Final validation numbers below are printed notebook evidence,
not independently rescored, because their row predictions are absent from this ZIP.

## Data and protocol

This is **original R3**, `spendly-synthetic-r3-v1`, not the new V7 synthetic
replication. Training folds fit320 users, stop80 different users and evaluate200
different users; refits use400 before the evaluation origin. Three evaluation
blocks cover April–December2022. Only allowed training history is used for search.
R3 validation is explicitly reused development evidence. Synthetic outcomes do
not establish real Spendly/Kenyan population performance.

## Main forecast result: retain V6 reference

| Three-seed mean, identical train-fold rows | WAPE | MAE KES | R2 | Bias KES | Within20% |
|---|---:|---:|---:|---:|---:|
| V6 reference | **32.358475%** | **2272.45** | **.458197** | **-1506.52** | **48.7130%** |
| No L2 candidate | 32.385716% | 2274.36 | .456562 | -1540.68 | 48.6852% |
| Small L2 candidate | 32.397896% | 2275.21 | .456564 | -1540.03 | 48.6111% |
| Recurring median | 32.799932% | 2303.45 | .461190 | -1451.96 | 47.4306% |

The no-L2 provisional candidate is **0.027241 percentage points worse** than the
reference in pooled WAPE. Candidate-minus-reference95% interval:
**[-0.027977,+0.080420]pp**. It crosses zero and fails the declared1pp material-gain
requirement. Guards pass, but guards do not replace improvement evidence.
Reference advantage over recurring median is only about **KES31 MAE /0.441457pp**.
No claim of universal equivalence is made: these are adaptive, conditional internal
intervals, not independent selection-adjusted tests.

Seed42 initially favored no-L2 on the mean-fold overall/worst-block selection
objective. After repeated seeds the reference is better on both mean objective and
pooled WAPE. Diagnostics are not selectable production candidates.

### Selected initial experiments, seed42 (not repeated-seed conclusions)

| Candidate | Pooled WAPE | Interpretation |
|---|---:|---|
| V6 reference | 32.3736% | comparison anchor |
| No L2 | 32.3695% | tiny initial gain disappears under repeated seeds |
| Median + MAD | 32.4052% | no useful gain |
| Plateau schedule | 32.4136% | no gain |
| Predictive stopping | 32.4272% | earlier stopping, no gain |
| Activity-shape channels | 32.4302% | no gain in this bundle |
| Median centering | 32.4420% | no gain |
| 26-week lookback | 32.4741% | no gain |
| Compact bundle | 32.5621% | worse |
| 13-week lookback | 32.6197% | worse |
| Huber | 32.7459% | better signed bias/R2, worse absolute error |

Huber changes bias from -KES1485.97 to -KES1303.47 and R2 from.45906 to.46652,
but MAE worsens from KES2273.51 to2299.65 and within20% falls48.56% to46.42%.
This is a trade-off, not a free correction for underprediction.

## Diagnostic findings

### Sequence contribution is small in this test

Seed42 pooled WAPE: full32.3736%, sequence-only32.3812%, context-only32.4080%,
shuffled32.4473%. Differences are small; strong temporal-order value is not
demonstrated. The sequence-only network still uses engineered sequence channels
and residual-baseline reconstruction, so it is not a raw-sequence-only baseline.
These single-seed ablations do not prove sequence information is absent.

### More users helped modestly

With fixed stopping/evaluation users, fit subsets25/50/100% yield WAPE
32.4978/32.4539/32.3736%. The largest improvement is only0.1242pp. More examples from
the same simulator alone are not demonstrated to solve the problem. Train and
evaluation populations differ, so their aggregate error gap is not a clean
capacity/overfitting test.

### Increasing the cap did nothing under the diagnostic stopping rule

Both120 and160 caps stopped after37/59/36 epochs and selected27/49/26, yielding
identical predictions/metrics. Extra permitted epochs were never used. This does
not establish that more training can never help: some original val_loss reference
fits reach120. It establishes only that this predictive-stopping policy stopped
well before either cap. Do not automatically increase epochs or patience.

### Tiny-subset capability test remains weak

On256 windows from6 users, weighted error fell about29.65% (final/initial=.7035),
failing the predeclared50% reduction diagnostic. Some learning occurred, but the
pipeline did not demonstrate strong memorization. Investigate capacity, optimization,
normalization and feature/target information before declaring irreducible noise.

### Large spending weeks dominate error

For the reference, seed42, on train-fold evaluation rows:

| Highest actual-spending weeks | Share of total absolute error | Mean bias KES |
|---|---:|---:|
| Top10% (>=KES17,235.95) | **53.53%** | -11,498.83 |
| Top5% | **42.36%** | -18,622.48 |
| Top1% | **20.93%** | -47,390.14 |

These overlapping descriptive groups use actual outcomes; they are not causal input
features or evidence that all large weeks are injected anomalies. The top actual
quartile holds71.86% of error. The reference beats median aggregate error for381/600
users (63.5%) but underpredicts mean spending for516/600 (86%).

Lowest/highest causal recurrence-share quartiles have WAPE56.07%/17.53% and within20%
34.56%/79.28%. Their MAE is similar (~KES2613/~KES2431): spending scale contributes
to the WAPE contrast. It suggests nonrecurring/discretionary predictability deserves
inspection, not that recurrence causally explains all errors. The zero-history
quartile diagnostic collapses to one group; this is not strong sparse/cold-start
coverage evidence.

## Printed original-R3 validation (final rows not supplied)

| Metric | Reference refit in V7 | Historical V6 |
|---|---:|---:|
| MAE KES | 2616.878601 | 2614.647320 |
| WAPE | 34.523757% | 34.494320% |
| R2 | .416328 | .414679 |
| Bias KES | -1777.488965 | -1818.823087 |
| Within20% | 47.0000% | 47.8333% |

No meaningful new forecast improvement. The recurring-median benchmark remains
WAPE35.146722% and MAE2664.10. Refitting can produce slightly different reference
weights and metrics from historical V6. Train-fold32.36% and legacy34.52% are not
before/after scores on the same evaluation rows.

## What PR #3 helped and what remains unknown

BenjaminKakai's merged PR contributed the collective-anomaly hypothesis: purchases
may be ordinary individually but unusual as a group. V7 tests an independently
implemented causal companion with completed-history baselines, contextual duplicate
matching and calibration-negative budgets. It also adds event/type recall and alert
burden reporting to evaluate the false-positive trade-off. Attribution is preserved.
This contribution concerns alerts, not the LSTM architecture.

The notebook records anomaly processing completed in2538.4s (~42.3min), with nearly
all time in CPU feature preparation. No anomaly metrics table is printed. The
checkpoint lacks anomaly outputs, so this review **cannot determine whether the
companion improves precision, recall, event coverage or alert burden**. The final
ZIP is necessary before making a performance claim about the PR's idea.

Recovery is now evidenced on Kaggle: restored10 experiments, completed remaining
work and exported a final archive. GPU preflight and persisted fit device records
support actual GPU-enabled training. Stored completed-fit durations total~1.18h,
excluding features, backups, interruption downtime and stages absent from the
checkpoint; it is not total wall time.

## Next decision

1. Download the existing final ZIP; verify final artifact hashes, independently
   rescore validation, inspect full diagnostic summaries and anomaly reports.
2. Retain V6 as reference; app integration remains on hold.
3. Before V8, diagnose high-spending/nonrecurring errors and the weak capability
   check. Observe bill timing, known income/payday context and category histories;
   do not use future payments or generator truth as model inputs.
4. Declare a small controlled experiment budget. Test observable payday features
   and/or improved recurrence decomposition only if diagnostics justify them.
   Quantile forecasts are a separately evaluated uncertainty objective, not a WAPE
   improvement claim. Do not tune generator seeds/noise until the model wins.
5. New V7-seed replication remains a separate development experiment, not a
   substitute for independent real-world validation.

## Tracking

The Kaggle run and recovery work are complete (#5, #10). Forecast review (#6)
and alert comparison (#7) still need the final archive. App integration (#9)
remains on hold. PR #3 is the source of the collective-anomaly direction;
its original findings and the V7 follow-up are separate experiments.
