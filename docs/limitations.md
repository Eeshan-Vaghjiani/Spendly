# Project Limitations

1. All retained financial training records are synthetic.
2. Results cannot establish real Kenyan young-adult behaviour or model quality.
3. The quick history spans about 180 days and the forecast test has three
   unique target weeks.
4. Linear Regression outperformed the LSTM on current test MAE and RMSE.
5. Forecast MAPE is high, especially for small actual spending values.
6. Isolation Forest has low controlled-test precision, recall, and F1.
7. Anomaly explanations are heuristic input context, not causal attribution.
8. Category and budget patterns in live user data may differ from simulation.
9. No live M-Pesa, banking, or account-aggregation integration exists.
10. The prototype has no password-reset, token-revocation, account-erasure,
    notification, or production monitoring service.
11. Flutter is currently scaffolded for Android only.
12. A public deployment still needs TLS, rate limits, backup, monitoring,
    secret rotation, and a formal privacy/retention policy.
