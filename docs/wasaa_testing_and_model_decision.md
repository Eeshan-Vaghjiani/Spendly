# Wasaa testing and model selection decision

## Purpose and conclusion

Wasaa data was used to investigate how the R3-trained spending models behaved on
an independently generated synthetic household dataset. The purpose was to test
transfer, not to retrain until the external scores improved.

**The dataset was accepted as evaluation evidence. The proposed model replacement
was not accepted for the deployed Spendly pilot.** These are different decisions:
poor transfer is a finding to report, not a reason to discard an inconvenient test.

The existing total-spending LSTM and single excess-view Isolation Forest remain
the pilot models. This retention preserves an established serving contract and
audited artifacts; it does not demonstrate strong real-world performance. The
application has already been deployed. This report does not require redeployment,
new training or replacement of the installed APK.

## 1. Dataset and provenance

The evaluated snapshot contains:

| Dataset | Rows | Purpose |
|---|---:|---|
| spending_records | 293,448 | Transaction history and actual weekly expenditure |
| budget_categories | 80,013 | Join validation and retrospective budget association |
| Households | 500 | Evaluation population |

The records span April 2025 to September 2026. Both sources are **synthetic**;
neither the R3 nor Wasaa results establish representative real-user accuracy.

Snapshot SHA256 identities:

- Spending: `ce7d857048c6ede0844e33084ad0358011a619ee962406b7a367c104126741da`
- Budgets: `78673fe0dd5b0786c015ede22ad6d0029a760330dc5dd572fda6e2af50f87cac`

Structural checks found no repeated spending IDs, duplicate category-period
budget rows, unmatched budget links, household/category mismatches, or UTC
month/year mismatches. Spending sums reconciled to the corresponding budget
actual totals. Of the category-months, 26,460 (33.07%) exceeded their allocation.
That percentage describes budget performance, not anomaly labels or advice acceptance.

Credentials and raw exports are not published. Aggregate evidence is available
in `model_research/evidence/wasaa_transfer/` and the snapshot review associated
with PR #41. The evaluated files have no anomaly-label columns or merchant field.

## 2. Evaluation procedure

1. Preserve the trained R3 artifacts, scalers, feature equations and IF threshold.
   No `fit`, threshold calibration or training on Wasaa was performed.
2. Verify input and artifact identities and record the evaluation scenarios before
   scoring. Convert timestamps to Africa/Nairobi and use Monday-start weeks.
3. Use history from 7 April 2025. Evaluate twelve weeks from 6 July 2026 to
   28 September 2026 (exclusive), avoiding the snapshot's partial boundary weeks.
   Complete recording within this interval is an explicit assumption, not an
   independently verified household coverage attestation.
4. Produce 6,000 household-week forecasts for each model/scenario combination.
   Only transactions before each target week enter its feature history.
5. Evaluate the retained LSTM on consumption excluding Savings, all outflows
   including Savings, and a mapped-category subset. These scenarios expose the
   uncertain meaning of Savings rather than silently choosing the best result.
6. Compare the retained LSTM and R3-trained category candidate on identical
   mapped-subset targets. Map Groceries to Food, Medical to Healthcare and School
   Fees to Education; retain Rent, Transport, Utilities and Entertainment.
7. Exclude Savings, Household Help and Airtime and Data from that subset. It covers
   84.21% of evaluation outflow amount, not the full household target. All nine
   candidate outputs count towards error, including unsupported positive output
   for categories with zero actual spending in this restricted scenario.
8. Represent missing merchants with the existing empty-string fallback. Do not
   fabricate merchants from payment source or descriptions. Record the impact as
   a limitation of input equivalence for both models.
9. Score the retained IF on consumption transactions using its fixed threshold
   of 0.6451359189730762. Report alert behaviour; do not manufacture ground truth
   from budget overruns.
10. Preserve predictions, recompute metrics, check per-household outputs and
    investigate extreme results without clipping, retraining or changing scenarios.

The actual execution used Windows CPU, not Kaggle GPU. An initial timed-out run
was restarted after adding per-household output checkpoints. Only persistence
changed; weights, mappings, dates and thresholds remained fixed.

## 3. Results and comparison with R3

### Retained total-spending LSTM

| Metric | R3 reused validation | Wasaa consumption scenario |
|---|---:|---:|
| WAPE | 34.52% | 75.28% |
| MAE (KES) | 2,616.88 | 11,906.71 |
| RMSE (KES) | 7,755.99 | 18,057.03 |
| R2 | 0.4163 | -0.5988 |
| Mean bias (KES) | -1,777.49 | -11,605.12 |
| Within 20% of actual spending | 47.00% | 7.55% |

Wasaa consumption WAPE was 40.75 percentage points higher. The retained LSTM
outperformed a last-week forecast on WAPE (75.28% versus 86.63%), but substantially
underpredicted expenditure. Beating that baseline does not demonstrate adequate
forecasting quality. The R3 column is development-validation evidence, not an
untouched final LSTM test. Cross-dataset differences do not isolate one cause.

### R3-trained category LSTM candidate

On identical mapped-subset targets, retained LSTM WAPE was 80.35%; candidate WAPE
was approximately 2.069e19%. The unusually large figure is not a formatting error:
286 of 6,000 predictions exceeded KES 1 million, and 122 exceeded KES 1 billion.
The maximum was approximately KES 1.717e25.

The largest case reproduced exactly using the original notebook feature equations
and manual inverse transformation. A large learned log-space output is amplified
by `expm1`. One row accounts for 98.41% of absolute error. The result demonstrates
severe extrapolation failure for this frozen artifact and scenario; it was not
trimmed or capped to improve the score.

