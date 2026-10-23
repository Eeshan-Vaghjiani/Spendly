# Spendly 1.4.1 — private educational release

API **1.4.1** and Android **1.4.1+15** contain the approved dashboard/analytics,
budget and forecast UI improvements, transaction source icon beside the date,
admin charts/focus correction, and fast refresh-error handling from PRs #94,
#96 and #98. The API adds owner-scoped expense category totals without requiring
older clients to send new fields. Wasaa import is not implemented in this release.

## Verified candidate

- Fresh analyzer: no issues. Complete offline Flutter suite: **179 passed**, one
  intentional live-service skip. These tests use fake repositories/HTTP fixtures.
- Backend/rule gate: **216 passed**, six existing Alembic warnings; SQLite and
  fake inference fixtures, excluding the two documented real-model suites.
- Admin JavaScript: **18 passed**. Android JVM: **16 passed**, zero failures/errors.
- Actual opt-in native CSV suite on disposable AVD `SpendlySmsFinal_20261023`,
  `emulator-5564`, API36: **one passed**, no skips, 2m29s including teardown.
  Checked actual chooser cancellation, mixed rows, duplicate replay, invalid-file
  recovery and large-text budget editing. Its stale combined-budget-label
  assertion was updated for the approved separate Spent/Limit labels.
- Initial emulator setup encountered unavailable shared storage and a System UI
  not-responding dialog. The fixture driver waits for boot and uses the observed
  Wait control; final native execution passed. The helper removes its fixed
  invented CSV/XML files even after partial setup failure.
- Earlier four-screen native finance and thirteen-page200% text runs remain
  separately scoped in `evidence/android_finance_2026_10_23.md` and
  `evidence/ui_polish_2026_10_23.md`; they were not relabelled as fresh runs.
- Independent read-only release review found no promotion blockers after the
  test helper's partial-setup cleanup issue was corrected.
- No migration, model artifact or training change exists relative to 1.4.0.
  No persistent database rehearsal was repeated for this metadata/UI release.

## Build and APK identity

The first release build crashed its 8GB Gradle daemon while Windows reported
paging-file exhaustion. Issue #99 bounds the heap to3GB, metaspace to1GB and
workers to2. Owned test services/emulator were stopped before rebuilding. The
subsequent release build passed in93.8 seconds. No SDK/dependency upgrade occurred.

| Field | Verified value |
|---|---|
| APK | `Spendly-1.4.1-15.apk` |
| Package | `com.evagh.capstone.spending_support` |
| Version | `1.4.1+15` |
| Source commit used for build | `a4f7963c430e1cbeb4040c2203a39170ba719af6` |
| SHA-256 | `886c4ce0a84a2ba1646e6e4d89c8540ae14ea846b497a66848e4d3d3d1627bb6` |
| Certificate SHA-256 | `1586c2bea26d90ab930a322d8442100ac23e0a09c0eca9e643727326958a5000` |
| API | `https://spendly-api-t1d0.onrender.com/api/v1` |

The compiled APK retains the previous public Google Web client ID. Signature and
actual manifest checks passed: original package, higher versionCode, backups and
cleartext disabled, non-debuggable release, SMS receiver initially disabled,
protected receiver/job service. Generated release flags confirm SMS capability
enabled and test-source/emulator-lab disabled; the acceptance package is absent.
SMS consent still defaults OFF per account. Earlier versioned APKs are preserved.

Signed APK rehearsal on the named disposable AVD passed: install1.4.0+14,
update in place to1.4.1+15 with unchanged first-install timestamp, launch, reject
an ordinary downgrade with `INSTALL_FAILED_VERSION_DOWNGRADE`, clean-install
the older APK and launch, then reinstall/launch1.4.1. No account was signed in
and no financial records existed. Clean fallback erases local app state and is
not an authenticated data-recovery test or a recommendation to uninstall a user's app.

The existing Android Debug certificate is retained; this is not Play signing or
a public SMS distribution approval. The owner explicitly chose to continue
without the physical phone. No new-binary Google success, physical OEM/radio
behavior or personal inbox acceptance is claimed.

## Promotion and remaining scope

Promote the reviewed preparation PR to staging, then use a separate PR to
`agent/spendly-live-deployment`. Verify the exact Render/GitHub deployment revision,
healthy API1.4.1/database/models, unchanged public model-info and unauthenticated
route rejection. Branch membership alone does not establish live deployment.

The owner/institution still needs to decide privacy/retention/re-consent (#81).
Actual browser zoom and assistive-technology checks (#82), physical OAuth/device,
CSV process-death/provider interruption, radio-loss and authenticated data-recovery
coverage remain explicit limits. Automated fixtures and layout tests do not certify
TalkBack or legal compliance. Wasaa #95 waits for the key, contract and secure linking.

Do not uninstall the owner's app to roll back. Same-certificate installation is
the normal update path. Any destructive fallback rehearsal is restricted to the
named disposable emulator with no real account or financial records.
