---
description: Run Spendly local diagnostics and relevant safe test suites, reporting actual coverage and blockers.
agent: spendly-dev
---

Load spendly-app and read AGENTS.md. Check the requested scope: $ARGUMENTS

Default to mobile analyzer and offline Flutter tests; run lightweight backend checks when
backend scope is requested or affected and an isolated environment is available. Use
.opencode/scripts/check-app.ps1. Diagnose failures without changing app code unless the
user also requests fixes. Never turn on the live test URL, start persistent Compose, or
run release packaging as part of a routine check. Report exact commands, counts, and gaps.
