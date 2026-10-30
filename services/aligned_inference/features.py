"""Shared causal feature construction for the aligned LSTM/Isolation Forest models.

Both the research notebook lineage and the opt-in backend adapter use this module so
the two cannot silently diverge. Everything here is past-only and label-blind: no
column named label, is_anomaly, anomaly_type, event_id or family is ever read.

Inputs are cleaned expense frames with columns user_id, transaction_id,
transaction_timestamp (naive Africa/Nairobi), amount (KES), category, merchant.
"""

from __future__ import annotations

from collections import defaultdict, deque
from types import MappingProxyType

import numpy as np
import pandas as pd

LOOKBACK_WEEKS = 8
RECURRENCE_HISTORY_WEEKS = 26
REPORTING_TIMEZONE = "Africa/Nairobi"

FORECAST_FEATURES = tuple(
    [f"lag{i}" for i in range(1, 9)]
    + [f"nonrec_lag{i}" for i in range(1, 9)]
    + [
        "mean4",
        "std8",
        "recurring",
        "nonrecurring",
        "log_scale",
        "nonrec_median",
        "nonrec_std",
        "due_confidence",
        "count4",
        "zero_fraction",
    ]
)

ANOMALY_FEATURES = (
    "amount_ratio",
    "category_ratio",
    "category_deviation",
    "merchant_ratio",
    "count_hour",
    "sum_hour_ratio",
    "count_day",
    "sum_week_ratio",
    "duplicate_hour",
    "merchants_hour",
    "night_rarity",
    "category_rarity",
    "user_cold",
    "merchant_missing",
)

DERIVED_ANOMALY_FEATURES = (
    "category_excess",
    "merchant_excess",
    "rare_large",
    "burst_amount",
)

#: Ground-truth columns that must never influence a feature value.
FORBIDDEN_COLUMNS = frozenset(
    {"label", "is_anomaly", "anomaly_type", "event_id", "family"}
)


class InsufficientHistory(ValueError):
    """A genuine caller-visible precondition: not enough observed history."""


class TargetWindowError(ValueError):
    """A server-side contract fault: bad target alignment, timezone or grouping."""


def utc_to_reporting_time(values) -> pd.Series:
    """Convert stored naive UTC timestamps to the naive Nairobi wall clock.

    Backend rows are persisted as naive UTC. Every feature here is defined on
    Nairobi calendar weeks and local hours, so skipping this conversion silently
    shifts week buckets and night-time flags by three hours.
    """
    series = pd.to_datetime(pd.Series(values), errors="raise")
    if series.dt.tz is None:
        series = series.dt.tz_localize("UTC")
    return series.dt.tz_convert(REPORTING_TIMEZONE).dt.tz_localize(None)


