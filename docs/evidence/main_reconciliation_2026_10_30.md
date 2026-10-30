# Main application baseline reconciliation — 30 October 2026

The owner requested new work through PRs into `main`, with no direct main push
and no deployment-branch change. `main` at `6c57913` lacked the current private
app sources on staging `5c33d42`, including the M-PESA prerequisites for #107.

## Reconciliation boundaries

Prepared a main-based `chore/reconcile-app-main` merge branch. Resolved the old
research-directory rename conflict by preserving main's research tree exactly.
Kept main's generated-output trees, diagram scripts, optional OpenCode tooling
configuration and Render blueprint rather than importing unrelated staging copies.

Before committing, both comparisons completed with exit code 0:

```powershell
git diff --cached origin/staging --exit-code -- backend mobile services/recommendation_engine services/aligned_inference artifacts/candidates/selected_v6
git diff --cached origin/main --exit-code -- artifacts/models model_research university_trial_colab services/spend_advisor output tmp render.yaml .opencode opencode.json scripts/build_chapter4_diagrams.mjs scripts/build_chapter4_drawio.py scripts/build_chapter4_source_style.mjs scripts/qa_chapter4_drawio.py scripts/qa_chapter4_source_style.py
```

No V1 artifact, research notebook/seed or advisor code was replaced or executed.
The existing selected V6 serving bundle comes unchanged from the app baseline.
No application logic was newly written for this reconciliation. README, agent
guidance, acceptance/workflow notes and the conventional-history audit were
updated to reflect the owner's actual main-first flow and available tooling.

## Checks actually run on the reconciled tree

- Flutter analyzer: **no issues found**.
- Flutter offline suite: **179 passed, one intentional live-backend skip**.
- Backend/recommendation lightweight gate: **217 passed**, six existing Alembic
  deprecation warnings; SQLite/synthetic fixtures and fake endpoint inference.
- Admin Node suite: **18 passed**.
- Independent integration review checked the source/protected-tree comparisons
  and found no code-level integration blocker. Its two workflow/tooling guidance
  findings were fixed and independently rechecked with no new findings.

The shell gates were used because the Dart MCP test/analyzer calls in the prior
settings work timed out. Flutter commands were serial, and locked dependencies
were resolved without upgrades.

## Delivery boundary

This is source reconciliation through a PR, not a new private APK or deployment.
The deployment remote-tracking ref was `d9fb4989a074f6bbb731a3d901fbc98a02fb9e3a`
before this work. `render.yaml` is deliberately preserved from main; its flags
are not asserted to match the live deployment. No migrations, server changes,
signing, hosted/private data access, new model evaluation or training occurred.

No native/device, hosted database or real-model gate was run for this merge.
Existing acceptance/privacy/public-distribution issues retain their own gates.
The baseline and feature worktrees plus normal build/dependency caches remain;
no app, backend listener, emulator or database process was launched.
