"""Create-only V7 development replication using the unchanged R3 simulator."""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import platform
from types import MappingProxyType

import numpy as np
import pandas as pd

import synthetic_r3_data as r3
from synthetic_r3_data import audit_user, generate_user

VERSION = 'spendly-synthetic-v7-dev-v1'
ALLOWED_COHORTS = ('train', 'validation', 'calibration')
# Preregistered before generation; never selected against diagnostics or scores.
SEEDS = MappingProxyType(dict(train=170306173, validation=170417239, calibration=170528307))
DEFAULT_COUNTS = MappingProxyType(dict(train=600, validation=100, calibration=100))
SOURCE_FILES = ('build_v7_dataset.py', 'synthetic_r3_data.py',
                'V7_DATA_PROTOCOL.md', 'R3_DATA_PROTOCOL.md')
MODEL_COLUMNS = (
    'transaction_id', 'user_id', 'transaction_timestamp', 'amount', 'category',
    'merchant', 'transaction_type', 'currency', 'is_anomaly', 'event_id',
    'anomaly_type', 'observation_start', 'observation_end', 'source_dataset',
    'is_synthetic',
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_config(output, weeks, counts):
    """Validate the complete configuration before making any directories."""
    if type(weeks) is not int or weeks < 24:
        raise ValueError('weeks must be an integer >=24 (156 for the default run)')
    try:
        end = r3.START + timedelta(weeks=weeks)
    except (OverflowError, ValueError) as error:
        raise ValueError('weeks exceeds supported calendar coverage') from error
    # The generator advances month starts beyond the final observed month.
    if end.year >= 9999:
        raise ValueError('weeks exceeds supported calendar coverage')
    counts = DEFAULT_COUNTS if counts is None else counts
    if not isinstance(counts, Mapping) or set(counts) != set(ALLOWED_COHORTS):
        raise ValueError('counts must contain exactly train, validation, calibration')
    if any(type(n) is not int or n < 1 for n in counts.values()):
        raise ValueError('every cohort needs a positive integer user count')
    if len(set(SEEDS.values())) != 3 or set(SEEDS.values()) & {v[0] for v in r3.COHORTS.values()}:
        raise ValueError('V7 seeds must be distinct and disjoint from all R3 seeds')
    if not isinstance(output, (str, Path)) or not str(output).strip():
        raise ValueError('output must be a nonempty directory path')
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f'Create-only output already exists: {output}')
    # Inspect ancestors without reading any existing dataset contents.
    if any(parent.exists() and not parent.is_dir() for parent in output.parents):
        raise ValueError('output parent must be a directory')
    return output, {name: counts[name] for name in ALLOWED_COHORTS}, end


