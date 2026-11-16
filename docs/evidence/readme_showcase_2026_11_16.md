# README showcase verification — 16 November 2026

## Scope and provenance

Documentation-only work based on `main` at `111105f`. The README reorganises the
existing app/release material and adds a five-screen gallery, workflow and
architecture diagrams, research figures and source-labelled metrics.
The supporting architecture and installation guides correct the outdated
V1-only description and unpublished-draft download instructions.

The [existing media](../media/README.md) remains authentic acceptance-build
evidence with fictional data. It is a screenshot slideshow, not a tap recording
or a recording of the distributed APK. No visual asset is regenerated.

## Research sources

- [July forecasting comparison](../../reports/forecasting_model_comparison.md):
  identical 900 chronological targets; MAE KES 3,895.086 Linear Regression,
  5,156.716 LSTM, 5,344.964 moving average and 6,798.629 previous-period naive.
  The README rounds these to two decimals. The figure source aggregates mean
  predictions across users at three target dates.
- [Final R3 IF submission](../../model_research/IF_SUBMISSION_RESULTS.md):
  standard 32,841 rows, precision 62.32%, recall 71.39%, F1 0.6655;
  shifted 32,599 rows, precision 54.73%, recall 69.95%, F1 0.6141.
  Frozen model/threshold and independent synthetic cohorts; original 80%
  aspiration not achieved.
- [Historical July IF](../../reports/isolation_forest_evaluation.md):
  precision 0.1634, recall 0.1374, F1 0.1493, reported separately from final R3.
- [V9 retained V6 export](../../model_research/V9_RESULTS.md):
  WAPE 34.523757%, MAE KES 2,616.8786, R² 0.416328 on reused R3 validation,
  not an untouched test and not the rejected checkpoint candidate.
- [Frozen Wasaa transfer](../../model_research/WASAA_TRANSFER_RESULTS.md):
  consumption LSTM WAPE 75.28%, MAE KES 11,906.71, R² −0.5988;
  46 IF alerts / 39,679 transactions, 0.1159% alert rate. The unlabelled snapshot
  cannot establish IF precision/recall/F1. Later trained/labelled notebooks are
  a different experiment. The [retention decision](../wasaa_testing_and_model_decision.md)
  preserves the poor-transfer and unpromoted-category-model findings.

## Public APK verification

Anonymous GitHub API inspection found **10 published versions and 13 APKs**;
`v1.4.1` remains Latest, published 14 November 2026. Its release page and checksum
were publicly accessible. The original APK was streamed for verification,
without saving, rebuilding or changing it:

- File: `Spendly-1.4.1-15.apk`
- Size: **55,806,018 bytes**
- SHA256: `886c4ce0a84a2ba1646e6e4d89c8540ae14ea846b497a66848e4d3d3d1627bb6`
- Digest matches both the companion checksum and GitHub asset metadata.

The Android Debug certificate, minimum Android 7/API 24 and ABI information come
from the retained [binary verification](apk_release_verification_2026_11_12.md).
This is byte-identity evidence, not a fresh signing/device/Play Protect assessment.

All **10 release pages and 24 original release assets** returned HTTP 200/206
anonymously. Historical APK availability used range requests, not a new full
checksum audit. Release IDs, tags, bodies and asset IDs/names/sizes/digests matched
the pre-edit API snapshot; download counters were excluded from that comparison.

## Documentation checks

| Check | Result |
|---|---|
| Headings and navigation | 27 unique README headings; 19 linked Markdown anchors resolved |
| Local references | 134 local links/image references across the four changed documents resolved |
| Metrics | 24 assertions matched the cited July, R3 and Wasaa records, including percentage conversion/rounding |
| Visual integrity | 9 existing image hashes unchanged; all frames decoded; GIF remains 35 frames, 1080 × 860, 21.4 seconds |
| Mermaid | Both README diagrams and the detailed architecture diagram rendered using Mermaid 11 |
| Desktop/mobile layout | Chrome at 1280px and 390px; 14 README images/badges loaded, no whole-page horizontal overflow |
| Reduced motion | Static PNG selected with reduced-motion emulation; direct static link retained |
| Scope and whitespace | Only README/supporting Markdown changes; `git diff --check` passed |
| Sensitive content | Added documentation checked for credential/private-key/token/connection-string patterns; no findings |

The pre-commit preview uses GitHub's Markdown API output and stylesheets, with
Mermaid rendered locally. The API's image-wrapping behavior differs from the
repository page, so its preview uses the original `<picture>` element after
checking the existing public README's actual markup. Final PR-page rendering is
checked separately. Wide metric tables scroll within their own containers on
mobile; gallery thumbnails link to the original checked-in images.

An independent read-only AI review found no actionable documentation findings.
It is not human maintainer approval and does not satisfy the contribution
policy's separate pre-merge review requirement.

## Coverage boundary

This task does not run application tests, inference, training, database migrations,
native Android/OAuth/SMS acceptance or hosted-backend checks. Existing test counts
are not presented as new results. No deployment or release mutation is part of
the documentation workflow.

Temporary validation scripts, HTML and browser screenshots are retained outside
the repository; they contain public documentation and synthetic app imagery.
