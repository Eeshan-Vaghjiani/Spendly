# IS project completion checklist

Updated 23 October 2026. The private educational release is API 1.4.0 and
Android 1.4.0+14. The approved UI changes are merged into staging in PR #94;
they still need separate release promotion and a replacement APK.
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
| Budgets and analytics | Automated tests; PR #94 native page tour and category summary on synthetic account | Full native budget CRUD/filter/offline acceptance beyond the page tour |
| Forecast | Selected LSTM active; package parity; dated week and history confirmation | Make coverage/limitations clear; verify stale/zero/missing-data behaviour end-to-end |
| Alerts | Linked transaction, explanatory context, confirmation flow tested | Verify edit-save/rescore and deleted-entry states on device; retain user decision history |
| Recommendations | Spendly rules react to confirmed spending | Map to the actual approved SRS; do not invent an external service requirement |
| Wasaa | Dataset/report complete; optional advisor prototype remains research | Live import #95 waits for credentials, contract and secure linking; no working feed claimed |
| Release | Private 1.4.0+14 built; SMS emulator and disposable PostgreSQL checks recorded in release notes. PR #94: 175 Flutter passes/one skip, 216 backend/rule passes, native thirteen-page200% text tour | Promote staging separately; verify new binary on physical device, OAuth cancellation, TalkBack/network loss and disposable rollback (#22/#56) |
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
resolved. Privacy wording is implemented; the owner/institution still needs to
review terms, retention and whether re-consent is required (#81). This is not
legal certification. See the [admin browser evidence](evidence/admin_browser_2026_10_23.md)
for the completed checks and remaining manual zoom coverage in #82.

Use the [demo checklist](final_demo_checklist.md) for a synthetic rehearsal.
Any source fix after the candidate's recorded revision needs a newly verified APK
before distribution; staging UI changes are not present in the existing 1.4.0+14 binary.
