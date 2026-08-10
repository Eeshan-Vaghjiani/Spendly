# Isolation Forest Evaluation

Training date (UTC): 2026-07-25T15:45:03.158927+00:00

Purpose: identify unusual spending behaviour. Outputs are not fraud classifications.

The model was fitted on the earlier training partition without anomaly labels as features. Existing behaviour-relative features include historical-amount deviation, recent spending change, category proportion, transaction frequency, and time since the previous transaction.

## Validation tuning

| Contamination | Precision | Recall | F1 | False-positive rate |
|---:|---:|---:|---:|---:|
| 0.0050 | 0.8000 | 0.0755 | 0.1379 | 0.0003 |
| 0.0100 | 0.5385 | 0.1321 | 0.2121 | 0.0016 |
| 0.0150 | 0.4118 | 0.1321 | 0.2000 | 0.0027 |
| 0.0200 | 0.3500 | 0.1321 | 0.1918 | 0.0036 |
| 0.0300 | 0.2045 | 0.1698 | 0.1856 | 0.0096 |

Selected contamination: **0.0100**

Selected anomaly-score threshold: **0.001414**

The threshold was selected using the chronological validation slice only. The later evaluation slice was not used for threshold selection.

## Final chronological evaluation

- Precision: **0.1634**
- Recall: **0.1374**
- F1-score: **0.1493**
- False-positive rate: **0.0093**
- Labelled anomalies: **182**
- Detected true anomalies: **25**
- Total alerts: **153**

### Detected anomalies by controlled scenario

| Anomaly type | Labelled | Detected | Recall |
|---|---:|---:|---:|
| duplicate_like_spending | 16 | 0 | 0.0000 |
| random_financial_shock | 90 | 18 | 0.2000 |
| sudden_category_change | 6 | 1 | 0.1667 |
| sudden_transaction_frequency_increase | 56 | 0 | 0.0000 |
| unexpected_recurring_expense_increase | 3 | 3 | 1.0000 |
| unusually_high_weekend_spending | 6 | 0 | 0.0000 |
| unusually_large_category_expenditure | 5 | 3 | 0.6000 |

## Alert explanations

Isolation Forest has no native per-feature causal attribution. Each flagged row therefore includes a clearly labelled heuristic explanation listing the three inputs furthest from their training medians. This is context for a user, not proof of why a tree ensemble produced the score.

## Limitations

- Evaluation labels are controlled synthetic scenarios.
- Performance does not establish real-world unusual-spending accuracy.
- Some valid but rare purchases may be flagged.
- Alerts require user review and must never be presented as fraud findings.
