# Final Isolation Forest results — submission record

## Status and final decision

**Isolation Forest research is frozen and final evaluation is complete.** Retain
the original single excess-view forest. No additional feature search, training,
threshold tuning or test-driven model selection is part of this submission.
Mobile integration and native acceptance checks are a separate deliverable.

The final scores below supersede development scores as the primary performance
claim. The model did **not** meet the historical80% precision/recall/F1 aspiration.
This is a completed experimental result with limitations, not a claim of meeting
every performance target or being production-proven.

Tracking: #27; development selection evidence #25 / PR #26.
Branch: `research/isolation-forest-submission`.
Pre-evaluation protocol/source lock commit: `f0b3e1c` (pushed before test access).

## Frozen model

- Standard sklearn IsolationForest:300 trees, max_samples128, five excess-view
  features, original trained weights, seed42; no final refit.
- Features in order: category_excess, merchant_excess, duplicate_hour, rare_large,
  burst_amount. The versioned historical feature implementation uses strictly
  earlier same-user transactions; simultaneous transactions share earlier history.
- Transform: log1p; score: negative score_samples; flag when score >=
  **0.6451359189730762**. No additional imputer/scaler is required for this model.
- Training ends2023-04-24. The threshold remains the original separate-cohort
  FPR-capped calibration threshold. It is not recalibrated on either final cohort.
- Original alert archive SHA256:
  `98617ac130c456a5ee8917100e39451c63224ebe99877d7adb1db23c46dc4c42`.
- Runtime: Python3.12.13, numpy2.0.2, pandas2.3.3, sklearn1.6.1, joblib1.5.3,
  Windows CPU. No LSTM/TensorFlow training or inference in this evaluation.

## Dataset and evaluation design

Original `spendly-synthetic-r3-v1`: independent synthetic users and fixed cohort
seeds. Standard cohort100 users/146,145 raw transactions; shifted cohort100 users/
144,443 raw transactions. All raw cohort entries were hash-verified and checked
for ownership overlap, counts, binary labels and observation coverage.

Evaluation includes expense transactions from2023-04-24 inclusive to2024-01-01
exclusive (the final36weeks), retaining earlier same-user expenses only as causal
history. No new warm-up filter was introduced. This yields32,841 standard and
32,599 shifted scored rows. Income remains excluded from anomaly features.

The protocol was committed before this evaluation. Exclusive persistent access
markers were written before each holdout ZIP was opened. Both cohorts are now
**consumed for model evaluation** and must not be reused for further selection.
The original dataset manifest is retained unchanged as generation provenance;
the access ledger and this report supersede its old model_evaluated=false fields.

Prior project records indicated no earlier model evaluation of these cohorts.
Unrelated external sessions cannot be independently attested; this limitation is
part of the provenance record rather than a claim of universal access auditing.

## Final metrics

| Metric | Standard test | Shifted robustness test |
|---|---:|---:|
| Scored transactions | 32,841 | 32,599 |
| Labelled anomalies | 776 | 579 |
| **Precision** | **62.32%** | **54.73%** |
| **Recall** | **71.39%** | **69.95%** |
| **F1** | **0.6655** | **0.6141** |
| Average precision (AP) | 0.6847 | 0.6444 |
| ROC-AUC | 0.9496 | 0.9460 |
| False-positive rate | 1.0448% | 1.0462% |
| Accuracy | 98.30% | 98.44% |
| Balanced accuracy | 85.17% | 84.45% |
| Transaction alert rate | 2.7070% | 2.2700% |
| Event recall | 73.87% (164/222) | 72.19% (122/169) |
| Alerts | 889 | 740 |
| False alerts / all alerts | 37.68% | 45.27% |
| Alerted active user-days | 541/17,181 | 481/17,305 |
| Maximum alerts per active user-day | 9 | 8 |

High accuracy reflects the predominance of normal transactions; precision,
recall and F1 are the headline measures. A1% calibration FPR budget does not
guarantee an exactly1% FPR on a different population or period.

### Confusion counts

| Cohort | TP | FP | FN | TN |
|---|---:|---:|---:|---:|
| Standard | 554 | 335 | 222 | 31,730 |
| Shifted | 405 | 335 | 174 | 31,685 |

