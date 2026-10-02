# LSTM improvement review before external evaluation

Tracking: #34. Branch: `research/lstm-improvement-review`.

## Decision

Keep the frozen V6-reference LSTM for Wasaa transfer evaluation. Existing V7–V9
comparisons and the bounded saved-prediction check below do not establish a
material improvement worth another model export or serving change. This is a
decision about available evidence and project scope, not a mathematical ceiling
on LSTM performance or proof that all possible improvements have been exhausted.

The supervisor's instruction is to test the R3-trained model on independently
generated Wasaa synthetic data, without retraining. This review precedes that
evaluation at the user's request and does not change the trained reference.

## What has already been tested

| Investigation | Evidence | Decision |
|---|---|---|
| V7: history length, centering/scaling, loss, regularization, schedule, activity features | 14 configurations; repeated seeds for strongest candidates. No-L2 mean WAPE32.385716% versus reference32.358475% | Retain reference |
| V8: observed income and category history | Best mean WAPE32.298784%, gain0.059691pp / KES4.19; interval crosses zero | Retain reference |
| V9: full120-epoch predictive checkpoint policy | Mean WAPE32.354624%, gain0.003851pp / KES0.27; interval crosses zero;20.6% more comparison training time | Retain reference |
| Tiny fit-only update diagnostic | More updates improved training error23.7%; matching local tensors, unresolved archived identity difference | Not unseen-user gain; no justification for automatic960epochs |
| Large-week diagnosis | 7.75% of weeks containing injected events contribute52.67% of absolute error | Preserve difficult rows; no generator tuning, event removal or universal ceiling claim |

Sources: V7_KAGGLE_RESULTS_REVIEW.md, V8_RESULTS.md, V9_RESULTS.md,
UPDATE_BUDGET_RESULTS.md and LARGE_WEEK_FINDINGS.md. Historical deployment/issue
status paragraphs in those reports describe their review dates; current tracking
is #33/#34, and final IF cohorts have since been evaluated/consumed in #27.

## Bounded equal-seed-ensemble diagnostic

Hypothesis: averaging existing seed predictions might reduce instability without
retraining. This was declared in #34 before computing the comparison. An earlier
large-week analysis already used the three-seed mean descriptively, so this is a
follow-up diagnostic on reused evidence, not independent hypothesis confirmation.

Protocol:

- Read only the three V6-reference training-user outer-fold prediction CSVs and
  their manifest from the SHA256-pinned final V9 archive. No model loading.
- Seeds42/123/2026, arithmetic mean with equal weights; no weight/offset search.
- Identical7,200 user/week rows,600 users, dates2022-04-11 through2022-12-12.
- Fixed comparator seed42; report other seeds and recurring-median baseline too.
- Preserve the existing1pp material-WAPE criterion. Use1000 paired user-cluster
  bootstrap resamples with seed2026 for conditional uncertainty.
- No raw dataset, final/shifted data, final validation prediction CSV or Wasaa
  records are parsed. The entire archive is byte-hashed for identity; only the
  enumerated development members are parsed.

| Metric | Fixed seed42 reference | Equal three-seed mean |
|---|---:|---:|
| WAPE | 32.373598% | 32.324309% |
| MAE KES | 2273.5083 | 2270.0469 |
| RMSE KES | 7020.6974 | 7025.6537 |
| R2 | 0.459061 | 0.458297 |
| Bias KES | -1485.9681 | -1506.5165 |
| Within20% | 48.5556% | 48.9028% |
| Worst pooled time-block WAPE | 33.119284% | 33.107957% |

Gain0.049289 WAPE percentage points / KES3.4614 MAE. Candidate-minus-reference
95% interval [-0.074338,-0.021785]pp excludes zero conditionally on these reused
folds, but the practical1pp criterion fails. WAPE improves in all three folds;
343/600 users have lower total error and257 higher. RMSE and signed bias worsen.

Seed123 WAPE32.383145%; seed2026 WAPE32.318683%. The ensemble is slightly worse
than seed2026 on pooled WAPE. Do not choose a lucky seed after reviewing these
figures and describe it as a new reliable improvement. Mean-seed WAPE32.358475%
is also a different statistic from WAPE of mean predictions32.324309%.

An ensemble would require three fitted inference paths/artifact sets, not merely
changing one parameter in the existing selected model. Runtime/storage impact
was not benchmarked. This modest diagnostic gain does not justify that change.

## What remains possible, and what would count as new research

1. **Observable planned expenses / improved bill timing.** Potentially useful
   only when the input existed before the forecast origin. Requires data and a
   new feature contract; cannot inject generator truth or future actual spending.
2. **Calibrated prediction intervals.** Could improve communication of uncertainty,
   but must be evaluated for coverage and width. Not an improvement to point-WAPE
   merely because an interval includes more outcomes.
3. **New architecture or compute budget.** Not ruled out universally, but no
   remaining evidence here supports a particular broad search as the best next
   use of effort. It would require a separately bounded protocol, matched folds,
   repeated seeds, and an unchanged comparator. Existing claims remain tied to
   their original models; new results must not overwrite old version labels.
4. **Bias correction.** Negative mean bias alone is insufficient justification for
   adding KES or multiplying forecasts. MAE-oriented predictions can underpredict
   the mean on skewed spending. Any correction is learned postprocessing and
   needs separate calibration/evaluation; it is not a free accuracy fix.

R3 final/shifted cohorts have been consumed by IF evaluation. Their observed
anomaly patterns must not guide new LSTM selection. Existing training folds are
also reused, so adaptive optimism remains. No final-cohort selection or generator
retuning is proposed. The independent Wasaa set should remain unseen until the
transfer protocol and mapping are fixed, and never become retraining data for
the supervisor's requested transfer claim.

## Accurate current forecast claim

The retained exported reference's reused R3 validation has WAPE34.523757%,
MAE KES2616.8786, R2.416328 and47% of predictions within20% of recorded actuals.
These were independently rescored in V8/V9; they are not external-transfer or
final LSTM test results. Do not call100-minus-WAPE model accuracy.

The original V7 final validation-row export gap remains an archival issue in #6;
V9's verified retained-reference rows are not falsely relabelled as recovered V7
evidence. That gap does not require retraining or block this review's conclusion.

## Verification / reproduction

Four regression tests plus three subtests passed: known ensemble/error arithmetic,
deterministic paired uncertainty, shuffled alignment, missing/duplicate/mismatched
rows, nonfinite values, seed identity and cross-fold user overlap. Three actual
prediction-member hashes and the complete V9 archive hash were verified.
Results: `evidence/v7_source_audit/lstm_ensemble_review.json`.

```powershell
python -m pytest model_research/test_review_lstm_ensemble.py -q
python model_research/review_lstm_ensemble.py --archive "<verified V9 archive.zip>" --output "<new aggregate report.json>"
```

No training, model deserialization, held-out cohort evaluation, mobile/backend
change, external data retrieval or deployment occurred. There is no new final
LSTM artifact from this review. Next action remains #29 mapping, then #30 frozen
external evaluation, with the original model and historical results preserved.
