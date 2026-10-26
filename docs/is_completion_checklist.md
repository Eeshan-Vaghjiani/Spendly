# IS project completion checklist

Updated 26 October 2026. Start with the [current acceptance status](acceptance_status.md)
for priorities, evidence mapping and remaining dependencies. Fresh analyzer,
179 Flutter passes/one intentional skip, 216 backend/rule passes and 18 admin
JavaScript passes are recorded in the [26 October review](evidence/release_review_2026_10_26.md).
The reported phone-installation failure remains unresolved; see the
[installation guide](android_installation.md). The private educational 1.4.1 release has a verified
Android 1.4.1+15 APK, including the approved UI, source indicators and refresh
fixes. See [release identity and checks](release_1_4_1.md); the deployment PR's
runtime evidence establishes which exact revision is live. Previous APKs remain preserved.
Wasaa dataset evaluation/report work is complete. The newly requested live
transaction import (#95) is a separate, paused integration awaiting a server key,
API contract, synthetic test identity and verified account linking. The optional
advisor prototype's separate deployment remains outside scope.

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
| Accounts and consent | Existing API/widget tests; native synthetic login/logout checked; owner reached dashboard through Google on signed 1.3.5+10 | Google cancellation/failure recovery and remaining lifecycle checks |
| Transaction management | CRUD API tests, synthetic native form/repeated-save/edit and actual CSV cancel/mixed/duplicate/invalid/recovery checks passed | Remaining native picker leave-screen/process-death checks |
| Budgets and analytics | Native synthetic budget CRUD/cancellation, all five analytics filters, real socket-failure error/retry and draft preservation passed; see [finance evidence](evidence/android_finance_2026_10_23.md) | Physical-device accessibility/radio-network coverage and native picker/provider lifecycle remain separate |
| Forecast | Selected LSTM active; package parity; dated week and history confirmation | Make coverage/limitations clear; verify stale/zero/missing-data behaviour end-to-end |
| Alerts | Linked transaction, explanatory context, confirmation flow tested | Verify edit-save/rescore and deleted-entry states on device; retain user decision history |
| Recommendations | Spendly rules react to confirmed spending | Map to the actual approved SRS; do not invent an external service requirement |
| Wasaa | Dataset/report complete; optional advisor prototype remains research | Live import #95 waits for credentials, contract and secure linking; no working feed claimed |
| Release | 1.4.1+15 integrity and emulator install/launch verified; 26 October analyzer/179 Flutter/216 backend/18 JS checks passed. Earlier JVM, CSV/SMS/PostgreSQL/finance evidence retains its date | Deployment 7278401307 succeeded; live health retry passed on 26 October after a timeout. Investigate reported phone installation; physical new-binary OAuth, TalkBack/radio/OEM and authenticated recovery remain open (#22) |
| Admin | Browser login, overview, management, narrow layouts, dialog scrolling and focus checks passed; 18 Node tests and 216 backend/rule tests in this review | Actual browser zoom and screen-reader review remain manual (#82); privacy/retention decision remains #81 |
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

The page/storage/CSV fixes #76–80 and late preference-response race #85 are
resolved. The controlled finance test found fast refresh errors in four screens
(#97); regressions and the corrected native run pass, and1.4.1 includes the fix.
Privacy wording is implemented; the owner/institution still needs to
review terms, retention and whether re-consent is required (#81). This is not
legal certification. See the [admin browser evidence](evidence/admin_browser_2026_10_23.md)
for the completed checks and remaining manual zoom coverage in #82.

Use the [demo checklist](final_demo_checklist.md) for a synthetic rehearsal.
Any source fix after the candidate's recorded revision needs a newly verified APK
before distribution; the approved UI is present in1.4.1+15 and absent from1.4.0+14.
