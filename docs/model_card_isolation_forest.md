# Model Card: Isolation Forest v1

## Purpose

Identify transactions whose behaviour is unusual relative to available
spending history. The output is not a fraud classification.

## Data and features

- Source: controlled synthetic KES transactions
- Training rows: 41,239
- Held-out rows divided chronologically into threshold-validation and final
  evaluation slices
- Final evaluation rows: 13,877
- Positive controlled labels: 182
- Features: amount, category code, past seven-day frequency, time since prior
  transaction, historical-amount deviation, recent spending change, category
  proportion, recurring flag, hour, and weekend flag

Labels are stored separately and were not included as model features.
Robust scaling was fitted on the training partition only.

## Training and threshold

- Scikit-learn Isolation Forest
- 300 trees
- Candidate contamination values: 0.005 to 0.03
- Selected contamination: 0.01
- Threshold selected by validation F1

## Final controlled-test metrics

- Precision: 0.1634
- Recall: 0.1374
- F1-score: 0.1493
- False-positive rate: 0.00935
- True positives: 25
- False positives: 128

Performance is limited. Alerts must be presented as review prompts.

## Explanations

Isolation Forest has no native causal per-feature attribution. The API supplies
a labelled heuristic listing the three inputs furthest from their training
medians. This is context, not proof of causation.

## Expected and inappropriate uses

Expected: controlled unusual-spending prompts that a user can review.

Inappropriate: fraud accusations, transaction blocking, disciplinary action,
or performance claims about real Kenyan users.

## Artefacts

`artifacts/models/anomaly/v1/`

## Limitations

- Controlled synthetic labels may be easier or different from real anomalies.
- Recall is low and several scenario types are frequently missed.
- Valid rare spending may be flagged.
- User-level behavioural drift is not continuously recalibrated.