### 95% user-cluster bootstrap intervals

2000 replicates, seed42. Conditional on this frozen model and the represented
synthetic users; these do not measure training-seed or real-population variation.

| Metric | Standard | Shifted |
|---|---:|---:|
| Precision | 56.02%–67.49% | 47.70%–61.10% |
| Recall | 66.23%–76.94% | 63.62%–76.10% |
| F1 | 0.6171–0.7035 | 0.5543–0.6658 |
| FPR | 0.9046%–1.1905% | 0.9117%–1.1872% |

### Transaction recall by controlled anomaly family

| Family | Standard detected / support | Recall | Shifted detected / support | Recall |
|---|---:|---:|---:|---:|
| Burst | 307/360 | 85.28% | 213/250 | 85.20% |
| Duplicate | 118/120 | 98.33% | 119/126 | 94.44% |
| Large | 50/52 | 96.15% | 30/32 | 93.75% |
| Recurring increase | 4/36 | 11.11% | 2/31 | 6.45% |
| Split | 75/208 | 36.06% | 41/140 | 29.29% |

Event recall means at least one member of a represented labelled event was
flagged in the evaluation interval. All positive scored rows have event IDs.
This must not be confused with identifying every transaction in an event.

## Why this model was retained

The historical reproduced validation F1 was0.7208; it remains development
evidence. A supplied V2.1 notebook reported0.7697 under a different protocol
(normal-only fit, broad evaluation dates, validation-selected F1 threshold).
After correctness fixes and a predeclared common chronological development
comparison, the retained architecture achieved0.7028 versus candidate0.5429.
Those comparison artifacts were not substituted for the original selected model.

Final standard F1 is lower than development F1. This is reported as observed;
there was no post-test adjustment. The shifted result shows further performance
degradation, especially precision. Failure on recurring increases and split
events is a documented limitation, not removed from evaluation or relabelled.

## Submission wording

> The frozen Isolation Forest identified potential unusual spending on synthetic
> R3 held-out users with62.32% precision,71.39% recall and an F1 score of0.6655.
> The false-positive rate was1.0448%. On the separate shifted robustness cohort,
> precision was54.73%, recall69.95% and F10.6141. Performance was strongest for
> duplicate-like and large-spending anomalies and weak for recurring increases
> and split transactions. The results did not meet the original80% aspiration
> across precision, recall and F1. Alerts require user review and do not establish
> fraud or real-world financial risk.

The simulator's labels are controlled experimental truth, not human assessments
of real spending. No claim of representative performance for Kenyan young adults,
fraud detection, realized savings or real-user acceptance follows from this study.
The supervisor's recommendation/savings/acceptance-rate use case remains separate
from completing the Isolation Forest component.

## Deliverables and verification

- `Spendly_Final_Isolation_Forest_Submission.ipynb`: standalone final notebook;
  default Run All reviews embedded aggregate evidence, not another inference run.
- `IF_SUBMISSION_PROTOCOL.md`, `if_submission_lock.json`: pre-run protocol and
  exact executable source/environment identity.
- `if_submission.py`: frozen evaluator; no fit/calibration code path.
- `if_submission_requirements.txt`: compatible research dependencies.
- `evidence/if_submission/`: metrics,95% intervals, plots, protocol, access/completion
  records and saved-score verification summary. No raw rows/models committed.
- Persistent local package: `artifacts/candidates/if_submission_final/`, including
  final joblib, metadata, feature/evaluation source, row-score evidence and notebook.
  Joblib is executable serialization; load only this self-produced trusted package.

Five synthetic evaluator tests passed before test access. The actual archived
estimator was loaded with strict source archive/member hashes and compatible
versions. Exact reload parity passed on128 scored rows per cohort. A subsequent
audit used the65,440 saved score rows to reproduce confusion counts, family/event
metrics, AP, ROC-AUC and bootstrap intervals, verifying all8 run artifact hashes.
It did not rerun model inference or reopen holdout ZIPs.

Research is complete for this frozen protocol. PR review/merge and the separately
requested mobile integration are administrative/product follow-ups, not grounds
to keep tuning the model. No services were launched or app artifacts replaced.
