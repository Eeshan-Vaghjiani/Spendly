# Optional M-PESA SMS import

Implementation and verification handoff, 23 October 2026. Work remains isolated on
`feat/mpesa-sms-import`; no Render deployment or production data operation is authorized.

## Permission and distribution decision (before adding permissions)

`READ_SMS` and `RECEIVE_SMS` are restricted Google Play permissions. Money/budget
management is a listed possible exception, subject to declaration and review;
neither consent nor a successful sideload proves Play eligibility. See
[Google's permission policy](https://support.google.com/googleplay/android-developer/answer/10208820)
and [Android default-handler guidance](https://developer.android.com/guide/topics/permissions/default-handlers).
No default-handler, accessibility or notification workaround will be used.

The normal APK will exclude SMS permissions/receivers/jobs. An explicit
`SPENDLY_SMS_CAPABILITY=true` build enables the optional native capability; the
user preference remains OFF. The server also defaults its capability OFF.
Only a disclosure acceptance in the SMS settings screen may request permissions.
No launch/login/onboarding path requests or reads SMS.

## Phase A: file and data design

- Backend: new `models/mpesa.py`, `services/mpesa_import.py`, `routes/mpesa.py`,
  strict normalized schemas and migration `0008_mpesa_sms_import`. Modify model
  exports, blueprint registration, config and transaction source serialization.
- Add account SMS consent/version/timestamp, an owner/reference-unique source
  event ledger, component links unique by event/principal-or-fee and a reversed
  transaction flag. Keep the existing owner/fingerprint uniqueness unchanged.
- Modify financial queries in repositories/analytics/admin to exclude reversed
  rows from totals/model inputs while retaining visible history. Include ledger
  data in authorized account export/deletion; do not store SMS bodies or balances.
- Android: pure Kotlin typed parser/money/date/category domain classes, encrypted
  atomic account-bound state/queue, restrictive receiver, JobScheduler service and
  a contextual MethodChannel permission bridge in MainActivity. No new Flutter
  plugin, framework, SDK or background-library upgrade is planned.
- Flutter: repository consent/batch contracts, native bridge/controller, settings
  screen and Profile link, transaction source/reversal labels, auth-boundary stop
  hook and refresh signals. Existing manual/CSV flows remain.
- Tests: Python API/schema/migration/dedupe/reversal/ownership; JVM parser and
  state tests without an Android device; Flutter fake-channel consent/UI/account
  switching; available separate-package synthetic native acceptance.

```mermaid
flowchart LR
  A[Explicit disclosure acceptance] --> B[Android permission]
  B --> C[Account-bound local consent gate]
  C --> D[MPESA sender-only inbox query or receiver]
  D --> E[Local typed parser]
  E --> F[Encrypted normalized pending events]
  F --> G[JWT batch API and server consent gate]
  G --> H[Unique source ledger and existing fingerprints]
  H --> I[Normal transactions and separate nonzero fee]
```

## Invariants and accounting

Consent and permission are separate. OFF, denied/revoked permission, missing
identity, server rejection and account changes prevent reads and parsing.
Disabling/logging out cancels work and destroys that account's pending queue.
The queue retains only normalized fields, credentials required for authenticated
background sync, a scan watermark and bounded summary counters, encrypted with
an Android Keystore key; no raw inbox cache, phone/account numbers or balances.

The backend trusts JWT ownership only. Reference identity survives edits/deletes;
payload hashes distinguish a genuine replay from a conflicting reference reuse.
Each event commits its principal and nonzero fee atomically. An existing financial
fingerprint conflict is reported for review, not silently treated as a reference
duplicate. Fees use `transaction_fees`; principal is never silently inflated.

Reversal messages must name a completed reversal and an exact original reference.
Unsupported reversal wording is ignored. A pending reversal is retained if it
arrives first. Matched principal rows become reversed and are excluded from new
totals/model inputs; fees remain expenses unless explicitly confirmed refunded.
Existing analysis outputs remain dated historical snapshots. No automatic ML
analysis runs for individual SMS or retry attempts.

The parser uses bounded specific confirmation families, exact decimal strings,
Kenya-local time converted to UTC and deterministic 2000–2099 two-digit years.
Names never determine a category. Unknown payments use `other`, person transfers
use `transfers`; airtime uses `airtime_and_data`. Cash deposits/withdrawals describe
wallet inflows/outflows, not total wealth, and may require user categorization.
Sender/body matching is not cryptographic verification by Safaricom.

## Risks and verification boundaries

OS scheduling, force-stop and battery restrictions can delay jobs. Expired or
revoked JWTs require sign-in; no stale identity may be swapped for another account.
Timeout retries use source references and database constraints. Per-account row
locks serialize consent/import/reversal where supported; uniqueness remains the
final authority, including concurrent workers.

No personal inbox may be used for automatic acceptance. Use sanitized fictional
fixtures and a disposable backend/test device. Permission approval, real-device
background/process-death delivery and production database behavior must be
reported separately from fake-channel/JVM/SQLite results. No claims of full
completion are inferred from the architecture plan alone.

## Implemented consent states

| Local feature consent | Both OS SMS permissions | Behavior |
|---|---|---|
| Off | Either state | Receiver disabled; no inbox query, PDU decode, parsing, queueing or upload |
| On | Missing/revoked | Permission required; no SMS access |
| On | Granted | Account-bound synchronization, subject to current service consent and JWT |
| On | Granted, service disabled/revoked/session expired | Pause and clear local binding when service rejection is observed |

Enabling first records the dedicated disclosure version `2026-10-22` on the
authenticated account, then binds the device to that same identity, then requests
Android permission. No permission request occurs on login, onboarding or startup.
Permission possession alone never enables import. A denied request can be retried
from this contextual screen. Closing the historical-import offer means new messages
only. Last 30 days, last 90 days and all available history require explicit selection.

Turning off first disables the receiver, cancels work, permanently cancels active
HTTP operations and destroys the local encryption key/file. The server preference
is then updated. If offline, the device remains off and the UI explains that the
service preference still needs updating. Imported transactions remain. A failed
local purge is surfaced and prevents successful logout/account switching.
An already accepted server request cannot be recalled; the shared server write
boundary gives import and consent withdrawal a definite order.

## Exact parser coverage and examples

Only sender `MPESA` or `M-PESA`, ignoring surrounding spaces/case, is accepted.
The message must begin with a ten-character ASCII alphanumeric reference and
`Confirmed`, followed by one recognized completed financial family and its date.
Formatting variations include whitespace/newlines, NBSP, case, grouped thousands,
two/four-digit years and AM/PM. Kenya local times become UTC; two-digit years use
the 2000s deterministically. Money uses `BigDecimal` locally and decimal strings /
SQL `Numeric(14,2)` on ingestion. Negative, zero-principal, excessive-precision,
malformed grouped and nonfinite amounts are rejected, including malformed fees.

| Recognized financial wording | Accounting |
|---|---|
| `Ksh214.25 sent to Example Person … on …` | Expense 214.25, neutral `transfers`; nonzero fee separately |
| `You have received Ksh2,345.60 from Fictional Sender … on …` | Income 2345.60, `other` |
| `You bought Ksh75.00 of airtime on …` | Expense 75.00, `airtime_and_data` |
| `Ksh… paid to … on …` | Completed merchant/till expense; known exact merchant aliases or `other` |
| `Ksh… sent to … for account … on …` | PayBill expense; bill-account identifier discarded |
| `You have withdrawn Ksh… from … on …` / `Ksh… withdrawn from … on …` | Wallet outflow, `transfers` |
| `Ksh… deposited into/to your [M-PESA] account on …` | Wallet inflow, `transfers` |

Phone/masked-phone suffixes and bill-account fields are removed from counterparties.
Names are not used to guess categories. Exact aliases currently cover selected
supermarkets, utilities and subscriptions; unrecognized merchants remain `other`.
Transfers and cash movements can be edited through the existing transaction form.
Wallet inflows are not proof of earnings; outflows are not proof of consumption.

The **strict synthetic-tested reversal family** is:
`Ksh… from transaction ORIGINAL has been reversed back into/from your [M-PESA]
account on …`. Optional `Transaction fee refunded, Ksh…` is required to reverse a
fee. An original reference, original amount and direction must match. Partial fee
refunds, self-references, reversal chains and financial/source conflicts fail safely
or need review. This wording has not been established as exhaustive official
Safaricom reversal syntax; other reversal templates are ignored. Pending reversals
reconcile when their original financial event arrives.

Balance text, daily limits, URLs, OTPs, adverts, failures and unrelated senders never
become financial rows. Unsupported loan/Fuliza, savings, international-currency,
partial-reversal and unfamiliar message templates are not guessed. Sender matching
is not sender authentication. See [Safaricom's fraud guidance](https://www.safaricom.co.ke/PartnerNewsletter/highlights/emerging-m-pesa-fraud-tactics).

## API, database and duplicate behavior

Example normalized request, using fictional reference and counterparty only:

```json
{
  "events": [
    {
      "external_reference": "LABS000001",
      "transaction_timestamp": "2026-10-11T13:10:00Z",
      "kind": "sent",
      "parser_version": "mpesa-v1",
      "amount": "214.25",
      "transaction_cost": "8.50",
      "transaction_type": "expense",
      "category": "transfers",
      "merchant": "Example Person"
    }
  ]
}
```

This represents 16:10 in Nairobi. It creates a KES 214.25 expense and a separate
KES 8.50 fee. It contains no SMS text, phone number, balance or client user ID.
Ownership comes from the authenticated JWT; the source is fixed by the endpoint.

- `GET /api/v1/mpesa/settings`: owner identity and dedicated service consent.
- `PUT /api/v1/mpesa/settings`: strict boolean `enabled`; enabling additionally
  requires `disclosure_accepted: true` and the exact current consent version.
- `POST /api/v1/transactions/mpesa/import`: JWT-owned `events`, 1–50 normalized
  events per batch, indexed per-event results and created/duplicate/invalid/review/
  reversal counts. Extra root/event fields, including raw SMS and user IDs, fail.
- Migration `0008_mpesa_sms_import`, after `0007_sign_in_activity`, adds three
  dedicated user consent fields, `transactions.is_reversed`, `mpesa_events` and
  `mpesa_components`. Defaults are off/not reversed; old records are preserved.

`(user_id, external_reference)` is database-unique. Each component is unique by
event and `principal`/`fee`. The original owner/fingerprint constraint is unchanged.
Canonical payload hashes normalize decimal and timezone equivalents. Same source /
same payload is a duplicate; different payload is a source conflict. A different
reference with the same financial fingerprint is retained as `needs_review`,
without creating a duplicate financial row. An event savepoint commits both
principal and fee or neither. Database failures return a sanitized retry response.

Consent changes and imports acquire the same owner write boundary. A no-op user
UPDATE before reloading consent supplies serialization on SQLite as well as row
locking on databases that support it. Unique constraints remain the final defense
against duplicate workers. No client-supplied owner is trusted.

User/admin deletion and retention explicitly detach transaction component links.
Source references, hashes and original amount/fee/direction audit values survive
transaction edits/deletes to prevent resurrection and validate later reversals.
These minimal source records currently remain until account deletion, including
after a financial-record retention purge. Authorized account export includes them;
account deletion explicitly removes them. Raw SMS, balances and phone/bill-account
identifiers are never stored in this ledger. Institutional retention review remains
necessary before a public release; there is no automatic source-ledger expiry.

Reversed rows remain visible and labelled in transaction history. Current dashboard,
cash flow, budget spending, forecast actuals and inference inputs exclude them.
Unrefunded fees still count. Existing forecasts/alerts/recommendations remain dated
historical outputs; future analyses use the revised history. Import never trains
models or triggers an analysis for each message.

## Android scheduling, queue and cancellation

The opt-in manifest declares `READ_SMS`, `RECEIVE_SMS`, `RECEIVE_BOOT_COMPLETED`
and `ACCESS_NETWORK_STATE` (required for network-constrained jobs), a
disabled-by-default sender receiver and a protected JobService.
Receiver consent/permission/account gates run before platform PDU decoding and
again under the import-state lock. Multipart messages must agree on sender and
are bounded. Inbox selection restricts sender and date/id watermark at the provider;
it does not enumerate unrelated conversations. The importer never marks SMS read
or deletes phone messages.

Native JobScheduler provides a network-bound one-shot job and a persisted
15-minute periodic job with backoff. Android can delay either; force-stop prevents
delivery until the user reopens the app. No foreground-service notification,
default-SMS role, accessibility or notification-listener workaround is added.

The encrypted queue is capped at 1,500 normalized events / 2 MB encrypted state.
Scans use pages of 200, at most 1,000 messages per job, with explicit continuation
status. A full queue does not advance past an unaccepted message. Atomic persistence
keeps queue and cursor together; a persistence error blocks subsequent activity.
Offline broadcasts can queue locally; historical scanning requires the current
server-consent check to succeed. Replays after a crash are safe at the API boundary.

AES-GCM uses an Android Keystore key and `noBackupFilesDir`; app backups are also
disabled. The pending credential is the same short-lived account JWT, not a new
cross-account credential. Authentication expiry requires sign-in and re-enabling.
Logout/switch destroys it before changing the app session. Generation fences protect
late scan/upload/UI results. HTTP redirects are disabled and response sizes bounded.
Permanent request cancellation covers the gap before first socket I/O and fences
already-started I/O; disconnect failure still reaches the cancellation fence.

Native financial-change events and app resume refresh current data. This does not
rerun model analysis. A single sync worker prevents overlapping jobs; server source
identity handles repeats from broadcasts plus historical scanning.

## Reproducing checks

Run the normal Flutter analyzer/tests from `mobile/` and the documented lightweight
Python gate from the repository root. Parser/cancellation tests:

```powershell
./gradlew.bat :app:testDebugUnitTest --console=plain
```

Run that command from `mobile/android/`. Build verification must inspect the final
APK manifest, not only the tracked base manifest. A normal build omits SMS capability;
an explicitly capable build uses `--dart-define=SPENDLY_SMS_CAPABILITY=true`.
The backend also requires its new migration and `MPESA_SMS_ENABLED=true` before
enabling can succeed. These are future deployment steps, not performed by this task.

The real-inbox acceptance target is restricted to a **new disposable emulator**:

```powershell
python -m backend.scripts.run_sms_acceptance_backend
python scripts/run_mpesa_sms_lab.py
```

The first script binds loopback port 5057 and always uses an in-memory SQLite
database. The host script requires emulator serial `emulator-5580`, emulator
hardware and the disposable-service attestation. Add an owned `adb reverse
tcp:5057 tcp:5057`, then run from `mobile/`:

```powershell
flutter test integration_test/mpesa_sms_acceptance_test.dart -d emulator-5580 --no-pub `
  --dart-define=SPENDLY_ACCEPTANCE_BUILD=true `
  --dart-define=SPENDLY_SMS_CAPABILITY=true `
  --dart-define=SPENDLY_SMS_EMULATOR_LAB=true `
  --dart-define=SPENDLY_SMS_LIFECYCLE_HARNESS=true `
  --dart-define=API_BASE_URL=http://127.0.0.1:5057/api/v1 `
  --dart-define=ACCEPTANCE_API_BASE_URL=http://127.0.0.1:5057/api/v1
```

The host driver permits only the explicitly named Spendly disposable AVDs listed
in its guard. Use an empty synthetic inbox and a newly started in-memory service
for each full run. Reusing old fixture messages invalidates the expected counts.
Test control uses `10.0.2.2:5057`, while app/native data uses the owned ADB reverse
at `127.0.0.1:5057`. Both attest the same random process `lab_id` before fixture
setup. Removing the reverse interrupts only the data path; control remains
reachable. The test observes encrypted pending state before reconnect/logout.
This tests transport failure, not a physical radio outage. Neither the native
importer nor the repository has a fallback to the control route.

After successful completion with `SPENDLY_SMS_LIFECYCLE_HARNESS=true`, build the
separate lifecycle entry point from `mobile/`:

```powershell
flutter build apk --debug --no-pub -t tool/mpesa_sms_lifecycle_main.dart `
  --dart-define=SPENDLY_ACCEPTANCE_BUILD=true `
  --dart-define=SPENDLY_SMS_CAPABILITY=true `
  --dart-define=SPENDLY_SMS_EMULATOR_LAB=true `
  --dart-define=API_BASE_URL=http://127.0.0.1:5057/api/v1
```

Install it with `adb -s emulator-5580 install -r` using that generated debug APK.
Flutter's `test` device runner uninstalls the suite package on completion. Sign
into the synthetic Alpha account in the newly installed real app, re-enable SMS
through its disclosure/permission screen and choose Only new messages. No personal
account or inbox is used. This installation and consent are test setup, not
process-death evidence. The guarded
entry point initializes Flutter bindings, verifies the disposable target and
completed checkpoint, then opens the real application with actual auth restoration.
Run `scripts/check_mpesa_sms_lifecycle.py` from the repository root. The
script checks killed-process receiver recovery with a new PID, Android force-stop
pause and reopen catch-up, and actual permission revocation. Its `finally` cleanup
withdraws synthetic service consent and uninstalls only the acceptance package.
Remove the owned reverse, stop the disposable backend/driver/emulator when done;
never stop an unrelated service or clear a personal inbox.

`SPENDLY_SMS_TEST_SOURCE=true` is the separate fake-source mode; it must not be
combined with emulator-lab mode and cannot decode real telephony broadcasts.
Both acceptance modes require the separate debug `.acceptance` package. Real inbox
lab mode additionally rejects physical hardware before SMS access. Never point the
live-backend test at a real service or use a personal inbox for automated acceptance.

## Manual acceptance checklist

1. Use a separate SMS-capable acceptance build and synthetic account on the stated
   disposable target. Confirm normal launch/login/onboarding never requests SMS.
2. Seed fictional M-PESA and unrelated/OTP messages while off. Confirm no importer
   reads/rows. Open Profile → Automatic M-PESA transactions; cancel disclosure.
3. Accept disclosure, deny Android permission: show Permission required, no reads.
   Grant contextually later; choose Only new messages and verify old history stays
   untouched. Explicitly select 30/90/all history when testing each range.
4. Confirm sent/received/airtime/merchant rows and separate nonzero fees, no balance
   or zero-fee rows, stripped phone/bill-account fields, editable categories and labels.
5. Repeat history/new-message delivery, restart and retry an ambiguous network result:
   one principal/fee pair per owner/reference. A second user's consent/data stays separate.
6. Test background and process death, real network loss, recovery and Android
   permission revocation. Force-stop requires reopening and must not be described
   as uninterrupted background delivery. Review pending/summary/error states.
7. Turn off with OS permission still granted; deliver another fictional SMS: no
   parsing/query/queue/upload. Repeat offline, logout and account switch while a
   request is paused. Confirm old pending data cannot bind to the next account.
8. Test supported full reversal before/after original, fee/no-fee refund, mismatch,
   self-reference and reversal chain. History remains visible, totals exclude only
   reconciled components. Compare current budgets/cash flow and a fresh analysis.
9. Test manual entry/CSV, narrow screens/200% text, denied service capability,
   corrupted local state and storage failure. Keep secrets and raw SMS out of logs.

## Verification record and remaining release gates

- Backend lightweight gate: **212 passed**, six existing Alembic deprecation
  warnings. Includes 39 SMS API/ownership/reversal/migration/retention/concurrency
  tests. SQLite migration upgrade/downgrade/upgrade and metadata parity passed.
- Flutter final full suite: **162 passed, one live-service test skipped**;
  analyzer: **no issues**. This includes 12 SMS consent/settings/recovery tests and
  three SMS contract/metadata/budget tests. Fake native channels do not establish
  real permission, inbox, storage or background behavior.
- JVM: **16 passed**, comprising 12 parser, three permanent-cancellation and one
  independent-cleanup test.
  A malformed grouping test exposed a partial fee match; its boundary was fixed
  and the complete JVM suite reran successfully.
- Native real-emulator acceptance: **one complete suite passed in 1m 28s** on
  the new `SpendlySmsFinal_20261023` AVD, Android API 36, Google Play x86_64,
  hardware `ranchu`, serial `emulator-5580`, 720 × 1280 at density 280. It used
  only fictional SMS and synthetic accounts against loopback in-memory SQLite.
  It verified no reads while off, actual contextual permission, three historical
  confirmations creating four rows including a fee, background delivery,
  interrupted transport/encrypted pending queue/natural retry, duplicate delivery,
  no reads after off, queued logout purge and account isolation with OS permission
  still granted. Synthetic Alpha retained exactly six rows and Beta received none.
- Separate lifecycle checks: **three passed** on the same AVD after installing
  the guarded real-app launcher and signing in/enabling through the actual UI:
  killed-process delivery with a new PID and encrypted binding restoration;
  force-stop prevents import until real-app reopen catches up; actual `READ_SMS`
  revocation confirmed in package state prevents the next import. No jobs were
  forcibly run. Cleanup withdrew fixture service consent and uninstalled the
  acceptance package. This does not establish OEM/personal-phone battery behavior.
- Earlier interrupted/System UI startup runs and a fixed-delay queue assertion
  failure are **not passes**. The final test initializes integration bindings
  before network setup and observes pending state through independent test-only
  control checkpoints instead of guessing an SMS-delivery delay.
- Normal no-flag debug APK build passed. Inspection of the actual APK with
  `aapt dump permissions` and `aapt dump xmltree ... AndroidManifest.xml`
  confirmed the original application package and **no READ_SMS, RECEIVE_SMS,
  RECEIVE_BOOT_COMPLETED, M-PESA receiver or M-PESA JobService**. Its SHA-256 was
  `5de8ebfaf5bd4f93a923910e7baa7660b4869ef60aca5ca8231ab79ed0ef1bdb`.
- Real inference/training, native Google OAuth and the existing personal phone
  were not exercised for this feature. Model artifacts and deployed behavior were
  not changed. Python fixture inference is mocked.
- PostgreSQL migration/locking still requires a disposable PostgreSQL rehearsal;
  Docker Desktop was unavailable during this run. SQLite evidence is not a
  PostgreSQL result. Production migrations and deployment were not run.
- Google Play permission declaration/approval and institutional privacy/retention
  approval remain release gates. No public distribution or Play approval is claimed.

Acceptance APK identities (debug, separate `.acceptance` package, version 1.3.5+13;
these are test artifacts, not a new distributable release):

| Entry point | SHA-256 |
|---|---|
| Integration suite | `9f810b9c41eaa60af60791fe869c7f5a44a76e0eabd1148332c8b6f03c49ccef` |
| Guarded real-app lifecycle launcher | `eb5ff1d6ed4d015cffc8c26ab14d765cda9c3ec9c6756b5e77bb7ca3bc685f96` |

Full-suite, native and lifecycle logs were kept locally under the current user's
temporary directory as `spendly-mpesa-flutter-publish.log`,
`spendly-mpesa-native-complete.log` and `spendly-mpesa-lifecycle-final.log`.
They are not committed. Test APK build output is ignored and may be overwritten
by the following normal-build verification. The stable Downloads APK is unchanged.
The normal debug APK was not installed on a personal device or copied over the
stable release. All owned app/backend/driver/emulator processes were stopped and
the owned port-5057 reverse was removed. Three new disposable AVD directories
(`SpendlySmsLab_20261022`, `SpendlySmsLifecycle_20261022`,
`SpendlySmsFinal_20261023`) remain stopped, containing fictional fixtures only;
no existing AVD or phone was wiped. Ordinary SDK/Gradle daemons may remain.

## Git handoff

Issue: [Import M-PESA transactions #89](https://github.com/Eeshan-Vaghjiani/Spendly/issues/89).
The feature branch targets `staging`; review and outstanding release gates precede
any deployment promotion. See `git_workflow.md`. No main/deployment branch push,
Render deployment, production database operation or model replacement was performed.

## Changed files

- `backend/app/config.py`
- `backend/app/models/__init__.py`
- `backend/app/models/entities.py`
- `backend/app/models/mpesa.py`
- `backend/app/repositories/financial.py`
- `backend/app/retention.py`
- `backend/app/routes/__init__.py`
- `backend/app/routes/admin.py`
- `backend/app/routes/admin_management.py`
- `backend/app/routes/analysis.py`
- `backend/app/routes/analytics.py`
- `backend/app/routes/mpesa.py`
- `backend/app/routes/transactions.py`
- `backend/app/services/alert_review.py`
- `backend/app/services/mpesa_import.py`
- `backend/migrations/versions/0008_mpesa_sms_import.py`
- `backend/scripts/run_sms_acceptance_backend.py`
- `backend/tests/test_mpesa_import.py`
- `docs/admin_management.md`
- `docs/git_workflow.md`
- `docs/mpesa_sms_import.md`
- `docs/security_and_privacy.md`
- `mobile/android/app/build.gradle.kts`
- `mobile/android/app/src/main/kotlin/com/evagh/capstone/spending_support/MainActivity.kt`
- `mobile/android/app/src/main/kotlin/com/evagh/capstone/spending_support/mpesa/BoundedInput.kt`
- `mobile/android/app/src/main/kotlin/com/evagh/capstone/spending_support/mpesa/CancelableSmsRequest.kt`
- `mobile/android/app/src/main/kotlin/com/evagh/capstone/spending_support/mpesa/MpesaImporter.kt`
- `mobile/android/app/src/main/kotlin/com/evagh/capstone/spending_support/mpesa/MpesaJobService.kt`
- `mobile/android/app/src/main/kotlin/com/evagh/capstone/spending_support/mpesa/MpesaSmsParser.kt`
- `mobile/android/app/src/main/kotlin/com/evagh/capstone/spending_support/mpesa/MpesaSmsReceiver.kt`
- `mobile/android/app/src/main/kotlin/com/evagh/capstone/spending_support/mpesa/MpesaStateStore.kt`
- `mobile/android/app/src/main/kotlin/com/evagh/capstone/spending_support/mpesa/SmsCleanup.kt`
- `mobile/android/app/src/test/kotlin/com/evagh/capstone/spending_support/mpesa/CancelableSmsRequestTest.kt`
- `mobile/android/app/src/test/kotlin/com/evagh/capstone/spending_support/mpesa/MpesaSmsParserTest.kt`
- `mobile/android/app/src/test/kotlin/com/evagh/capstone/spending_support/mpesa/SmsCleanupTest.kt`
- `mobile/integration_test/mpesa_sms_acceptance_test.dart`
- `mobile/lib/core/config/app_config.dart`
- `mobile/lib/data/models/models.dart`
- `mobile/lib/data/models/mpesa_models.dart`
- `mobile/lib/data/repositories/api_spending_repository.dart`
- `mobile/lib/data/services/mpesa_platform.dart`
- `mobile/lib/domain/repositories/spending_repository.dart`
- `mobile/lib/main.dart`
- `mobile/lib/presentation/controllers/mpesa_controller.dart`
- `mobile/lib/presentation/controllers/providers.dart`
- `mobile/lib/presentation/screens/budget_screen.dart`
- `mobile/lib/presentation/screens/home_shell.dart`
- `mobile/lib/presentation/screens/mpesa_settings_screen.dart`
- `mobile/lib/presentation/screens/privacy_info_screen.dart`
- `mobile/lib/presentation/screens/profile_screen.dart`
- `mobile/lib/presentation/screens/transaction_history_screen.dart`
- `mobile/lib/presentation/widgets/privacy_summary.dart`
- `mobile/test/mpesa_consent_test.dart`
- `mobile/test/mpesa_contract_test.dart`
- `mobile/test/privacy_summary_test.dart`
- `mobile/test/widget_test.dart`
- `mobile/tool/mpesa_sms_lifecycle_main.dart`
- `scripts/check_mpesa_sms_lifecycle.py`
- `scripts/run_mpesa_sms_lab.py`