def coverage_audit(frame, daily, end):
    """Check declared full exposure, separately from days containing transactions."""
    if tuple(frame.columns) != MODEL_COLUMNS:
        raise ValueError('Unexpected generator model CSV schema')
    required = [c for c in MODEL_COLUMNS if c not in ('event_id', 'anomaly_type')]
    if frame[required].isna().any().any():
        raise ValueError('Missing required model CSV values')
    start = pd.to_datetime(frame.observation_start, utc=True)
    stop = pd.to_datetime(frame.observation_end, utc=True)
    times = pd.to_datetime(frame.transaction_timestamp, utc=True)
    days = (end - r3.START).days
    expected_days = {(w, d) for w in range(days // 7) for d in range(7)}
    if (not start.eq(r3.START).all() or not stop.eq(end).all()
            or not times.ge(start).all() or not times.lt(stop).all()
            or len(daily) != days or set(zip(daily.week, daily.day)) != expected_days):
        raise ValueError('Observation coverage violation')
    observed_days = times.dt.tz_convert('Africa/Nairobi').dt.date.nunique()
    return dict(observation_start=r3.START.isoformat(), observation_end=end.isoformat(),
                observation_days=days, transaction_days=int(observed_days),
                zero_transaction_days=days - int(observed_days),
                first_transaction=frame.transaction_timestamp.iloc[0],
                last_transaction=frame.transaction_timestamp.iloc[-1],
                coverage_complete=True)


def write_json(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def table_entry(path, output, rows):
    return dict(csv=path.relative_to(output).as_posix(), sha256=sha256(path), rows=rows)


def build(output, weeks=156, counts=None):
    output, counts, end = validate_config(output, weeks, counts)
    here = Path(__file__).resolve().parent
    # Missing provenance sources also fail before any output is created.
    sources = {name: sha256(here / name) for name in SOURCE_FILES}
    manifest = dict(
        version=VERSION, status='complete', currency='KES', timezone='Africa/Nairobi',
        weeks_per_user=weeks, counts=counts, cohorts={}, sources=sources,
        protocol_sha256=sources['V7_DATA_PROTOCOL.md'], synthetic_only=True,
        development_only=True, holdout_model_evaluations=0,
        provenance=dict(
            purpose='synthetic development replication', generator_version=r3.VERSION,
            independent_real_population_evidence=False, existing_dataset_rows_accessed=False,
            seed_policy='fixed preregistered seeds; no seed tuning',
            generator_functions=['synthetic_r3_data.generate_user', 'synthetic_r3_data.audit_user'],
            shifted=False, inject=True, generated_cohorts=list(ALLOWED_COHORTS),
            source_dataset_override=VERSION, identity_policy='unchanged R3-generated identifiers',
        ),
        environment=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
    )
    output.mkdir(parents=True, exist_ok=False)
    development = output / 'development'
    diagnostics = output / 'diagnostics_DO_NOT_TRAIN'
    development.mkdir()
    diagnostics.mkdir()
    for cohort in ALLOWED_COHORTS:
        print(f'Generating {cohort}: {counts[cohort]} users, {weeks} weeks',flush=True)
        path = development / (cohort + '.csv')
        audits, profiles = [], []
        family_counts, category_counts, type_counts = {}, {}, {}
        with path.open('x', encoding='utf-8', newline='') as handle:
            for index in range(counts[cohort]):
                frame, profile, daily, origins = generate_user(
                    SEEDS[cohort], index, cohort, weeks=weeks, shifted=False, inject=True)
                coverage = coverage_audit(frame, daily, end)
                audit = audit_user(frame, profile.iloc[0], daily, origins)
                audit.update(coverage)
                audits.append(audit)
                profiles.append(profile)
                # Preserve every generated value except the wrapper dataset provenance.
                frame = frame.assign(source_dataset=VERSION)
                frame.to_csv(handle, index=False, header=index == 0, lineterminator='\n')
                if (index+1)%50==0:
                    print(f'  {cohort}: {index+1}/{counts[cohort]} users',flush=True)
                for column, totals in [('anomaly_type', family_counts), ('category', category_counts),
                                       ('transaction_type', type_counts)]:
                    for value, n in frame[column].value_counts().items():
                        totals[str(value)] = totals.get(str(value), 0) + int(n)
        audit = pd.DataFrame(audits)
        row_count = int(audit.rows.sum())
        exposure = int(audit.observation_days.sum())
        summary = dict(
            total_rows=row_count, users=len(audit), expenses=int(audit.expense_rows.sum()),
            anomaly_transactions=int(audit.anomaly_transactions.sum()),
            anomaly_prevalence=float(audit.anomaly_transactions.sum() / audit.expense_rows.sum()),
            events=int(audit.events.sum()), profiles={str(k): int(v) for k, v in audit.profile.value_counts().items()},
            family_counts=family_counts, category_counts=category_counts, transaction_type_counts=type_counts,
            observation_coverage=dict(
                start=r3.START.isoformat(), end_exclusive=end.isoformat(),
                expected_user_days=counts[cohort] * weeks * 7, observed_user_days=exposure,
                complete_users=int(audit.coverage_complete.sum()),
                transaction_days=int(audit.transaction_days.sum()),
                zero_transaction_days=int(audit.zero_transaction_days.sum()),
                zero_expense_days=int(audit.zero_expense_days.sum()),
                zero_ordinary_days=int(audit.zero_ordinary_days.sum()),
                zero_expense_day_fraction=float(audit.zero_expense_days.sum() / exposure),
                zero_ordinary_day_fraction=float(audit.zero_ordinary_days.sum() / exposure)),
            diagnostic_medians={c: float(audit[c].median()) for c in (
                'conditional_ordinary_noise_ratio', 'utilities_cv', 'realized_payday_ratio',
                'realized_weekend_ratio', 'realized_holiday_ratio')},
            benign_lookalikes={c: int(audit[c].sum()) for c in ('benign_duplicate', 'benign_burst', 'benign_large')},
        )
        tables = {}
        for name, table in [('user_audit', audit), ('diagnostic_profiles', pd.concat(profiles, ignore_index=True))]:
            diagnostic_path = diagnostics / f'{cohort}_{name}.csv'
            table.to_csv(diagnostic_path, index=False, mode='x', lineterminator='\n')
            tables[name] = table_entry(diagnostic_path, output, len(table))
        qa_path = diagnostics / f'{cohort}_aggregate_qa.json'
        write_json(qa_path, summary)
        manifest['cohorts'][cohort] = dict(
            **table_entry(path, output, row_count), users=counts[cohort], seed=SEEDS[cohort],
            shifted=False, model_evaluated=False, status='development_available',
            audit=summary, diagnostic_tables=tables,
            aggregate_qa=dict(json=qa_path.relative_to(output).as_posix(), sha256=sha256(qa_path)))
    manifest['total_rows'] = sum(entry['rows'] for entry in manifest['cohorts'].values())
    # Completion is published last. A failed build has no manifest and cannot resume.
    write_json(output / 'manifest.json', manifest)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new, nonexisting output directory')
    parser.add_argument('--weeks', type=int, default=156)
    for cohort in ALLOWED_COHORTS:
        parser.add_argument(f'--{cohort}-users', type=int, default=DEFAULT_COUNTS[cohort])
    args = parser.parse_args(argv)
    counts = {name: getattr(args, name + '_users') for name in ALLOWED_COHORTS}
    try:
        manifest = build(args.output, args.weeks, counts)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    print(f"Completed {VERSION}: {manifest['total_rows']} rows; development only")


if __name__ == '__main__':
    main()
