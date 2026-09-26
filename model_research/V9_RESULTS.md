# V9 checkpoint-policy results

## Verified evidence

Final archive: `spendly_v9_evidence_20260926_080654.zip`.
SHA256: `e3c3b893a51d9f29976a0245a290699a829cb4c65d49a793a985f9c18972089e`.
Executed notebook: `spending-model-v9-checkpoint-kaggle.ipynb`; all10 generated
code cells and an extra setup cell have execution counts, no saved errors.

ZIP CRC and all349 manifest file hashes passed. Recomputed90 fold records,
six seed summaries, five final validation records and the paired bootstrap intervals
(1000 resamples of600 users) without discrepancies. Verified18 checkpoint records against
saved histories and best-epoch schedules. Four shared metric-audit regression
tests and two final-record coverage tests passed; the complete archive orchestration
itself has no separate synthetic ZIP fixture test.
Only ZIP/notebook JSON/CSV were read. No model deserialization, training or raw
dataset reads. Model reload parity is reported by the run, not rerun locally.

## Main result

Original R3, three seeds and matched user-separated folds. All120 epochs were
completed for each predictive-policy stopping fit. V6 original stopping was the
control; no feature/architecture/data changes were made.

| Policy | Mean WAPE | MAE KES | RMSE KES | Bias KES | Within20% |
|---|---:|---:|---:|---:|---:|
| V6 reference |32.358475%|2272.4463|7026.3045|-1506.5165|48.7130%|
| Predictive full budget |32.354624%|2272.1759|7027.1961|-1509.1671|48.8194%|

Gain: **0.003851 percentage points WAPE / KES0.2704 MAE**. Paired candidate-minus-
reference95% interval **[-0.013335,+0.006120]pp** includes zero. The1pp material
criterion fails despite passing practical guards. The selected model remains
**v6_reference**. Internal adaptive intervals are not independent confirmation.

Seed42 WAPE improves32.373598% to32.366357%; seed123 improves32.383145% to32.378834%;
seed2026 is exactly unchanged at32.318683%. Across18 paired fold/seed fits, the
restored epoch differs in only three of the nine policy pairs. The changed pairs
are seed42 fold1 (65→105), seed42 fold2 (60→93), seed123 fold2 (51→116).
Other pairs select the same epoch; the identical training recipe gives identical
refit predictions there. Per-user summed error improves212 users, is equal for200,
and worsens188. This is not a practical model breakthrough.

Highest-spending10/5/1% week groups slightly worsen in candidate WAPE; the prior
large-week weakness is not resolved. The tiny-fit23.7% training gain therefore did
not translate into a meaningful gain from this full-data checkpoint intervention.
This does not rule out all possible optimization or modeling improvements.

## Time and final model

Comparison stopping+refit training totals: reference661.1s, candidate797.1s,
approximately20.6% more training for the candidate. Total recorded run time2223.7s
(37.1min) excludes final compression; feature generation524.6s, all training1579.1s.
These measured timings are for this Kaggle run, not future runtime guarantees.

The final exported fallback's validation predictions reproduce WAPE34.523757%,
MAE KES2616.8786, RMSE KES7755.9940, R2.416328, bias -KES1777.4890 and within20%47%.
This is validation of the retained reference, not the rejected candidate.
Only original R3 train/validation cohorts are recorded in the access log. No
anomaly training or final/shifted-cohort evaluation is part of V9.

## Decision

Retain V6; stop extending checkpoint/epoch tuning on the strength of the tiny-fit
result. V7/V8/V9 tested different ideas but none met the promotion criterion.
Keep app activation on hold until the intended product behavior and evidence are
reviewed. Useful next directions are a clearly evaluated uncertainty estimate or
observable planned expenses, rather than promising precise predictions of random
future shock events. Those change the question and need their own data/protocol.

V7 alert results remain a separate outstanding review. V9 provides a complete
forecast evidence archive but cannot answer whether the collective rules helped.

Reproduction command:

```powershell
python model_research/analyze_v9_results.py --archive "<final V9.zip>" --output "<aggregate report.json>"
```

Aggregate audit: `evidence/v7_source_audit/v9_results_verified.json`.
No commits, pushes or deployment performed during this analysis.
