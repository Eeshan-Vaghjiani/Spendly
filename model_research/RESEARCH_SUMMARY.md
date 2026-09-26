# Spendly model research — current position

## Decision

**Retain the V6 forecasting reference. App activation is still on hold.** V7, V8
and V9 completed their experiments, but none demonstrated the declared meaningful
improvement. A completed experiment does not require a positive result.

| Work | Question | Finding |
|---|---|---|
| V7 | Do features, history length, loss or regularization help? | No reliable material improvement across repeated seeds |
| V8 | Do observed income and category histories help? | Best gain0.0597 WAPE percentage points (~KES4.19 MAE); interval crosses zero |
| V9 | Did early stopping miss better predictive checkpoints? | Gain0.00385pp (~KES0.27 MAE), with20.6% more comparison-training time |
| Large-week diagnosis | Where is forecast error concentrated? |7.75% of evaluated weeks contain injected events and account for52.67% of error |
| Update-budget check | Was the tiny-fit test too short? | More updates reduced fit-only MAE23.7%; not a held-out accuracy gain |

The final reference refit has **34.52% WAPE, KES2616.88 MAE, and47% within20%** on
reused synthetic R3 validation. WAPE is not classification accuracy. This is not
evidence of performance for real app users. The data contains deliberately severe
random scenarios, so event-free subgroup scores must not replace the overall score.

## Spending alerts and PR #3

PR #3 contributed the group-level anomaly idea: individually ordinary purchases
may be unusual together. V7's follow-up added past-only context, merchant/category
duplicate matching, calibrated false-positive budgets, and event/alert-volume
reports. Its completed Kaggle alert outputs were lost before being supplied for
review. A separate reproduction has now completed: the single forest achieves
66.84% precision /78.21% recall (F1.7208). Adding collective rules to the stricter
forest adds2 true detections and97 false alerts; that companion is not adopted.
The two-forest comparator improves recurring-increase event detection but lowers
overall transaction F1. See [ALERT_RESULTS.md](ALERT_RESULTS.md).

`Spending_Alerts_Review_Kaggle.ipynb` reproduces only the frozen alert comparison
using CPU, with no LSTM training. Its results are a reproduction, not recovered
historical measurements. Issue #7 records the completed review.

## What is complete and what remains

- Complete: forecast experiments and result reviews (#13–#16), original Kaggle
  execution (#5), checkpoint recovery (#10), V7 publication (#8).
- Complete: V8/V9 code and findings published through PR #17.
- Current: review the consolidated findings and agree product acceptance criteria (#11).
- Complete: reproduce and review missing alert results (#7).
- Paused: new-dataset replication (#4) and app integration (#9).

No V10 search is needed to finish this evidence package. A future uncertainty or
planned-expense feature would need a separately agreed objective and evaluation.

## Where evidence lives

- GitHub: code, output-free notebooks, tests, protocols and aggregate results.
- Separate backup: raw synthetic datasets, executed notebooks, trained model and
  result ZIPs. **Pushing code does not back up Kaggle working storage.**
- Final V9 ZIP was received and its349 manifest file hashes and prediction metrics
  verified. V8 forecast-complete ZIP was also verified. Reports state the remaining
  gaps instead of treating missing artifacts as tested evidence.

Detailed results: [V8](V8_RESULTS.md), [V9](V9_RESULTS.md),
[large weeks](LARGE_WEEK_FINDINGS.md), [training budget](UPDATE_BUDGET_RESULTS.md).
Test/smoke evidence is software verification; performance claims refer only to
the separately identified full Kaggle experiments.
