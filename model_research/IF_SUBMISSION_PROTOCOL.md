# Frozen Isolation Forest submission protocol

User authorization: complete the retained Isolation Forest research for submission;
mobile integration excluded. Tracking #27, parent #25. This protocol is recorded
before opening standard or shifted cohort rows in this evaluation.

## Model and decision

Retain the original selected single excess128 forest from alert archive SHA256
`98617ac130c456a5ee8917100e39451c63224ebe99877d7adb1db23c46dc4c42`.
300 trees, 128 samples, five historical excess-view features, log1p transform,
negative score_samples, threshold **0.6451359189730762**. No refit or threshold
selection. The recently fitted comparison reference/candidate are not substituted.

The retained forest fit ends2023-04-24; its original calibration threshold remains
fixed. Evaluate the final36weeks [2023-04-24,2024-01-01) of each holdout cohort.
Use only past transactions from that same user as feature context. Preserve the
historical feature implementation and eligibility (all expenses in the interval,
no new warm-up filter). Score only the retained forest; not other candidates.

R3 original manifest SHA256:
`0280b31519bf89515e5d1c105612f8f2a660880e695a903a68a814af25b0b8f5`.
Verify archive and inner CSV hashes, counts, coverage, labels and disjoint user/ID
ownership. Standard then shifted; report shifted results separately.

## Evidence and interpretation

Primary: precision, recall, F1. Supplementary: AP, ROC-AUC, FPR, accuracy, balanced
accuracy, transaction alert rate, confusion counts, family and event recall,
daily burden. Report2000-replicate user-cluster bootstrap95% intervals for
precision/recall/F1/FPR with seed42, conditional on the frozen model.

Report whether the historical80% precision/recall/F1 aspiration was met. This is
not a newly agreed supervisor acceptance threshold. Research completion means
the experiment and evidence are complete, not that every target was attained.
No tuning, candidate choice or re-evaluation based on these outcomes.

Project manifests and prior run records indicate no preceding holdout model
evaluation. A local review cannot independently attest all external notebook
sessions; this provenance limitation will remain in the submission report.

## Execution controls

- Freeze executable source hashes, protocol and versions in a pre-run lock.
- Use the original compatible numpy2.0.2/pandas2.3.3/sklearn1.6.1/joblib1.5.3
  environment; record the actual Python version. No TensorFlow inference/training.
- Write an exclusive access marker before opening each holdout archive. Failed
  reads remain recorded, and ordinary retries refuse access. A local ledger is
  not protection against a user deliberately changing/deleting its location.
- Save row scores, metrics and hashes; later reporting uses saved scores, not
  another holdout inference run. Verify serialized model reload score parity.
- Keep raw data and executable model artifacts local. Publish sanitized aggregate
  results, frozen source, notebook and protocol on a research branch only.
- Native/mobile serving changes are explicitly outside this task.
