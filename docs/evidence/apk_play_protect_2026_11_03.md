# Play Protect investigation — 3 November 2026

Related: #108, #22, #81 and #89. This is a fresh **local copy** inspection of
the existing private release, not an affected-phone retest or a Play Protect scan.
No replacement APK was created, signed, uploaded or distributed; no appeal was filed.

## Binary checks actually completed

The existing downloaded `Spendly-1.4.1-15.apk` was inspected using Android SDK
build-tools **36.0.0** (`aapt`, `apksigner`, `zipalign`) and Python `zipfile`.

| Property / check | Actual result |
|---|---|
| Size | 55,806,018 bytes |
| SHA-256 | `886c4ce0a84a2ba1646e6e4d89c8540ae14ea846b497a66848e4d3d3d1627bb6` — matches the release record |
| Package / version | `com.evagh.capstone.spending_support`, `1.4.1`, version code `15` |
| Minimum / target Android API | 24 / 36 |
| Native ABIs | `arm64-v8a`, `armeabi-v7a`, `x86_64` |
| ZIP integrity | Every member passed CRC validation |
| APK signature | Verification passed; one signer, v2 signature |
| Certificate SHA-256 | `1586c2bea26d90ab930a322d8442100ac23e0a09c0eca9e643727326958a5000` — matches the release record |
| Certificate identity | Existing Android Debug certificate; not a new Play-signing identity |
| Alignment | `zipalign -c -P 16 -v 4` passed |
| Manifest SMS permissions | **`READ_SMS` and `RECEIVE_SMS` are present** |
| Other observed permissions | Internet, boot completion, network state, biometric/fingerprint and package-scoped dynamic-receiver permission |
| Manifest safeguards | Backup disabled; cleartext traffic disabled; SMS receiver protected by `BROADCAST_SMS`, job service by `BIND_JOB_SERVICE` |

No APK signature/key was changed. A valid signature/CRC/alignment proves neither
absence of malware nor approval by Google. It also does not prove a friend's
received file matches this local copy. The debug certificate alone is not a
diagnosis of the reported block; changing keys would disrupt update identity.

## Supported diagnosis, not a confirmed cause

[Google's warning guidance](https://developers.google.com/android/play-protect/warning-dev-guidance)
was read on 3 November. It documents automatic sensitive-permission blocks in
select markets for internet-sideloaded apps declaring `READ_SMS`/`RECEIVE_SMS`.
The associated prompt is:

> This app can request access to sensitive data. This can increase the risk of
> identity theft or financial fraud.

This binary has the relevant declarations, so this is a concrete hypothesis to
compare with the actual warning. The exact affected warning, market/device and
received APK identity are **not known**. Do not equate this with a harmful-app
classification, an unknown-source prompt or a scan recommendation. Do not claim
that a hosted API move, disabling import in settings, renaming the APK or signing
again resolves classification. No protection was disabled and no inbox was read.

## What can be prepared without another phone

The tracked main manifest contains no SMS permissions. `build.gradle.kts` adds
the SMS overlay only when `SPENDLY_SMS_CAPABILITY=true`; the default is off.
An explicitly SMS-permission-free distribution variant can therefore retain
manual/CSV entry without inventing a new ingestion mechanism. This is source
inspection, **not verification of a newly built no-SMS APK**. Producing/signing a
new version still needs the owner's product/distribution choice, then final
manifest/certificate/update checks and an affected-phone retest. Removing SMS
permissions does not guarantee removal of every Play Protect warning.

Keeping automatic SMS import instead requires the applicable reviewed distribution,
permission declaration/exception, privacy and device gates. OTP retrieval is not
an M-PESA history API; accessibility/notification collection must not be used as
a permission bypass.

## Missing evidence to close #108

- Exact warning text or a screenshot limited to the warning (no account/SMS data).
- Phone model, Android version, installation source, fresh install versus update.
- Received file size/hash/version, compared with the values above.
- Owner's choice: SMS-free manual/CSV variant, or retain SMS and pursue the relevant
  distribution review. No choice or approval is inferred from this investigation.
- Affected-phone retest with Play Protect enabled; investigate a harmful-app
  classification separately and obtain approval before any appeal submission.

Until these exist, #108 remains blocked. The old owner-resolved installation
report #102 is not reopened and its original cause remains unknown.
