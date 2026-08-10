"""Shared utilities for the capstone data pipeline."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml

LOGGER = logging.getLogger("finance_data_pipeline")
DEFAULT_SEED = 42


def configure_logging(verbose: bool = False) -> None:
    """Configure consistent console logging for command-line scripts."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def repo_root_from_file(file_path: str | Path) -> Path:
    """Return the repository root for a file located under scripts/."""
    return Path(file_path).resolve().parents[1]


def load_config(root: Path, config_path: str | Path | None = None) -> dict[str, Any]:
    """Load the YAML configuration and apply small backwards-compatible defaults."""
    path = Path(config_path) if config_path else root / "config" / "data_config.yaml"
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    config.setdefault("random_seed", DEFAULT_SEED)
    config.setdefault("selected_age_range", [18, 35])
    config.setdefault("synthetic_data_inclusion", True)
    return config


def mode_config(config: dict[str, Any], mode: str) -> dict[str, Any]:
    """Return global configuration merged with the selected mode settings."""
    if mode not in {"quick", "full"}:
        raise ValueError("mode must be 'quick' or 'full'")
    merged = dict(config)
    merged.update(config.get("modes", {}).get(mode, {}))
    merged["mode"] = mode
    return merged


def ensure_output_directories(root: Path) -> None:
    """Create pipeline-owned folders without touching original repository files."""
    for relative in (
        "config",
        "data/original",
        "data/processed",
        "data/synthetic",
        "data/model_ready",
        "reports",
        "scripts",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write a compressed Parquet file atomically enough for local pipeline use."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, engine="pyarrow", compression="zstd")


def write_csv_sample(df: pd.DataFrame, path: Path, rows: int = 250) -> None:
    """Write a compact CSV sample alongside a model or canonical Parquet dataset."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.head(rows).to_csv(path, index=False)


def write_json(payload: Any, path: Path) -> None:
    """Write deterministic, human-readable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=json_default, sort_keys=True)


def json_default(value: Any) -> Any:
    """JSON conversion for common NumPy, pandas and Path values."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if pd.isna(value):
        return None
    raise TypeError(f"Cannot serialize {type(value)!r}")


def parse_mixed_dates(series: pd.Series) -> pd.Series:
    """Parse the known date variants conservatively, leaving failures as NaT."""
    text = series.astype("string").str.strip()
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y%m%d",
        "%d%b%Y",
        "%Y_%m",
    )
    for fmt in formats:
        missing = result.isna() & text.notna()
        if not missing.any():
            break
        result.loc[missing] = pd.to_datetime(text.loc[missing], format=fmt, errors="coerce")
    missing = result.isna() & text.notna()
    if missing.any():
        result.loc[missing] = pd.to_datetime(text.loc[missing], errors="coerce")
    return result


def numeric_amount(series: pd.Series) -> pd.Series:
    """Convert currency-decorated values to floats without inferring exchange rates."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = (
        series.astype("string")
        .str.replace(",", "", regex=False)
        .str.replace(r"\(([^)]+)\)", r"-\1", regex=True)
        .str.extract(r"([-+]?\d*\.?\d+)", expand=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def safe_identifier(series: pd.Series) -> pd.Series:
    """Normalize identifiers as strings while retaining missing values."""
    output = series.astype("string").str.strip()
    return output.mask(output.isin(["", "nan", "None", "<NA>"]))


def normalize_category(value: Any) -> str:
    """Map common noisy category labels to a compact canonical vocabulary."""
    text = re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()
    aliases = {
        "fod": "Food",
        "foodd": "Food",
        "foods": "Food",
        "food drink": "Food",
        "groceries": "Food",
        "rentt": "Rent",
        "utilties": "Utilities",
        "utlities": "Utilities",
        "educaton": "Education",
        "health": "Healthcare",
        "medical": "Healthcare",
        "travel": "Transport",
        "gas fuel": "Transport",
        "coffee shops": "Food",
        "fast food": "Food",
        "alcohol bars": "Entertainment",
    }
    if text in aliases:
        return aliases[text]
    return text.title() if text else "Other"


def append_lineage(root: Path, records: Iterable[dict[str, Any]]) -> None:
    """Append and de-duplicate output lineage records."""
    path = root / "reports" / "data_lineage.csv"
    new = pd.DataFrame(list(records))
    if path.exists():
        old = pd.read_csv(path)
        new = pd.concat([old, new], ignore_index=True)
    if not new.empty:
        key = [column for column in ("output_path", "pipeline_stage", "mode") if column in new]
        if key:
            new = new.drop_duplicates(subset=key, keep="last")
        new.to_csv(path, index=False)


def chronological_boundaries(dates: pd.Series) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return 70% and 85% chronological boundaries over unique timestamps."""
    unique_dates = pd.Series(pd.to_datetime(dates).dropna().unique()).sort_values()
    if len(unique_dates) < 3:
        raise ValueError("At least three unique timestamps are required for splitting")
    train_index = min(len(unique_dates) - 2, max(0, int(np.floor(len(unique_dates) * 0.70)) - 1))
    validation_index = min(
        len(unique_dates) - 1,
        max(train_index + 1, int(np.floor(len(unique_dates) * 0.85)) - 1),
    )
    return pd.Timestamp(unique_dates.iloc[train_index]), pd.Timestamp(unique_dates.iloc[validation_index])
