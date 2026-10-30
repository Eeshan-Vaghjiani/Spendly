# V7 development-only synthetic data protocol

## Scope and preregistration

Dataset version: **`spendly-synthetic-v7-dev-v1`**. This is synthetic development
replication under the unchanged R3 simulation assumptions, **not independent real
population evidence**. New pseudorandom draws do not establish Kenyan population
representativeness or real-world generalization. No model scores or aggregate QA
may select seeds, reject inconvenient users, or trigger seed tuning/regeneration.

The fixed configuration, declared before generation, is:

| Cohort | Seed | Default users | Role |
| --- | ---: | ---: | --- |
| train | 170306173 | 600 | Development fitting and inner splits |
| validation | 170417239 | 100 | Development selection, after configuration lock |
| calibration | 170528307 | 100 | Development threshold calibration |

Default coverage is **156 weeks per user**, 800 users total. All seeds are distinct
and disjoint from all five R3 cohort seeds (306173, 417239, 528307, 639373, 740419).
Seeds are fixed in source; there is no seed, cohort-selection, shift, or injection
CLI override. Counts must name exactly these three cohorts and be positive integers.
Weeks must be an integer >=24 with representable calendar coverage; 24-week small
runs are software fixtures, not replacements for the default research configuration.
Boolean, fractional, missing, extra, and nonpositive count values are rejected.

There is no test, final, or shifted cohort generation or evaluation. The builder has
no existing-dataset input and reads no existing dataset rows. It calls the existing
`synthetic_r3_data.generate_user` and `audit_user` unchanged, explicitly using
`shifted=False` and `inject=True`. R3's profile distributions, transaction generation,
noise, lookalikes, injected scenarios, and audit calculations are inherited without
parameter changes. Refer to `R3_DATA_PROTOCOL.md` for those assumptions; its holdout
generation policy does not apply to this separate development-only builder.

## Identity, labels, and observation coverage

Generated identifiers retain the `r3_<cohort>_<seed>_<index>` format, including event
and transaction IDs. New seeds separate the identity namespace from R3 without
reading R3 rows. The wrapper changes only `source_dataset` to the V7 version.
Each model CSV retains the generator's exact column order:

```text
transaction_id,user_id,transaction_timestamp,amount,category,merchant,
transaction_type,currency,is_anomaly,event_id,anomaly_type,observation_start,
observation_end,source_dataset,is_synthetic
```

Amounts are KES, timezone is Africa/Nairobi, and observation begins
`2021-01-04T00:00:00+03:00`. The exclusive end is start + the configured weeks.
Income and expenses are both exported. Every covered day is observed, including
days with zero transactions. Observed exposure must not be inferred from the first
and last transactions. Coverage QA checks constant bounds, timestamps inside the
interval, and one generator diagnostic record for every covered week/day pair.

`is_anomaly` describes injected synthetic unusual-spending scenarios, not fraud.
Labels, event IDs, and scenario families are evaluation metadata, not predictive
features. Profiles, latent parameters, expected-spend diagnostics, and audit columns
must never enter model feature matrices.

## Create-only artifacts and provenance

All configuration and source availability checks occur before creating directories.
The output root must not already exist, even if empty. Existing files, directories,
and symlinks are rejected. All artifacts use exclusive creation. No overwrite,
resume, dataset discovery, archive reading, training, or model evaluation occurs.
On failure a partial output may remain without a completed manifest; preserve it
for diagnosis and use a new path after resolving the failure.

```text
<output>/manifest.json
<output>/development/{train,validation,calibration}.csv
<output>/diagnostics_DO_NOT_TRAIN/<cohort>_user_audit.csv
<output>/diagnostics_DO_NOT_TRAIN/<cohort>_diagnostic_profiles.csv
<output>/diagnostics_DO_NOT_TRAIN/<cohort>_aggregate_qa.json
```

The manifest is written last with `status=complete`, version, currency, timezone,
weeks_per_user, exact cohort names, and each cohort's CSV path, SHA256, users, rows,
and seed. Separate diagnostic tables and aggregate QA also have hashes. `sources`
contains SHA256 digests of this protocol, the R3 protocol, the builder, and unchanged
generator source. `protocol_sha256` identifies this protocol explicitly. Provenance
records development-only synthetic replication, unchanged generator version and
functions, no existing-row access, no seed tuning, and no real-population evidence.

Per-user audits and latent profile tables are separate from model CSVs. Aggregate QA
reports exposure in user-days, complete users, active/zero transaction days, zero
expense/ordinary days, label/event support, category/type/profile counts, benign
lookalikes, and R3 diagnostic medians. Exposure is checked; diagnostic magnitudes
are descriptive only, without performance acceptance thresholds. Short fixtures may
lack seasonal or anomaly-family support. No daily latent or origin table is exported.

CSV ordering, line endings, JSON ordering, and fixed seeds support byte reproducibility
in the same Python/NumPy/pandas environment. The manifest records those versions and
omits wall-clock timestamps and elapsed times. Cross-version floating-point/RNG/CSV
serialization equivalence is not promised. Source or protocol changes alter manifest
digests even if generated CSV bytes remain unchanged. Hashes provide integrity
evidence, not cryptographic signing or access control.

## V7 loader compatibility boundary

The manifest and CSVs satisfy existing `v7_runtime.load_cohort`: `sha256`, `users`,
and `rows` are the exact model CSV bytes/composition. Files are uniquely named for
its whitelist discovery. Validation still requires `configuration_lock.json` in
the runner result directory. Diagnostics have distinct filenames.

`v7_runtime.load_manifest` explicitly accepts both R3 and V7 development versions,
preserves version provenance, and assigns `fresh synthetic development replication`
to V7 inputs. V7 manifests containing additional cohorts are rejected. Do not relabel
new inputs as R3. Builder tests exercise loader functions with a minimal cleaner;
the notebook smoke separately exercises the embedded real cleaner and V7 manifest.

## Commands and limits

From the repository root, test only (temporary fixtures are automatically removed):

```powershell
python -B -m unittest discover -s model_research -p test_v7_dataset.py -v
```

Proposed default generation command, **not executed as part of this implementation**:

```powershell
python -B model_research/build_v7_dataset.py --output datasets/spendly_synthetic_v7_dev_v1 --weeks 156 --train-users 600 --validation-users 100 --calibration-users 100
```

An optional small software fixture can use a new disposable output directory and
`--weeks 24 --train-users 2 --validation-users 1 --calibration-users 1`. Changing user
counts preserves existing indices at a fixed duration; changing weeks is not promised
to preserve a history prefix. Fixture results must not inform seed selection.
Full generation is deferred until reporting back. No full dataset, existing dataset
rows, final evaluations, notebook execution, or real-world validation is needed for
the builder's unit checks.