### Retained Isolation Forest

| Measure | R3 final standard test | Wasaa consumption scenario |
|---|---:|---:|
| Precision | 62.32% | Not measurable without labels |
| Recall | 71.39% | Not measurable without labels |
| F1 | 0.6655 | Not measurable without labels |
| Transactions scored | 32,841 | 39,679 |
| Alerts | 889 | 46 |
| Alert rate | 2.707% | 0.1159% |

Forty Wasaa households received an alert. Forty-three of the 46 alerts were linked
to over-budget category-months. This is retrospective association, **not** 93.48%
precision: over-budget transactions are not necessarily anomalous. A lower alert
rate establishes neither improved precision nor degraded recall. Merchant
availability and other distribution differences limit interpretation.

## 4. Why replacement was not accepted

- The existing LSTM's weak transfer gives no basis for claiming reliable general
  forecasting outside its development conditions.
- The R3-trained category candidate is worse on the common external target set
  and generates implausible extremes; it does not justify replacing the pilot model.
- IF correctness cannot be established from unlabelled external records. Its low
  alert rate cannot justify promoting a replacement or declaring detection failure.
- The app's existing feature and API contracts differ from the candidate notebooks.
  Easier file loading is not sufficient evidence of serving parity or useful output.
- No post-test adjustment was made to manufacture an improvement. Wasaa results
  are retained as negative/limited transfer findings in the project evidence.

This decision concerns model promotion, not the quality or legitimacy of the
provided dataset. Neither synthetic dataset is a universal substitute for later
representative, consented app evaluation.

## 5. Later Wasaa-trained notebooks are separate experiments

The subsequently supplied `WASAA LSTM.ipynb` and `WASAA ISOLATION FOREST.ipynb`
train new models on a newer Wasaa export. Their saved outputs show 298,536
spending rows, 17 categories and label columns. They are **not** the files or
models used in the frozen transfer experiment above.

| Later notebook evidence | Saved result | Limitation |
|---|---|---|
| Wasaa-trained LSTM, 75-user holdout | Total WAPE 58.57%; category WAPE 87.79%; total R2 -0.0797 | Different dataset, targets and fitting procedure; still weak category forecasts |
| Wasaa-trained IF, constructed post-freeze benchmark | Precision 82.08%; recall 92.80%; F1 0.8711 | 375 added cases versus 2,547 reference rows assigned normal labels; not native-label detection evaluation |

These figures were read from saved notebook outputs. IF confusion arithmetic was
checked; full saved-artifact inference and row-score verification were not repeated.
The IF notebook acknowledges prior exploration of the same household population.
It drops native label fields and builds new injected cases, so its headline metrics
cannot be presented as native-labelled Wasaa performance or a direct improvement
over the retained R3 forest. Older R3 headings in that notebook do not describe its
new executed Wasaa pipeline.

The LSTM runtime review reproduced timezone failure, omitted trailing quiet weeks
and history-length feature drift when history is truncated. These findings, along
with the results, do not support immediate promotion of the exported runtime.
The newer label columns do not retroactively label the older evaluated snapshot.

## 6. Verification record

The completed transfer run contains 24,000 model/scenario forecast rows, 54,000
category rows and 39,679 IF scores. The saved-output audit verified five result
file hashes, 1,500 household checkpoints and sixteen metric records. Eight
evaluator/audit/notebook tests passed in the original evaluation. No new model
run is required to document those results.

Sources:

- [Full transfer report](../model_research/WASAA_TRANSFER_RESULTS.md)
- [Saved result notebook](../model_research/Wasaa_Model_Results.ipynb)
- [Metric JSON](../model_research/evidence/wasaa_transfer/results.json)
- [Audit JSON](../model_research/evidence/wasaa_transfer/audit.json)
- [Extreme-case verification](../model_research/evidence/wasaa_transfer/extreme_verification.json)
- [R3 LSTM result](../model_research/V9_RESULTS.md)
- [R3 final IF result](../model_research/IF_SUBMISSION_RESULTS.md)

## Report-ready conclusion

> The R3-trained models were evaluated without retraining on a separate synthetic
> Wasaa household dataset. The retained LSTM's WAPE increased from 34.52% on
> reused R3 validation to 75.28% in the Wasaa consumption scenario, indicating
> limited transfer under the stated input-mapping and coverage assumptions.
> A category-level candidate exhibited severe extrapolation errors and was not
> adopted. Isolation Forest generated 46 alerts among 39,679 eligible transactions,
> but external detection accuracy could not be estimated because that snapshot
> contained no anomaly labels. Accordingly, the established pilot models were
> retained with documented limitations; no model replacement or improved
> real-world-performance claim was supported by this evaluation.

## Documentation closure and remaining work

The original V7 final validation-row archive was not located in the current
Downloads search. Its missing export remains an explicit historical limitation;
the independently verified V8/V9 retained-reference results are not relabelled as
recovered V7 results. No retraining is required to recreate that history.

The earlier category development checkpoint/scalers were not found in the inspected
Drive folders. The available final-refit bundle was evaluated instead and was not
promoted. Recovering that old development checkpoint is optional archival work,
not a release prerequisite after this decision.

Next submission task: complete the SRS requirement-to-evidence table and applicable
QA/design documentation in #11. Existing pilot deployment, remaining native QA,
and any separate Wasaa service handoff should be recorded independently. A deployed
Spendly backend does not by itself establish that the separate `/recommendations`
service has been configured in the Wasaa platform.
