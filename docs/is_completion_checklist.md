# IS project completion checklist

Updated 20 October 2026. API 1.3.5 and admin sign-in activity are deployed;
synthetic admin acceptance and disposable PostgreSQL recovery checks passed.
Wasaa is **dataset evaluation and report only**, as confirmed by the owner.
The optional advisor prototype is preserved; its separate deployment and
feedback rollout are outside the submission scope (#9/#21/#31/#32 closed).

## Current assessment

Spendly has a working experimental app, deployed API and documented model comparisons.
This is a substantial IS project, but **complete** depends on the approved SRS and
assessment rubric, not feature count or one metric. Do not claim the whole project
is complete while integration/acceptance and untested native flows remain open.

## What the model evidence supports

- LSTM reference: synthetic reused-validation WAPE34.52%, MAE KES2616.88, within20%47%.
  This supports a labelled estimate, not a guaranteed budget or spending allowance.
- Single Isolation Forest: final standard synthetic test precision62.32%,
  recall71.39%, F1.6655; shifted-test F1.6141. The earlier development F1.7208
  is a different evaluation. Review, correction and intentional-spending feedback
  remain essential; alerts are not fraud findings.
- Frozen Wasaa transfer: retained LSTM consumption WAPE75.28%, R2 -0.5988;
  IF46 alerts among39,679 expenses, without labels to estimate detection accuracy.
  Later Wasaa-trained notebooks use different data and evaluation designs.
- V7–V9 comparisons did not justify replacing the reference. The portable runtime
  preserves trained-model predictions; it does not increase forecast accuracy.

## Required finishing work

| Area | Evidence/status | Remaining completion criterion |
|---|---|---|
| Accounts and consent | Existing API/widget tests; native synthetic login/logout checked | Native Google sign-in and documented failure/recovery checks |
| Transaction management | CRUD API tests and actual synthetic native form/repeated-save/edit checks passed | Actual native CSV picker/lifecycle and invalid/duplicate import/recovery acceptance |
| Budgets and analytics | Existing automated tests and UI | Native budget CRUD, filters, empty and offline states |
| Forecast | Selected LSTM active; package parity; dated week and history confirmation | Make coverage/limitations clear; verify stale/zero/missing-data behaviour end-to-end |
| Alerts | Linked transaction, explanatory context, confirmation flow tested | Verify edit-save/rescore and deleted-entry states on device; retain user decision history |
| Recommendations | Spendly rules react to confirmed spending | Map to the actual approved SRS; do not invent an external service requirement |
| Optional Wasaa advisor | Local contract/feedback prototype exists | Outside confirmed dataset/report scope; no deployment or real adoption claim |
| Release | Unpublished 1.3.4+9 candidate built and certificate verified; actual synthetic Android13 acceptance recorded | Remaining native OAuth/import/accessibility/offline and signed update/rollback in #22/#56 |
| Documentation | Research results and GitHub issues/milestones | Map approved SRS requirements to tests, complete applicable QA/design documents and supervisor review |

## New features: prioritize only what closes an actual gap

1. **Finish the approved SRS mapping and native acceptance** before adding scope.
   No separate advisor deployment or recommendation-acceptance study is required.
2. **Preserve recorded-actual-versus-estimate comparison** with missing-history caveats;
   do not call `100 - percentage error` model accuracy.
3. **Forecast/alert limitation and review states**, especially expensive or irregular
   spending and false-positive alerts.

Optional future experiments (not release prerequisites): planned-expense entry,
calibrated forecast intervals, targeted recurring-bill-change prompts. Each needs
real available inputs and an evaluation plan. More dashboards, an AI chatbot or
another model version do not automatically improve project completeness.

This checklist is an evidence-based proposal; the supervisor's approved SRS remains
the authority. No unsupported grade, production-readiness or real-user accuracy claim.

Use the [demo checklist](final_demo_checklist.md) for a synthetic rehearsal.
Any source fix after the candidate's recorded revision needs a newly verified APK
before distribution; it is not automatically present in the existing 1.3.4+9 binary.
