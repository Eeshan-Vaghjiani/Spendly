# Issue disposition and submission index reconciliation — 7 November 2026

## Purpose and boundary

Separate completed work and optional future proposals from the active private
delivery queue. This is documentation and issue triage, not a new app release,
model experiment, institutional approval, or physical-device test result.
The recorded private release remains API **1.4.1** / Android **1.4.1+15**.

The repository owner requested one batch of PR/issue closeout. Existing merged
evidence and explicit private-delivery scope determine the dispositions below.
No missing test result is inferred from the request to tidy the repository.

## Dispositions

| Issue | Disposition | Basis and remaining limit |
|---|---|---|
| [#38 Category LSTM comparison](https://github.com/Eeshan-Vaghjiani/Spendly/issues/38) | Close completed for the comparison/archival disposition | The final-refit candidate was actually compared on matched external targets in merged [#43](https://github.com/Eeshan-Vaghjiani/Spendly/pull/43), and the non-promotion decision is documented in merged [#46](https://github.com/Eeshan-Vaghjiani/Spendly/pull/46). The earlier development checkpoint/scalers were not recovered; no reconstruction or new predictive score is claimed. |
| [#4 Repeat V7](https://github.com/Eeshan-Vaghjiani/Spendly/issues/4) | Close not planned for this delivery | Optional future experiment, already outside the submission path. Historical cohorts/results remain unchanged. Reopen only if a distinct protocol is approved; no consumed final data reuse. |
| [#61 New IF experiment](https://github.com/Eeshan-Vaghjiani/Spendly/issues/61) | Close not planned for this delivery | Retain the established model. Existing optimizer development and reload evidence are preserved, but independent confirmation and promotion were not performed. Reopen for a separately agreed frozen confirmation, not automatic activation. |
| [#89 Public SMS release](https://github.com/Eeshan-Vaghjiani/Spendly/issues/89) | Close not planned for this delivery | The importer is delivered for private educational use. Public publication is excluded, not approved. Reopen only if that scope is chosen and privacy, device, permission and distribution requirements are addressed. |
| [#22 Android acceptance](https://github.com/Eeshan-Vaghjiani/Spendly/issues/22) | Keep open | Current-binary physical OAuth, signed/current-device recovery, OEM/radio and matched native sync timing/recovery evidence remain separate from completed emulator checks. |
| [#81 Privacy and retention](https://github.com/Eeshan-Vaghjiani/Spendly/issues/81) | Keep open | Responsible operator, administration, per-record retention/export/deletion and policy/re-consent decisions need their actual owner/institution record. No policy or stored consent was changed. |
| [#11 Final report](https://github.com/Eeshan-Vaghjiani/Spendly/issues/11) | Keep open; evidence index improved | The SRS/template/date, genuine required screenshots and supervisor review cannot be supplied by changing issue state. This PR adds current source-handover references and distinguishes historical evidence. |
| [#33 Roadmap](https://github.com/Eeshan-Vaghjiani/Spendly/issues/33) | Keep open | Aggregates the remaining acceptance, policy and report requirements; it is not complete while those remain. |
| [#95 Wasaa import](https://github.com/Eeshan-Vaghjiani/Spendly/issues/95) | Leave open/blocked | Owner requested waiting. Provider access, contract, test identity and ownership link remain prerequisites; no provider probe or data read was performed. |
| [#106 Oracle preparation](https://github.com/Eeshan-Vaghjiani/Spendly/issues/106) | Leave open/blocked | Owner requested waiting. No host access, entitlement/billing check, benchmark, database change or deployment was performed. |

Closing a proposal as not planned means it is not part of this delivery; it does
not mark its unchecked acceptance criteria as passed. Preserve the original issue
bodies and historical negative findings. These optional items may be reopened
with their own inputs and approval rather than fabricated completion evidence.

## Report evidence now indexed

The U-CS38 source handover is
[upstream PR #1](https://github.com/ApexTechHorizon/strathmore-skeleton/pull/1),
commit `3eff9e903aa930952206a2b7a05948c196f6d419`. Its state was checked as **open**,
not merged. The advisor implementation, run/QA documentation, synthetic demo,
recommendation JSON and acceptance accounting are source-delivery evidence.
The [fork CI run](https://github.com/Eeshan-Vaghjiani/strathmore-skeleton/actions/runs/42166502618)
belongs to that separate project. No advisor test counts are reclassified as
fresh Spendly tests. Authenticated Wasaa import #95 is a different requirement.

See the updated [report draft](../submission_report.md),
[submission matrix](../submission_evidence.md),
[completion checklist](../is_completion_checklist.md) and
[acceptance index](../acceptance_status.md). Earlier tables retain their dated
revision/binary limitations; this PR does not overwrite historical model evidence.

## Verification for this batch

- Read the ten open issues, the current main acceptance documents, and the category
  model comparison/decision documents. GitHub confirms #43 and #46 are merged.
- Verified U-CS38 upstream PR #1 remains open at the source commit above.
- Checked **83 repository-relative file links across six Markdown files** and
  whitespace/diff; all passed.
- Confirmed the change set is limited to Markdown; no research result, model artifact,
  application code, policy value, signing identity or deployment configuration changed.

No new app/backend tests, real-model inference, notebook execution, device run,
hosted health probe or distribution was performed for this documentation-only PR.
Existing test results remain dated historical evidence, not newly rerun passes.
The original working tree and its unrelated changes were left intact; this work
uses a separate branch/worktree from main.
