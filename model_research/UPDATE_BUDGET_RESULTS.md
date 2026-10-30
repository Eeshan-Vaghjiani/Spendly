# LSTM update-budget diagnostic

## Result

The same local256 fit-only windows, architecture, MAE loss, LR.001, no L2 and
seed42 were used for three actual CPU fits. Optimizer iterations were checked
directly, not inferred solely from epoch labels.

| Control | Epochs | Updates | Training MAE KES | Training WAPE |
|---|---:|---:|---:|---:|
| Batch256 |120|120|3284.23|36.34%|
| Batch32 |120|960|3104.60|34.35%|
| Batch256 |960|960|2506.45|27.73%|

At the same batch size, eight times as many updates reduced training MAE by
approximately23.7%. This supports further fitting capacity under a larger budget;
it is **not a23.7% improvement on unseen users**. All errors are on the training
subset. None met the original50% reduction relative to untrained predictions:
the best final/untrained KES-error ratio is.5366 (46.34% reduction).

The batch32/960 and batch256/960 comparison matches updates but not data exposure:
they process30,720 and245,760 examples respectively. It cannot isolate batch size
as a cause. The batch256120-versus960 comparison is the clean longer-training test.
The first-epoch logged metric differs from the untrained model error; both ratios
are retained in the aggregate report rather than being conflated.

## Reconstruction and verification limits

Only the original hash-verified R3 train.csv was read. The fixed sorted fit-user
prefix and inner time cutoff reconstruct256 windows from6 users, with the same
target mean as the saved diagnostic. The local120-update MAE3284.230940 is very
close to archived GPU3284.230943, but **full saved fit identity did not match**.
The source of that hash difference is unresolved; don't claim byte-exact archival
tensor reproduction. Local tensor fingerprints, source hashes, full configurations
and the recreated identity are retained for investigation. All three local controls
do share the exact same local tensors.

Local TensorFlow2.21 CPU differs from original Kaggle TensorFlow2.20 GPU. No
held-out performance, new architecture selection, or production readiness is
established. Model-only reload parity passed for all three controls with KES.01
tolerance; the test reuses in-memory preprocessing, not a fresh-process bundle.
Two preliminary passes were retained separately while adding provenance checks;
their displayed numerical results agree. The authoritative final report is
`evidence/v7_source_audit/update_budget_final.json`.

Three regression tests passed: declared update counts, partial-batch counting,
and independently assembled synthetic ordered reconstruction including cutoff,
excluded users, missing identities and the256-row boundary. Independent review
identified reconstruction/provenance gaps; those were addressed before the final
run. No temporary models/scalers remain, and no commits or pushes were made.

## Next decision

Do not set full training to960 epochs on the strength of this fit-only result.
Full-data runs already take many more than120 updates and may overfit if extended.
The next hypothesis, if pursued, should be a bounded train-fold comparison with
an explicit update/compute budget, reporting held-out WAPE, bias, worst-block error
and repeated seeds. Keep all difficult event weeks in evaluation. The saved
cap120/160 diagnostic did not test this hypothesis because early stopping ended
before either cap. App integration remains on hold.
