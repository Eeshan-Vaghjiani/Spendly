# Contributing to Spendly

Spendly is an Android-first Flutter personal-finance application with a Flask
backend. Contributions should preserve its academic evidence, user privacy,
and clear distinction between financial estimates and guaranteed outcomes.
Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report vulnerabilities
through [SECURITY.md](SECURITY.md), not a public bug report.

## Architecture and scope

| Area | Location and responsibility |
| --- | --- |
| Mobile UI and state | `mobile/lib/presentation/`: screens, shared widgets, Riverpod 2 providers |
| Mobile data boundary | `mobile/lib/domain/repositories/` and `mobile/lib/data/`: repository contracts, API parsing, HTTP client |
| Flask API | `backend/app/`: application factory, `/api/v1` routes, validation, authenticated ownership, services |
| Persistence | `backend/app/models/`, `backend/app/repositories/`, `backend/migrations/`: SQLAlchemy and Alembic; PostgreSQL pilot, MySQL Compose setup |
| Insights | `backend/app/services/`, `services/recommendation_engine/`: feature preparation, versioned inference, rule-based recommendations |
| Models and research | `artifacts/models/`, `model_research/`: serving artifacts and separate research evidence |
| Tests | `mobile/test/`, `mobile/integration_test/`, `backend/tests/`, `services/recommendation_engine/tests/` |

Keep screens → repository interface → API repository → API client boundaries.
Keep Flask routes thin and ownership/validation on the server. Amounts are KES.
The [architecture guide](docs/system_architecture.md),
[API guide](docs/api_guide.md), and [OpenAPI document](docs/openapi.yaml)
provide context; current routes, schemas, and tests determine the contract.
Historical model descriptions do not establish which runtime a deployment uses.

## Development setup

Commands below use PowerShell. Start in the repository root unless stated
otherwise. Read [AGENTS.md](AGENTS.md), [README_DEVELOPMENT.md](README_DEVELOPMENT.md),
and [START_APP.md](START_APP.md) before operating a database or model runtime.
For the current examiner/source workflow, see
[installation and reproducibility](docs/INSTALLATION_AND_REPRODUCIBILITY.md).
Training, seeding, retention purges, and deployment in those guides are separate
operations, not prerequisites for a normal documentation or application change.

### Prerequisites

- Git; Python 3.10 for the documented full backend/model environment.
- Flutter with a Dart SDK satisfying `mobile/pubspec.yaml` (currently `^3.11.1`),
  plus the Android SDK and an explicitly designated test emulator.
- Docker Desktop with Compose when running the documented local Flask/MySQL stack.

### Python and Flask

For the offline application tests, use an isolated environment. Python 3.10–3.12
is suitable for the lightweight requirements. On a fresh environment:

```powershell
python -m venv .venv-app
.\.venv-app\Scripts\Activate.ps1
python -m pip install -r backend/requirements-light.txt pytest
```

Reuse an existing compatible environment rather than replacing it. The lightweight
requirements omit TensorFlow and do not include pytest themselves. The full
container uses `backend/requirements.txt`; the broader research environment in
`README_DEVELOPMENT.md` uses the root `requirements.txt`.

For a local server, configure a **disposable development database** first. In a
fresh checkout without an existing `.env`, copy `.env.example` to `.env`, replace
placeholders with distinct local-only values, and verify the database target.
Never overwrite an existing configuration or commit `.env`.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Compose persists MySQL data and `backend/start.sh` applies migrations at startup.
Starting it is therefore a database operation: confirm the target with its owner
before using an existing volume. The API is at `http://127.0.0.1:5000/api/v1`;
its health endpoint is `/api/v1/health`. Use `docker compose down` to stop a stack
you started; do not delete volumes as routine cleanup. Do not seed or purge data
without separate approval. Use the checked-in model artifacts, not a training run,
for application development.

### Flutter

Run from `mobile/` after starting the intended local backend:

