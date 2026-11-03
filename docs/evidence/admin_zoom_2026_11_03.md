# Admin zoom, focus and board follow-up — 3 November 2026

Related: #82, #108, #22 and #33. Source base: `main` at `e12e230`;
branch `test/admin-install-board-20261103`. This changes source, not the deployed
API or Android release. All browser records/accounts were invented fixtures.

## Actual browser method

- Chrome **156.0.8078.74**, Windows, a fresh isolated profile and owned browser
  process; no personal Chrome profile, hosted admin or real account was used.
- Existing `backend.scripts.run_admin_acceptance_backend` on **127.0.0.1:5058**,
  with in-memory SQLite, 25 synthetic accounts, 45 transactions and an initial
  budget. Saved portable artifacts load at startup; no new model evaluation.
- Node 24 built-in WebSocket/CDP drove real mouse/keyboard input and snapshots.
  A bounded Windows helper sent Chromium's native browser menu zoom commands
  (`IDC_ZOOM_NORMAL=38002`, `IDC_ZOOM_PLUS=38001`) only to the owned PID's single
  visible, unowned Chrome main window. No CSS zoom, pinch scale or viewport
  emulation was substituted for browser zoom.
- The browser window remained 1280 pixels wide. Measured DPR was **1 / 2 / 4**,
  CSS viewport width **1264 / 632 / 316**, height **805 / 402 / 201** at
  **100% / 200% / 400%**; `visualViewport.scale` remained **1**.

## Findings fixed

1. Management focus outline `#59ae99` had **2.645:1** contrast against white.
   It now uses existing primary `#176b5b`, **6.382:1** against white, also above
   3:1 on the tested mint/canvas surfaces. Sidebar outlines use `currentColor`.
2. Overview's amber outline had **2.017:1** contrast against its dark sidebar.
   Sidebar link outlines now follow their existing readable text colour; this
   also adapts to overview's white mobile sidebar rather than using a fixed pale
   colour that would disappear on white.
3. Narrow management navigation required horizontal scrolling at magnification.
   It now wraps, preserving the existing links/order and green/mint design.

Three dependency-free Node regressions failed before the relevant corrections.
The final admin Node suite passes **21 tests** (the prior 18 plus these three).
These are targeted CSS/contrast checks, not a claim of full WCAG certification.

## Browser coverage and limits

The actual browser checks exercise login, loaded overview, management, a selected
account, Add transaction and Add budget at each zoom level. Assertions cover no
**document-level** horizontal overflow, wrapped management navigation, exposed
Username/dialog names, and background buttons absent from the modal's exposed
accessibility tree. Transaction-dialog forward Tab samples verify control/outline
visibility, no background control receiving focus, and return to the opener on
Escape. The browser's BODY transition is recorded rather than misclassified as
a background button; subsequent Tab returns to dialog fields.

Screenshots were inspected, including 400% login/overview/navigation/both dialogs
and 200% selected-account content. Vertical scrolling and table-local horizontal
scrolling remain available. Viewport intersection checks do not establish that
every element is completely unobscured; this is bounded zoom/keyboard/AX evidence,
not an exhaustive page or assistive-technology usability audit. There was no
financial correction, export, deletion, analysis toggle or other admin mutation;
login/view auditing occurs only in the disposable in-memory fixture.

Actual screen-reader speech, reading order, live announcements, reverse traversal
and a full keyboard-only journey remain unverified. No global Narrator setting
was changed and no spoken-screen-reader result is claimed. **Keep #82 open.**

## Final verification and artifacts

| Check actually run | Result |
|---|---|
| Browser layout snapshots | **18 passed**: six page/dialog states at 100%/200%/400% |
| Navigation reflow assertions | **3 passed**: navigation scroll width does not exceed its client width |
| Transaction-dialog Tab samples | **54 recorded**: 51 dialog-control samples with visible outlines, three BODY transitions, no background control reached |
| AX names and Escape/opener return | Passed for the exercised Username/transaction/budget controls at all three zoom levels |
| Admin Node suite | **21 passed, 0 failed**; three new regressions |
| Lightweight backend/rule gate | **223 passed**, six existing Alembic warnings; SQLite/fake inference, real-model suites excluded |
| Independent read-only source review | No required changes; browser-harness review required bounded claims/verified cleanup, which this report preserves |
| Owned process/port cleanup | Fixture and Chrome main exited; backend 5058 and owned debugging port closed |

Final synthetic evidence is retained locally under approved temporary directory
`spendly-admin-browser-CSVjvd` (screenshots, `results.json`, `cleanup.json`).
All nine disposable Chrome profiles created during the attempts were removed
after shutdown; synthetic screenshots/results and the small helpers remain.
Results SHA-256: `064b1ab23065dcaf22cedbb047b7140bbd1a35f1605159e11bd7e91bd691f673`.
Cleanup SHA-256: `f38187d5a7822f0dc517b11bd228994d7d0309aabbcfc4480bc95afc7de6d351`.
The small temporary Node/PowerShell helpers are local acceptance scaffolding,
not a new product dependency or device integration suite.

Earlier harness attempts stopped on overstrict URL/focus/window assumptions;
these were not established product bugs. One later functional pass reported an
immediate port-close verification failure; an OS check found no listener and the
final bounded shutdown/port verification passed. No incomplete run is counted
as the final passing result.

Flutter/native tests were not repeated for these CSS/docs-only app changes;
the **200 Flutter passes / one intentional live skip** in #114 retain their
earlier source-gate scope. No signed APK, Play Protect scan/appeal, physical OAuth,
hosted/private account, persistent database, deployment or model change occurred.

## Kanban and milestones

The private Spendly project **6** had an obsolete README describing early V7
research. It now describes current delivery, source-versus-release boundaries,
blocked/deferred work and the actual milestone names. The unrelated project and
board visibility were not changed.

- Added missing merged PR #114 and marked it Done.
- Moved #11 from In review to blocked Backlog: missing SRS/template is not an
  active review. Moved device-blocked #22 from In progress to Backlog. #33 is the
  actively maintained In progress tracker.
- All **12 open issues** are represented; none is incorrectly Done. All **49**
  closed/merged cards were Done at the audit, for **61 cards** total before this
  follow-up PR is added. All open items now have P1/P2 priorities: six core
  acceptance/report items P1; six blocked-integration/optional/deferred items P2.
  Milestone membership was checked through issue queries, not solely cached
  summary counters: #89 remains an open deferred item in Public release.
- Completed research/admin milestones stay closed. Android acceptance and final
  submission remain open for real missing evidence/decisions; optional future
  models/public release remain explicitly deferred. No deadline was invented.

The separate [APK inspection](apk_play_protect_2026_11_03.md) confirms the local
release identity and actual SMS declarations, not a friend's warning or scan.
