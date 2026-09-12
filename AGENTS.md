# Spendly Project Guidance

Spendly is an Android-first Flutter personal-finance app backed by Flask. It tracks
income/expenses, budgets, cash flow, next-week spending estimates, unusual-spending
alerts, and rule-based recommendations. Amounts are KES. Alerts are not fraud findings.

## Work Autonomously Within Scope

- For implementation requests, inspect relevant code, implement the smallest complete
  change, add regression tests, run relevant checks, and review the diff before reporting.
- Do not stop at a plan when a bounded local implementation is possible. Ask only for
  material product ambiguity, missing access, conflicting edits, or risky external actions.
- Start with `git status --short`. Preserve unrelated edits, notebooks, exports, and
  generated files. Never reset or clean the worktree to make tests pass.
- Load the `spendly-app` skill for app/backend work. Use `spendly-review` for independent
  review of substantial auth, data, API, or UI changes; delegate non-overlapping work only.
- Prefer existing architecture and dependencies. No framework, SDK, or database upgrade
  unless necessary for the request and explicitly explained.

## Map

| Area | Sources |
|---|---|
| Flutter entry and auth routing | `mobile/lib/main.dart` |
| State and dependency injection | `mobile/lib/presentation/controllers/providers.dart` |
| Screens and shared widgets | `mobile/lib/presentation/screens/`, `mobile/lib/presentation/widgets/` |
| Theme | `mobile/lib/core/theme/app_theme.dart` |
| Domain/API contract | `mobile/lib/domain/repositories/spending_repository.dart`, `mobile/lib/data/` |
| Backend factory/routes | `backend/app/__init__.py`, `backend/app/routes/` |
| Validation and data ownership | `backend/app/schemas/`, `backend/app/repositories/` |
| Inference and feature contracts | `backend/app/services/`, `artifacts/models/` |
| Recommendation rules | `services/recommendation_engine/` |
| Tests | `mobile/test/`, `backend/tests/`, `services/recommendation_engine/tests/` |

Routes and tests outrank stale prose. Consult `README_DEVELOPMENT.md`, `START_APP.md`,
`docs/security_and_privacy.md`, and `docs/admin_management.md` when relevant.

## App Conventions

- Flutter uses Riverpod 2 StateNotifier/providers and imperative Navigator routes.
  Keep screens -> repository interface -> API repository -> ApiClient boundaries.
- Preserve the Material 3 green/mint visual language, shared panels, loading/empty/error
  states, stable widget keys, accessible controls, and small-screen/large-text layouts.
- Handle async disposal with mounted checks; dispose controllers; avoid duplicate submits.
- API prefix is `/api/v1`; responses use success/data or success/error envelopes.
  Change Dart parsing, Flask validation, and both test layers together when contracts change.
- Financial ownership must come from authenticated identity. Never trust client user IDs.
  Preserve consent gating, optional training opt-in, JWT revocation, and secure token storage.
- Username editing is not email editing. Admin sessions/CSRF are separate from mobile JWTs.
  Test logout and account switching for stale data, including failed/offline refreshes.

## Verification

Use shell-tool working directories instead of inline directory changes. Paths contain
spaces; quote them. This machine uses PowerShell, not Bash. Run Flutter commands serially
to avoid SDK startup locks. Do not use historical test counts as current evidence.

From `mobile/`, after dependency resolution if necessary:

```powershell
flutter analyze --no-pub
flutter test --no-pub
```

From the repository root, using an isolated compatible Python environment:

```powershell
python -m pytest backend/tests services/recommendation_engine/tests --ignore=backend/tests/test_model_inference.py --ignore=backend/tests/test_vertical_slice_real.py -q
```

The backend fixture uses SQLite and fake inference, but reads the checked-in V1 JSON
schemas. Plain `pytest` also includes real-model tests; do not call it the lightweight gate.
The repeatable wrapper is `.opencode/scripts/check-app.ps1`; its default is mobile checks.
It never installs dependencies, launches services, or invokes the live backend test URL.

## Local Runtime And Boundaries

- Android emulator API URL: `http://10.0.2.2:5000/api/v1`; host test URL:
  `http://127.0.0.1:5000/api/v1`. Pass explicitly; never use a tester APK's hosted URL.
- An emulator is not a disposable backend. Existing Compose uses persistent MySQL and
  applies migrations at startup. Do not start it without confirming the data target.
- `mobile/test/live_backend_test.dart` skips without `LIVE_API_BASE_URL`. With it, it
  creates an account and financial records without cleanup. Explicit disposable target only.
- No device integration suite currently exists. Widget tests are not native OAuth,
  secure-storage, file-picker, installation, or actual on-device UI verification.
- For device work, inspect devices/emulators, choose an explicitly disposable emulator,
  use a local/synthetic backend, and record the actual device and checks. Never wipe an AVD
  or use a personal device/account without approval. Stop only processes you started.
- Dart MCP supplies development tools, not unrestricted control of Android or Google login.
  Register only the `mobile/` project root. Inspect available tools before claiming support.

## Protected Actions

Do not read secrets through grep, terminal, MCP, or another tool to bypass a read restriction.
Do not log tokens, credentials, user financial records, or screenshots of real accounts.
Use synthetic fixtures and sanitized diagnostics. No automatic training on user data.

Ask before deployment, publishing/sharing, signing, hosted-service mutations, real-user
exports/deletion, persistent DB migrations/seeding, retention application, machine-wide
installs, SDK upgrades, or commits/pushes. Do not use `--auto` or blanket permission bypasses.
Do not replace V1 artifacts, run training notebooks, or alter Colab final seeds during app work.

Report: behavior changed, tests actually run, pass/fail counts, mocked versus real coverage,
remaining blockers, and any processes/artifacts left behind. Never claim complete testing
when device, backend, or production-like database checks were skipped.