```powershell
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

`10.0.2.2` reaches the host from an Android emulator. Do not substitute the hosted
tester API for local testing. Android is the supported scaffold in this checkout.
Real Google authentication also needs the authorized configuration described in
[Google Sign-In setup](docs/google_sign_in_setup.md).

## Quality and testing

- Follow surrounding Python/Dart style and reuse existing components and dependencies.
  Avoid unrelated formatting, SDK upgrades, or lockfile churn.
- Preserve accessible controls, widget keys, loading/empty/error states, mounted
  checks, controller disposal, and duplicate-submit protection.
- Add focused regression coverage for behavior changes, especially money,
  authentication, account switching, ownership, and input validation.
- Change Dart parsing, Flask schemas, and both test layers together for API changes.
  Document migration compatibility and rollback considerations when schemas change.
- Keep frozen model artifacts, notebooks, evaluation results, and historical
  reports intact unless a separately reviewed research change explicitly targets them.

Run the applicable checks and record actual results. From the repository root,
with the Python environment active:

```powershell
python -m pytest backend/tests services/recommendation_engine/tests --ignore=backend/tests/test_model_inference.py --ignore=backend/tests/test_vertical_slice_real.py -q
git diff --check
```

From `mobile/`, after dependency resolution, run Flutter commands serially:

```powershell
flutter analyze --no-pub
flutter test --no-pub
```

The backend fixture uses in-memory SQLite and fake inference while reading V1
JSON schemas. The two excluded tests require real model artifacts/runtime; an
unqualified `pytest` run is not the lightweight gate. Widget tests do not prove
native OAuth, secure storage, file-picker, installation, or physical-device behavior.
The opt-in `mobile/test/live_backend_test.dart` writes accounts and financial
records without cleanup: set `LIVE_API_BASE_URL` only for an explicitly approved
disposable target. Normal offline runs leave it unset.

Native suites under `mobile/integration_test/` have their own guards and disposable
targets; follow their documented setup rather than running them against a personal
device, inbox, or hosted account.

For documentation-only changes, validate links, file references, template YAML,
and whitespace; application suites need not run unless behavior is affected.
Report commands, pass/fail/skip counts, mocked versus real coverage, and blockers.
Never copy historical test totals as evidence for a new PR.

## Security, privacy, and test data

- Use synthetic accounts and financial records in tests, issues, screenshots,
  examples, and demonstrations. Remove tokens, personal identifiers, SMS contents,
  transaction exports, database URLs, and credentials from shared diagnostics.
- Derive financial ownership from authenticated identity, never a client `user_id`.
  Preserve consent gating, separate optional training opt-in, JWT revocation,
  secure token storage, and the separate admin session/CSRF boundary.
- Test that one account cannot access another's records and that failed refreshes,
  logout, and account switching cannot restore stale financial data.
- Do not add automatic training on user records. Forecasts are estimates;
  unusual-spending alerts are review prompts, not fraud findings, and rule-based
  recommendations are not professional financial advice.

Consult [security and privacy notes](docs/security_and_privacy.md) and the newer
[admin safeguards](docs/admin_management.md) for operational context. Earlier
absence-of-feature statements are historical, not a substitute for current code.

## Branches, review, and pull requests

1. Discuss substantial changes in an issue first. Use a focused branch from
   `main`: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `test/<topic>`, or
   `chore/<topic>`. Keep research work separately scoped.
2. Prefer commit subjects such as `docs(community): explain contribution checks`.
   Preserve other contributors' edits and generated research evidence.
3. Open a PR targeting `main` using the [PR template](.github/PULL_REQUEST_TEMPLATE.md).
   Include the related issue, behavioral changes, evidence, limitations, and
   synthetic screenshots for visible changes.
4. **All changes to `main` require a reviewed PR and recorded maintainer approval
   before merge. Do not commit directly to `main`.** Identify who reviewed the
   change and resolve their comments. Automated checks or self-review must not be
   represented as independent human approval; arrange a reviewer when the author
   is the only maintainer.

This is the contribution policy, not a claim of GitHub enforcement. The read-only
check on 14 November 2026 found `main` unprotected and no repository rulesets.
Enabling required reviews/status checks needs the owner's separate approval.

### Deployment approval

Merging source into `main` does not authorize deployment. The documented release
workflow uses separate promotion to `agent/spendly-live-deployment`, with
`staging` used for release integration when requested by the maintainer.
Follow the [branch workflow](docs/git_workflow.md), including `[skip preview]`
in feature/preparation PR titles to suppress Render PR previews.
Obtain explicit owner approval before promotion, hosted-service changes,
persistent migrations/seeding, retention actions, signing, APK distribution, or
store publishing. Follow the [deployment guide](docs/live_deployment_and_tester_apk.md)
and [admin rollout guidance](docs/admin_management.md); verify the intended revision
and database before executing their commands.

## License status

No repository-wide license has been selected. Public visibility is not a general
permission to reuse or redistribute the project. Licensing options and the
pending owner decision are recorded in [community setup](docs/community_setup.md).
Do not introduce material that the project lacks permission to distribute.
