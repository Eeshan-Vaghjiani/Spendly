## Summary

Describe what changed, why, and the user-visible effect.
Include `[skip preview]` in the PR title as described in the
[branch workflow](https://github.com/Eeshan-Vaghjiani/Spendly/blob/main/docs/git_workflow.md).

## Related issue

Link the issue, or explain why this change has no issue. Use `Closes #...`
only when the PR fully resolves it. Keep vulnerability details private under
[SECURITY.md](https://github.com/Eeshan-Vaghjiani/Spendly/blob/main/SECURITY.md).

## Testing evidence

| Command or manual check | Environment / revision | Result (pass, fail, skip) |
| --- | --- | --- |
| | | |

Include actual counts where applicable. Identify mocked inference/SQLite/widget
coverage separately from real models, database migrations, native Android, and
OAuth checks. Explain anything not run and any known failures.

## Security and privacy

Describe impacts on ownership, authentication, consent, uploads, logs, permissions,
and data retention, or state why none apply. Use synthetic data only; remove
financial records, personal identifiers, tokens, credentials, and private URLs
from evidence.

## Screenshots or recordings

For visible UI changes, include synthetic before/after evidence, including
small-screen or large-text layouts where relevant. Otherwise mark not applicable.

## Compatibility and rollout

Describe API compatibility, database migrations, required deployment order,
and recovery/rollback considerations, or mark not applicable. Link any explicit
owner approval for release actions. Source review/merge is not deployment approval.

## Checklist

Mark items complete or explain why they are not applicable.

- [ ] The scope is focused and unrelated edits/research evidence are preserved.
- [ ] Relevant tests and `git diff --check` were run; results and gaps are recorded.
- [ ] API/schema changes include compatible Dart parsing, Flask validation, and tests.
- [ ] Database migrations and data-loss/rollback implications are documented and tested on disposable data when applicable.
- [ ] Documentation and examples reflect the change without overstating evidence.
- [ ] Shared fixtures, logs, and screenshots contain only synthetic/sanitized data.
- [ ] Accessibility, empty/error states, and account isolation were considered.
- [ ] A reviewer has been requested; maintainer approval will be recorded before merging into `main`.
- [ ] Any deployment/promotion, persistent migration, signing, or distribution has separate explicit owner approval; this PR does not authorize it.

Follow [CONTRIBUTING.md](https://github.com/Eeshan-Vaghjiani/Spendly/blob/main/CONTRIBUTING.md)
and the [deployment guide](https://github.com/Eeshan-Vaghjiani/Spendly/blob/main/docs/live_deployment_and_tester_apk.md).
