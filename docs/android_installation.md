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
cause of the owner's phone failure or physical ARM-device acceptance. Keep the
reported failure open until the exact device result is captured and resolved.
