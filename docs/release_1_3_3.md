# Mobile 1.3.3 (build 8)

Release candidate from `release/mobile-1.3.3`, based on the selected-model pilot
and merged network fix #50, plus CSV lifecycle fix #52. No model change.

## Changes

- Friendly connection, timeout, TLS and gateway errors instead of raw diagnostics.
- Retry only reads automatically; uncertain writes advise checking before resubmitting.
- CSV picker cancellation/failures handled; overlapping opens prevented.
- Late picker/upload/navigation results no longer update disposed screens.

## Verification

Full local Flutter run:54 passed,1 opt-in live test skipped; analyzer clear.
JSON reporter ended with success=true despite tool timeout. New lifecycle tests
use a synthetic picker/repository; native picker and Google OAuth remain separate.
Independent review completed for the network and upload changes.

APK built from the isolated release worktree. Package:
`com.evagh.capstone.spending_support`, version1.3.3, code8.
Signing certificate SHA256:
`1586c2bea26d90ab930a322d8442100ac23e0a09c0eca9e643727326958a5000`.
This matches the existing tester certificate, not Play Store signing readiness.

APK SHA256:
`940faadaa1b3edbc1a224e48d7eac1fc927fef57e8c0b700419cb087678e953f`.
Local delivery path: `mobile/dist/spendly-1.3.3-8.apk`; ignored binary, not in Git.
Previous1.3.2 APK remains available. Manifest stored separately under the new version.

API: `https://spendly-api-t1d0.onrender.com/api/v1`. Direct health/model-info checks
returned200 before packaging, selected models loaded and database connected.
Backend remains release1.3.0. Build does not deploy or mutate hosted records.
Gradle emitted three Java8 source/target deprecation warnings; build succeeded.

## Remaining release gate

No connected Android device was available at packaging; update installation and
native network/picker checks are not claimed. #48/#51 implementation is verified
locally; rollout evidence remains #22. Merge the version PR into #52's branch
before merging #52 into the deployment branch. Preserve
the existing signing/package identity, and use synthetic accounts for native checks.