def _required(frame: pd.DataFrame) -> None:
    missing = {"user_id", "transaction_id", "transaction_timestamp", "amount", "category", "merchant"} - set(frame.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    present = FORBIDDEN_COLUMNS & set(frame.columns)
    if present:
        # Fail loudly rather than relying on the loop happening not to read them.
        raise ValueError(
            "Ground-truth columns must not be supplied to feature construction: "
            + ", ".join(sorted(present))
        )
    if frame.empty:
        raise ValueError("Transaction history is empty")
    amounts = pd.to_numeric(frame["amount"], errors="coerce")
    if not np.isfinite(amounts).all():
        raise ValueError("Amounts must be finite KES values")
    if frame["transaction_timestamp"].isna().any():
        raise ValueError("Transaction timestamps must be present")
    if not frame.index.is_unique:
        raise ValueError("Transaction frame requires a unique index")


def infer_schedule(group: pd.DataFrame, minimum: int = 2) -> dict | None:
    """Monthly or short-cycle schedule inferred from observed history only."""
    dates = pd.DatetimeIndex(group.transaction_timestamp).unique().sort_values()
    if len(dates) < minimum:
        return None
    months = dates.year * 12 + dates.month
    monthly = months.is_unique and dates.day.max() - dates.day.min() <= 3
    gaps = np.diff(dates.to_numpy()) / np.timedelta64(1, "D")
    if monthly and np.median(np.diff(months)) <= 2 and np.max(np.diff(months)) <= 3:
        step, period = "month", 30.0
        anchor = int(round(float(np.median(dates.day))))
    else:
        period = float(np.median(gaps))
        if not 5 <= period <= 16 or np.median(np.abs(gaps - period)) > 0.12 * period:
            return None
        step, anchor = "days", None
    amounts = group.sort_values("transaction_timestamp").amount.tail(6)
    amount = float(amounts.median())
    if amount <= 0 or float(np.median(np.abs(amounts - amount))) > 0.30 * amount:
        return None
    return dict(
        last=dates[-1],
        amount=amount,
        step=step,
        period=period,
        anchor=anchor,
        confidence=min(1.0, (len(dates) - 1) / 2),
    )


def next_occurrence(schedule: dict, current: pd.Timestamp) -> pd.Timestamp:
    if schedule["step"] == "month":
        month = current.normalize().replace(day=1) + pd.DateOffset(months=1)
        day = min(schedule["anchor"], month.days_in_month)
        return month.replace(day=day) + (schedule["last"] - schedule["last"].normalize())
    return current + pd.Timedelta(days=round(schedule["period"]))


def schedule_features(history, left, right, lag_start, pooling=True, minimum=2):
    """Category pooling recovers a bill whose merchant changed between cycles."""
    due, recurring_ids, confidence = 0.0, set(), []
    groups = []
    for _, category in history.groupby("category", sort=True):
        schedule = infer_schedule(category, minimum) if pooling else None
        if schedule is not None:
            groups.append((category, schedule))
        else:
            groups.extend(
                (merchant, infer_schedule(merchant, minimum))
                for _, merchant in category.groupby("merchant", sort=True)
            )
    for group, schedule in groups:
        if schedule is None:
            continue
        due_date = next_occurrence(schedule, schedule["last"])
        if due_date < left - pd.Timedelta(days=40):
            continue
        while due_date < right:
            if due_date >= left:
                due += schedule["amount"]
                confidence.append(schedule["confidence"])
            due_date = next_occurrence(schedule, due_date)
        recurring_ids.update(
            group.loc[group.transaction_timestamp.ge(lag_start), "transaction_id"]
        )
    return due, recurring_ids, float(np.mean(confidence)) if confidence else 0.0


def _forecast_row(group: pd.DataFrame, boundaries, index, pooling=True):
    left, right = boundaries[index], boundaries[index + 1]
    lag_start = boundaries[index - LOOKBACK_WEEKS]
    window = group.loc[group.transaction_timestamp.lt(left) & group.transaction_timestamp.ge(lag_start)]
    week = window.transaction_timestamp.dt.normalize() - pd.to_timedelta(
        window.transaction_timestamp.dt.weekday, unit="D"
    )
    totals = window.groupby(week).amount.agg(["sum", "count"]).reindex(
        boundaries[index - LOOKBACK_WEEKS : index], fill_value=0.0
    )
    past = totals["sum"].to_numpy()
    scale = max(float(np.mean(past)), 1.0)
    history = group.loc[
        group.transaction_timestamp.lt(left)
        & group.transaction_timestamp.ge(left - pd.Timedelta(weeks=RECURRENCE_HISTORY_WEEKS))
    ]
    due, ids, confidence = schedule_features(history, left, right, lag_start, pooling)
    discretionary = window.loc[~window.transaction_id.isin(ids)]
    dweek = discretionary.transaction_timestamp.dt.normalize() - pd.to_timedelta(
        discretionary.transaction_timestamp.dt.weekday, unit="D"
    )
    nonrec = (
        discretionary.groupby(dweek)
        .amount.sum()
        .reindex(boundaries[index - LOOKBACK_WEEKS : index], fill_value=0.0)
        .to_numpy()
    )
    values = [
        *(past[::-1] / scale),
        *(nonrec[::-1] / scale),
        past[-4:].mean() / scale,
        past.std() / scale,
        due / scale,
        nonrec.mean() / scale,
        np.log(scale),
        np.median(nonrec) / scale,
        nonrec.std() / scale,
        confidence,
        float(totals["count"].iloc[-4:].mean()),
        np.mean(past == 0),
    ]
    context = dict(
        user_id=group.user_id.iloc[0],
        time=left,
        end=right,
        scale=scale,
        recurring=due + float(nonrec.mean()),
        due=due,
    )
    return context, values


def next_week_features(data: pd.DataFrame, target_start, pooling: bool = True, observed_through=None, observed_from=None):
    """One forecast input for one user, using only observations before target_start.

    ``observed_through`` attests that history is complete up to that instant. Without
    it the caller must accept that a dormant account yields a near-zero forecast built
    from eight empty weeks, so it is required here rather than inferred.
    """
    _required(data)
    left = pd.Timestamp(target_start)
    if left.tzinfo is not None or left != left.normalize() or left.weekday() != 0:
        raise TargetWindowError("Target must be Monday midnight in normalized Nairobi time")
    if data.user_id.nunique() != 1:
        raise TargetWindowError("Exactly one user history is required")
    if observed_through is None:
        raise InsufficientHistory("Explicit observation coverage through the target start is required")
    coverage = pd.Timestamp(observed_through)
    if coverage.tzinfo is not None:
        raise TargetWindowError("Observation coverage must be a naive Nairobi timestamp")
    if coverage < left:
        raise InsufficientHistory("Recorded history does not reach the requested forecast week")
    past = data.loc[data.transaction_timestamp.lt(left)].sort_values(
        ["transaction_timestamp", "transaction_id"]
    )
    if past.empty:
        raise InsufficientHistory("Observed transaction history is empty")
    start = past.transaction_timestamp.min().normalize()
    if observed_from is not None:
        start = pd.Timestamp(observed_from)
        if pd.isna(start) or start.tzinfo is not None or start >= coverage:
            raise TargetWindowError('Observation start must be a finite local timestamp before coverage end')
        past = past.loc[past.transaction_timestamp.ge(start)]
        if past.empty:
            raise InsufficientHistory('No recorded spending within observation coverage')
    if start > left - pd.Timedelta(weeks=LOOKBACK_WEEKS):
        raise InsufficientHistory("At least eight complete weeks of history are required")
    lag_start = left - pd.Timedelta(weeks=LOOKBACK_WEEKS)
    if not past.transaction_timestamp.ge(lag_start).any():
        # A coverage attestation cannot distinguish "spent nothing" from "stopped
        # recording". With no observation in the whole lookback there is no signal to
        # forecast from, and scale would collapse to the 1 KES floor.
        raise InsufficientHistory("No recorded spending in the eight weeks before the forecast week")
    # Nine lag boundaries plus the target week's closing boundary.
    boundaries = pd.date_range(
        left - pd.Timedelta(weeks=LOOKBACK_WEEKS), left + pd.Timedelta(weeks=1), freq="7D"
    )
    context, values = _forecast_row(past, boundaries, LOOKBACK_WEEKS, pooling)
    return pd.DataFrame([context]), pd.DataFrame([values], columns=list(FORECAST_FEATURES))


def anomaly_features(data: pd.DataFrame) -> pd.DataFrame:
    """Per-transaction causal features; simultaneous rows share only earlier history."""
    _required(data)
    values = []
    for _, group in data.groupby("user_id", sort=False):
        group = group.sort_values(["transaction_timestamp", "transaction_id"])
        history = deque(maxlen=100)
        categories = defaultdict(lambda: deque(maxlen=40))
        merchants = defaultdict(lambda: deque(maxlen=20))
        recent, category_counts, seen, nights = deque(), defaultdict(int), 0, 0
        for t, batch in group.groupby("transaction_timestamp", sort=True):
            while recent and recent[0][0] < t - pd.Timedelta(days=7):
                recent.popleft()
            hour = [r for r in recent if r[0] >= t - pd.Timedelta(hours=1)]
            day = [r for r in recent if r[0] >= t - pd.Timedelta(days=1)]
            for row in batch.itertuples():
                amount, category, merchant = row.amount, row.category, row.merchant
                typical = max(float(np.median(history)) if history else 1.0, 1.0)
                cat = categories[category]
                centre = max(float(np.median(cat)) if cat else typical, 1.0)
                spread = max(
                    float(np.median(np.abs(np.asarray(cat) - centre))) * 1.4826 if cat else 0.0,
                    centre * 0.20,
                    1.0,
                )
                merchant_centre = max(
                    float(np.median(merchants[merchant])) if merchant and merchants[merchant] else centre,
                    1.0,
                )
                night = t.hour < 5 or t.hour >= 23
                values.append(
                    (
                        row.Index,
                        [
                            amount / typical,
                            amount / centre,
                            max(0.0, (amount - centre) / spread),
                            amount / merchant_centre,
                            len(hour),
                            sum(r[1] for r in hour) / typical,
                            len(day),
                            sum(r[1] for r in recent) / typical,
                            sum(
                                bool(merchant) and r[2] == merchant and r[3] == category and abs(r[1] - amount) < 0.01
                                for r in hour
                            ),
                            len({r[2] for r in hour if r[2]}),
                            float(night) * (1 - (nights + 1) / (seen + 2)),
                            1 - category_counts[category] / max(1, seen),
                            float(seen < 10),
                            float(not merchant),
                        ],
                    )
                )
            for row in batch.itertuples():
                history.append(row.amount)
                categories[row.category].append(row.amount)
                if row.merchant:
                    merchants[row.merchant].append(row.amount)
                recent.append((t, row.amount, row.merchant, row.category))
                seen += 1
                nights += int(t.hour < 5 or t.hour >= 23)
                category_counts[row.category] += 1
    frame = pd.DataFrame(
        [v for _, v in values], index=[i for i, _ in values], columns=list(ANOMALY_FEATURES), dtype=float
    ).reindex(data.index)
    frame["category_excess"] = np.maximum(0.0, frame.category_ratio - 1.0)
    frame["merchant_excess"] = np.maximum(0.0, frame.merchant_ratio - 1.0)
    frame["rare_large"] = frame.category_rarity * np.log1p(frame.category_excess) * (1 - frame.user_cold)
    frame["burst_amount"] = frame.count_hour * np.log1p(frame.amount_ratio)
    return frame


ANOMALY_VIEWS = MappingProxyType(
    {
        "all": list(ANOMALY_FEATURES) + list(DERIVED_ANOMALY_FEATURES),
        "context": [
            "category_ratio",
            "category_deviation",
            "merchant_ratio",
            "count_hour",
            "duplicate_hour",
            "rare_large",
            "burst_amount",
        ],
        "excess": ["category_excess", "merchant_excess", "duplicate_hour", "rare_large", "burst_amount"],
    }
)
