---
name: spendly-app
description: Use for Spendly mobile app, Flutter screens, Riverpod state, Flask API, authentication, budgets, transactions, app debugging, and local testing. Guides implementation and verification without touching production or research models.
---

# Spendly App Workflow

Read root `AGENTS.md`. This skill is for the application, not model-research notebooks.
Paths below are repository-relative. Inspect current sources rather than treating this
document as a frozen API specification.

## Implement A Vertical Slice

1. Inspect status, relevant existing tests, and the full screen-to-API path. Define expected
   success, empty/loading, invalid-input, unauthorized, and network-failure behavior.
2. UI-only changes stay in presentation/theme unless domain behavior really changes.
   API changes include `SpendingRepository`, `ApiSpendingRepository`, response entities,
   Flask request schemas/routes/services, and contract tests as appropriate.
3. Add the narrowest regression test. Use `ProviderScope.overrides`, `FakeRepository`,
   `FakeGoogleIdentity`, `MemoryTokenStore`, and HTTP `MockClient` as existing tests do.
4. Implement; preserve stable keys, mounted checks, disposal, disabled save states,
   error/retry panels, and current Riverpod 2/Navigator conventions.
5. Format only touched Dart files. Run focused tests, analyzer, then the relevant complete
   offline suite. Review diffs and obtain independent review for substantial changes.
6. Report evidence and limitations. Missing hardware must not stop unrelated unit checks.

## Security And Domain Checks

- For auth/profile, cover 401 restoration, consent/onboarding routing, username conflicts,
  logout/account switching, optional training preference failures, and stale cached insights.
- For financial endpoints, test a second user cannot read/update/delete the first user's
  records. Keep KES rounding/date/week semantics consistent with backend behavior.
- For API retries, verify whether mutations can be duplicated. Do not add blind retries.
- For insights, preserve cold-start fallbacks and explain estimates honestly. Lightweight
  inference is not a mock; it still needs saved artifacts. No model retraining on requests.
- Use `backend/tests/conftest.py` to understand isolation before invoking tests. Inspect
  tests with unusual setup for external I/O; never assume a name guarantees safety.

## Commands

At repository root:

```powershell
pwsh -NoProfile -File .opencode/scripts/check-app.ps1 -Suite Doctor
pwsh -NoProfile -File .opencode/scripts/check-app.ps1 -Suite Mobile
pwsh -NoProfile -File .opencode/scripts/check-app.ps1 -Suite Backend -Python .venv-app/Scripts/python.exe
```

The wrapper is fail-reporting, not an installer. If Python dependencies are unavailable,
prefer an isolated Python 3.10-3.12 environment for the lightweight requirements; never
upgrade the shared research Python environment. `backend/requirements-light.txt` excludes
pytest, so a prepared test environment also needs pytest. Full TensorFlow requirements
have stricter Python compatibility. Ask before downloading a new SDK/runtime or changing
machine-wide tooling. Do not inspect `.env` to bootstrap test credentials.

At `mobile/`, for a bounded regression and formatting check:

```powershell
flutter test --no-pub test/api_client_test.dart test/widget_test.dart
dart format --output=none --set-exit-if-changed path/to/touched_file.dart
```

If dependencies are missing, run `flutter pub get` after inspecting `pubspec.yaml` and
lockfile. Do not use `pub upgrade`; inspect resulting changes. Avoid parallel Flutter
commands because the SDK uses a startup lock.

## Runtime Inspection

The configured `dart` MCP starts `dart mcp-server --force-roots-fallback` through Windows
cmd. After OpenCode restart, use the server's advertised tools to add the absolute mobile
root, inspect diagnostics, run bounded tests, and connect to a local debug session when
available. Discover current tool names; do not invent UI automation capabilities. Keep
MCP logs off because they can capture runtime data. MCP tools require approval by default.

Use `flutter devices` and `flutter emulators`. Launch only a designated test emulator;
launching an existing AVD does not authorize wiping its data. For an approved local backend:

```powershell
flutter run -d <android-device-id> --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

This repository currently has Android scaffolding only. Chrome/Windows listed by Flutter
does not mean Spendly supports those build targets. Do not run `flutter create .` to make
an unsupported target work. Real Google authentication requires authorized test credentials
and native configuration; fake Google tests do not establish OAuth success.

The live repository test is opt-in and writes accounts/records without cleanup. Require a
known disposable local database before setting `LIVE_API_BASE_URL`. Do not silently start
the persistent Compose stack. When device automation is requested, add focused Flutter
integration tests with synthetic fixtures rather than claiming widget tests tap the real app.

## Completion Gate

All applicable focused tests and offline gates pass, or each failure is clearly classified
as pre-existing, introduced, or blocked. No secrets or unintended generated artifacts in
the diff. Explain any omitted native/database/model checks and stop only owned processes.
