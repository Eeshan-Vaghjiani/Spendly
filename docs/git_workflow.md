# Branch and release workflow

Use a short feature branch for each change, for example
`feat/mpesa-sms-import` or `fix/budget-total`.

## Current owner instruction — 30 October 2026

```text
feature or fix branch -> reviewed PR -> main
deployment branch: unchanged until separate owner approval
```

The application baseline from `staging` is reconciled into `main` through its
own reviewed PR, preserving main's research and V1 artifacts. Subsequent feature
PRs target `main`; do not directly push to `main` or treat a source merge as an
APK release, migration or hosted deployment.

1. Start new work from the latest `main` after baseline reconciliation and keep changes focused.
2. Use conventional commit messages such as `feat(mobile): add M-PESA import
   settings`, `fix(api): preserve transaction ownership` or `test(android): cover
   account switching`.
3. Push the feature branch and open a PR targeting `main`, with relevant tests
   and remaining checks in its description. Review before merging.
4. Test the integrated source, including disposable database/native checks when
   applicable. Hold the deployment branch, hosted settings, persistent migrations
   and APK signing/distribution until separately approved. Updating a branch
   connected to hosting may deploy; verify the host's configured branch first.
5. Use conventional PR/merge titles too. Do not rewrite shared history merely
   to rename old commits; that cannot be applied to `main` through a normal PR.
6. Delete a feature branch only after its PR is merged and no checkout still
    needs it. Keep `staging`, the deployment branch and `main`.

The earlier feature -> staging -> deployment flow was used for private releases
1.4.0/1.4.1. Those dated release records remain historical evidence, not permission
to promote new work to the deployment branch. `staging` is a Git branch, not proof
that a separate staging server exists.

Feature/preparation PR titles include `[skip preview]` to suppress Render PR
previews. User-authorized private educational promotions are documented in
`release_1_4_0.md` and `release_1_4_1.md`. Render
documents this opt-out for both
[preview environments](https://render.com/docs/preview-environments) and
[service previews](https://render.com/docs/service-previews).

Public SMS distribution additionally requires the outstanding privacy, database
and Google Play permission checks in `mpesa_sms_import.md`. Passing unit tests
does not replace those checks.
