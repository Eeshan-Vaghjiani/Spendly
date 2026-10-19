"""Read allowlisted aggregate evidence only for the loaded artifact identity."""

import hashlib
import json
import math
from urllib.parse import urlparse

IDENTITY_FIELDS = ("format", "weights_sha256", "source_forecast_sha256", "source_alert_sha256", "threshold")
METRICS = {"rows", "MAE_KES", "RMSE_KES", "WAPE", "R2", "bias_KES", "within_20_percent",
           "precision", "recall", "F1", "FPR", "TP", "FP", "FN", "TN"}


def evaluation_metadata(path, identity):
    unavailable = {"status": "unavailable", "cohorts": []}
    try:
        with path.open('rb') as source_file:
            raw = source_file.read(100_001)
        if len(raw) > 100_000:
            return {name: unavailable.copy() for name in ("forecasting", "anomaly")}
        data = json.loads(raw)
        expected = {key: identity[key] for key in IDENTITY_FIELDS}
        if data.get("schema_version") != 1 or data.get("identity") != expected:
            raise ValueError("Evidence identity differs")
        result = {}
        for name in ("forecasting", "anomaly"):
            cohorts = []
            for item in data[name]:
                metrics = {key: value for key, value in item["metrics"].items() if key in METRICS}
                if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)
                       for value in metrics.values()):
                    raise ValueError("Invalid aggregate metric")
                source = item["source"]
                url = urlparse(source["url"])
                if url.scheme != "https" or url.netloc != "github.com" or not url.path.startswith("/Eeshan-Vaghjiani/Spendly/blob/"):
                    raise ValueError("Invalid evidence source")
                cohorts.append({"label": str(item["label"]), "scope": str(item["scope"]),
                                "limitation": str(item["limitation"]), "metrics": metrics,
                                "source": {"url": source["url"], "sha256": source["sha256"]}})
            result[name] = {"status": "artifact_matched", "cohorts": cohorts,
                            "metadata_sha256": hashlib.sha256(raw).hexdigest()}
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, RecursionError):
        return {name: unavailable.copy() for name in ("forecasting", "anomaly")}
