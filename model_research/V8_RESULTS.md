# V8 observed-income results

## Evidence reviewed

Archive: `spendly_v8_evidence_20260926_044353_forecast_complete.zip`.
SHA256: `be107c13edbb27f4960f935e4d68067a5015526d636551c66aa9eab3dacec6b6`.
This forecast-stage backup contains completed selection, diagnostics, final refit,
validation predictions and the selected model. It predates the final figures and
artifact manifest, but contains sufficient CSV/JSON evidence for this forecast review.

ZIP CRC passed, 543 checkpoint-referenced hashes matched, and published stage
output hashes matched. Independently recalculated all330 fold metric records
(including baselines), checked prediction residuals and unique user/week coverage,
and reproduced all five candidates'1000-resample paired user-bootstrap intervals.
All five final validation records matched the3600 exported prediction rows.
No model was unpickled or executed for this review; saved reload-parity metadata
reports a passed KES.01 tolerance. GPU preflight records /GPU:0. No full inference
reproduction, app tests or production validation was performed.

## Decision

Original synthetic R3 dataset;600 training users with15,709 observed income rows.
Five configurations, three seeds, identical grouped chronological evaluation rows.

| Candidate | Mean WAPE | Mean MAE KES |
|---|---:|---:|
| V6 reference |32.358475%|2272.4463|
| Predictive-stopping control |32.396195%|2275.0953|
| Income context |32.339246%|2271.0959|
| Income sequence |32.326372%|2270.1918|
| Income + category sequence |**32.298784%**|**2268.2544**|

Provisional winner income_category improves pooled WAPE by0.059691 percentage
points (~0.1845% relative) and MAE by KES4.19 per weekly prediction. The paired
candidate-minus-reference95% interval is[-0.141910,+0.022190]pp, crossing zero.
Practical guards pass, but the1pp material threshold and interval criterion do not.
The selected/exported model is correctly **v6_reference**, not income_category.
Intervals are conditional on adaptive selection, not independent confirmation.

## Stability and remaining weaknesses

| Seed | Reference WAPE | Income/category WAPE |
|---|---:|---:|
|42|32.373598%|32.236759%|
|123|32.383145%|32.321028%|
|2026|32.318683%|32.338566%|

Candidate wins two seeds and loses one. It improves per-user aggregate error for
314/600 users (52.3%). Mean bias worsens from -KES1506.52 to -KES1533.12; within20%
rises only from48.7130% to48.9491%. Fold0/2 WAPE improves and fold1 worsens slightly.

Among the highest actual-spending10% of evaluated weeks, candidate WAPE42.0366%
is slightly worse than reference41.9750%. The top1% remains approximately71.58%
WAPE. These are descriptive outcome-based subgroups, not deployable features.
Observed-income features did not resolve the expensive-week error concentration.

The diagnostics ran on the retained reference, not the rejected income/category
candidate. They therefore repeat the reference findings: cap120/160 gave identical
results under predictive stopping; tiny-subset error fell29.65% but missed its50%
reduction criterion; sequence-order sensitivity remains small. These do not prove
an irreducible information ceiling or establish candidate-specific behavior.

## Final reused validation

Exported V6 reference: WAPE34.523757%, MAE KES2616.8786, R2.416328,
bias -KES1777.4890 (-23.4499%), within20%47.0%. Recurring median: WAPE35.146722%,
MAE KES2664.0990. This is the fallback refit, not final validation of income_category.
All values were independently recomputed from the supplied row predictions.

## Conclusion and next work

The hypothesis was tested successfully; a substantial forecast gain was not found.
Retain V6 and report the negative result. Do not describe0.0597pp as0.0597 absolute
WAPE or5.97pp, and do not present WAPE as classification accuracy.

Before another version, investigate the expensive-week errors and limited tiny-fit
capability on permitted development data: bill timing, ordinary versus injected
spending, feature/target reconstruction and optimization. Income alone is not a
demonstrated solution. Any new architecture or loss change requires a separately
declared experiment; no seed or generator tuning to manufacture gains.

V8 was forecast-only and contains no new anomaly evaluation. The V7 final anomaly
reports remain required for issue #7. App integration remains on hold. The full
V8 final ZIP is useful for archived plots/final manifest, but another run is not
needed to establish the conclusion above. No commits, pushes or deployment were
made during this review.
