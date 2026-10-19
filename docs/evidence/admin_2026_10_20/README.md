# Synthetic admin and PostgreSQL acceptance — 20 October 2026

Source: issue-60 PR, based on release 1c17d3a8739c27fd18cf3d75551216a11266390e.
No hosted credentials or real user records were used.

## Browser target and results

`python -m backend.scripts.run_admin_acceptance_backend` binds 127.0.0.1:5058,
uses in-memory SQLite and the actual portable V6 registry. Its deterministic
fixture has 25 example.invalid accounts, 45 invented transactions and one budget.
The same connection is retained without recycling; HTTP serving is serial.

Verified through the actual browser:

- Login/logout, account pages 1/2, search from page 2 resetting to page 1.
- Selected account transaction pages 1/2/3 (45 records), final Next disabled.
- Audit pages 1/2 and return to page 1.
- Transaction correction 125.50 → 130.75 KES; totals changed by 5.25 KES.
- Incorrect reconfirmation password rejected; password field cleared.
- Display-name correction; protected identity/consent fields absent from the form.
- Budget correction 6000 → 6500.25 KES and new transport budget 500.50 KES.
- Export downloaded: 45 transactions/one budget at export time, with credential
  hashes and Google subject excluded. The generated local JSON was removed.
- Account disable/enable, delete prerequisite, exact-username warning and Cancel
  preserving the account. Final irreversible browser deletion was not submitted;
  successful deletion and wrong confirmation were tested against PostgreSQL below.

Screenshots contain only these invented records. The corrections screenshot
shows the restored active account and both budget amounts. The deletion screenshot
shows the explicit irreversible-action warning with empty password/confirmation.
Earlier narrow-layout, keyboard and offline-retry evidence remains in
`../admin_2026_10_19/README.md`.

## Actual PostgreSQL rehearsal

The owner started Docker Desktop with existing project containers stopped.
The only new target was `spendly-acceptance-pg-20261020`, loopback port 55432,
384 MiB memory cap, one CPU, tmpfs database storage and automatic container removal.
PostgreSQL reported **16.15**; image `postgres:16-alpine` digest:
`sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`.

`python -m backend.scripts.rehearse_acceptance_postgres` passed:

1. Refuse a nonempty target; use only a fixed disposable loopback database.
2. Upgrade to 0004, insert an invented legacy account, upgrade through
   `0006_alert_reviews`, preserve that account and default token version zero.
3. Compare Alembic/ORM metadata against PostgreSQL: no differences.
4. Export an invented account, reject deletion while active, disable it, reject
   wrong username and delete it with exact confirmation.
5. Verify dependent Transaction/AlertReview cleanup, retained deletion audit and
   survival of the unrelated legacy account.

`pg_dump -Fc` followed by `pg_restore --exit-on-error` into a second disposable
`spendly_recovery` database succeeded. Restored queries returned migration
`0006_alert_reviews`, one legacy account and one deletion audit. This rehearses
backup recovery rather than an unsafe downgrade of audit/revocation migrations.
A repeat invocation of the migration script rejected the nonempty original target
before migration/write activity; its legacy account and head revision remained.
No Neon connection, persistent Compose database or production migration was used.

## CORS and limits

The blueprint now disables cross-origin browser access by default. Actual Flask
preflights verify an empty list and untrusted origin receive no allow-origin
header; an explicit trusted origin works. Android and same-origin admin are
unaffected. The environment parser also ignores the older blanket `*` value so
a retained host setting cannot preserve unrestricted access. Before this change,
a read-only live preflight reflected the untrusted origin; post-deploy validation
is recorded separately in the PR.
This is not an authentication or CSRF replacement.

The final PR records gate counts and cleanup. Model inference was not evaluated by
the PostgreSQL script; actual portable inference is covered by native acceptance.
No real OAuth, native picker, signed Android update, production concurrency or
restore of a hosted backup is claimed.

Cleanup verified: both owned loopback servers stopped, the owned PostgreSQL
container stopped/removed, and ports 5057/5058/55432 had no listener. Its database,
backup and recovery copy were discarded. The downloaded official PostgreSQL image
remains cached. Docker Desktop was started by the owner and was left running.
Browser logged out; the generated synthetic JSON export was removed. The two
screenshots and this report are intentional evidence artifacts.

Fixture credentials are now supplied at runtime: the browser fixture requires
`SPENDLY_ACCEPTANCE_ADMIN_PASSWORD` (at least 16 characters); the PostgreSQL
rehearsal requires `SPENDLY_ACCEPTANCE_PG_PASSWORD` matching its disposable
container. The rehearsal generates its own ephemeral admin password internally.
No reusable admin/database password is embedded in these scripts or logged.
The PostgreSQL procedure and recovery checks were repeated successfully after
this change; that second container was also removed.
