"""Non-secret release identity; do not infer a deployed revision from local Git."""
import re
from flask import current_app

API_RELEASE = "1.4.0"


def inference_runtime(registry):
    return "portable_lstm" if hasattr(registry, "forecast_history") else getattr(registry, "runtime", "unknown")


def release_info():
    revision = current_app.config.get("SOURCE_REVISION") or ""
    return {"api_release": API_RELEASE,
            "source_revision": revision if isinstance(revision, str) and re.fullmatch(r"[0-9a-fA-F]{40}", revision) else None}
