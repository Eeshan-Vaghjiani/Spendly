# IS project completion checklist

## Current assessment

Spendly has a working experimental app, deployed API and documented model comparisons.
This is a substantial IS project, but **complete** depends on the approved SRS and
assessment rubric, not feature count or one metric. Do not claim the whole project
is complete while integration/acceptance and untested native flows remain open.

## What the model evidence supports

- LSTM reference: synthetic reused-validation WAPE34.52%, MAE KES2616.88, within20%47%.
  This supports a labelled estimate, not a guaranteed budget or spending allowance.
- Single Isolation Forest: precision66.84%, recall78.21%, F1.7208 on reproduced R3
  development validation. Approximately one-third of alerts are false positives in
  that dataset. Review, correction and intentional-spending feedback are therefore
  essential; alerts are not fraud findings.
- V7–V9 comparisons did not justify replacing the reference. The portable runtime
  preserves trained-model predictions; it does not increase forecast accuracy.

## Required finishing work

| Area | Evidence/status | Remaining completion criterion |
|---|---|---|
| Accounts and consent | Existing API/widget tests; native synthetic login/logout checked | Native Google sign-in and documented failure/recovery checks |
| Transaction management | CRUD API tests; native list/edit navigation checked | Complete native add/edit/save/delete/import checks, duplicate/invalid import cases |
| Budgets and analytics | Existing automated tests and UI | Native budget CRUD, filters, empty and offline states |
| Forecast | Selected LSTM active; package parity; dated week and history confirmation | Make coverage/limitations clear; verify stale/zero/missing-data behaviour end-to-end |
| Alerts | Linked transaction, explanatory context, confirmation flow tested | Verify edit-save/rescore and deleted-entry states on device; retain user decision history |
| Recommendations | Rules react to confirmed spending | Match approved U-CS38 output and data source, not synthetic demo assumptions |
| U-CS38 service | Local contract/demo exists | Agree auth/upstream targets/ops-metrics feedback, persist issued advice and demonstrate measured accept rate |
| Release | APK signing/update and health checks | Finish #22, correct stale wording #23, retain model/APK backups and rollback instructions |
| Documentation | Research results and GitHub issues/milestones | Map approved SRS requirements to tests, complete applicable QA/design documents and supervisor review |

## New features: prioritize only what closes an actual gap

1. **Recommendation feedback with persistence and provenance** once team contracts
   are agreed. This directly supports the assigned acceptance-rate requirement.
2. **Clear recorded-actual-versus-estimate comparison** with missing-history caveats;
   do not call `100 - percentage error` model accuracy.
3. **Forecast/alert limitation and review states**, especially expensive or irregular
   spending and false-positive alerts.

Optional future experiments (not release prerequisites): planned-expense entry,
calibrated forecast intervals, targeted recurring-bill-change prompts. Each needs
real available inputs and an evaluation plan. More dashboards, an AI chatbot or
another model version do not automatically improve project completeness.

This checklist is an evidence-based proposal; the supervisor's approved SRS remains
the authority. No unsupported grade, production-readiness or real-user accuracy claim.
