# Spendly: implementation and evaluation report draft

This repository-backed draft supports the final submission document. It does not
replace the approved SRS, institution-specific structure, literature review or
reviewer sign-off. See [the evidence matrix](submission_evidence.md) for source
baselines, executable checks and unresolved coverage.

## 1. System purpose

Spendly is an Android-first personal-finance decision-support application. It
records income and expenses, manages budgets, displays cash flow, estimates
weekly spending and raises unusual-spending prompts for review. Amounts are KES.
Forecasts are estimates; alerts are not fraud determinations; proposed savings
are conditional planning scenarios rather than realized financial outcomes.

The project has three related deliverables: a deployed Flutter/Flask pilot,
versioned model research, and a separate HTTP advisor service for integration.
Their completion evidence is recorded independently rather than inferred from
the presence of a working application alone.

## 2. Implementation design

The pilot routes Flutter screens through Riverpod controllers and a repository/API
boundary into authenticated Flask endpoints under `/api/v1`. SQLAlchemy manages
financial persistence and owner-scoped access. Income and expenses remain distinct.
JWT/consent and input validation are backend responsibilities; the client does
not establish financial ownership by supplying an arbitrary user identifier.

The selected release at `60e3bd0` executes portable numeric LSTM and Isolation
Forest artifacts in the backend. It does not train models in requests, and the
selected forecast path does not use the legacy linear-regression blend. Model
features and saved transformations must match research-time definitions.

Forecasts use a fixed Nairobi Monday-Sunday interval and pre-target history.
The pilot asks for complete-history confirmation and explains the eight-week
requirement. Alert review links to the underlying transaction, supports explicit
intentional-spending confirmation and invalidates stale confirmations after edits.
Confirmed expenses remain in accounting totals. Asynchronous account-scoped state
prevents results from a previous account being applied to the next session.

The separate advisor exposes `/health` and `POST /recommendations` returning up
to three `{type, reason, savingKes, targetId}` items. Its implemented baseline
reviews approved category-budget gaps from a synthetic snapshot. Versioned
SQLite feedback tracks delivery, explicit display and decisions. The proposed
server-to-server authentication and feedback transport still need integration
agreement; local tests are not evidence that the external platform has connected.

Historical architecture/API pages may describe V1. Use the source baselines in
the evidence matrix for the pilot version rather than copying outdated diagrams.
Local Compose and hosted database configurations must likewise be distinguished;
no live database schema inspection was performed for this draft.

## 3. Model development and selection

R3 is controlled synthetic data, not sampled financial behaviour from Kenyan young
adults. V7 tested alternative history lengths, losses, regularization and feature
representations; V8 added observed income/category context; V9 tested checkpoint
policies. None met the predeclared material improvement criterion over the retained
V6 reference. A subsequent equal-seed prediction diagnostic also produced too
small a gain to justify replacing the single reference.

The retained LSTM's reused R3 validation WAPE is34.52%, MAE KES2,616.88 and
R2 .4163. These are development-validation results, not final-test classification
accuracy. The model's limitations include expensive irregular weeks and systematic
underprediction. Failed improvement experiments are reported rather than removed.

The retained single Isolation Forest was frozen before final R3 evaluation. Its
standard-test precision is62.32%, recall71.39% and F1 .6655; shifted-test F1 is
.6141. The historical80% aspiration across precision/recall/F1 was not met.
Strong detection of some large/duplicate-like events coexists with weak recurring-
increase and split-event recall. Therefore user review is essential to the design.

## 4. External Wasaa test

The completed external experiment tested frozen R3-trained artifacts on a
293,448-row Wasaa synthetic spending snapshot with80,013 budget rows and500
households. Twelve target weeks yielded6,000 forecasts per model/scenario.
The [detailed testing account](wasaa_testing_and_model_decision.md) records hashes,
pre-target windows, category mappings, missing-merchant fallback and coverage
assumptions. No weights, scalers or alert thresholds were fitted on Wasaa.

