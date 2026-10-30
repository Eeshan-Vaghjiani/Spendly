# Spendly 1.4.0 — private educational release

Android version **1.4.0+14** and API release **1.4.0** introduce optional M-PESA
SMS import. This is a private educational/tester build, not a Google Play release.
The existing Android Debug certificate is retained for an in-place update from
1.3.5+13. No new signing setup or public distribution approval is claimed.

## Consent and deployment configuration

The private APK is built with `SPENDLY_SMS_CAPABILITY=true`; acceptance,
test-source and emulator-lab modes are disabled. The receiver starts disabled.
Existing and new accounts default to SMS import OFF. Disclosure acceptance and
both contextual Android SMS permissions are required before SMS processing.

The deployment Blueprint enables service availability with
`MPESA_SMS_ENABLED=true`; Python's default remains false when this is omitted.
The public health response reports `mpesa_sms_available` so an unapplied hosting
setting can be detected without accessing accounts or changing anyone's consent.

Promotion uses feature PR #90 -> staging -> a separate deployment PR. The
deployment PR's runtime evidence, not a local Git branch name, establishes what
is live. `backend/start.sh` upgrades migrations to head before starting Gunicorn;
the new migration is `0008_mpesa_sms_import` after `0007_sign_in_activity`.

## Verified before promotion, 23 October 2026

- Backend/rule gate: **213 passed**, six existing Alembic warnings. The new health
  test distinguishes global availability from account consent. Fixture inference
  is mocked; deployed model artifacts and configuration are unchanged.
- Flutter: **162 passed**, one intentional live-service skip, analyzer clean.
  These cover the app implementation; the later version bump changes metadata.
- Kotlin JVM: **16 passed**.
- Actual API-36 disposable-emulator suite: one pass in **1m28s**, plus three
  separate process-death, force-stop/reopen and permission-revocation checks.
  See `mpesa_sms_import.md` for the exact device, scope and test APK identities.
- **PostgreSQL 16 rehearsal passed** using a newly created random-named container,
  an existing official image, tmpfs data and loopback port 55432. No Compose or
  existing project container was used. Upgrade 0007 -> 0008 -> downgrade 0007 ->
  upgrade 0008 preserved a synthetic legacy account and KES125.50 transaction,
  defaulted consent/reversal flags correctly and matched ORM metadata.
- Four concurrent PostgreSQL imports produced exactly one source event, two
  financial/component rows and three duplicate results. Deletion/replay,
  second-owner isolation and both consent-withdrawal/import lock orderings passed.
  The owned temporary container was removed in cleanup, without a persistent volume.
- Release APK built successfully in 105.3 seconds. Package, signature, version,
  restricted SMS permission inclusion, disabled receiver, protected job service,
  disabled backups/cleartext and disabled test modes were inspected.

Run the repeatable database check from the repository root with the isolated
application Python environment:

```powershell
python -m backend.scripts.rehearse_mpesa_postgres
```

It accepts no arbitrary database URL, refuses a nonempty target, uses an installed
`postgres:16-alpine` image with `--pull=never`, and generates a fixture password
in memory without printing it. Docker Desktop must already be running.

## APK identity

| Field | Value |
|---|---|
| Package | `com.evagh.capstone.spending_support` |
| Version | `1.4.0+14` |
| SHA-256 | `43b65e81fad2bc053326fc57f759f52e9dd881269dd14287177e73bf6e55c6c1` |
| Certificate SHA-256 | `1586c2bea26d90ab930a322d8442100ac23e0a09c0eca9e643727326958a5000` |
| Public API | `https://spendly-api-t1d0.onrender.com/api/v1` |

Earlier versioned APKs are preserved. The release APK has not been installed on
the owner's phone in this release run; no phone was connected. New-binary OAuth,
in-place phone update and OEM battery behavior therefore remain unverified.
Emulator tests are not a substitute for those checks.

Before public distribution, complete privacy/retention review, physical-device
coverage and any required Google Play SMS declaration/approval. SMS matching is
not cryptographic Safaricom verification. Consent remains separate from training,
and this release does not train or replace any model.

## Runtime acceptance after promotion

Verify API health reports release 1.4.0, connected database, loaded models and
`mpesa_sms_available=true`. Verify unauthenticated SMS routes reject access and
public model metadata is unchanged. Inspect the GitHub/Render deployment status
for the exact promoted revision. Do not create financial records or enable any
user's consent merely to verify a deployment. Record observed results in the
deployment PR and the private project report.
