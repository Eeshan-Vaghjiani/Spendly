# Spendly acceptance status

Updated **7 November 2026**. Current recorded private release: API **1.4.1**, Android
**1.4.1+15**. Use this index for current app completion; older release/evidence
files retain their original dates. The approved SRS and assessment rubric remain
the authority for academic completion.

The fresh [release review](evidence/release_review_2026_10_26.md) passed analyzer,
179 Flutter tests (one opt-in live test skipped), 216 backend/rule tests and 18
admin JavaScript tests. The live health retry succeeded after one 30-second
timeout. No current automated regression requires a new app version. The owner
confirmed successful phone installation on 26 October; #102 is closed.
The original failure cause remains unknown, and this is owner-reported evidence.

The subsequent [CSV recovery work](evidence/csv_recovery_2026_10_26.md) adds a
repeatable native interruption runner. Its fresh offline gate passed analyzer,
179 Flutter tests (one intentional live skip) and 217 backend/rule tests.

30 October follow-up: settings search/grouping and a direct Transactions-to-sync
shortcut are implemented for reviewed source integration in #107. The current Flutter gate passed
**187 tests, one intentional live-backend skip**, and analyzer was clean; see
[dated evidence](evidence/settings_search_2026_10_30.md). The owner also reports slow
sync #105 and a new Google Play/Play Protect installation block on friends' phones
#108; neither cause has been established. No new APK or server release was made.

2 November follow-up: a reproducible stale-status problem during manual M-PESA
sync is addressed on the task branch with bounded local-status observation and navigation guidance.
The final offline gate passed **196 Flutter tests (one live-backend skip)**,
**217 backend/rule tests**, **18 admin JavaScript tests**, and analyzer. See
[sync progress evidence](evidence/sync_progress_2026_11_02.md). This is not a measured
speed improvement or native recovery result; #105 remains open. No Android device
was connected during device discovery, and no APK or deployment was changed.

3 November review: #110, #111 and #113 are merged into `main`; there are no open
PRs. #105 and #112 are closed on GitHub, but closing #105 did not supply the
missing native performance/recovery measurements. A local follow-up fixes stale
counts after reopening active SMS settings without starting another import.
Its fresh gate passed analyzer, **200 Flutter tests (one intentional live skip)**,
**223 backend/rule tests** and **18 admin JavaScript tests**; independent code
review found no required changes. These are offline checks, not native acceptance.
See the [completion review](evidence/completion_review_2026_11_03.md) for the
remaining issue decisions, fresh checks and source-versus-release boundary.

Later 3 November follow-up: actual isolated Chrome **200%/400% browser zoom**
checks completed on the synthetic loopback admin. Focus-contrast and narrow-nav
wrapping defects were fixed with three regressions; see
[browser/board evidence](evidence/admin_zoom_2026_11_03.md). Actual screen-reader
speech/announcements remain unverified. The existing APK's hash, signature,
alignment and SMS declarations were freshly checked; see
[Play Protect investigation](evidence/apk_play_protect_2026_11_03.md). No affected
phone was connected and no replacement APK, appeal or deployment was produced.

