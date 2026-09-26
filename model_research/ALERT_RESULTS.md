# Reproduced V7 spending-alert results

## Evidence and scope

Archive: `spendly_alert_review_20260926_092057_results.zip`.
SHA256: `98617ac130c456a5ee8917100e39451c63224ebe99877d7adb1db23c46dc4c42`.
Full-development CPU reproduction on original R3, not recovered original artifacts.
Evaluation starts2023-04-24;100 validation users,35,151 transactions,1,005 labelled
positive transactions and34,146 negatives. There are278 represented labelled events.

ZIP CRC and all14 manifest hashes passed. Recomputed precision, recall, F1, FPR,
accuracy, balanced accuracy and alert rate from all six confusion matrices; family
transaction counts reconcile to TP/support and event recalls imply integer counts.
Daily burden totals agree with alert counts. No models were unpickled or executed,
and no raw datasets were read. There are no row-level scores/flags in this export;
AP/AUC, actual per-row predictions and event membership cannot be independently
rescored. This is integrity/arithmetic verification, not independent model inference.

## Transaction-level comparison

| Detector | Precision | Recall | F1 | TP | FP | Observed FPR |
|---|---:|---:|---:|---:|---:|---:|
| Single forest |66.84%|78.21%|**.7208**|786|390|1.142%|
| Stricter excess forest |77.27%|66.97%|.7175|673|198|.580%|
| Rhythm forest component |23.79%|5.37%|.0877|54|173|.507%|
| Two-forest union |66.15%|72.14%|.6901|725|371|1.087%|
| Collective rules alone |23.98%|8.16%|.1218|82|260|.761%|
| Forest + collective union |69.59%|67.16%|.6835|675|295|.864%|

Retain the preselected **single forest**. The single detector alerts on1176
transactions across708/18069 active user-days (3.92%). Approximately one-third of
its alerts are false positives in this synthetic evaluation. Its98.27% accuracy
must not obscure that precision limitation or the missed219 positive transactions.

The single model uses a1% calibration-negative budget; union components each use
.5%. Thus a union can have lower recall than the single comparator without a union
logic bug: its forest component uses a stricter threshold. Compare added rules to
that same component: forest+rules versus strict forest adds **2 TP and97 FP**.
That is a poor marginal trade-off here, not evidence to deploy the companion.

Calibration FPR was within budget, but observed validation FPR differs. A calibration
budget is not a guaranteed population rate. Metrics are on reused synthetic
development data and are not fraud findings or real-user performance evidence.

## Event and family trade-offs

| Family | Single transaction recall | Two-forest transaction recall |
|---|---:|---:|
| Burst (444 rows /63 events) |88.29%|80.86%|
| Duplicate (201 /67) |98.51%|96.52%|
| Large (43 /43) |100%|90.70%|
| Recurring increase (52 /52) |**11.54%**|**100%**|
| Split (265 /53) |55.47%|30.57%|

Single detects at least one member in211/278 events (75.90%); the two-forest union
detects241/278 (86.69%). The rhythm component captures all52 recurring-increase
events, explaining why event recall improves even as transaction recall/F1 fall.
The single forest already catches all burst, duplicate and large events at least
once, but misses many recurring increases and some split events.

This supports a future **targeted recurring-bill alert** investigation if that
behavior matters to the product. It does not justify automatic union promotion or
choosing a new metric after the fact to declare the comparator a winner.

## What happened to the collective rules?

The calibration thresholds are7.70 for standalone rules and32.61 for the union
component. The score is max(day_count_ratio/4, weekend_ratio/6, duplicate_count).
A typical isolated three-transaction duplicate event contributes at most2 to its
duplicate channel. That channel alone cannot cross these thresholds. The aggregate
evidence suggests score-scale/calibration compatibility needs investigation; it
does not identify which channel generated every alert without row-level scores.
Benign lookalikes were deliberately present in the simulator, so reducing thresholds
may add false alerts. Do not tune on these validation results.

## Contribution of PR #3

The PR supplied the useful group-level anomaly hypothesis and prompted a causal,
budget-controlled comparison with per-type/event and alert-burden reporting.
The tested collective companion did not improve the required overall trade-off.
An unsuccessful hypothesis is still a research contribution: the experiment now
shows what to retain, what not to promote and where the existing detector is weak.
The rhythm-forest comparator is separate prior work, not an improvement attributable
to the PR's rules.

## Status

Alert reproduction and result review are complete. V6 remains the forecasting
reference and single excess-view Isolation Forest remains the alert reference.
App activation is still paused for product/serving-contract review. The run took
2956.7s (~49.3min) for anomaly processing; no LSTM was trained.
Summary tool: `analyze_alert_results.py`; aggregate output:
`evidence/v7_source_audit/alert_results_verified.json`.
