# Category LSTM comparison

Tracking: #36. Branch: `research/lstm-category-review`.

## Conclusion

The category model is a useful new research direction, but the supplied evidence
does not establish a better replacement for the retained total-spending LSTM.
Keep the retained reference for now. A matched development comparison is needed
before selecting the category model. No new Isolation Forest training is indicated.

Input notebook SHA256:
`e760268cb1d1fd0dfc40bf8c632cfcb2485040d4c6e44172cee37472b5601a6f`.
The original notebook was not modified, installed from, or executed end-to-end.
Only reviewed preprocessing/metric functions were exercised on generated fixtures.
References below use zero-based notebook cell indices.

## Architecture and recorded results

Selected candidate: 26-week input, 76 weekly features, LSTM128, dropout0.20,
Dense64 and nine linear category outputs. Loss is MAE on standardized log1p
category targets. Overall spending is the sum of inverse-transformed categories.
Search includes four architectures and two lookbacks, at seed42. Saved environment
output reports TensorFlow2.20, NumPy2.1.3, pandas2.2.3 and CPU execution.

| Metric | Retained total LSTM, reused validation | Category model, selected validation | Category model, calibration check |
|---|---:|---:|---:|
| Total WAPE | 34.5238% | 37.6903% | 37.1365% |
| Total MAE KES | 2616.8786 | 2751.3465 | 2719.7486 |
| Total RMSE KES | 7755.9940 | 7852.7036 | 7862.1679 |
| Total R2 | 0.4163 | 0.3641 | 0.4090 |
| Category WAPE | Not an output | 48.4659% | 48.2655% |
| Category MAE KES | Not an output | 393.1055 | 392.7549 |
| Category sMAPE | Not an output | 138.8145% | 138.0850% |

**These columns are not a matched head-to-head result.** Retained validation covers
3,600 weeks after its training cutoff; the candidate evaluates13,000 weeks after
26-week warm-up across nearly the full validation timeline. Lower printed WAPE
for the retained model is not proof it wins on identical rows, and category WAPE
cannot be compared to total WAPE as if they measure the same target.

The notebook's historical29.85% WAPE/R2.675 literals are not the verified retained
reference result and have no supporting run evidence in this file. Its older
category baseline literals (59.2233% category /48.9778% total validation WAPE)
suggest substantial progress, but different row eligibility prevents attributing
the full difference to architecture/features alone.

On the notebook's own10,400-row common seasonal-baseline subset, selected LSTM
total WAPE37.6066% beats seasonal-naive61.6666%, MA4 85.0184% and MA8 83.9562%.
This is meaningful within-notebook evidence, not a comparison against the retained
recurrence-aware baseline/model. ARIMA/ETS code exists, but the supplied file has
no saved results for that stage; its checked completion boxes exceed the evidence.

Category strengths: subscription WAPE12.85%, rent15.58%, utilities17.34%.
Weaknesses: shopping95.18%, healthcare92.86%, education89.60%. These are selected
validation diagnostics, not guaranteed category quality on new data.

## Methodology and implementation findings

1. **Lookbacks are selected on different rows (cells27/33).** A16-week model has
   14,000 validation sequences;26 weeks has13,000. Use identical target origins
   across lookbacks before ranking. The generated fixture reproduces88 versus68
   rows for two60-week histories. This is not evidence of target leakage, but
   confounds the model/window comparison.
2. **No held-forward calendar split.** Input scalers use training users only, and
   sequences do not cross users or include their own target weeks. However the
   model/scalers fit the full training timeline while evaluating overlapping
   calendar periods for validation users. That estimates new-user generalization,
   not the same chronological forward test used by the retained research.
3. **Validation reuse and one seed.** Validation controls stopping, learning-rate
   reduction and model selection. The results are development evidence. Fixed
   random seeds do not substitute for repeated-seed stability. Hardware changes
   batch size128/256, so a GPU rerun also changes the training recipe.
4. **Final refit is a different model (cell52).** It fits103,999 sequences from
   train+validation+calibration for50 epochs, with new scalers. Earlier selected-
   model validation/calibration metrics do not evaluate that final refit. It also
   omits the adaptive learning-rate schedule used during search. No independent
   result for the exported final estimator is supplied.
