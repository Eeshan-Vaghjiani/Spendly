# Community setup: owner review

Prepared locally on **14 November 2026** for
[Eeshan-Vaghjiani/Spendly](https://github.com/Eeshan-Vaghjiani/Spendly).
The owner subsequently authorized creating and merging the documentation PR into
the default branch, `main`. GitHub recognizes the files after that merge.

## Prepared GitHub description

Copy this exact text into the repository's **About → Description** field only
after owner approval:

> Spendly is a personal finance management app for Kenyan young adults, featuring expense tracking, budgeting, spending forecasts, anomaly detection, and personalized financial recommendations.

No repository metadata was changed during preparation.

## Expected Community Standards coverage

| Item | Prepared file / remaining action |
| --- | --- |
| Description | Text above; owner approval and GitHub metadata update pending |
| README | [README.md](../README.md), with purpose, features, setup, limitations, and community links |
| Code of conduct | [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md); durable confidential contact still needed |
| Contributing | [CONTRIBUTING.md](../CONTRIBUTING.md); reviewed PR policy is documented |
| License | Pending explicit license choice; no `LICENSE` file created |
| Security policy | [SECURITY.md](../SECURITY.md); durable private reporting channel still needed |
| Issue templates | [Bug report](../.github/ISSUE_TEMPLATE/bug_report.md) and [feature request](../.github/ISSUE_TEMPLATE/feature_request.md) |
| Pull request template | [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md) |

Root community documents and `.github` template paths are GitHub-supported
locations. The issue templates include YAML `name` and `about` fields. GitHub
recognition must be checked after merge; no completion percentage is promised.

## Initial read-only GitHub observations

Checked through the public GitHub API on 14 November 2026:

- The repository is public, its default branch is `main`, and its description is empty.
- The community profile identifies a README, but no code of conduct, contributing
  guide, license, issue template, or PR template. No `.github` directory was
  returned for `main`.
- The private-vulnerability-reporting endpoint returns `enabled: false`.
  The security policy therefore does not advertise an unavailable reporting route.
- Releases and tags lists are empty. Historical APK/version references are not
  a supported-version maintenance commitment.
- `main` returns `protected: false`; the repository rulesets list is empty.
  Writing a reviewed-PR policy does not enable branch protection.

No existing project license or community configuration was found in the local
checkout. Historical academic documentation also records the missing license.

For PR preparation, authenticated inspection also identified the unpublished
`v1.4.1` draft pre-release already referenced by main's README. It remains a draft;
the earlier unauthenticated public API results do not establish its absence.

## License decision — approval required

**Recommendation: MIT for the original application code**, if the owner and any
institutional rights holders intend to permit broad academic and commercial
reuse. It is short, widely understood, and requires preservation of its copyright
and permission notice. This is a recommendation, not a license grant.

| Choice | Effect and tradeoff |
| --- | --- |
| [MIT](https://choosealicense.com/licenses/mit/) | Permissive reuse, modification, and redistribution with notice preservation; simple for an academic codebase |
| [Apache-2.0](https://choosealicense.com/licenses/apache-2.0/) | Permissive reuse with an express patent license and additional notice/change obligations |
| [GPL-3.0](https://choosealicense.com/licenses/gpl-3.0/) | Copyleft: distributed derivative software must meet GPL source/license requirements; choose if that reciprocity is intended |
| [No license yet](https://choosealicense.com/no-permission/) | No general reuse/distribution permission beyond applicable law and platform terms; the GitHub license item stays incomplete |

Before adding a license, confirm the choice, copyright holder and year, university
or collaborator ownership requirements, and coverage. Third-party dependencies,
datasets, model artifacts, report material, and branding may have separate rights;
do not imply a code license grants rights to all of them. A documentation license
can be decided separately if needed. No license file, SPDX identifier, or license
badge has been added.

## Decisions and actions still needed

1. Approve a license and its ownership/coverage details.
2. Approve setting the prepared repository description.
3. Enable GitHub private vulnerability reporting or supply a monitored private
   security contact; verify it before updating `SECURITY.md` with the actual route.
   Also confirm a confidential conduct contact and who will handle complaints.
4. Approve branch protection/rulesets if reviewed PRs must be enforced by GitHub.
   Choose a feasible reviewer policy and checks that actually run.
5. The owner authorized the commit/push/PR/merge workflow on 14 November 2026.
   After merge, verify the [Community Standards page](https://github.com/Eeshan-Vaghjiani/Spendly/community)
   and template chooser; this approval does not select a license or change settings.
6. Review the [Android listing draft and icon](store-assets/README.md). Signing,
   store account details, a published privacy-policy URL, store declarations,
   screenshots, release acceptance, and publishing approval remain separate work.

Existing academic reports and historical release evidence remain intact. Their
version-specific claims and test counts should not be read as verification of
this documentation change or the currently hosted service.

## Initial local validation record

- Nine Markdown files parsed; 60 local/post-merge links (including two heading
  anchors) and 26 explicit file/directory references resolved with exact case.
  Links to new `main` files were checked against their local destinations and
  become reachable on GitHub after merge.
- All 13 unique external links returned HTTP 200, following redirects.
- Both issue templates parsed as YAML with nonempty `name` and `about` fields;
  community file locations matched GitHub's documented conventions.
- `git diff --check` passed; new Markdown files also passed whitespace,
  final-newline, and conflict-marker checks. No dependency was installed.
- The icon decoded as a 512 × 512, 32-bit sRGB PNG (244,561 bytes); every RGB
  pixel matched the source and all alpha values were opaque.
- Hash/existence checks preserved 2,066 pre-existing paths/deletions outside
  the edited README, including original branding. The prior README research-path
  edit and its 1.2.0 release evidence were retained.

Application, backend, model, and device suites were not run for this
documentation/asset-only change. During initial local preparation, no live service,
deployment, repository setting, commit, push, or publishing operation was performed.

## PR preparation

The PR is based on main at `426d54b`, using an isolated worktree. Main's newer
installation/reproducibility guide, draft-release references, academic evidence,
Nairobi reporting semantics, and 1.4.1/SMS limitations are preserved. The original
working directory retains its existing edits. The title includes `[skip preview]`
under the existing branch workflow; deployment remains separately approved work.
