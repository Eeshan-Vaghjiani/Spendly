# Original APK verification — 12 November 2026

## Scope and identity

Prepare an unpublished draft and examiner installation/source-reproduction
documentation without rebuilding, signing, deploying or changing existing files.
The source baseline for the documentation branch is main `d6e7f1f`; the original
APK source remains **a4f7963c430e1cbeb4040c2203a39170ba719af6**. These are not
interchangeable release claims. Its source `mobile/pubspec.yaml` records 1.4.1+15
and `backend/app/release.py` records API 1.4.1.

The original bytes were found in the retained local app-completion worktree at
`mobile/build/app/outputs/flutter-apk/app-release.apk`; a second APK-output copy
has the same hash. The old root workspace's generic release/tester copies are
older versions and were not substituted. The filename was generic; the release
asset copy is named `Spendly-1.4.1-15.apk` without changing its contents.

| Property | Fresh observed result |
|---|---|
| Size | 55,806,018 bytes |
| SHA256 | `886c4ce0a84a2ba1646e6e4d89c8540ae14ea846b497a66848e4d3d3d1627bb6` |
| Package / app label | `com.evagh.capstone.spending_support` / Spendly |
| Android version / code | 1.4.1 / 15 |
| Minimum / target SDK | 24 / 36 |
| Native ABIs | arm64-v8a, armeabi-v7a, x86_64 |
| Signature | Valid APK v2, one signer; checked from minimum SDK 24 |
| Certificate DN | C=US, O=Android, CN=Android Debug |
| Certificate SHA256 | `1586c2bea26d90ab930a322d8442100ac23e0a09c0eca9e643727326958a5000` |
| ZIP / alignment | All member CRCs pass; 16-KiB alignment passes |
| Manifest safety | Backup and cleartext disabled; no debuggable attribute (Android default false) |
| SMS declarations | READ_SMS / RECEIVE_SMS present; account opt-in remains separate |

The size, hash, certificate, package and version match
[the original record](../release_1_4_1.md). Android SDK build-tools 36.0.0
`aapt dump badging`, `aapt dump xmltree`, `apksigner verify --verbose --print-certs
--min-sdk-version 24`, and `zipalign -c -P 16 4` were used. Python independently
checked size, SHA256 and every ZIP member CRC. No private key was read.

## Reproduction checks and limits

- The four retained selected-V6 artifacts and all eight migration files exist
  at the original APK source. Main's selected manifest is
  `spendly-portable-v6-v1`, `v6_reference_lstm`, `single_excess128`, 300 trees,
  sample 128, cutoff 0.6451359189730762. Weights SHA256 is
  `6fcf6b12c5c0c00ad5057c126e2054588858b5b5bba10d6f10417ea6bf146538`.
- Direct actual-model smoke: bundle checksum/parity identity accepted; two
  synthetic forecast rows and two IF rows produced finite results; forecasts
  were nonnegative. Rules returned bounded recommendations. TensorFlow was not
  imported. This is loading/execution evidence, not a quality/parity re-evaluation.
- Smoke host: Python 3.13.2, NumPy 2.4.6, pandas 3.0.3, outside the lightweight
  requirement bounds. No Python 3.10 clean-environment, Windows PostgreSQL or new
  Flutter/native/device verification is claimed. No packages were installed.
- The recommended source reproduction pins the historical APK source, explicitly
  selects the retained portable bundle and uses a newly created local PostgreSQL
  database with a host/name guard before migrations. No such database or migration
  was created/run during this documentation task.
- No live backend health, OAuth, real inbox, physical phone, model training or
  distribution check was performed. Existing acceptance gaps remain unchanged.

## Draft preparation

No prior releases or tags existed at inspection. Created
[draft release 442571309](https://github.com/Eeshan-Vaghjiani/Spendly/releases/tag/untagged-fb4e55607f7607cbd021)
with `draft=true`, `prerelease=true`, `published_at=null`, configured tag
`v1.4.1` and exact target `a4f7963c430e1cbeb4040c2203a39170ba719af6`.
GitHub has not materialised the public `refs/tags/v1.4.1` while it is a draft.
No existing tag was moved and no new public release was published.

Uploaded APK, checksum and release/installation notes. GitHub reports the APK
asset uploaded at 55,806,018 bytes, digest
`sha256:886c4ce0a84a2ba1646e6e4d89c8540ae14ea846b497a66848e4d3d3d1627bb6`.
The APK asset ID is 738348392. The staged copy is byte-identical to the retained
original and leaves the original build outputs untouched.

Authenticated download of all **three draft assets** succeeded; each downloaded
file matched its staged bytes, and the APK checksum was independently rechecked.
All **10 PowerShell documentation blocks** parsed after substituting device-ID
placeholders; their database/build/install commands were not executed. All **29
local Markdown links** present at that check resolved, source/model/test paths
were confirmed at the pinned APK commit, and the whitespace diff check passed.
An attempted independent review was blocked by the review agent's worktree
read-access boundary; no independent review pass is claimed.

A draft is not published or downloadable by an ordinary examiner. Publication on this public repository
would make the assets public and requires separate owner approval. No production
Render/Neon setting, service, database, APK signing identity or branch history
was changed.
