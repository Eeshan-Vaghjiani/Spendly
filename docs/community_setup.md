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
| License | [MIT License](../LICENSE), explicitly approved by the owner on 14 November 2026 |
| Security policy | [SECURITY.md](../SECURITY.md); durable private reporting channel still needed |
| Issue templates | [Bug report](../.github/ISSUE_TEMPLATE/bug_report.md) and [feature request](../.github/ISSUE_TEMPLATE/feature_request.md) |
| Pull request template | [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md) |
| Accessibility (additional community file) | [ACCESSIBILITY.md](../ACCESSIBILITY.md), with reporting guidance and current verification limits |

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

## License decision — MIT approved

On **14 November 2026**, the owner explicitly selected MIT and supplied the full
license text with **Copyright (c) 2026 Eeshan Vaghjiani**. The root
[LICENSE](../LICENSE) contains that approved text. MIT permits reuse, modification,
and redistribution of the covered software, including commercially, subject to
preserving its copyright and permission notice.

The following options were considered before the decision:

| Choice | Effect and tradeoff |
| --- | --- |
| [MIT](https://choosealicense.com/licenses/mit/) | Permissive reuse, modification, and redistribution with notice preservation; simple for an academic codebase |
| [Apache-2.0](https://choosealicense.com/licenses/apache-2.0/) | Permissive reuse with an express patent license and additional notice/change obligations |
| [GPL-3.0](https://choosealicense.com/licenses/gpl-3.0/) | Copyleft: distributed derivative software must meet GPL source/license requirements; choose if that reciprocity is intended |
| [No license yet](https://choosealicense.com/no-permission/) | No general reuse/distribution permission beyond applicable law and platform terms; the GitHub license item stays incomplete |

The license covers Spendly's original application code and associated
documentation. Third-party dependencies, datasets, model artifacts, report
material, and branding may have separate rights; their existing terms and
permissions remain applicable. The owner's selection does not establish rights
to third-party material or substitute for institutional ownership requirements.

## Decisions and actions still needed

1. License selection is complete: the owner approved MIT and its copyright notice.
2. Approve setting the prepared repository description.
3. Enable GitHub private vulnerability reporting or supply a monitored private
   security contact; verify it before updating `SECURITY.md` with the actual route.
   Also confirm a confidential conduct contact and who will handle complaints.
4. Approve branch protection/rulesets if reviewed PRs must be enforced by GitHub.
   Choose a feasible reviewer policy and checks that actually run.
5. The owner authorized the commit/push/PR/merge workflow on 14 November 2026.
   After merge, verify the [Community Standards page](https://github.com/Eeshan-Vaghjiani/Spendly/community)
   and template chooser. MIT was subsequently approved separately as recorded above;
   repository-setting changes still require separate approval.
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

## Initial PR preparation

The PR is based on main at `426d54b`, using an isolated worktree. Main's newer
installation/reproducibility guide, draft-release references, academic evidence,
Nairobi reporting semantics, and 1.4.1/SMS limitations are preserved. The original
working directory retains its existing edits. The title includes `[skip preview]`
under the existing branch workflow; deployment remains separately approved work.
