# Final demonstration checklist

This is a proposed rehearsal, not evidence that every step has passed. Use only
invented accounts and transactions on an explicitly disposable local backend.
The approved SRS and institutional rubric determine the assessed requirements.

## Preparation

- [ ] Confirm the approved SRS, report template, presentation length and deadline.
- [ ] Record the source revision, APK version/hash and selected model identities.
- [ ] Rehearse the approved build. Record the [current private release](release_1_4_0.md)
  separately from [staging UI evidence](evidence/ui_polish_2026_10_23.md).
  The [native acceptance procedure](release_1_3_4.md)
  uses a separate Android package and in-memory database; it does not configure Google OAuth.
- [ ] Prepare an empty synthetic account and a separate account with eight known
  complete preceding weeks. Eight transactions alone do not establish coverage.
- [ ] Prepare a copy of the [CSV template](transaction_upload_template.csv)
  with invented records for valid, invalid and duplicate import cases.
- [ ] Capture genuine required screenshots and note their build/test target.

## Suggested sequence

| Step | Demonstrate | Explain |
|---|---|---|
| Accounts | Synthetic registration/sign-in and consent | Ownership is authenticated; training opt-in is optional |
| Cold start | Income/expense entry, balances and partial insights | No forecast is fabricated when history is insufficient |
| Financial controls | Budget and transaction editing, invalid values and repeated Save | KES totals remain accurate; duplicate writes are prevented |
| Import | Actual chooser and created/duplicate/invalid counts | Native picker evidence is separate from widget tests |
| Optional SMS import | Synthetic messages on the designated acceptance emulator | Consent starts OFF; sender matching is not cryptographic verification; no personal inbox is a demo fixture |
| Forecast | Dated estimate using known complete synthetic history | WAPE measures error; estimates can be wrong |
| Alerts/advice | Linked expense review and intentional-spending confirmation | Alerts are not fraud; confirmed expenses remain in totals |
| Account safety | Logout then sign into the empty synthetic account | Earlier balances/insights must not carry over |
| Admin | Synthetic user search, successful sign-in history, audit and model evidence | Enabled does not mean online; no device/IP tracking is implied |
| Research | Retained R3 results and Wasaa transfer findings | Synthetic datasets and incompatible experiments are clearly labelled |

Admin mutation examples require an approved disposable synthetic target. The
public production backend and personal financial records are not demo fixtures.

## Final review

- [ ] Map demonstrated behavior to actual approved SRS clauses.
- [ ] Distinguish mocks, actual saved-model inference, physical Android execution,
  disposable PostgreSQL and read-only hosted checks.
- [ ] Explain final IF F1 0.6655/0.6141, Wasaa LSTM WAPE75.28%, false alerts,
  underprediction and the original Wasaa snapshot's missing anomaly labels.
- [ ] Finish native OAuth, CSV/lifecycle, device accessibility/offline and signed
  update/rollback evidence in #22/#56. This checklist does not replace those checks.
- [ ] Finish references, limitations, installation instructions and supervisor review.

Consumer web dashboard remains paused. Optional M-PESA SMS import is in the
private 1.4.0 release; public distribution and physical-device coverage have
separate gates. New Wasaa live import #95 waits for the key, contract and secure
linking. Its earlier dataset evaluation is already documented. No automatic
model-training cycle is required to finish the educational prototype.
