# Spendly v1.4.1 (Build 15) - Private Educational Prototype

**Unpublished draft pre-release; owner approval required before distribution.**
Prepared 12 November 2026 from the retained original binary, not a new build.
Publishing this release on the public repository makes its assets public;
the words “private prototype” or “pre-release” do not restrict public access.

## Identity

- APK: **Spendly-1.4.1-15.apk**, **55,806,018 bytes**.
- Android version **1.4.1**, versionCode **15**.
- Package: `com.evagh.capstone.spending_support`.
- Minimum **Android 7.0 / API 24**; ARM32 (`armeabi-v7a`), ARM64 and x86_64.
- SHA256: `886c4ce0a84a2ba1646e6e4d89c8540ae14ea846b497a66848e4d3d3d1627bb6`.
- Certificate SHA256: `1586c2bea26d90ab930a322d8442100ac23e0a09c0eca9e643727326958a5000`.
- Certificate: **C=US, O=Android, CN=Android Debug**, valid APK v2 signature.
  This is not a Play Store/public-distribution signing approval.
- Proposed release tag **v1.4.1** targets the recorded APK source commit
  **a4f7963c430e1cbeb4040c2203a39170ba719af6**, not the latest main.
- Recorded matching backend API version: **1.4.1**.

The staged versioned asset is a byte-identical copy of the recovered
`app-release.apk` whose size/hash match the October release record. It was not
rebuilt, resigned, patched or relabelled as a newer source release. Later main
settings/status/accessibility fixes are not automatically included in this APK.

## Main features

Synthetic demonstration of account sign-in/onboarding, separate consent choices,
income/expense and budget management, CSV import, cash-flow/category analytics,
eligible weekly LSTM estimates, reviewable Isolation Forest spending prompts and
rule-based recommendations. This version includes the recorded dashboard,
budget/forecast/source-icon and refresh-error corrections. Optional M-PESA SMS
import requires separate disclosure, permission and account opt-in. Wasaa live
import is not implemented.

## Installation

1. Obtain the authorised APK and checksum; drafts are maintainer-only, not public
   download pages. Do not share the draft as an examiner download link.
2. On Windows, check the download:

   ```powershell
   $Apk = Get-Item -LiteralPath '.\Spendly-1.4.1-15.apk'
   if ($Apk.Length -ne 55806018) { throw 'Unexpected size; stop.' }
   if ((Get-FileHash -LiteralPath $Apk.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne '886c4ce0a84a2ba1646e6e4d89c8540ae14ea846b497a66848e4d3d3d1627bb6') {
       throw 'Checksum mismatch; do not install.'
   }
   ```

3. Open the verified file on a compatible Android test device and follow its
   ordinary per-source installation/update flow. Keep Play Protect enabled and
   allow scans; stop for harmful-app/sensitive-data blocks rather than bypassing.
4. Keep an existing matching installation/data. Do not uninstall, clear storage,
   force a downgrade or resign to resolve a conflict. Use a separate authorised
   test emulator if the package/certificate or installed version differs.
5. Launch Spendly, confirm 1.4.1+15 and use an authorised fictional account/data.
   Never share admin credentials or demonstrate with personal finances/inboxes.
   A designated test emulator may use `adb -s <serial> install -r` for installation.

## Backend and runtime

This APK uses the compiled HTTPS endpoint
`https://spendly-api-t1d0.onrender.com/api/v1`. It is not an offline-only app and
has no runtime endpoint switch. Availability and authorised synthetic-account
access must be checked by the owner before the exam. Free-tier cold starts can
delay the first request. No fresh hosted-health/capacity check is claimed here.

The trained retained models execute on the backend; testers need no training,
GPU, Python, Docker or local model files. A local source/debug build pointing at
`10.0.2.2` is a separate reproduction path, not this original release binary.

## Limitations and security

- This remains an experimental educational prototype, not financial advice,
  fraud certification or guaranteed savings/forecast accuracy. Synthetic model
  evaluations do not establish real-user generalisation.
- Forecasting needs eight complete preceding weeks and honest coverage
  confirmation. Missing history must not be fabricated for a demo.
- The APK declares SMS permissions even with import off. For examination, leave
  optional SMS/training off and prefer manual/CSV synthetic demonstrations.
  Do not grant access to a personal inbox solely to show functionality.
- Successful checksum/signature/CRC/alignment checks establish binary integrity,
  not universal Android compatibility or malware/public-permission approval.
- Historical emulator checks and owner-reported installation are scoped evidence,
  not fresh current-binary physical Google/OEM/background/recovery acceptance.
- No new code, model, database migration, service configuration, signing identity
  or deployment was changed to prepare this draft. No public release or APK
  distribution has been approved by preparing a draft.

## Documentation

The source documentation PR adds `docs/INSTALLATION_AND_REPRODUCIBILITY.md`.
Existing records include `docs/release_1_4_1.md`, `docs/android_installation.md`,
`docs/acceptance_status.md` and `docs/git_workflow.md`. The original release tag
points to the APK's historical source; the newer installation guide is a separate
documentation change, not part of that historical commit. Obtain it through the
reviewed documentation PR/main after merge or from the project owner.
