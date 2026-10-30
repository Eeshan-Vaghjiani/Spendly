# Release review — 26 October 2026

Reviewed the clean application baseline `b651382` on staging. The live release
remains API 1.4.1, deployment revision
`d9fb4989a074f6bbb731a3d901fbc98a02fb9e3a`; GitHub deployment 7278401307 reports
success. No production code, model, schema or APK was changed for this review.

## Fresh checks

| Check | Result and scope |
|---|---|
| `flutter analyze --no-pub` | No issues; 97.7 seconds |
| `flutter test --no-pub --reporter compact` | 179 passed; one intentional live-service test skipped; 34 seconds |
| Documented lightweight backend/rule pytest gate | 216 passed; six existing Alembic deprecation warnings; 52.61 seconds |
| Admin dashboard/sign-in Node tests | 18 passed; no failures or skips |
| Live `/api/v1/health` | First request timed out after 30 seconds; subsequent request succeeded with healthy API 1.4.1, database connected, portable LSTM and both models loaded, SMS capability available |

Flutter offline tests use fake repositories/HTTP fixtures. The backend gate uses
SQLite and fake inference and explicitly excludes `test_model_inference.py` and
`test_vertical_slice_real.py`. These checks do not rerun model quality evaluation
or establish physical-device, PostgreSQL, native OAuth or screen-reader behavior.
The live request was read-only; no account or financial record was created.
The first timeout is an observed delay, not a proven cold-start cause or uptime
measurement. A healthy retry does not erase that observation.

The separate [24 October installation investigation](../android_installation.md)
records integrity/signature/alignment and actual clean/repeat install/launch
checks. Those were not rerun or counted as fresh 26 October tests. JVM, native
CSV/SMS/finance and database rehearsals retain their earlier release dates.

## Browser acceptance attempt

An explicit loopback fixture used in-memory SQLite and invented accounts on
port 5059. No hosted admin account or real user data was accessed. It was intended
to check actual Chrome zoom, rather than substitute responsive viewport checks.

Computer-use automation stopped when selecting Chrome because the tool could
not determine the current browser URL with sufficient confidence to enforce its
policy. No Chrome inputs or zoom assertions were performed after that stop.
The fixture server was stopped and its temporary helper removed. No zoom,
screen-reader or focus acceptance is claimed from this attempt; issue #82 stays
open. Earlier browser evidence remains separately scoped.

## Findings and limits

- No reproducible app regression was found in the fresh automated gates or
  focused source inspection. This is not a full new page-by-page acceptance run.
- The reported phone-installation failure needs a device result; emulator success
  does not close it. The installation guide now records the exact known binary.
- Open issue bodies contained duplicated release history and stale pending-release
  wording. Current requirements and evidence are being consolidated into the
  [acceptance status](../acceptance_status.md), with completed results distinct
  from remaining phone, accessibility and institution-dependent decisions.
- Existing research, full model handoff and saved metrics are untouched. Wasaa
  live import still waits for its key/contract/verified account-link design.

No new APK/deployment is justified by this documentation-only change. Physical
installation/OAuth/OEM/radio tests, actual browser zoom/screen-reader checks,
remaining CSV process-death/provider interruption and authenticated recovery
still require their specific acceptance environment. Do not mark them passed
from the automated totals above.
