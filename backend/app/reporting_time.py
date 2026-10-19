"""Nairobi financial calendar boundaries over UTC-stored timestamps."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

REPORTING_TIMEZONE = "Africa/Nairobi"
NAIROBI = ZoneInfo(REPORTING_TIMEZONE)


def reporting_today() -> date:
    return datetime.now(NAIROBI).date()


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def reporting_date(timestamp: datetime) -> date:
    # Database-naive datetimes are UTC. Aware input already identifies its zone.
    utc = timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp
    return utc.astimezone(NAIROBI).date()


def utc_start(local_date: date) -> datetime:
    """Return Nairobi midnight as naive UTC for SQL comparisons."""
    return datetime.combine(local_date, time.min, NAIROBI).astimezone(timezone.utc).replace(tzinfo=None)
