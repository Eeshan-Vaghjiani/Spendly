# Spendly acceptance status

Updated **26 October 2026**. Current private release: API **1.4.1**, Android
**1.4.1+15**. Use this index for current app completion; older release/evidence
files retain their original dates. The approved SRS and assessment rubric remain
the authority for academic completion.

The fresh [release review](evidence/release_review_2026_10_26.md) passed analyzer,
179 Flutter tests (one opt-in live test skipped), 216 backend/rule tests and 18
admin JavaScript tests. The live health retry succeeded after one 30-second
timeout. No current automated regression requires a new app version. A reported
physical-phone installation failure remains unresolved.

## Next work, in order

| Priority | Item | Next concrete action | Completion boundary |
|---|---|---|---|
| 1 | Phone installation failure #102 | Obtain exact Android result and verify the received APK, device version/storage and existing package identity | Phone unavailable during the recorded investigation; no cause proven |
| 2 | Android acceptance #22 | Finish current-binary OAuth success/cancel/failure, CSV provider/process interruption, authenticated recovery and device accessibility/radio checks | Keep each native scenario separate; fake/widget tests cannot close these |
| 3 | Admin accessibility #82 | Check actual 200%/400% browser zoom and screen-reader navigation/announcements | 26 October computer-use attempt was blocked before interaction; earlier narrow viewports do not establish zoom |
| 4 | Privacy review #81 | Owner/institution records retention, support-access and re-consent decisions | Engineering checks cannot supply institutional approval or re-date acceptance |
| 5 | Project report #11 | Map this matrix and the full model/features handoff to approved SRS clauses and institutional template; capture required genuine screenshots | Template, approved numbering, deadline and supervisor review are not established |
| Deferred | Public M-PESA release #89 | Complete policy, distribution and physical-device gates if public publication is chosen | The current private educational importer is already implemented |
| Blocked | Wasaa import #95 | Await key, complete provider contract, test identity and verified ownership-link design | No live import is implemented; outside this turn's requested work |
| Deferred | Models #4, #38, #61 | Resume only after an explicit separate research decision | No new training/model replacement is needed to finish the current engineering report |

## Application evidence matrix

These `APP-*` labels are drafting aids, **not approved SRS numbers**. Add the real
clause numbers when provided. Test files identify reproducible coverage, not a
claim that every scenario below was exercised on a physical phone.

| ID / area | Implementation and repeatable evidence | Remaining limit |
|---|---|---|
| APP-01 Authentication | [Auth API tests](../backend/tests/test_auth.py); [native acceptance](../mobile/integration_test/native_acceptance_test.dart) | Fresh physical Google success/cancel/failure for 1.4.1+15 |
| APP-02 Consent and privacy | [Privacy summary evidence](evidence/privacy_summary_2026_10_20.md); [policy implementation](security_and_privacy.md) | Owner/institution retention and re-consent decision |
| APP-03 Transactions and ownership | [Transaction API tests](../backend/tests/test_transactions.py); [native finance evidence](evidence/android_finance_2026_10_23.md) | Physical device/OEM coverage; no unrestricted cross-account access implied |
| APP-04 CSV import | [Upload widget tests](../mobile/test/transaction_upload_test.dart); [release CSV acceptance](release_1_4_1.md) | Actual picker cancel/import/recovery passed; process-death/provider interruption remains distinct |
| APP-05 Budgets | [Budget API tests](../backend/tests/test_budgets.py); [native finance evidence](evidence/android_finance_2026_10_23.md) | Device radio/accessibility coverage |
| APP-06 Dashboard and analytics | [Analytics API tests](../backend/tests/test_analytics_admin.py); [UI evidence](evidence/ui_polish_2026_10_23.md) | Recorded totals are not a wallet balance or model accuracy score |
| APP-07 Forecast | [Selected registry tests](../backend/tests/test_selected_registry.py); [forecast wording tests](../mobile/test/forecast_wording_test.dart) | Eight complete preceding weeks; cold start/coverage is not statistical confidence |
| APP-08 Alerts and review | [Alert API tests](../backend/tests/test_alert_review.py); [mobile alert tests](../mobile/test/alert_review_test.dart) | Reviewable unusual spending, not fraud; complete device edit/rescore/deleted-entry acceptance |
| APP-09 Recommendations | [Recommendation rules](../services/recommendation_engine/rules.py) and their test suite | No real-user savings/adoption study or autonomous financial advice claim |
| APP-10 Account switching/storage | [Isolation tests](../mobile/test/analysis_isolation_test.dart); [native acceptance](../mobile/integration_test/native_acceptance_test.dart) | Authenticated recovery across installation failure/rollback still unverified |
| APP-11 M-PESA SMS | [Import contract and exact parser scope](mpesa_sms_import.md); [API tests](../backend/tests/test_mpesa_import.py) | Private opt-in release; personal inbox and public distribution not certified |
| APP-12 Transaction origin | [Source icon](../mobile/lib/presentation/widgets/transaction_source_icon.dart); [UI evidence](evidence/ui_polish_2026_10_23.md) | Origin survives editing; it does not authenticate edited values. Wasaa origin not implemented |
| APP-13 Admin management | [Admin capabilities](admin_management.md); [browser evidence](evidence/admin_browser_2026_10_23.md); [admin API tests](../backend/tests/test_admin_management.py) | Actual zoom and assistive-technology review outstanding |
| APP-14 Release/install | [APK identity](release_1_4_1.md); [installation guide and investigation](android_installation.md) | Phone failure remains open; emulator install success is narrower evidence |
| APP-15 Model evaluation | Full existing model handoff, saved research results and immutable model identities | No training or new predictive metrics from UI/SMS/import work |
| APP-16 Wasaa integration | [Issue #95](https://github.com/Eeshan-Vaghjiani/Spendly/issues/95) | Planned, not delivered; completed offline dataset evaluation is separate |

## Submission material ready to use

- The comprehensive local `Spendly_Full_Project_Report_Handoff_2026_10_20.md`
  was updated on 23 October with current features, M-PESA flow, proposed Wasaa
  design, seven Mermaid diagrams and documentation-change guidance. All 16 JSON
  model-evidence blocks were preserved. It is a source handoff, not institutional
  sign-off or the final formatted report.
- Use the [demonstration checklist](final_demo_checklist.md) to capture genuine
  synthetic-data evidence. Screen mockups are design illustrations, not proof
  of a successful app execution.
- Research/submission documents on `main` and the deployed application lineage
  are not interchangeable. The current app comes through `staging` and
  `agent/spendly-live-deployment`; do not merge old app files from `main` merely
  to obtain its research documents. Cite the appropriate revision for each.
- Feature → staging → deployment promotion is documented in
  [the Git workflow](git_workflow.md). Documentation-only acceptance updates do
  not require an APK rebuild or production redeployment.

## Remaining policy decisions to document

For #81, record the responsible project owner, who can use the admin account,
retention periods for financial rows/SMS source identities/sign-in history/admin
audit, the export/deletion process, and whether the institution requires revised
terms and new explicit consent. Current behavior is documented in
[security and privacy](security_and_privacy.md) and [SMS retention](mpesa_sms_import.md).
Leave decisions blank until approved; a tested purge command is not permission
to run it against live data.

There is no basis to close all remaining issues today. Close a task when its
specific acceptance evidence exists, defer optional future scope explicitly,
and retain missing device/access/approval work without inventing a due date.