Owner disposition, later 3 November: the remaining untested screen-reader/admin
accessibility limits are **owner-accepted for the private prototype** (#82), not
a newly passed test. The owner clarified #108 as the ordinary outside-Play-Store
installation notice and requested closure, not a confirmed harmful-app block.
Wasaa access is explicitly still ungranted; #95 remains waiting/blocked. See the
[decision record](evidence/owner_acceptance_2026_11_03.md) for the precise scope,
unverified checks and safe handling of any genuinely different warning.

7 November scope reconciliation: the category-model comparison #38 is complete
through the existing merged #43/#46 evidence; the missing historical development
checkpoint remains an archival limitation. Optional proposals #4/#61 and public
distribution #89 are closed as **not planned for this private delivery**, not as
successful experiments or public approval. No models, policy, release, or existing
research results changed. The separate U-CS38 advisor source was submitted in
[upstream PR #1](https://github.com/ApexTechHorizon/strathmore-skeleton/pull/1)
and is still open for maintainer review. See the
[issue disposition record](evidence/issue_closeout_2026_11_07.md) for scope and checks.

## Next work, in order

| Priority | Item | Next concrete action | Completion boundary |
|---|---|---|---|
| Done | Phone installation #102 | Owner confirmed installation works on 26 October | Failure cause unknown; not a new independently observed device test |
| Done (owner clarification) | APK notice #108 | Owner clarified the ordinary outside-Play-Store notice and accepted closure | Not an independently observed warning/installation retest; keep Play Protect enabled and reopen for a harmful-app/sensitive-data block |
| Evidence outstanding (issue closed) | Sync reliability #105 | Retain the unmeasured timing/recovery gap; reproduce on synthetic data if this work is resumed | #111 is merged; neither progress feedback nor issue closure establishes faster import or affected-phone recovery |
| Done (source) | Searchable settings #107 | Merged through #110; actual keyboard/TalkBack and relevant device navigation stay in #22 | Source integration is not a new APK release or installation for users |
| 2 | Android acceptance #22 | CSV provider/process interruption and acceptance-app authenticated in-place reinstall passed on the named emulator; finish current-binary physical OAuth and device accessibility/radio/recovery checks | Emulator debug acceptance is distinct from signed-release/physical-device coverage |
| Done (owner acceptance) | Admin accessibility #82 | Existing zoom/focus/reflow work complete; remaining untested limits accepted by owner for the private prototype | Spoken screen-reader, full keyboard-only/reverse traversal and announcements were not tested; no invented pass or public/institutional certification |
| 4 | Privacy review #81 | Owner/institution records retention, support-access and re-consent decisions | Engineering checks cannot supply institutional approval or re-date acceptance |
| 5 | Project report #11 | Map this matrix and the full model/features handoff to approved SRS clauses and institutional template; capture required genuine screenshots | Template, approved numbering, deadline and supervisor review are not established |
| Closed (not planned) | Public M-PESA release #89 | Excluded from the current private delivery; reopen if public publication is chosen | Policy, permission/distribution and physical-device gates are still required; no public approval claimed |
| Blocked (owner-confirmed wait) | Wasaa import #95 | Access is not yet granted; await key, complete contract, test identity and verified ownership-link design | No live import is implemented or authenticated access claimed |
| Done (existing comparison) | Category model #38 | Existing #43 comparison and #46 decision complete; retain the established model | Missing earlier development artifacts were not recovered and no new run was performed |
| Closed (not planned) | Model proposals #4, #61 | Excluded from this delivery; reopen only with a separate frozen research protocol | No new experiment, confirmation score, training or model replacement claimed |

Oracle preparation #106 is optional and awaits owner entitlement/shared-host and
security readiness. Neither an Oracle move nor additional model experiments are
required to close the current private project's existing engineering/report scope.

2 November native follow-up: the guarded API 36 emulator CSV suite completed
process-death/session restoration without unsolicited upload, explicit import
retry, DocumentsUI interruption/duplicate retry and authenticated in-place
reinstall of the separate acceptance app. A one-line runner correction fixes
false-negative leaf-control detection; focused tests passed **7/7**, and the
backend/rule gate passed **223 tests**. See
[dated evidence](evidence/csv_recovery_2026_11_02.md). These results are not
physical-device or signed-production-binary acceptance. No release changed.
Sync-feedback PR #111 and CSV recovery PR #113 are now merged into `main`.
Their source integration did not change the deployed API or signed APK.

## Application evidence matrix

These `APP-*` labels are drafting aids, **not approved SRS numbers**. Add the real
clause numbers when provided. Test files identify reproducible coverage, not a
claim that every scenario below was exercised on a physical phone.

| ID / area | Implementation and repeatable evidence | Remaining limit |
|---|---|---|
| APP-01 Authentication | [Auth API tests](../backend/tests/test_auth.py); [native acceptance](../mobile/integration_test/native_acceptance_test.dart) | Fresh physical Google success/cancel/failure for 1.4.1+15 |
| APP-02 Consent and privacy | [Privacy summary evidence](evidence/privacy_summary_2026_10_20.md); [policy implementation](security_and_privacy.md) | Owner/institution retention and re-consent decision |
| APP-03 Transactions and ownership | [Transaction API tests](../backend/tests/test_transactions.py); [native finance evidence](evidence/android_finance_2026_10_23.md) | Physical device/OEM coverage; no unrestricted cross-account access implied |
| APP-04 CSV import | [Upload widget tests](../mobile/test/transaction_upload_test.dart); [release CSV acceptance](release_1_4_1.md); [native recovery](evidence/csv_recovery_2026_11_02.md) | API 36 acceptance-app process/provider interruption and retry passed; other OEM/physical providers and signed-release checks remain distinct |
| APP-05 Budgets | [Budget API tests](../backend/tests/test_budgets.py); [native finance evidence](evidence/android_finance_2026_10_23.md) | Device radio/accessibility coverage |
| APP-06 Dashboard and analytics | [Analytics API tests](../backend/tests/test_analytics_admin.py); [UI evidence](evidence/ui_polish_2026_10_23.md) | Recorded totals are not a wallet balance or model accuracy score |
| APP-07 Forecast | [Selected registry tests](../backend/tests/test_selected_registry.py); [forecast wording tests](../mobile/test/forecast_wording_test.dart) | Eight complete preceding weeks; cold start/coverage is not statistical confidence |
| APP-08 Alerts and review | [Alert API tests](../backend/tests/test_alert_review.py); [mobile alert tests](../mobile/test/alert_review_test.dart) | Reviewable unusual spending, not fraud; complete device edit/rescore/deleted-entry acceptance |
| APP-09 Recommendations | [Recommendation rules](../services/recommendation_engine/rules.py) and their test suite | No real-user savings/adoption study or autonomous financial advice claim |
| APP-10 Account switching/storage | [Isolation tests](../mobile/test/analysis_isolation_test.dart); [authenticated acceptance-app in-place reinstall](evidence/csv_recovery_2026_11_02.md) | Recovery across interrupted installation/rollback or after uninstall/data clear is not established |
| APP-11 M-PESA SMS | [Import contract and exact parser scope](mpesa_sms_import.md); [API tests](../backend/tests/test_mpesa_import.py) | Private opt-in release; personal inbox and public distribution not certified |
| APP-12 Transaction origin | [Source icon](../mobile/lib/presentation/widgets/transaction_source_icon.dart); [UI evidence](evidence/ui_polish_2026_10_23.md) | Origin survives editing; it does not authenticate edited values. Wasaa origin not implemented |
| APP-13 Admin management | [Admin capabilities](admin_management.md); [actual zoom/focus evidence](evidence/admin_zoom_2026_11_03.md); [admin API tests](../backend/tests/test_admin_management.py); [owner acceptance](evidence/owner_acceptance_2026_11_03.md) | Untested screen-reader/announcements/full keyboard limits owner-accepted for private scope, not passed or publicly certified |
| APP-14 Release/install | [APK identity](release_1_4_1.md); [installation guide](android_installation.md); [owner clarification](evidence/owner_acceptance_2026_11_03.md) | #102 owner-resolved; #108 clarified as ordinary outside-store notice. No new independent affected-phone retest |
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
- Main's application baseline was reconciled with the private release
  lineage through #109, preserving its research sources.
  Historical evidence still belongs to the revision and binary it tested.
- The owner's 30 October instruction is feature -> reviewed PR -> main, with
  the deployment branch held until separate approval; see
  [the Git workflow](git_workflow.md). Source/documentation merges do not release
  an APK or authorize hosted changes, migrations or production redeployment.

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
