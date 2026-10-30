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

**Scope confirmed by the project owner on 20 October 2026: dataset evaluation
and report only.** A separately hosted Wasaa advisor API, platform integration
and recommendation-feedback rollout are not submission requirements. The existing
optional prototype is preserved; no external service deployment is claimed.

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

### Recovered settings and interpretation (20 October 2026)

The original LSTM and IF notebook files contain saved outputs with cleared execution
counters. Their outputs are historical evidence; neither notebook was executed in
this documentation check. File hashes and aggregate settings are recorded in
[the later-notebook review](../model_research/evidence/wasaa_transfer/later_notebooks_2026_10_20.json).

| Setting | Later Wasaa LSTM | Later Wasaa IF |
|---|---|---|
| Seed | 42 | 42 |
| Structure | LSTM 128 then 64; dropout 0.15 after each; Dense 64 ReLU; 17 linear outputs | 500 trees, 24 features |
| History / sampling | Selected 13 weeks from 13/26/39 | max_samples 16,384; max_features 0.75 |
| Optimizer / transform | Adam 0.0008, clipnorm 1.0, MAE; log1p then StandardScaler targets | contamination auto; explicit score threshold |
| Search / stopping | 4 configurations per window; cap 100 epochs; batch 64; early-stop patience 10; LR patience 5 | samples 2,048/8,192/16,384; feature fraction 0.5/0.75/1.0 |
| Selected final setting | Best epoch 7; seven-epoch development refit | Threshold printed as 0.467120 (rounded; full precision not recovered here) |
| Holdout evidence | 75 users, 4,928 sequences; MAE KES 10,272.46; RMSE KES 19,020.11 | 75 users; TP 348, FP 76, FN 27, TN 2,471 on the constructed benchmark |

The twelve LSTM search runs used all three windows with these four settings:

| Configuration | LSTM units | Dropout | Dense units | Loss | Adam learning rate |
|---|---|---|---|---|---|
| LSTM_128_MAE | 128 | 0.15 | 64 | MAE | 0.001 |
| LSTM_192_MAE | 192 | 0.20 | 96 | MAE | 0.0008 |
| LSTM_128x64_MAE (selected) | 128, 64 | 0.15 | 64 | MAE | 0.0008 |
| LSTM_128_HUBER | 128 | 0.15 | 64 | Huber | 0.001 |

The IF's final 24 inputs comprise 22 retained base features plus two time-context
features, `user_hour_prior_share` and `user_hour_support_distance`. The initial
`user_z` and `user_prior_count` features were removed before adding those two;
the initial 24-feature list is not the final serving order. Both lists are
preserved in the aggregate review JSON for reproducibility.

The LSTM's negative holdout total R2 (-0.0797) and near-100% WAPE for Rent
and several sparse categories do not support reliable category budgeting.
On validation, moving-average-8 has lower total RMSE and positive total R2
despite slightly worse WAPE (59.86% versus 58.42%). That is a validation
comparison, not a new holdout baseline result. WAPE 58.57% on this fitted newer
export cannot establish improvement over 75.28% on the older frozen-transfer
snapshot: training population, targets and protocol changed.

The IF's saved validation P/R/F1 are 0.8490/0.9147/0.8806; calibration values
are 0.8708/0.9440/0.9060; constructed holdout values are
0.8208/0.9280/0.8711. These split labels must not be reversed. They do not
measure detection accuracy against the newer export's original label columns.

The separately supplied `Final_Wasaa_LSTM_Spending_Forecasting_Deployment.ipynb`
contains code but no captured metric output. Its name does not establish a trained,
tested or deployed replacement. Saved-artifact serving parity remains unverified.

## 6. Verification record

The completed transfer run contains 24,000 model/scenario forecast rows, 54,000
category rows and 39,679 IF scores. The saved-output audit verified five result
file hashes, 1,500 household checkpoints and sixteen metric records. Eight
evaluator/audit/notebook tests passed in the original evaluation.

On **20 October 2026**, the local synthetic input hashes and structural checks
were verified again. The saved-output rescore reproduced the published audit
exactly, including all five hashes, 1,500 checkpoint files and sixteen metric
records. The same eight evaluator/audit tests passed again (zero failures).
No model inference, training, notebook execution or upstream data request was
performed. See [the fresh verification record](../model_research/evidence/wasaa_transfer/verification_2026_10_20.json).
The structural-audit helper's initial mapping-blocked placeholder is historical;
the completed transfer protocol and results establish current evaluation status.

Descriptive whole-household bootstrap intervals (1,000 resamples, seed 2026)
put retained consumption WAPE at 74.89%-75.68%, all-outflow WAPE at
73.29%-74.09%, and mapped-subset WAPE at 79.77%-81.00% (95% intervals).
They condition on the fixed models, mappings and coverage assumptions; they do
not establish real-user validity or include training/model-selection uncertainty.

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

**Wasaa dataset evaluation and reporting are complete for the confirmed scope.**
The remaining external advisor work in #9/#21/#31/#32 is outside that scope;
closure does not claim that an advisor URL, real feedback or platform acceptance
exists. The retained LSTM/IF are already integrated into the Spendly pilot.

Next submission task: complete the approved SRS requirement-to-evidence table,
institutional report format and applicable QA/design documentation in #11/#33.
Remaining Android OAuth, native import and signed-update acceptance in #22/#56
are separate app-release checks. Further model research is optional and needs a
new protocol and confirmation data, rather than reopening consumed final cohorts.
