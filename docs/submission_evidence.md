# Submission evidence and requirements traceability

## Scope and status

This is the repository-backed submission evidence index for Spendly. It combines
the deployed Android pilot and R3/Wasaa model research. The separate advisor
service is an optional prototype: the owner confirmed Wasaa dataset evaluation
and reporting only on 20 October 2026. It is not a signed-off academic SRS or
proof that every native flow passed.

The approved SRS, numbered assessment requirements and final report document were
not found in the repository. The `EV-*` identifiers below are review identifiers,
**not invented SRS numbers**. Match them to the approved requirements before final
submission. Applicable institutional templates and the submission date still need
confirmation in #11.

## Source baselines

| Baseline | Source | What it establishes |
|---|---|---|
| Submission/research | `main` at `fd63a36` | Merged research, advisor implementation and Wasaa decision documentation |
| Mobile pilot release | `agent/spendly-live-deployment` at `60e3bd0` | Mobile 1.3.2+7 and selected-model/alert-review release lineage |
| Core selected serving change | `b186a3f` | Portable selected LSTM/IF, history confirmation and transaction-linked alert review |
| Navigation patch | `47689de` | Menu on all main tabs |
| Wording/version patch | `60e3bd0` | Runtime package version and recorded-actual forecast wording |

The two branches are not interchangeable. `main` retains older application code
in some paths; do not cite its V1 model routes as the selected pilot implementation.
Release-only evidence below uses immutable links to `60e3bd0`. No branch merge,
application deployment or model replacement is part of this documentation task.

## Latest scoped evidence (20 October 2026)

