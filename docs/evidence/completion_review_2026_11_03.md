# Pending-work review — 3 November 2026

Reviewed GitHub's 12 open issues, recent closed issues and open PRs against
`main` at `a408a18`. Work is isolated on `fix/pending-completion-20261103`;
the older dirty development checkout is unchanged. No open PRs remained at review.
The private release remains API **1.4.1** / Android **1.4.1+15**; merged source
is not a new release. No issue was edited, reopened or closed during the initial
local review. The owner subsequently authorized commits, PRs and milestone cleanup.

## Completed locally

- Reproduced reopened SMS settings retaining zero pending records despite a
  synthetic native snapshot containing 12: the regression failed before the fix.
- Extended the existing one-second local-status observer to active settings after
  refresh, enable and manual-sync completion. Reopening no longer needs another
  manual sync to keep counts current. Observation preserves busy/action-error state,
  follows native error/recovery snapshots,
  rejects canceled/old-generation reads, stops on inactive status and disposal,
  and retains account/session fences. It never enables import, reads SMS, calls
  the network or starts a native worker. Native parsing/batching/timeouts and the
  API contract are unchanged; this is **not a measured speed improvement**.
- Reconciled the acceptance index with merged #110/#111/#113 and closed
  #105/#112; corrected the demonstration checklist's obsolete installation gap.

## What is actually left

| Issue | Status / next required input | Can engineering finish it without that input? |
|---|---|---|
| #108 Play Protect | Exact sanitized warning, phone/Android, APK hash/source, fresh/update status; owner-approved distribution choice and affected-phone retest | No. Capability-off build support and diagnostic guidance already exist. Do not disable Play Protect, alter signing identity or promise a no-SMS build removes every warning. |
| #22 Android acceptance | Current-binary physical Google success/cancel/failure, signed authenticated recovery, TalkBack, radio and OEM background evidence | No physical device/test identity is available. The completed API-36 CSV recovery checks are not these checks. |
| #82 Admin accessibility | Actual browser zoom at 200%/400% and screen-reader navigation/announcements | Not completed here; a browser/assistive-technology session is still needed. Node/layout fixtures cannot substitute. |
| #81 Privacy | Responsible operator/admin access, retention for each record class, export/deletion handling and policy-version/re-consent decision | Owner/institution approval, not an implementation gap. Current retention/consent must remain unchanged. |
| #11 Final report | Approved SRS clauses, institutional template, deadline, genuine required screenshots and supervisor review | Existing evidence matrix/demo checklist can be used now; final approval and missing inputs cannot be invented. |
| #33 Roadmap | Track the preceding acceptance/report work | A tracking issue, not an additional feature to implement. |
| #95 Wasaa import | Complete provider contract/key configuration, dedicated synthetic identity and verified ownership-link agreement | No. Do not use a shared student key or user-entered ID as ownership proof, or expose the key in Flutter. |
| #106 Oracle | Owner billing/free-tier confirmation, shared-host security/operations agreement and deployment decision | Optional; no cutover or hosted mutation authorized. |
| #89 Public SMS release | #81, physical-device gates and permission/distribution approval | Explicitly deferred; private delivery is not public approval. |
| #4 / #38 / #61 Models | Explicit research-resumption decision; respective frozen-evaluation/archive prerequisites | Three deferred issues. No training, artifact replacement or promotion is needed for app completion. |

#105 was closed on 3 November, but its recorded evidence still lacks matched
scan/parse/persist/consent/upload/job/UI timings and native background/recovery
measurement on the affected workload. #111 fixes manual progress feedback; this
local follow-up fixes reopened status. Neither proves the reported slowness is
resolved. Keep that distinction even if the owner leaves the issue closed.

## Verification

| Fresh check | Result | Scope |
|---|---|---|
| Pre-fix reopened-status regression | Failed as expected: expected 12, actual 0 | Fake native status, no device/network |
| Native-error recovery regression before follow-up | Failed as expected: stale error remained after recovery | Fake native status |
| Focused SMS consent/progress/contract tests | 28 passed, 0 failed | Four added tests; strengthened active-result stale-snapshot regression |
| Final full Flutter offline suite (`--no-pub --concurrency=1`) | 200 passed, 1 intentional live-backend skip, 0 failed | Widget/unit fixtures; not native OAuth, actual SMS import or secure-storage/device acceptance |
| Final `flutter analyze --no-pub` | No issues | Current Flutter source |
| Backend/recommendation lightweight gate | 223 passed, 6 existing Alembic deprecation warnings | In-memory SQLite/fake inference; real-model suites excluded |
| Admin Node tests | 18 passed, 0 failed | JavaScript fixtures, not actual browser/assistive technology |
| Device discovery | Windows/Chrome/Edge only; no Android device | No emulator launched or native acceptance rerun |
| Independent read-only review, including final error handling | No required changes | Connected controller/platform/native/provider lifecycle reviewed; reviewer did not independently rerun Flutter tests |
| Documentation local-link self-check | 46 checked, none missing | Acceptance index, demonstration checklist and this report |
| `git diff --check` | Passed | No whitespace errors |

An initial full Flutter attempt reached 154 passes/one intentional live skip
before the shell's 120-second command limit interrupted it; this was not a test
assertion failure or a complete suite result. The final no-timeout run above passed.
Historical native/model evidence retains its original date; it was not rerun.

The reviewed change is prepared for a feature-branch PR to `main`, following
`docs/git_workflow.md` and the owner's subsequent publication instruction. Issue
and milestone updates must preserve the acceptance gaps above, including #105's
unmeasured native performance; no incomplete acceptance milestone should be closed.

No deployment, APK creation/signing/sharing, persistent database migration, live
account/inbox access or research execution was performed. Local dependency/build
caches remain in the worktree. No test service was launched.
