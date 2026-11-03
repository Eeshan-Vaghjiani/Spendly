# Owner acceptance and warning clarification — 3 November 2026

Source base: `main` at `0ebaa09`, after merged #114/#115. The owner requested
closure of the screen-reader work, clarified that the reported APK message is
the usual warning about installing an app from outside the Play Store, and
confirmed that Wasaa access has not been granted and should remain waiting.

## Dispositions

| Item | Disposition | What this does not establish |
|---|---|---|
| #82 admin accessibility | Close on **owner acceptance of the remaining untested accessibility limitations** for the current private educational prototype. Implemented focus/reflow fixes, real 200%/400% Chrome zoom and bounded keyboard/AX evidence remain linked in #115. | No spoken screen-reader, live-announcement, reverse-traversal or complete keyboard-only test was run. Do not record an invented test pass or WCAG certification. |
| #108 APK warning | Close on **owner clarification/acceptance of the ordinary outside-Play-Store notice**, not a reproduced harmful-app or sensitive-data block. Local release identity/signature/integrity/alignment were already checked. | Exact warning text, the received binary and affected-phone behavior were not independently inspected or retested. The earlier SMS-permission hypothesis was not confirmed as this report's cause. |
| #95 Wasaa import | Keep **open/blocked**, waiting for provider access, full contract, test identity and secure ownership linking. Owner explicitly confirmed access is not yet granted. | No provider key, authenticated response, ownership proof or import implementation is supplied by this decision. No upstream probe is needed while waiting. |

The screen-reader acceptance is a recorded product-owner scope decision, not
institutional/legal approval or a public-distribution acceptance result. In #22,
record the same untested screen-reader limitation as owner-accepted for the
private prototype; physical OAuth/recovery/radio/OEM and native sync timing
gaps remain separate. Broader public/institutional accessibility requirements
must still be assessed if those scopes are resumed.

## APK handling remains safe

An outside-store notice alone is not evidence of malware or corruption. Use the
verified versioned APK and the normal Android per-source installation flow only
when the recipient trusts it; allow an offered security scan. **Keep Play Protect
enabled.** If a phone instead says harmful app, sensitive-data/financial-fraud
block, or refuses installation, stop and reopen #108 with the exact sanitized
message/device/file details. Do not apply ordinary-notice guidance to a different
warning, uninstall/clear data, rotate keys, force a downgrade or bypass security.

No replacement SMS-free APK, permission change, appeal, signing or distribution
is required or authorized by this clarification. Automatic SMS import remains
optional in the unchanged private release. Public SMS-distribution gates #89/#81
remain separate.

## Tracking after closure

- Move #82 and #108 to Done, retaining owner acceptance/clarification in their
  issue bodies rather than marking unperformed checks as passed.
- Keep #95 blocked; keep the other unfulfilled device, privacy and report-input
  requirements open. Optional hosting/research/publication remain deferred or
  waiting for their own decisions.
- Android release acceptance (milestone 2) still contains #22/#81/#95/#106;
  final submission (3) still needs #11/#33. Neither can honestly be closed by
  these two dispositions. Optional future models (6) and public release (8) are
  not completed work; completed research/admin milestones stay closed.
- The Kanban must contain every remaining open issue with a priority, no open
  issue incorrectly Done, and all closed issues/merged PRs Done. Preserve its
  private visibility and do not invent target dates.

This is documentation/issue triage only. No application behavior, consent or
retention setting, model artifact, deployed API, APK or persistent database was
changed. No new test result, device run or institutional sign-off is claimed;
prior results keep their original revision/date. No service was launched.