The source table above preserves the earlier documentation baseline. The latest
backend/admin release is API **1.3.5**, revision
`d857d0015b4b406b31998bf00a338a51d0bcc4ec`; see
[pinned admin activity acceptance](https://github.com/Eeshan-Vaghjiani/Spendly/blob/d857d0015b4b406b31998bf00a338a51d0bcc4ec/docs/evidence/admin_activity_2026_10_20/README.md).
Its recorded checks were 173 backend/rule tests, five Node tests, 67 Flutter
tests passed/one opt-in live skipped, analyzer clear, synthetic browser acceptance
and disposable PostgreSQL 16.15 upgrade/backup/restore. Public health was healthy
at 06:46 UTC; this supersedes the earlier 503 observation below. Admin #60/#70
are complete. These release checks were not rerun on this research branch.

The unchanged Android 1.3.4+9 candidate remains unpublished pending the scoped
native release checks in #22/#56. See [pinned Android acceptance](https://github.com/Eeshan-Vaghjiani/Spendly/blob/d857d0015b4b406b31998bf00a338a51d0bcc4ec/docs/evidence/android_2026_10_20.md)
and [candidate identity](https://github.com/Eeshan-Vaghjiani/Spendly/blob/d857d0015b4b406b31998bf00a338a51d0bcc4ec/docs/evidence/android_release_candidate_2026_10_20.md).

The current Wasaa-only check revalidated the local snapshot and saved outputs:
five result hashes, 1,500 checkpoints, sixteen metric records and eight passing
evaluator/audit tests. No training, new model inference or notebook execution.
See [verification JSON](../model_research/evidence/wasaa_transfer/verification_2026_10_20.json).

## Evidence matrix

Status refers to the stated scope, not whole-project completion. Automated test
names are reproducible identifiers, not claims of native execution.

| ID / requirement area | Implementation and evidence | Verification / limitations | Status |
|---|---|---|---|
| EV-01 Registration and authentication | `backend/tests/test_auth.py`: `test_register_login_and_me`, `test_invalid_login_does_not_reveal_account_state`, `test_protected_route_requires_token` | Local Flask tests; real native OAuth is not established by mocked Google verification | Automated backend evidence |
| EV-02 Required consent and optional training choice | `test_registration_requires_service_and_privacy_acceptance`, `test_existing_user_is_blocked_until_required_consent_is_recorded` in `backend/tests/test_auth.py`; `docs/security_and_privacy.md` | Tests use synthetic accounts. No automatic training or new privacy compliance sign-off | Automated backend evidence |
| EV-03 Income/expense CRUD and ownership | `backend/tests/test_transactions.py`: `test_create_list_and_delete_transaction`, `test_update_transaction_revalidates_and_persists_changes`, `test_user_cannot_delete_another_users_transaction` | Fresh backend checks passed; complete native edit/save/delete remains #22 | Backend complete; device gaps |
| EV-04 CSV import validation | `test_csv_upload_reports_created_duplicate_and_invalid_rows`, `test_csv_upload_rejects_missing_headers` in `backend/tests/test_transactions.py` | Covers backend parsing; native picker/import flow still needs documented device evidence | Backend complete; device gaps |
| EV-05 Budget management | `backend/tests/test_budgets.py`: `test_create_list_update_and_delete_budget`, `test_budget_date_validation` | Backend fixture database; native budget CRUD not fully signed off | Backend complete; device gaps |
| EV-06 Cash-flow analytics | `backend/tests/test_analytics_admin.py`: `test_cashflow_analytics_reports_balance_and_series`, `test_cashflow_analytics_rejects_unknown_resolution` | Synthetic backend calculations; filters/large-text/offline UI review remains #22 | Automated backend evidence |
| EV-07 Fixed-week selected forecast | [Release registry tests](https://github.com/Eeshan-Vaghjiani/Spendly/blob/60e3bd0/backend/tests/test_selected_registry.py): `test_selected_path_requires_confirmation_and_never_calls_linear`, `test_actual_portable_backend_without_tensorflow` | Explicit history confirmation, selected method and real numeric-artifact route. Historical release checks; not rerun in this main-branch gate | Release/artifact evidence |
| EV-08 Reviewable unusual-spending alerts | [Release alert tests](https://github.com/Eeshan-Vaghjiani/Spendly/blob/60e3bd0/backend/tests/test_alert_review.py): `test_alert_links_owner_transaction_and_context`, `test_intentional_review_preserves_spend_and_changes_advice`, `test_edit_invalidates_intentional_confirmation`, `test_recurrence_edit_and_delete_review_cleanup` | Owner checks, preserved totals, stale-review409 and mutation invalidation. Synthetic native open/confirm checked historically; save/rescore still #22 | Release evidence; device gaps |
| EV-09 Account-safe UI and navigation | [Release mobile tests](https://github.com/Eeshan-Vaghjiani/Spendly/tree/60e3bd0/mobile/test): `analysis_isolation_test.dart`, `quick_access_drawer_test.dart`, `forecast_wording_test.dart` | Earlier gate 41 passed/1 skip; latest recorded release gate 67 passed/1 skip, analyzer clear; no fresh Flutter gate in this task | Historical mobile evidence |
| EV-10 Forecast model selection and limitations | `model_research/V7_KAGGLE_RESULTS_REVIEW.md`, `V8_RESULTS.md`, `V9_RESULTS.md`, `LSTM_IMPROVEMENT_REVIEW.md` | Retain V6; no material gain established. WAPE is not classification accuracy; repeated development data acknowledged | Research documented |
| EV-11 IF final evaluation | `model_research/IF_SUBMISSION_PROTOCOL.md`, `IF_SUBMISSION_RESULTS.md`, `if_submission_lock.json`, `evidence/if_submission/` | Frozen standard/shifted synthetic tests; F1 .6655/.6141, historical80% aspiration unmet | Research complete |
| EV-12 External transfer testing and non-promotion | [Testing decision](wasaa_testing_and_model_decision.md); `model_research/WASAA_TRANSFER_RESULTS.md`, `Wasaa_Model_Results.ipynb`, `evidence/wasaa_transfer/` | Frozen original snapshot, explicit scenarios. Poor LSTM transfer; IF detection metrics unavailable for that snapshot. Newer labelled export is separate | Evaluation documented |
| EV-13 Exact recommendation HTTP contract | `services/spend_advisor/test_contract.py`: `test_contract_decimal_cap_and_deterministic_targets`, `test_bad_request`, `test_household_scope_missing_and_empty`, `test_exact_large_money_json` | `/health`, `/recommendations`, max3, Decimal gaps and target IDs. Retrospective baseline, not an ML saving forecast | Optional local contract complete |
| EV-14 Persistent feedback and acceptance accounting | `services/spend_advisor/test_feedback.py`: `test_restart_retries_and_unanswered_denominator`, `test_changed_offer_does_not_inherit_decision`, `test_display_is_explicit_and_latest_decision_wins`, `test_snapshot_change_preserves_identity_blocks_old_worker` | SQLite restart/retry/version coverage. Fixture acceptance is not measured human adoption; external transport is outside confirmed submission scope | Optional prototype tested |
| EV-15 Service authorization | `test_auth_and_health` and `test_endpoint_contract_auth_and_no_cache` in advisor tests; `services/spend_advisor/README.md` | Service key protects callers; external platform must authorize requested household. Platform-side identity enforcement not verified here | Optional; external integration unverified |
| EV-16 Deployment and operations | [Pilot release record](https://github.com/Eeshan-Vaghjiani/Spendly/blob/60e3bd0/docs/release_1_3_0.md); #22; `docs/live_deployment_and_tester_apk.md` | APK update/install and previous selected backend health recorded. Earlier checks returned 503; latest recorded API 1.3.5 health was healthy, disposable PostgreSQL checks passed; native/load gaps remain | Deployed; native/load QA gaps |
| EV-17 Separate Wasaa URL handoff | `services/spend_advisor/README.md`, #21/#31/#32 | Code exists on main; no deployed advisor URL/platform acknowledgement. Owner confirmed dataset/report only | Out of scope, not a submission blocker |
| EV-18 Reproducible report and final review | This index, `docs/submission_report.md`, model evidence links | Approved SRS numbering, final document integration, genuine synthetic screenshots and review sign-off still required | #11 in progress |

## Earlier documentation-baseline checks (historical)

On `docs/submission-evidence`, based on `fd63a36`:

```powershell
python -m pytest backend/tests services/recommendation_engine/tests services/spend_advisor --ignore=backend/tests/test_model_inference.py --ignore=backend/tests/test_vertical_slice_real.py -q -p no:cacheprovider
```

**70 tests and 11 subtests passed.** Backend fixtures use isolated in-memory SQLite
and a fake model registry. Advisor tests use synthetic CSV snapshots and temporary
SQLite ledgers. This gate does not reproduce model quality, hosted PostgreSQL/MySQL
behaviour, the selected release branch, native OAuth or device UI.

Historical evidence must remain labelled separately:

- Release backend/rules:110 passed; includes actual portable route checks.
- Release mobile:41 passed, one opt-in live test skipped; analyzer clear.
- Portable selected export:268 forecast windows/869 IF scores checked for parity.
- Wasaa evaluator/audit/notebook:8 tests; real CPU transfer run and saved-output audit.

Those numbers describe different scopes and dates. Do not add them into a single
"all tests passed" total or claim they were all rerun during report preparation.

## Artifact and illustration index

| Deliverable | Location / handling |
|---|---|
| Report draft | `docs/submission_report.md` |
| Wasaa method and decision | `docs/wasaa_testing_and_model_decision.md` |
| IF final figures | `model_research/evidence/if_submission/test_evaluation.png`, `test_shifted_evaluation.png` |
| Transfer tables | `model_research/evidence/wasaa_transfer/results.json`, `audit.json` |
| Final IF notebook | `model_research/Spendly_Final_Isolation_Forest_Submission.ipynb` |
| Wasaa result notebook | `model_research/Wasaa_Model_Results.ipynb` |
| Private frozen artifacts and row scores | Local `artifacts/candidates/`; hashes and aggregates in Git, not raw datasets or executable model binaries |
| Pilot APK | Earlier 1.3.2+7 record is historical; current unpublished candidate is 1.3.4+9 with pinned identity above |
| Device screenshots | Not collected in this task. Capture only approved synthetic accounts; do not use mock screenshots as actual execution evidence |

## Final hand-in checklist

- [ ] Supply the approved SRS and replace/map EV review IDs to its actual clauses.
- [ ] Transfer the draft into the required report format with correct references.
- [ ] Confirm the documentation checklist, due date and reviewer decisions.
- [ ] Capture required device evidence on synthetic accounts and resolve #22 availability.
- [x] Confirm Wasaa scope: dataset evaluation/report only; optional advisor handoff is excluded.
- [ ] Keep failed targets, missing artifacts and unverified checks explicitly documented.

No new training, deployment or app change is necessary merely to complete this
index. Outstanding acceptance checks should be executed only in their agreed scope.
