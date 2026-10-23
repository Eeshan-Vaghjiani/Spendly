# Branch and release workflow

Use a short feature branch for each change, for example
`feat/mpesa-sms-import` or `fix/budget-total`.

```text
feature or fix branch -> staging -> agent/spendly-live-deployment
                                -> main (submission snapshot when approved)
```

`staging` is the shared integration branch. It was created from the current
deployment branch on 23 October 2026 so existing app fixes remain in the baseline.
Its name alone does not create a staging server or change any hosting settings.

1. Start new work from the latest `staging` and keep changes focused.
2. Use conventional commit messages such as `feat(mobile): add M-PESA import
   settings`, `fix(api): preserve transaction ownership` or `test(android): cover
   account switching`.
3. Push the feature branch and open a PR targeting `staging`, with relevant tests
   and remaining checks in its description. Review before merging.
4. Test the integrated branch, including database migration and native checks
   when applicable. Promote it through a separate reviewed PR to the deployment
   branch. Updating a branch connected to hosting may deploy; obtain release
   approval and check the configured host before promotion.
5. Update `main` through a reviewed PR when the submission/release snapshot is
   ready. Do not force-push or rewrite collaborators' published history.
6. Delete a feature branch only after its PR is merged and no checkout still
   needs it. Keep `staging`, the deployment branch and `main`.

For this unreleased SMS feature, PR titles include `[skip preview]` to suppress
Render PR previews. A later, explicitly requested private educational promotion
is documented in `release_1_4_0.md`. Render
documents this opt-out for both
[preview environments](https://render.com/docs/preview-environments) and
[service previews](https://render.com/docs/service-previews).

Public SMS distribution additionally requires the outstanding privacy, database
and Google Play permission checks in `mpesa_sms_import.md`. Passing unit tests
does not replace those checks.
