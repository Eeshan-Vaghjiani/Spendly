# Install the private Android build

Current private educational build: **Spendly 1.4.1+15**. The API release is
1.4.1. This APK has not been published on Google Play.

| File property | Expected value |
|---|---|
| Filename | `Spendly-1.4.1-15.apk` |
| Size | 55,806,018 bytes (55.8 MB / 53.2 MiB) |
| SHA-256 | `886c4ce0a84a2ba1646e6e4d89c8540ae14ea846b497a66848e4d3d3d1627bb6` |
| Package | `com.evagh.capstone.spending_support` |
| Minimum Android | Android 7.0 / API 24 |
| Architectures | 32-bit ARM, 64-bit ARM and x86_64 |

## Normal update

1. Obtain the exact versioned APK from the project owner. Save a complete copy
   to Downloads; if received through WhatsApp, open the saved file from the
   phone's Files app. The transfer method alone does not establish corruption.
2. Keep the existing Spendly installation and data. Open the APK and use the
   normal Android installation/update prompt. Do not downgrade or uninstall to
   bypass a failed update.
3. Open Spendly and confirm version 1.4.1+15 in the app's version information.
   SMS import remains optional and requires its own disclosure and permission.

The existing package/signing certificate was retained. An update should preserve
local app data; uninstalling is not an equivalent update or a verified recovery
method. See [release identity and scope](release_1_4_1.md).

## If installation fails

Record the **exact Android error**, filename, Android version, phone model and
whether the file came from WhatsApp/Downloads/another source. Check the received
file's size and, where available, SHA-256. Keep screenshots limited to the
installation message; do not include account details or financial records.

Do not assume every failure means a bad signature or WhatsApp corruption. The
specific result determines whether to investigate a partial file, Android/ABI
compatibility, storage, existing package identity or an installation restriction.
Do not broadly turn off device security protections to diagnose an unknown error.

With the owner's USB-debugging approval, a developer can inspect the device
version and installed package, compare signing identity and capture the exact
Android package-manager result. Use an in-place `adb install -r` only after the
target and update identity are confirmed. Never use `adb uninstall`, `pm clear`
or a forced downgrade against a personal device as a routine diagnostic step.

## Google Play / Play Protect warnings on a friend's phone

The owner reported new blocks on friends' phones on **30 October 2026**. The exact
warning and affected APK/device identity are still needed; do not equate this
report with the resolved 24 October failure below. Track the new report in
[#108](https://github.com/Eeshan-Vaghjiani/Spendly/issues/108).

| What the phone says | Appropriate next step |
|---|---|
| This source is not allowed to install apps | If the recipient trusts the verified APK, use Android's per-source installation permission for the chosen Files/browser app. This is different from disabling Play Protect. A managed phone may require its administrator. |
| Scan recommended / app unknown to Play Protect | Allow the offered security scan and follow its result; unknown does not establish malware or a clean bill of health. |
| App blocked; sensitive data / identity theft / financial fraud | Record the exact warning. Google documents sensitive-permission sideload blocks in some markets, including SMS permissions. Review the actual APK and distribution path; do not bypass the block. |
| Harmful app blocked | Stop distributing that binary pending investigation; review the app/dependencies and use the official appeal if classification appears incorrect. Do not dismiss it as an ordinary unknown-source prompt. |
| App not installed / package conflicts / invalid package | Check received-file integrity, Android/ABI compatibility, available storage, package/version and signing identity. Do not uninstall or clear data to guess at a fix. |

An SMS-capable APK declares `READ_SMS`/`RECEIVE_SMS`. Turning import **off in
settings does not remove those declarations**, so it may still meet the
permission-based block conditions. Moving the backend from Render to Oracle,
renaming the APK, or signing it again is not a verified remedy.

Two legitimate product/distribution choices remain:

1. Offer an explicitly SMS-permission-free build using the existing default
   capability-off build path; manual entry and CSV remain available, but automatic
   M-PESA import does not. Inspect the final APK manifest, preserve update/signing
   identity and obtain approval before creating/signing/sharing a replacement.
   This removes the SMS-permission trigger, not every possible Play Protect warning.
2. Retain automatic SMS import and pursue reviewed distribution, the required SMS
   permissions declaration/eligible money-management exception and the privacy and
   physical-device gates in #89/#81/#22. Internal/closed testing is not a blanket
   permission-policy exemption or a guarantee of acceptance.

If a warning appears erroneous after review, the owner can submit the
[official Play Protect appeal](https://developers.google.com/android/play-protect/warning-dev-guidance#request-appeal)
with the actual warning and binary identity. No appeal or new build has been
submitted for this report. Do not use accessibility, notification access or OTP
retrieval APIs as a workaround for financial SMS permissions; OTP APIs do not
provide an M-PESA history feed.

References: [Google's warning guidance](https://developers.google.com/android/play-protect/warning-dev-guidance),
[SMS permission policy and money-management exceptions](https://support.google.com/googleplay/android-developer/answer/10208820).

## Recorded investigation, 24 October 2026

The owner reported an install failure after opening the APK from WhatsApp and
also reported trying uninstalling. The phone was unavailable; its precise error,
received-file identity and final installed state were not observed.

The local APK matched the release hash and passed ZIP integrity, signature,
supported-API signing and 16-KiB alignment checks. Its certificate matched the
previous 1.4.0+14 APK. A clean install, repeat install and cold launch passed on
the disposable API-36 x86_64 emulator `SpendlySmsFinal_20261023`. The app remained
running in the foreground. No account, financial records or inbox was accessed.

This establishes the tested binary's installation on that emulator, not the
cause of the owner's phone failure or physical ARM-device acceptance. The owner
subsequently confirmed on **26 October 2026** that phone installation
worked, so [issue #102](https://github.com/Eeshan-Vaghjiani/Spendly/issues/102)
is closed. The exact corrective step and original failure cause were not
established. This confirmation does not establish current Google sign-in,
account recovery or all physical-device acceptance checks.
