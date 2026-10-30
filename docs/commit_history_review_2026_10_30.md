# Conventional commit history review — 30 October 2026

The owner requested conventional commit names across branches, PR-only changes
to `main`, and no changes to the deployment branch pending further approval.

A read-only `git log --all --no-merges` review found six nonconventional subjects
among the locally known branch histories:

| Existing commit | Existing subject | Conventional equivalent |
|---|---|---|
| `6621405` | Initial commit | `chore: initialize Spendly project` |
| `3c13a96` | Prepare Spendly live tester deployment | `chore(deploy): prepare Spendly tester deployment` |
| `1f0612e` | Fix live admin dashboard authentication | `fix(admin): correct live dashboard authentication` |
| `86a47d6` | Support Unicode admin credentials | `fix(admin): support Unicode credentials` |
| `b0a0f85` | Release Spendly 1.2.0 with account UX and audited admin management | `feat(app): add account UX and audited admin management` |
| `35dff56` | model development-ipynb file fix | `fix(research): correct model development notebook` |

The other nonconventional-looking subjects are GitHub-generated merge messages,
not new implementation commits. New implementation, documentation, PR and merge
titles should use the existing `feat`, `fix`, `docs`, `test`, `build`, `chore`, etc.
pattern with a useful optional scope. Preserve the original meaning; do not
reclassify every historical change as a fix.

## Why the old messages have not been rewritten

These commits are already shared. Rewording one changes its ID and every
descendant ID, including branch/merge history; it can disrupt collaborators,
existing PRs, signed references and release/source evidence. The initial commit
is an ancestor of the deployment branch, which the owner explicitly put on hold.

A normal PR adds/merges history; it cannot replace the base branch's existing
commits. Consequently an all-branches rewrite conflicts with both the PR-only
`main` instruction and the deployment hold. No history rewrite or force-push has
been attempted. This audit supplies truthful replacement subjects if a separate,
coordinated rewrite is ever approved, with backups and explicit affected refs.
