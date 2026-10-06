# Frozen-model results on Wasaa synthetic data

## Conclusion

Submission summary: [Wasaa testing and model decision](../docs/wasaa_testing_and_model_decision.md).
This report concerns the original 293,448-row snapshot. Later notebooks use a
different 298,536-row export with label columns and newly trained models; their
results must not be merged into this frozen transfer experiment.

**The retained total-spending LSTM transfers better than the updated category
LSTM in this evaluation, but both transfer poorly.** The category model produces
extreme forecasts and should not replace the retained model on this evidence.
Isolation Forest alert behaviour was measured, but detection accuracy cannot be
estimated because the external data has no independent anomaly labels.

The models were trained on R3 and evaluated without refitting weights, scalers or
thresholds on independently generated Wasaa synthetic data. This is external
synthetic transfer evidence, not real-user validation. Scope and mappings were
declared in #30 before scoring. All scenarios are reported, including failures.

## Data and protocol

- Snapshot:293,448 spending records and80,013 category-month budgets;500 households.
- History:2025-04-07 onward. Targets:12 Monday-start weeks from2026-07-06 through
  2026-09-21, ending2026-09-28 exclusive. First and final partial snapshot weeks
  are excluded. Internal weeks are **assumed fully recorded**, not independently
  attested by a household observation log.
- Each forecast scenario contains6,000 identical household/week target identities.
- Retained model scenarios: consumption excluding Savings; all outflows including
  Savings; and mapped-category subset. These are alternative target definitions,
  not tuned variants or a claim that Savings has a confirmed accounting meaning.
- Mapped subset: Groceries->Food, Medical->Healthcare, School Fees->Education;
  Rent, Entertainment, Transport and Utilities unchanged. The mapping is an
  explicit evaluation assumption, not a verified platform ontology.
- Savings, Household Help and Airtime and Data are excluded from the category
  scenario. Included rows account for **84.21% of recorded evaluation outflow
  amount**, so this scenario is not a complete-household spending forecast.
- The category model's nine outputs are all included in its total. Predictions
  for Shopping/Subscriptions count as error against zero within this restricted
  target definition; their absence is part of the distribution mismatch.
- Missing merchants are empty strings, using existing retained-feature fallback
  behaviour. Description and payment source are not fabricated merchant IDs.
  This affects both recurrence context and IF duplicate/merchant features.
- Budgets do not enter model features, fitting or target selection. Their
  overrun status is used only for retrospective alert association.

## Forecast results

WAPE below is shown as a percentage; machine-readable reports store it as a ratio.
Lower WAPE/MAE/RMSE is better. Within20 is the fraction of forecasts within20% of
actual weekly spending, not classification accuracy.

| Scenario / model | WAPE | MAE KES | RMSE KES | R2 | Within20 |
|---|---:|---:|---:|---:|---:|
| Consumption / retained LSTM | **75.28%** | 11,906.71 | 18,057.03 | -0.5988 | 7.55% |
| Consumption / last week | 86.63% | 13,702.17 | 19,488.21 | -0.8623 | 12.53% |
| All outflows / retained LSTM | 73.69% | 12,302.17 | 18,444.10 | -0.6127 | 7.63% |
| All outflows / last week | 82.58% | 13,785.86 | 19,563.64 | -0.8144 | 13.88% |
| Mapped subset / retained LSTM | **80.35%** | 11,295.99 | 17,480.29 | -0.5959 | 6.98% |
| Mapped subset / category LSTM | **2.069e19%** | 2.908e21 | 2.217e23 | -2.567e38 | 7.15% |
| Mapped subset / last week | 96.34% | 13,544.08 | 19,350.89 | -0.9557 | 11.38% |

The retained LSTM beats the last-week baseline on aggregate absolute/squared
error, but underpredicts heavily and has lower Within20. It is not enough to say
it transfers well merely because it beats one baseline. Consumption bias is
**-KES11,605.12**; median prediction is KES3,885 versus median actual KES11,238.

### R3 versus Wasaa

| Evidence | Retained LSTM WAPE | MAE KES | R2 |
|---|---:|---:|---:|
| R3 reused validation (V9 retained export) | 34.52% | 2,616.88 | 0.4163 |
| Wasaa consumption scenario | 75.28% | 11,906.71 | -0.5988 |

WAPE is40.75 percentage points higher on Wasaa consumption. This describes a
cross-dataset performance difference, not a controlled estimate of how much any
single feature/domain factor caused the loss. Spending scales, user populations,
recording patterns, category meanings and merchant availability differ.

