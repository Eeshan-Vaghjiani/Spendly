# Spendly: installation and source reproduction

Verified **12 November 2026**. Choose **A** to use the existing APK or **B** to
run the source locally. These are different deliverables: later main changes do
not update the signed APK, and a local Flutter build is not the original binary.

## A. Install the ready-made Android prototype

### A1. Obtain the authorised file

Ask the project owner for the verified APK and checksum through an authorised
private transfer. A GitHub draft is visible only to authorised repository
maintainers; it is **not yet an examiner download link**. Publication or wider
distribution requires the owner's separate approval. Do not use a generic old
`spendly-testers.apk` or build a replacement simply to obtain the filename.

The verified assets are attached to the
[unpublished draft pre-release](https://github.com/Eeshan-Vaghjiani/Spendly/releases/tag/untagged-fb4e55607f7607cbd021).
Its configured tag is `v1.4.1`, targeting the APK source below. GitHub has not
created a public tag ref while the release remains a draft; do not tell an
examiner to clone a tag that is not yet published. Use the exact source SHA in B1.

| Identity | Expected value |
|---|---|
| File / size | `Spendly-1.4.1-15.apk` / **55,806,018 bytes** |
| Android / build | **1.4.1 / 15** |
| Package | `com.evagh.capstone.spending_support` |
| Minimum Android | **7.0 / API 24**; ARM32, ARM64 or x86_64 |
| SHA256 | `886c4ce0a84a2ba1646e6e4d89c8540ae14ea846b497a66848e4d3d3d1627bb6` |
| Signing certificate SHA256 | `1586c2bea26d90ab930a322d8442100ac23e0a09c0eca9e643727326958a5000` |
| Recorded APK source | `a4f7963c430e1cbeb4040c2203a39170ba719af6` |

The original binary was recovered under the generic build-output name
`mobile/build/app/outputs/flutter-apk/app-release.apk` in the retained local
app-completion worktree. The versioned release asset is a byte-identical copy,
not a rebuild. Its valid v2 APK signature uses the existing **Android Debug**
certificate. This is a private educational prototype, not a Play-certified app.
See [the original release record](release_1_4_1.md) and
[fresh binary verification](evidence/apk_release_verification_2026_11_12.md).

### A2. Verify before installing

Save the APK to a known folder. In PowerShell, with that folder as the working
directory:

```powershell
$Expected = '886c4ce0a84a2ba1646e6e4d89c8540ae14ea846b497a66848e4d3d3d1627bb6'
$Apk = Get-Item -LiteralPath '.\Spendly-1.4.1-15.apk'
if ($Apk.Length -ne 55806018) { throw 'Unexpected APK size; do not install.' }
if ((Get-FileHash -LiteralPath $Apk.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Expected) {
    throw 'Checksum mismatch; stop and obtain the original file from the owner.'
}
```

The companion [checksum file](releases/Spendly-1.4.1-15.sha256) records the same
hash. Hash equality proves byte identity to this recorded release, not universal
safety, real-device compatibility or approval to access an inbox.

### A3. Install, launch and demonstrate

1. On a compatible test phone, open the verified file through Files/Downloads.
   If necessary, authorise installation for that specific trusted source. Keep
   Play Protect enabled and allow an offered scan. Do not bypass harmful-app or
   sensitive-data blocking warnings.
2. If updating an existing matching package/certificate, use the ordinary Update
   flow; keep its data. If a newer version or signing conflict exists, stop and
   use another authorised test device rather than uninstalling or downgrading.
3. Alternatively, start a designated Android test emulator from Android Studio
   Device Manager. Drop the verified APK onto it, or use SDK platform-tools:
   `adb -s <emulator-serial> install -r ".\Spendly-1.4.1-15.apk"`.
   Replace the serial using `adb devices`; never silently select a personal phone.
4. Open **Spendly** and check the installed version is 1.4.1+15.
5. Internet access is required. This APK is compiled for
   `https://spendly-api-t1d0.onrender.com/api/v1`; there is no runtime URL switch.
   You do not need a laptop backend for this binary. Free-tier idle wake-up can
   delay the first request; retry normally rather than repeatedly saving data.
   Service availability was not freshly checked for this documentation task.
6. Use an owner-authorised synthetic test account, never administrator credentials
   or real financial data. If a new account is authorised, register through the
   app and complete required consent/onboarding. Demonstrate manual income/expense,
   budget and analytics flows, using invented KES amounts. Do not bulk-seed the
   hosted database or fabricate complete historical coverage to force a forecast.
7. SMS import is optional and defaults off per account. For an examiner demo,
   prefer manual/CSV synthetic input and leave SMS and training opt-ins off.
   This binary still declares SMS permissions even while collection is disabled;
   do not grant personal-inbox access for demonstration.

For unavailable forecasts, explain the eight complete preceding weeks/history
confirmation requirement. More history does not guarantee accuracy. Estimates,
unusual-spending prompts and rule suggestions are not financial advice or fraud
findings. Current-binary physical OAuth, OEM/background and signed authenticated
recovery are not established by emulator/widget tests; see
[acceptance status](acceptance_status.md).

### A4. Non-destructive troubleshooting

- **Hash/size mismatch:** stop. Do not install, upload or rename another APK as
  this release. Obtain the original and repeat verification.
- **“App not installed”:** record the exact message, Android version, available
  storage, file identity and existing package/version/certificate. Do not clear
  app data, uninstall, force a downgrade or resign to guess at a fix.
- **Outside-store notice:** use Android's ordinary per-source permission only
  for a trusted verified file. A harmful-app or SMS-sensitive-data block is a
  different result; stop and ask the owner. Do not disable device protections.
- **Backend/login unavailable:** check connectivity and the owner's service
  status; preserve drafts. Password sign-in avoids making a fresh Google/OEM
  acceptance claim. Do not change the APK endpoint or production configuration.

Detailed warning distinctions: [Android installation guide](android_installation.md).

## B. Reproduce the source on Windows

### B1. Prerequisites and revision

Install Git, **Python 3.10**, Flutter with Dart **3.11.1-compatible** SDK, Android
Studio/Android SDK with Java 17 support, and a **local PostgreSQL 16** server plus
its `psql`, `createuser` and `createdb` tools. Follow their official installers;
do not upgrade an existing shared environment blindly. Flutter 3.41.4/Dart 3.11.1
is the recorded development toolchain, not a guarantee for every newer SDK.

The lightweight container uses `python:3.10-slim` and
[these requirements](../backend/requirements-light.txt). Gunicorn is used inside
the Linux container; use Flask's development server for this Windows-only local
demo. Docker/Compose is not required. Existing Compose uses persistent MySQL and
is deliberately **not** the PostgreSQL reproduction procedure below.

```powershell
git clone https://github.com/Eeshan-Vaghjiani/Spendly.git Spendly-examiner
Set-Location -LiteralPath '.\Spendly-examiner'
git switch --detach a4f7963c430e1cbeb4040c2203a39170ba719af6
git rev-parse HEAD
py -3.10 -m venv .venv
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m pip install -r backend/requirements-light.txt 'pytest>=8'
```

The detached checkout pins the **recorded APK source**, not today's main. Save
this guide before checkout; it was added later. For new development, use a new
branch based on main and record its own revision/tests. Neither rebuilding the
old source nor installing a debug build guarantees the original signed bytes,
because build environment, flags and signing material also matter. No rebuild
or signing is needed to use the retained trained models.

### B2. Create a separate local test PostgreSQL database

Use a fresh local PostgreSQL installation/test instance, never the Render/Neon
connection. Run these from the repository root in PowerShell with PostgreSQL's
`bin` directory on PATH. The role/database names below are **new local resources
to create**, not credentials recovered from the live service. Use unique names
and consistently update the local commands if those names already exist; stop
on creation errors instead of reusing, deleting or overwriting a database.

```powershell
$PgAdmin = Read-Host 'Existing administrator role on your LOCAL PostgreSQL instance'
createuser --host=127.0.0.1 --port=5432 --username=$PgAdmin --pwprompt --no-superuser --no-createdb --no-createrole spendly_examiner
if ($LASTEXITCODE -ne 0) { throw 'Local role creation failed; stop.' }
createdb --host=127.0.0.1 --port=5432 --username=$PgAdmin --owner=spendly_examiner spendly_examiner_repro
if ($LASTEXITCODE -ne 0) { throw 'Local database creation failed; stop.' }
```

Choose the new role password interactively. Do not put it in a script, Git,
screenshots or a published connection string. No credentials are supplied here.

### B3. Configure this shell for local use only

Stay in the repository root. Do not copy a production `.env`. Process variables
override dotenv defaults and apply only to this local shell/child processes.

```powershell
$DbPassword = Read-Host 'Password you just assigned to LOCAL spendly_examiner' -AsSecureString
$EncodedPassword = [uri]::EscapeDataString([System.Net.NetworkCredential]::new('', $DbPassword).Password)
$env:DATABASE_URL = "postgresql+psycopg://spendly_examiner:$EncodedPassword@127.0.0.1:5432/spendly_examiner_repro"
Remove-Variable DbPassword, EncodedPassword
$env:SECRET_KEY = (& $Python -c 'import secrets; print(secrets.token_hex(32))')
$env:JWT_SECRET_KEY = (& $Python -c 'import secrets; print(secrets.token_hex(32))')
$env:MODEL_ROOT = (Resolve-Path '.\artifacts\models').Path
$env:SELECTED_MODEL_ROOT = (Resolve-Path '.\artifacts\candidates\selected_v6').Path
$env:MODEL_RUNTIME = 'lightweight'
$env:LOAD_MODELS = 'true'
$env:MPESA_SMS_ENABLED = 'false'
$env:DATA_RETENTION_DAYS = '0'
$env:SESSION_COOKIE_SECURE = 'false'
$env:ALLOWED_CORS_ORIGINS = ''
$env:GOOGLE_WEB_CLIENT_ID = ''
```

Keep these same-shell values for the commands below. No local admin account is
needed for a mobile password-only demo; admin credentials and Google configuration
require separate setup if those optional flows are demonstrated. Secrets are
ephemeral and must be generated again for a fresh local run. Empty Google settings
do not verify native Google sign-in.

### B4. Guard the target, migrate and start Flask

These commands modify **only the new local database**. First confirm the actual
connection target without printing its password:

```powershell
& $Python -c "import os; from urllib.parse import urlsplit; u=urlsplit(os.environ['DATABASE_URL']); assert u.scheme == 'postgresql+psycopg' and u.hostname == '127.0.0.1' and u.port == 5432 and u.path == '/spendly_examiner_repro'; print('Verified local-only reproduction database target')"
if ($LASTEXITCODE -ne 0) { throw 'Database target check failed; do not migrate.' }
& $Python -m flask --app backend.run:app db upgrade --directory backend/migrations
if ($LASTEXITCODE -ne 0) { throw 'Local migration failed; do not start the app.' }
& $Python -m flask --app backend.run:app db current --directory backend/migrations
& $Python -m flask --app backend.run:app run --host 127.0.0.1 --port 5000
```

The release source has migrations **0001–0008**, ending at
`0008_mpesa_sms_import`. Loading the selected root verifies its manifest,
weights checksum and parity identity before serving. If a model is missing or
incompatible, fix the local checkout/configuration; do not retrain or bypass the
checks. Linux container startup also migrates, so never point a reproduction
container at a production database. Keep that separate from this local procedure.

In a second PowerShell window:

```powershell
$Health = Invoke-RestMethod 'http://127.0.0.1:5000/api/v1/health'
$Health.data
Invoke-RestMethod 'http://127.0.0.1:5000/api/v1/model-info'
```

Expect the success/data envelope, healthy database, models loaded,
`api_release: 1.4.1`, `inference_runtime: portable_lstm`, and SMS availability
false for this local configuration. A failed/503 result is not a successful
reproduction. Do not substitute a hosted URL for these local checks.

### B5. Start the local Flutter client

Use a designated **empty test emulator**, not an examiner's/personal existing
Spendly installation. A local debug key/package may conflict with the original
APK; use a separate test AVD rather than clearing data or resigning the release.
From `Spendly-examiner\mobile` in the second window:

```powershell
flutter --version
flutter doctor
flutter pub get
flutter emulators
flutter emulators --launch <chosen-test-emulator-id>
flutter devices
flutter run -d <android-device-id> --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

Replace angle-bracket device IDs with the actual selected test target. Android
emulator `10.0.2.2` reaches the Windows host loopback; host-side checks use
`127.0.0.1`. The default source build has SMS capability off; do not enable SMS
or real inbox access for this demo. Register a fictional local test account and
use synthetic financial data. Local records do not affect the hosted service.

### B6. Run tests and actual retained-model load checks

From `mobile/`, serially:

```powershell
flutter analyze --no-pub
flutter test --no-pub
```

From the repository root, using the venv Python:

```powershell
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m pytest backend/tests services/recommendation_engine/tests --ignore=backend/tests/test_model_inference.py --ignore=backend/tests/test_vertical_slice_real.py -q
& $Python -m pytest backend/tests/test_selected_registry.py services/recommendation_engine/tests -q
```

The ordinary backend fixtures use isolated SQLite and mostly fake inference;
the explicitly named selected-registry test loads the real retained portable
LSTM/IF bundle and invokes analysis on synthetic data. Recommendation tests
exercise the deterministic rule engine. These do not contact the hosted service.
The mobile live-backend test remains intentionally skipped unless separately
opted in; do not enable it against the shared service—it creates records without
cleanup. The excluded legacy model suites have different data/runtime prerequisites.

The selected models are **already trained**, and this path needs **no training,
GPU or TensorFlow**. Its [manifest](../artifacts/candidates/selected_v6/manifest.json),
numeric weights and matching parity record must all be retained. Ordinary training
consent is not permission to retrain, and numerical load parity is not proof of
good unseen-user predictive accuracy.

## Reproduction limits and examiner handover

The fresh checks for this documentation task verified the original APK and a
direct selected-model/rule smoke check. A clean Python 3.10/PostgreSQL migration,
fresh Flutter build and new phone/emulator session were **not** performed here.
The smoke environment was Python 3.13.2/NumPy 2.4.6/pandas 3.0.3, outside the
documented lightweight dependency bounds; it is not an environment-certification
substitute. Dependency declarations are ranges, so record resolved versions and
results when reproducing in the recommended fresh environment.

Before examiner access: approve the exact binary/distribution method, verify the
checksum again, arrange an authorised synthetic account and working backend,
review privacy/SMS limits, test the actual intended device non-destructively,
and provide the source revision plus this guide. If you choose to publish the
draft on this public repository, the assets become public; a pre-release label
does not keep them private. See [acceptance status](acceptance_status.md),
[release identity](release_1_4_1.md), [model evaluation](wasaa_testing_and_model_decision.md)
and [Git workflow](git_workflow.md).

### Owner checklist before handing the prototype to an examiner

1. Review and merge the documentation PR; retain the APK source SHA separately
   from the documentation revision.
2. Review the draft's three assets/notes and choose an authorised **private
   transfer**, or separately approve public publication. Do not publish merely
   to make a draft URL accessible; publication exposes the APK on this public repo.
3. Confirm the intended test phone/emulator meets API/ABI requirements and has
   no conflicting/newer installation. Recheck the transferred APK hash and size.
4. Check the configured backend is available and arrange a dedicated authorised
   synthetic account. Do not supply admin credentials or real personal finances.
5. Rehearse the exact examiner workflow without clearing existing data. Keep SMS
   and training off; document any actual Google/OEM/recovery limits encountered.
6. Supply the APK, checksum, notes, this guide and source commit. If source
   reproduction will be assessed, first run B on a fresh compatible local
   environment/test database and record its results. This task did not certify
   that full setup or a new device run.
