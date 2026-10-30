# Why large weeks dominate forecast error

## What was checked

Matched saved V8 reference predictions to the original R3 **training** CSV after
verifying its SHA256 against the run's split record. All7,200 expense-week totals
matched to KES.01. Only weeks ending before the permitted training cutoff were
used. No validation, calibration, final or shifted CSV was read. All published
results are aggregates; no user transaction rows were exported.

Attribution uses the mean of three reference forecasts. Its32.3243% WAPE is
therefore different from mean-seed WAPE32.3585%. This is descriptive analysis,
not an adopted ensemble or a new improvement result.

## Main findings

| Evaluation subset | Weeks | WAPE | Median-baseline WAPE | Share of absolute error |
|---|---:|---:|---:|---:|
| All weeks |7200|32.32%|32.80%|100%|
| Contains an injected scenario |558|69.88%|69.62%|52.67%|
| No injected scenario |6642|20.23%|20.94%|47.33%|
| No injection, includes named bills |3538|14.33%|14.86%|25.76%|
| No injection, no named bills |3104|39.76%|41.09%|21.57%|

Only7.75% of evaluated weeks contain injected events, but they account for52.67%
of total absolute error. These weeks contain77.02% injected spending by amount.
Event-free weeks remain hard enough that they cannot be described as solved.
WAPE differences also depend on spending scale: ordinary bill/nonbill groups
have similar MAE (~KES1190/~KES1136) despite different WAPE.

The highest-spending10% of weeks account for53.63% of all error. Within that group,
266 weeks contain injected events and454 do not. Their WAPE is72.12% versus16.44%.
The event-containing part accounts for42.25% of all error. This is association,
not a causal estimate of how much removing those events would improve a model.

Duplicate-scenario weeks are particularly influential:93 weeks,89.0% WAPE and
24.20% of total error. Families overlap when multiple events occur in a week;
their shares must not be summed as disjoint contributions.

## Simulator mechanism explains why past-income context was insufficient

In `synthetic_r3_data.py`, injection week/day is randomly drawn; amount is drawn
as10–40% of the user's simulated monthly income. Duplicate scenarios add **three**
transactions at that amount, totaling30–120% of monthly income in one event.
That is a severe synthetic stress scenario, not a measured population parameter.
Income may convey spending scale but does not reveal a randomly drawn future date.
Split events can span target boundaries, and recurring-increase scenarios modify
a bill, so not every scenario has identical predictability.

This does not prove a universal forecasting ceiling. It does explain why demanding
a very low all-week error from historical transactions alone may be unrealistic
under this simulator. Do not change injection seeds/severity after seeing results,
remove labelled events, or advertise event-free WAPE as all-user accuracy.
Known planned spending, if supplied by users before the origin, would be a different
observable input. Anomaly detection observes an event as it happens; it cannot
retroactively make the preceding week's forecast prescient.

## Tiny-fit diagnostic needs a fair optimization budget

The saved check has256 windows, batch256 and120 epochs: **120 optimizer updates**,
not120 passes with hundreds of steps each. It ran about2.67 seconds on GPU and
reduced weighted error29.65%. This proves some learning, but neither strong
memorization nor incapacity. Compared with full training, its optimization budget
is very small. Treating it as proof that the pipeline cannot learn was unwarranted.

## Next bounded experiment (not yet run)

Before another forecasting version, repeat the capability test on the same fixed
fit-only256 windows with baseline/best preprocessing checks:

1. Reproduce batch256 ×120 updates.
2. Keep architecture/loss/seed fixed, batch32 ×120 epochs (960 updates).
3. Keep batch256 and allow960 updates to separate batch size from update count.

Log optimizer iterations, initial/final KES MAE and normalized MAE, gradient norms,
baseline error and save/reload parity. Confirm residual reconstruction exactly.
No held-out labels choose the winning setup; this diagnoses optimization only.
A stronger memorization result is not evidence of improved generalization. Only
then propose a matched train-fold comparison with a fixed compute budget.

For product usefulness, a separately evaluated prediction interval may be more
appropriate than pretending large random shocks can be forecast precisely. Retain
the point forecast score on all weeks and test interval coverage/width separately.
App integration remains on hold; final V7 alert reports still need review.

## Reproduce this analysis

```powershell
python -m unittest discover -s model_research -p test_diagnose_large_weeks.py -v
python model_research/diagnose_large_weeks.py --archive "<V8 forecast_complete.zip>" --train-csv datasets/spendly_synthetic_r3/development/train.csv --output "<aggregate report.json>"
```

Five tests passed: expense/cutoff accounting, target reconciliation, seed alignment
and finiteness, zero-valued post-cutoff rejection, and baseline summary schema.
Independent review identified alignment/cutoff gaps; these were fixed and the
analysis rerun. Output: `evidence/v7_source_audit/v8_large_week_diagnosis.json`.
No training, dataset modification, deployment, commit or push performed.
