# Why the Isolation Forest misses three anomaly types

All numbers below come from the existing held-out split and the committed
`reports/anomaly_predictions.parquet`. Running
`python -m models.training.detect_collective_anomalies` reproduces them.

## The observation

Three labelled anomaly types score exactly zero recall, and no amount of tuning moves
them. That is not a tuning problem — it is structural.

## Why

Isolation Forest isolates points that sit far from the bulk of the data. Comparing the
mean of each anomaly type against the mean of normal transactions, as a ratio:

| anomaly type | amount | txns last 7d | time since previous | detected |
|---|---|---|---|---|
| unusually_large_category_expenditure | **38.4x** | 0.91 | 1.02 | yes |
| unexpected_recurring_expense_increase | **29.6x** | 1.09 | 1.10 | yes |
| random_financial_shock | **20.5x** | 0.94 | 0.99 | partly |
| sudden_category_change | **16.7x** | 1.15 | 0.54 | partly |
| unusually_high_weekend_spending | 6.5x | 1.17 | 0.63 | **no** |
| duplicate_like_spending | 2.0x | 1.10 | **0.50** | **no** |
| sudden_transaction_frequency_increase | **0.42x** | **1.42** | **0.10** | **no** |

Everything the model catches is extreme in `amount`. The three it misses are not.

`sudden_transaction_frequency_increase` is the clearest case: its transactions are
**smaller than average** — 0.42x. A detector looking for extreme points will never
find them, because individually they are not extreme. They are perfectly ordinary
transactions that are only unusual *as a group*, in one user's day.

These are **collective anomalies**, not point anomalies. Isolation Forest is the wrong
shape of tool for them, and that is a property of the algorithm rather than a fault in
the data or the features.

## The fix

Aggregate first, then flag. Three rules, each measured against the same user's own
history so a high spender is not permanently suspicious:

| rule | what it measures | targets |
|---|---|---|
| `day_count_ratio` | transactions today / that user's mean per active day | frequency increase |
| `duplicate_pair` | near-identical amount, same user, within 3 hours | duplicate-like |
| `weekend_ratio` | that weekend-day's total / that user's median weekend day | weekend spending |

## Result

| detector | precision | recall | F1 |
|---|---|---|---|
| Isolation Forest only | 0.163 | 0.106 | 0.129 |
| Collective rules only | 0.084 | 0.545 | 0.145 |
| **Combined** | 0.091 | **0.600** | **0.158** |

Per type, combined:

| anomaly type | before | after | labelled |
|---|---|---|---|
| sudden_transaction_frequency_increase | 0.00 | **1.00** | 77 |
| unusually_high_weekend_spending | 0.00 | **1.00** | 6 |
| duplicate_like_spending | 0.00 | **0.54** | 24 |
| unexpected_recurring_expense_increase | 1.00 | 1.00 | 3 |
| unusually_large_category_expenditure | 0.20 | 0.60 | 5 |
| random_financial_shock | 0.23 | 0.33 | 111 |
| sudden_category_change | 0.22 | 0.22 | 9 |

## The honest caveat

**Precision drops from 0.163 to 0.091** — roughly one true flag in eleven. Recall rises
nearly six times and F1 improves, but this is a trade, not a free win.

Which side of that trade is right depends on what a flag *does*. A gentle in-app nudge
can carry false positives. Blocking a transaction cannot. The threshold sweep is
printed by `--sweep` so the operating point is chosen deliberately.

## Why accuracy was never the right metric here

Anomalies are about 1.3% of rows. A model that flags nothing scores roughly 98.7%
accuracy while catching none of them. Precision and recall are the only metrics that
say anything useful on a problem this imbalanced — which is why they are what this
report carries.

## Worth noting separately

The forecasting data has **about six months of history per user**. `moving_average_4`
consumes four of those. An LSTM has almost no sequence to learn from, which is the most
likely reason it loses to linear regression on every metric. That is a data question
rather than a modelling one, and separate from anything in this note.
