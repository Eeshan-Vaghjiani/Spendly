# Spendly Development Assistant

Quit and restart OpenCode from the repository root after changing configuration, agents,
commands, or skills. Existing sessions do not hot-load this setup.

## Use

- `/app-dev <feature or bug>` selects the Spendly development agent and asks it to implement,
  test, and review the request within local safety boundaries.
- `/app-check` runs mobile checks without changing application code.
- `/app-check backend` checks the lightweight backend if its test environment is ready.
- Select `spendly-dev` as the primary agent for ongoing app work. The project's default
  agent/model is not changed, so model-research work and your provider settings still work.
- `spendly-review` is a read-only reviewer used for independent regression/security review.

`AGENTS.md` provides always-available project context. The auto-discovered `spendly-app`
skill contains detailed workflows. No separate skill installation or API key is required.

## Capabilities And Limits

The local Dart MCP server uses the installed SDK through `cmd.exe` on this Windows host.
It can expose analysis, test, and debug-session tools; exact availability depends on SDK
version and a running app. Register only the absolute `mobile/` project root. It is not
an Android remote-control service, an emulator, or an OAuth credential provider.

Permissions allow ordinary edits and a small set of routine checks without approval;
other shell/MCP actions ask. Secrets/signing files have additional restrictions and session
sharing is disabled. Content search asks because grep does not inherit file read denials;
scope searches to known non-secret source/test directories. The reviewer defaults to deny
for tools other than its explicit read/research allowances, including inherited MCP tools.
Tool rules are guardrails, not a sandbox: shell scripts/tests execute
project code, MCP has its own filesystem access, and inherited config may add permissions.
Never route around a denial or run OpenCode with `--auto` to bypass this policy.

No production credentials, global packages, SDK upgrades, release signing, deployment,
database services, or emulator data changes are installed/performed by this configuration.
Use synthetic test accounts. Explicit approval is still required for protected actions.

## Repeatable Checks

From the repository root:

```powershell
pwsh -NoProfile -File .opencode/scripts/check-app.ps1 -Suite Doctor
pwsh -NoProfile -File .opencode/scripts/check-app.ps1 -Suite Mobile
pwsh -NoProfile -File .opencode/scripts/check-app.ps1 -Suite Backend -Python .venv-app/Scripts/python.exe
```

`All` combines mobile/backend. The wrapper records failures and exits nonzero; it does not
install anything. If Flutter packages are absent, resolve them with `flutter pub get` in
`mobile/`. Backend tests need an isolated compatible Python environment, dependencies from
`backend/requirements-light.txt`, and pytest. Prefer Python 3.10-3.12; the default Python
3.13 on this machine is also used for research and should not be modified for app setup.

The live Flutter test is deliberately skipped unless explicitly enabled separately. It
creates records without cleanup, so it is not run by this wrapper against any server.
No full native integration suite exists yet. A feature that needs device verification
must add/run suitable integration checks or explicitly report that coverage as blocked.

On non-Windows hosts replace the MCP command with
`["dart", "mcp-server", "--force-roots-fallback"]` and use the appropriate Python executable.

## Setup Verification

Verified on 2026-09-09; rerun checks for future changes rather than reusing these counts:

- OpenCode recognized both agents and the spendly-app skill; Dart MCP connected.
- Flutter 3.41.4 / Dart 3.11.1: analyzer clean, 20 tests passed, 1 live test skipped.
- Backend gate correctly exited 1 because default Python 3.13 lacks pytest; no backend
  tests executed. A compatible isolated app environment remains to be provisioned.
- Five synthetic script probes passed: normal mobile checks, nonzero native exit,
  invocation exception, backend working directory, and missing Python executable.
- Android AVDs were listed but not launched: Medium_Phone_API_36.0, Pixel_8_Pro, Pixel_9.
  None is yet designated as a disposable app-test device. No device/OAuth checks ran.

No app/backend services were started, no persistent database was changed, and no emulator
was wiped. Flutter test/build caches may have been refreshed by verification.