| Evidence | Main result | Interpretation |
|---|---|---|
| Retained LSTM, R3 reused validation | WAPE34.52%; MAE KES2,616.88 | Limited development performance |
| Retained LSTM, Wasaa consumption scenario | WAPE75.28%; MAE KES11,906.71 | Poor transfer and substantial underprediction |
| Retained versus category LSTM, common Wasaa subset | Retained WAPE80.35%; category candidate catastrophic extremes | Category replacement not supported |
| Retained IF, Wasaa consumption scenario |46 alerts /39,679 transactions | Alert behaviour only; this snapshot has no anomaly labels |

The mapped subset covers84.21% of recorded outflow amount. Missing categories,
merchant signals and assumed complete weeks limit equivalence with R3. Results
were not clipped or retuned; the largest category forecast was independently
reproduced using the original feature equations and inverse transform.

Wasaa was accepted as evaluation evidence. The evidence did not support promoting
the candidate models into the existing pilot. The retained model's relative
advantage does not mean reliable cross-population forecasting was demonstrated.
Budget-overrun association is not a substitute for anomaly ground truth.

Later notebooks train new models on a298,536-row Wasaa export with17 categories
and label columns. Their saved in-domain and constructed-injection results are
separate experiments. They must not be combined with this original frozen transfer
test or used to retroactively label the original snapshot.

## 5. Testing approach and results

Testing separates software correctness, artifact compatibility and model quality.
Backend fixture tests validate API boundaries, input handling and owner isolation.
Widget/controller tests cover UI and state logic. Artifact parity checks compare
trained-model predictions with the serving representation. Held-out and external
model evaluations measure performance under their explicitly recorded protocols.

For the current documentation baseline,70 backend/rule/advisor tests and11 subtests
passed in an isolated environment. Backend inference was faked in this gate;
the two real-model suites were explicitly excluded. Historical selected-release,
Flutter and actual artifact checks are listed separately in the evidence matrix.
They are not relabelled as current device or production tests.

The deployed pilot has recorded synthetic Samsung smoke evidence for navigation,
forecast/history confirmation, linked alert editor opening and intentional review.
Complete native CRUD/import/budget/OAuth/recovery coverage remains unresolved in
#22. During the preceding documentation check, health/model-info returned HTTP503.
An existing deployment is therefore distinguished from presently verified uptime.

## 6. Limitations

- Both datasets are synthetic; representative real-user performance remains unknown.
- Reused validation, different fitting periods and category targets constrain
  model-to-model comparisons; not every reported metric comes from the same rows.
- The original V7 final validation export and earlier category development
  checkpoint were not recovered. Available later artifacts are separately attributed.
- The tested Wasaa snapshot lacks native anomaly labels and merchant identities.
- Later model notebooks have different dataset versions and constructed evaluation
  designs; their higher numbers are not proof of improved transfer.
- Device, hosted-resource/database and external service authorization checks have
  gaps. Local fixture success does not establish production acceptance.
- Delivery/feedback accounting exists, but simulated decisions do not establish
  actual household acceptance or realized savings.

## 7. Conclusion

Spendly demonstrates an implemented personal-finance pilot and a reproducible
model-evaluation process. The research supports retaining the established pilot
artifacts with explicit limitations rather than replacing them on the basis of
incomparable or unstable results. External Wasaa testing contributed a negative
transfer finding, which remains part of the submitted evidence. The remaining
submission work is requirements traceability, required document formatting and
targeted acceptance evidence, not another automatic model-training cycle.

## Supporting documents

- [Requirement-to-evidence matrix](submission_evidence.md)
- [Wasaa testing and model decision](wasaa_testing_and_model_decision.md)
- [R3 LSTM experiments](../model_research/V9_RESULTS.md)
- [Final R3 Isolation Forest evaluation](../model_research/IF_SUBMISSION_RESULTS.md)
- [Full Wasaa transfer results](../model_research/WASAA_TRANSFER_RESULTS.md)
- [Advisor service contract and feedback](../services/spend_advisor/README.md)