5. **Incorrect income fallback (cell13), reproduced.** If no expense type exists,
   the function retains all rows. Income-only histories become expenditure.
   Require the schema and return an explicit no-expense state; do not fall back
   to treating receipts as spending.
6. **Coverage and inference origin (cells17/66), reproduced/inspected.** Panels
   start/end at first/last expense, not declared observation bounds. A five-week
   covered fixture emits only three weeks. Complete quiet weeks are dropped at
   edges, while the current partial week can enter inference without checks.
   An explicit as-of/coverage contract must define the last complete week and
   next target date. Missing records must not automatically become zero spending.
7. **Timezone and data quality.** Dates are parsed without explicit Nairobi
   conversion; invalid dates/amounts are coerced/dropped. Manifest versions and
   counts are printed but source hashes are not enforced. Reject or separately
   account for invalid rows and normalize timezone before weekly aggregation.
8. **Metric definition (cell29), reproduced.** sMAPE excludes jointly-zero pairs
   from the denominator. [0,100] versus [0,0] yields200%, whereas counting the
   joint-zero contribution as zero yields100%. This is a convention difference,
   not fabricated performance; label it explicitly, particularly for sparse
   categories. Log-space loss is not the same objective as KES-WAPE. Positive
   predictions for zero categories can inflate sMAPE; do not infer loss mismatch
   is the sole cause without residual/zero-week diagnostics.
9. **Statistical baseline sample consistency (cell45).** Failure rows are dropped
   separately per model; ARIMA/ETS/LSTM may then evaluate different targets.
   Use a shared valid mask and report failure counts. Endpoint-only evidence is
   not a full rolling-origin benchmark.
10. **Export reproducibility and test access.** Final files are overwritten in a
    fixed folder, there is no content-hash freeze or exact reload prediction test,
    and inference depends on mutable notebook globals. Save environment, category
    order, source, scalers and model identity together. Test booleans are not an
    access ledger. The supplied notebook's test stages are disabled; R3 final
    cohorts have separately been consumed by IF evaluation and must not become
    another LSTM selection set.

## Checks performed

- All33 code cells parsed;69 cells inventoried with content hash.
- Reviewed causal feature/sequence functions preserve input sequences when target
  or later weeks are changed, with scalers held fixed.
- Target inverse transform round-trip matches to KES0.001 on fixtures.
- Reproduced lookback population mismatch, income-only fallback, omitted covered
  boundary weeks and sMAPE joint-zero convention.
- Three review-harness tests passed; original notebook top-level code never ran.
- Saved selected-metric JSON was extracted, not independently recomputed from
  prediction rows. No matching model/scaler/prediction bundle was provided locally.
- No training, raw cohort access, external data access or model promotion.

Reproduce with `review_category_lstm.py --notebook <original.ipynb> --output <new.json>`.
The script requires the exact reviewed hash. Evidence is aggregate-only in
`evidence/v7_source_audit/category_lstm_review.json`.

## Recommended next step before external evaluation

**No additional IF candidate training.** Keep its completed evaluation frozen.

For LSTM, first obtain the existing **pre-refit development** artifacts:

- `lstm_best_development.keras` (the selected model before the all-cohort refit).
- Matching development input/target scalers, feature/category configuration and
  runtime versions (final scalers are not interchangeable).
- Validation/calibration predictions keyed by user, target week and category,
  with raw KES actuals; full search table and per-candidate histories.

Then audit those files and compare total forecasts on common, predeclared rows.
An existing-model comparison still needs to state each model's training horizon;
matching rows alone cannot undo overlapping-time training.

If category forecasts are required and a training experiment remains justified,
run **one fixed26-week/128-unit candidate versus the unchanged retained recipe**
on identical grouped chronological development folds and matched seeds42/123/2026.
Fit preprocessing inside each fold; use common target weeks; preserve all spending
events. Fix schema/coverage defects first. Evaluate total WAPE/MAE, worst-block
error, bias and category errors against suitable category baselines. Preserve the
existing1pp material total-WAPE criterion with paired user uncertainty for a
replacement decision; a category-only capability decision needs its own declared
criterion and must not be called a total-forecast improvement.

Do not repeat the eight-model grid or fit on Wasaa data. An existing checkpoint
and predictions may settle the question without training. If they are unavailable,
record that limitation before reconstructing a new matched experiment. The final
all-cohort model alone cannot provide independent validation on those same cohorts.