The updated category notebook reported37.69% total validation WAPE for its
pre-refit development checkpoint. The actual Wasaa artifact is the later
train+validation+calibration refit. Thus its severe transfer failure is real for
the tested artifact/scenario, but its stored validation score must not be relabelled
as an independently measured R3 score for that final refit.

### Extreme category outputs: verified, not hidden

-286 of6,000 total forecasts exceed KES1million;122 exceed KES1billion.
- Largest forecast: **KES1.717117247359962e25**, compared with maximum mapped
  actual weekly spending of KES104,411.
- One row contributes98.41% of total absolute error; the top10 contribute nearly
  all of it. Aggregate failure metrics are intentionally not clipped or trimmed.
- The maximum case is dominated by Rent. Original notebook feature equations
  exactly match the adapter on the same panel. A separate CPU diagnostic
  reproduces the saved forecast exactly, both in the original12-row batch and
  as a single input.
- The maximum inverse-scaled log output is58.1053; applying expm1 reproduces the
  extreme value. Maximum absolute standardized input is10.15. This supports
  out-of-distribution extrapolation amplified by the inverse-log transform;
  it does not isolate a complete causal explanation of the learned failure.

The extreme diagnostic was performed after evaluation solely to verify the
calculation. No weights, transforms, caps or selection choices were changed.

### Descriptive uncertainty

Post-run1,000-replicate user-cluster bootstrap95% intervals (seed2026):

- Consumption retained WAPE:74.89%–75.68%.
- All-outflows retained WAPE:73.29%–74.09%.
- Mapped retained WAPE:79.77%–81.00%.
- Category mapped WAPE:5.471e16%–6.253e19%.

These intervals are conditional on these frozen models and scenario assumptions.
They do not include mapping uncertainty, training-seed variation or real-population
uncertainty. The huge category interval reflects influential catastrophic outputs.

## Isolation Forest

The original fixed threshold remains0.6451359189730762. In the consumption,
missing-merchant scenario:

| Measure | Wasaa |
|---|---:|
| Evaluated transactions | 39,679 |
| Alerts | 46 |
| Alert rate | **0.1159%** |
| Households receiving an alert | 40 of500 |
| Precision / recall / F1 / AP / ROC-AUC | **Unavailable: no anomaly ground truth** |

43 of46 alerts occur among12,983 transactions linked to over-budget categories;
3 occur among26,696 transactions in categories not over budget. Alert rates are
0.3312% versus0.0112%. This is retrospective association, **not**91% precision:
being over budget neither proves anomaly nor makes a transaction fraudulent.

R3 standard test had62.32% precision,71.39% recall,F10.6655 and2.707% alert rate.
Wasaa's lower alert rate cannot establish better precision or worse recall. The
missing merchant signal and changed transaction distributions limit comparison.

## Execution and verification

- Actual Windows CPU inference; no GPU, fitting or upstream writes.
- Retained trained arrays/threshold and category model/scalers stayed frozen.
  Source and input hashes were locked before scoring and retained with results.
- Initial30-minute attempt stopped after200 households before final output was
  saved. Only checkpoint persistence was added; the same scenarios were rerun
  from the start. Both locks are retained locally. No partial scores selected a
  new model, mapping, threshold or evaluation period.
- Complete run:500 households,24,000 forecast rows across four model/scenario
  combinations,54,000 category rows,39,679 IF score rows.
- Saved-output audit verifies5 run-file hashes and1,500 per-household checkpoint
  files; independently recomputes16 forecast/category/baseline metric records,
  common target identity, category sums and threshold flags.
- Eight evaluator/audit/notebook tests passed. The maximum-case diagnostic additionally
  verifies original feature equations and inference/inverse-transform behaviour.
- Published data is aggregate-only. Local score rows and exact inference sources
  are preserved under `artifacts/candidates/wasaa_transfer_evaluation/`, including
  checkpoint audit inputs. The completed temporary run is also retained.

`Wasaa_Model_Results.ipynb` displays these saved aggregate results without
training or rereading raw data. `evaluate_wasaa_models.py` runs the locked
evaluation when explicitly supplied the snapshot, original source directories and
frozen bundles. `audit_wasaa_results.py` audits saved outputs without inference.

## Decision

For this comparison, **retain the original total LSTM; do not promote the category
model**. Do not claim either achieves satisfactory general-purpose transfer.
Keep the IF frozen and describe its external evidence as alert behaviour, not
labelled detection performance. Wasaa has now been inspected for model performance;
if these outcomes guide later model selection/development, it is no longer an
untouched final confirmation set for that later model.

This task measures model transfer only. Service deployment and mobile integration
remain separate. Further experiments require a new protocol and confirmation
data rather than repeatedly tuning against these external outcomes.
