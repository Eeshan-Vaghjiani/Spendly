# Android CSV recovery checks, 26 October 2026

Scope: issue #22, a separate debug acceptance app using normal Spendly screens,
the real API repository, Android secure storage and Android DocumentsUI. The
fixture backend always uses fresh in-memory SQLite on loopback port 5057.
Only fictional data is used. No hosted account, personal phone or inbox is read.

## Repeatable procedure

1. From the repository root, start
   `python -m backend.scripts.run_csv_recovery_backend` in the app Python environment.
2. From `mobile/`, build the separate package:

   ```powershell
   flutter build apk --debug --no-pub --target tool/csv_recovery_main.dart --dart-define=SPENDLY_ACCEPTANCE_BUILD=true --dart-define=API_BASE_URL=http://127.0.0.1:5057/api/v1
   ```

3. Start the disposable `SpendlySmsFinal_20261023` AVD on port 5564. Do not wipe
   it, use another AVD or substitute a personal device. Wait for Android boot.
4. From the root, run `python scripts/check_csv_recovery.py` without `-O`.
   The runner verifies the named emulator, package identity, absent SMS permission
   and fresh backend marker before resetting only the acceptance package.
5. Stop the fixture and emulator after the run. The runner removes its CSV,
   UI dump, acceptance package and port reverse in its cleanup path.

The synthetic entrypoint may log in only on its first startup. Later startups
must restore the same account from real secure storage; lost storage cannot be
hidden by a fresh automatic login. Only this standalone fixture provides the
checkpoint endpoints; production returns 404 for them.

## Scenarios and evidence requirements

- Kill the background Spendly process while the real file picker is open.
  Finish selection, verify a restored session and no unsolicited import, then
  retry from the normal upload screen and create exactly one transaction.
- Stop the observed DocumentsUI package while selecting a file. Verify the
  Spendly process survives, the upload button becomes usable, and retry completes.
- Confirm that second import receives one row, creates zero, skips one duplicate
  and rejects zero. A fresh backend completion checkpoint is required; an old
  screen summary and unchanged transaction count alone cannot pass this check.
- Reinstall the same acceptance APK in place while authenticated. Verify a new
  startup restored the account, normal signed-in navigation appears, and the
  server still returns the single synthetic transaction.

## Results

| Check | Result |
|---|---|
| Debug acceptance APK build | Passed, including the final lint-only correction |
| Flutter analyzer | Passed, no issues |
| Flutter offline tests | 179 passed, one intentional opt-in live-service skip |
| Backend/rule gate | 217 passed, six existing Alembic deprecation warnings |
| Fixture regression | Included above: production routes absent, owner/auth/type checks, lost-session rejection and fresh import/duplicate checkpoints |
| Python syntax and optimized-mode guard | Passed; `-O` exits before device access as intended |
| Native CSV interruption/reinstall scenarios | **Not completed**; no pass claimed |

The selected AVD was Android API 36, x86_64. Initial runs with 1536 MiB guest
memory encountered unavailable UIAutomator roots and a visible Android Digital
Wellbeing not-responding dialog. A clean emulator restart with 2048 MiB/four
cores and the final rebuilt APK completed fixture login/startup acknowledgement,
then ADB reported the device offline before navigation/CSV acceptance completed.
The original phone installation problem is separately resolved by the owner's
confirmation, not by these unsuccessful emulator attempts.

No reproducible production-app defect was established. The host was under memory
pressure; that is an observed constraint, not a proven root cause for every
emulator failure. Run this suite again on a stable disposable emulator before
checking off process/provider interruption or authenticated reinstall recovery.
The fresh offline suite uses SQLite/fake inference except the standalone fixture
setup, which loads the existing portable model artifacts. No predictive metrics
were recomputed. Independent review corrected a potential stale-summary false
pass by requiring fresh backend completion counts and exact import results.

After ADB reconnected, cleanup was verified: the separate acceptance package was
uninstalled, the invented CSV/UI/screenshot files were removed, the port reverse
was absent, and the owned emulator and loopback backend were stopped. The debug
APK remains in `mobile/build/app/outputs/flutter-apk/app-debug.apk`; it is a lab
artifact, not an update for the user's phone. Local ignored `tmp/csv-*` diagnostic
files remain. The versioned release APK in Downloads was not changed.

## Limits

The harness uses the actual app code with a guarded synthetic startup and no
SMS capability. It is not the signed 1.4.1+15 production binary. Reinstalling
the same acceptance APK does not establish rollback, interrupted installation,
backup restoration or recovery after uninstalling. No real Google OAuth,
physical OEM/radio behavior, TalkBack, PostgreSQL or new model-quality evaluation
is established by this fixture.
