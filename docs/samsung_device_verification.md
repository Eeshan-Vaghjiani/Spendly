# Samsung synthetic-device verification

Tracking: #22. Device: Samsung SM-G988B, Android arm64, adb-authorized USB.
Installed release before and after testing: Spendly1.3.2 (build7), package
`com.evagh.capstone.spending_support`.

## Target and method

The signed-out phone received a temporary debug APK built from the existing
local mobile working tree with API_BASE_URL=http://127.0.0.1:5000/api/v1.
USB reverse forwarded only port5000 to a disposable local Flask backend.
`scripts/device_smoke_backend.py` used temporary SQLite, a synthetic account,
16 historical expenses and one KES25,000 expense. The backend health reported
release1.3.0, portable_lstm and both selected models loaded.

The mobile working tree contains preserved earlier edits and is not a clean
checkout of a release commit. These checks establish native behaviour of this
local debug build, not byte-identical release-build behaviour or hosted acceptance.
UIAutomator semantic nodes and Android input actions were used; HTTP status logs
provided supporting evidence. No personal account screens or records were opened.

## Completed checks

| Check | Observed result |
|---|---|
| Synthetic email/password sign-in | Dashboard identifies the synthetic account; local login200 |
| Add expense | KES321.50/food/NativeSmoke appears in Transactions; POST201 |
| Invalid amount | Zero amount rejected with 'Enter an amount greater than zero'; edit remains open |
| Edit expense | Change to KES456.75 saved; PUT200 and list reload |
| Delete expense | Confirmation accepted; DELETE200; totals return to original fixture values |
| Budget empty state | 'No budget is configured' displayed |
| Create budget | KES30,000 total budget appears; POST201 |
| Edit budget | KES31,000 displayed after save; PUT200 |
| Delete budget | Confirmation accepted; DELETE200; dashboard reports no active budget |
| Analytics | Monthly totals load; daily selection requests correct resolution with200 |
| Quick-access drawer | Opens from Analytics and navigates to Transactions |
| Connection failure and retry | Removed forwarding; refresh shows failure. Restored forwarding; Retry returns transaction data. Raw exception/URL text is a UX defect tracked in #48 |
| CSV entry point | Upload screen and 'Choose CSV file' control open. Native file picker/import not exercised |
| Empty analysis history | Forecasts/Alerts/Advice tabs load; no stored forecasts initially |
| Installed-version display | Profile shows '1.3.2 (build 7)' |
| History confirmation | First insight request rejected422; date picker and explicit completeness dialog shown; confirmation produces analysis200 |
| Selected forecast | Dashboard shows Oct5-Oct11 weekly estimate KES123 for this fixture, separate from history readiness |
| Alert detail/edit/rescore | KES25,000 alert shows prior16-entry median KES107.50; correct editor opens. Save KES125; analysis reruns200 and this alert disappears |
| Intentional review | Remaining KES100 cold-history alert changes to Confirmed intentional with totals-preservation text; review200 |
| Sign-out | Returned to unauthenticated create-account/sign-in screen |
| Release restoration | Original release APK reinstalled successfully without uninstall/storage clear; version1.3.2/build7 and non-debug package flags verified |

These are manual native checks, not an automated test-suite pass count. The
offline error-message finding prevents claiming an entirely defect-free run.
Initial rapid Android typing corrupted synthetic login input; it was corrected
with focus waits and select-all. This was automation input timing, not an app
authentication failure. No personal credentials were used.

## Not established by this run

- Native Google OAuth (disabled in the local build; no personal Google account used).
- Actual file selection, CSV import, invalid/duplicate CSV handling on device.
- Income-entry flow, account switching, native secure-storage durability and
  large-text/small-screen layouts beyond the observed device configuration.
- All analytics filters/charts, all date-picker boundary cases and alert deletion states.
- Hosted API/database migrations, concurrency, memory/load or current availability.
- Final release rendering parity, complete absence of runtime errors, or model quality.

The live API previously returned503; local success does not resolve that separate
availability issue. No hosted accounts or financial records were created.

## Restore and cleanup

Before installing the debug build, the installed APK was copied from the device.
Its SHA256 matches the recorded1.3.2 release:
`29700a50b4c7c8e39b8ddac2a509d971d97f2c56eb30905aa7baede9544053ac`.

After sign-out, that exact APK was restored with `adb install -r`. No uninstall,
app-storage clearing or device wipe occurred. Port5000 forwarding was removed,
the on-device UI dump was deleted, owned backend PID25236 was stopped, and no
port5000 listener or owned backend process remained in the final check.

Local artifacts retained: restore APK, debug build, synthetic UI dump/helper
scripts and sanitized backend request log under the approved temporary directory.
The test backend was force-stopped, so its temporary SQLite directory may remain;
it contains only generated fixture records. ADB remains available for the connected
device; no test backend or app automation process remains running.

Gradle automatically installed Android SDK Platforms34 and35 during the debug
build. This unplanned shared-SDK side effect is recorded; no Flutter SDK upgrade
was run. No research models were retrained or deployment configuration changed.

## Follow-up

Resolve #48 user-facing network errors and the hosted503 issue before the next
live demo. Complete the remaining native checklist as a separate session. Keep
#22 open until its agreed acceptance scope is satisfied; use this record as
additional evidence for #11 rather than replacing unperformed checks with passes.
