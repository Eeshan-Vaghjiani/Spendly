"""Train, tune, and evaluate Isolation Forest for unusual spending."""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import RobustScaler


LOGGER = logging.getLogger(__name__)
FEATURES = [
    "amount",
    "category_code",
    "transaction_count_last_7d",
    "time_since_previous_hours",
    "deviation_from_historical_average",
    "recent_spending_change",
    "category_proportion",
    "is_recurring",
    "hour_of_day",
    "is_weekend",
]


def repository_root(file_path: str | Path) -> Path:
    return Path(file_path).resolve().parents[2]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Configuration must be a mapping: {path}")
    return payload


def chronological_validation_mask(
    timestamps: pd.Series, fraction: float
) -> pd.Series:
    if not 0 < fraction < 0.5:
        raise ValueError("validation_fraction must be between 0 and 0.5.")
    unique_dates = pd.Series(pd.to_datetime(timestamps).sort_values().unique())
    cutoff_index = max(0, min(len(unique_dates) - 2, int(len(unique_dates) * fraction) - 1))
    cutoff = unique_dates.iloc[cutoff_index]
    return pd.to_datetime(timestamps) <= cutoff


def binary_metrics(
    labels: np.ndarray, predictions: np.ndarray
) -> dict[str, float | int]:
    labels = labels.astype(bool)
    predictions = predictions.astype(bool)
    tn, fp, fn, tp = confusion_matrix(
        labels, predictions, labels=[False, True]
    ).ravel()
    return {
        "precision": float(
            precision_score(labels, predictions, zero_division=0)
        ),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn),
        "predicted_anomalies": int(predictions.sum()),
        "labelled_anomalies": int(labels.sum()),
        "rows": int(len(labels)),
    }


def select_threshold(
    scores: np.ndarray,
    labels: np.ndarray,
    minimum_recall: float,
) -> tuple[float, dict[str, float | int]]:
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    if not len(thresholds):
        threshold = float(np.quantile(scores, 0.99))
        predictions = scores >= threshold
        return threshold, binary_metrics(labels, predictions)
    candidates: list[tuple[float, float, float, float]] = []
    for index, threshold in enumerate(thresholds):
        denominator = precision[index] + recall[index]
        f1 = (
            2 * precision[index] * recall[index] / denominator
            if denominator
            else 0.0
        )
        candidates.append(
            (
                float(f1),
                float(precision[index]),
                float(recall[index]),
                float(threshold),
            )
        )
    eligible = [
        candidate for candidate in candidates if candidate[2] >= minimum_recall
    ]
    selected = max(eligible or candidates, key=lambda value: (value[0], value[1]))
    threshold = selected[3]
    return threshold, binary_metrics(labels, scores >= threshold)


def alert_explanation(
    row: pd.Series,
    scaled_row: np.ndarray,
    feature_names: list[str],
) -> str:
    ranked = np.argsort(np.abs(scaled_row))[::-1][:3]
    values = [
        f"{feature_names[index]}={row[feature_names[index]]:.3f}"
        for index in ranked
    ]
    return (
        "Heuristic explanation based on the most atypical inputs relative to "
        "training medians: " + ", ".join(values) + "."
    )


def markdown_report(
    metadata: dict[str, Any],
    tuning: pd.DataFrame,
    overall: dict[str, float | int] | None,
    by_type: pd.DataFrame,
) -> str:
    lines = [
        "# Isolation Forest Evaluation",
        "",
        f"Training date (UTC): {metadata['training_date_utc']}",
        "",
        "Purpose: identify unusual spending behaviour. Outputs are not fraud "
        "classifications.",
        "",
        "The model was fitted on the earlier training partition without anomaly "
        "labels as features. Existing behaviour-relative features include "
        "historical-amount deviation, recent spending change, category proportion, "
        "transaction frequency, and time since the previous transaction.",
        "",
        "## Validation tuning",
        "",
        "| Contamination | Precision | Recall | F1 | False-positive rate |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in tuning.to_dict(orient="records"):
        lines.append(
            f"| {row['contamination']:.4f} | {row['precision']:.4f} | "
            f"{row['recall']:.4f} | {row['f1']:.4f} | "
            f"{row['false_positive_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            f"Selected contamination: **{metadata['selected_contamination']:.4f}**",
            "",
            f"Selected anomaly-score threshold: **{metadata['decision_threshold']:.6f}**",
            "",
            "The threshold was selected using the chronological validation slice "
            "only. The later evaluation slice was not used for threshold selection.",
            "",
            "## Final chronological evaluation",
            "",
        ]
    )
    if overall is None:
        lines.append(
            "No compatible labels were available, so no precision, recall, F1, "
            "or false-positive-rate values were invented."
        )
    else:
        lines.extend(
            [
                f"- Precision: **{overall['precision']:.4f}**",
                f"- Recall: **{overall['recall']:.4f}**",
                f"- F1-score: **{overall['f1']:.4f}**",
                f"- False-positive rate: **{overall['false_positive_rate']:.4f}**",
                f"- Labelled anomalies: **{overall['labelled_anomalies']}**",
                f"- Detected true anomalies: **{overall['true_positives']}**",
                f"- Total alerts: **{overall['predicted_anomalies']}**",
                "",
                "### Detected anomalies by controlled scenario",
                "",
                "| Anomaly type | Labelled | Detected | Recall |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in by_type.to_dict(orient="records"):
            lines.append(
                f"| {row['anomaly_type']} | {int(row['labelled_count'])} | "
                f"{int(row['detected_count'])} | {row['recall']:.4f} |"
            )
    lines.extend(
        [
            "",
            "## Alert explanations",
            "",
            "Isolation Forest has no native per-feature causal attribution. Each "
            "flagged row therefore includes a clearly labelled heuristic explanation "
            "listing the three inputs furthest from their training medians. This is "
            "context for a user, not proof of why a tree ensemble produced the score.",
            "",
            "## Limitations",
            "",
            "- Evaluation labels are controlled synthetic scenarios.",
            "- Performance does not establish real-world unusual-spending accuracy.",
            "- Some valid but rare purchases may be flagged.",
            "- Alerts require user review and must never be presented as fraud findings.",
        ]
    )
    return "\n".join(lines) + "\n"


def train(
    root: Path,
    data_config: dict[str, Any],
    model_config: dict[str, Any],
) -> dict[str, Any]:
    settings = model_config["anomaly"]
    seed = int(settings.get("random_seed", data_config["random_seed"]))
    version = str(model_config["model_version"])
    model_dir = root / "data" / "model_ready"
    artifact_dir = root / "artifacts" / "models" / "anomaly" / version
    report_dir = root / "reports"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    train_frame = pd.read_parquet(
        model_dir / "isolation_forest_train.parquet"
    )
    held_out = pd.read_parquet(model_dir / "isolation_forest_test.parquet")
    labels_path = model_dir / "isolation_forest_labels.parquet"
    labels = pd.read_parquet(labels_path) if labels_path.is_file() else None
    if labels is not None:
        keys = ["transaction_id", "user_id", "transaction_timestamp"]
        if not held_out[keys].reset_index(drop=True).equals(
            labels[keys].reset_index(drop=True)
        ):
            raise ValueError("Isolation Forest features and labels are misaligned.")
    validation_mask = chronological_validation_mask(
        held_out["transaction_timestamp"],
        float(settings["validation_fraction"]),
    )
    validation_frame = held_out.loc[validation_mask].reset_index(drop=True)
    evaluation_frame = held_out.loc[~validation_mask].reset_index(drop=True)
    validation_labels = (
        labels.loc[validation_mask, "is_anomaly"].to_numpy(dtype=bool)
        if labels is not None
        else None
    )
    evaluation_labels_frame = (
        labels.loc[~validation_mask].reset_index(drop=True)
        if labels is not None
        else None
    )

    preprocessor = RobustScaler()
    train_values = preprocessor.fit_transform(train_frame[FEATURES])
    validation_values = preprocessor.transform(validation_frame[FEATURES])
    evaluation_values = preprocessor.transform(evaluation_frame[FEATURES])

    tuning_records: list[dict[str, Any]] = []
    fitted_models: dict[float, IsolationForest] = {}
    for contamination in settings["candidate_contamination"]:
        contamination = float(contamination)
        candidate = IsolationForest(
            n_estimators=int(settings["estimators"]),
            contamination=contamination,
            random_state=seed,
            n_jobs=-1,
        )
        candidate.fit(train_values)
        fitted_models[contamination] = candidate
        if validation_labels is not None:
            default_predictions = candidate.predict(validation_values) == -1
            record = binary_metrics(validation_labels, default_predictions)
        else:
            default_predictions = candidate.predict(validation_values) == -1
            record = {
                "precision": np.nan,
                "recall": np.nan,
                "f1": np.nan,
                "false_positive_rate": np.nan,
                "predicted_anomalies": int(default_predictions.sum()),
            }
        tuning_records.append({"contamination": contamination, **record})
    tuning = pd.DataFrame(tuning_records)
    if validation_labels is not None:
        eligible = tuning[
            tuning["recall"] >= float(settings["minimum_recall_for_threshold"])
        ]
        ranked = (eligible if not eligible.empty else tuning).sort_values(
            ["f1", "precision"], ascending=False
        )
        selected_contamination = float(ranked.iloc[0]["contamination"])
    else:
        selected_contamination = float(
            settings["candidate_contamination"][0]
        )
    model = fitted_models[selected_contamination]
    validation_scores = -model.decision_function(validation_values)
    if validation_labels is not None:
        threshold, validation_threshold_metrics = select_threshold(
            validation_scores,
            validation_labels,
            float(settings["minimum_recall_for_threshold"]),
        )
    else:
        threshold = float(
            np.quantile(validation_scores, 1 - selected_contamination)
        )
        validation_threshold_metrics = None

    evaluation_started = time.perf_counter()
    evaluation_scores = -model.decision_function(evaluation_values)
    evaluation_predictions = evaluation_scores >= threshold
    inference_seconds = time.perf_counter() - evaluation_started
    overall = (
        binary_metrics(
            evaluation_labels_frame["is_anomaly"].to_numpy(dtype=bool),
            evaluation_predictions,
        )
        if evaluation_labels_frame is not None
        else None
    )

    predictions = evaluation_frame[
        [
            "transaction_id",
            "user_id",
            "transaction_timestamp",
            "category",
            *FEATURES,
        ]
    ].copy()
    predictions["anomaly_score"] = evaluation_scores
    predictions["decision_threshold"] = threshold
    predictions["is_unusual_spending"] = evaluation_predictions
    if evaluation_labels_frame is not None:
        predictions["is_labelled_anomaly"] = evaluation_labels_frame[
            "is_anomaly"
        ].to_numpy(dtype=bool)
        predictions["anomaly_type"] = evaluation_labels_frame[
            "anomaly_type"
        ].astype(str)
        predictions["label_explanation"] = evaluation_labels_frame[
            "explanation"
        ].astype(str)
    else:
        predictions["is_labelled_anomaly"] = pd.NA
        predictions["anomaly_type"] = "unavailable"
        predictions["label_explanation"] = "No compatible labels available."
    explanations = []
    for position, (_, row) in enumerate(predictions.iterrows()):
        if evaluation_predictions[position]:
            explanations.append(
                alert_explanation(
                    row,
                    evaluation_values[position],
                    FEATURES,
                )
            )
        else:
            explanations.append("")
    predictions["alert_explanation"] = explanations
    predictions.to_parquet(
        report_dir / "anomaly_predictions.parquet", index=False
    )
    categories = sorted(
        set(train_frame["category"].astype(str))
        | set(held_out["category"].astype(str))
    )
    category_mapping = {
        category: index for index, category in enumerate(categories)
    }
    observed_codes = (
        pd.concat(
            [
                train_frame[["category", "category_code"]],
                held_out[["category", "category_code"]],
            ],
            ignore_index=True,
        )
        .drop_duplicates()
        .assign(category=lambda frame: frame["category"].astype(str))
    )
    observed_mapping = dict(
        zip(
            observed_codes["category"],
            observed_codes["category_code"].astype(int),
        )
    )
    if category_mapping != observed_mapping:
        raise ValueError(
            "Observed category codes do not match deterministic alphabetical mapping."
        )

    by_type_records: list[dict[str, Any]] = []
    if evaluation_labels_frame is not None:
        positive_types = sorted(
            evaluation_labels_frame.loc[
                evaluation_labels_frame["is_anomaly"], "anomaly_type"
            ]
            .astype(str)
            .unique()
        )
        for anomaly_type in positive_types:
            type_mask = (
                evaluation_labels_frame["anomaly_type"].astype(str)
                == anomaly_type
            ).to_numpy()
            labelled_count = int(type_mask.sum())
            detected_count = int(
                np.logical_and(type_mask, evaluation_predictions).sum()
            )
            by_type_records.append(
                {
                    "anomaly_type": anomaly_type,
                    "labelled_count": labelled_count,
                    "detected_count": detected_count,
                    "recall": (
                        detected_count / labelled_count
                        if labelled_count
                        else 0.0
                    ),
                }
            )
    by_type = pd.DataFrame(by_type_records)
    metric_rows = [
        {
            "scope": "overall",
            "anomaly_type": "all",
            **(overall or {}),
        }
    ]
    metric_rows.extend(
        {
            "scope": "anomaly_type",
            **record,
        }
        for record in by_type_records
    )
    pd.DataFrame(metric_rows).to_csv(
        report_dir / "anomaly_metrics.csv", index=False
    )

    joblib.dump(model, artifact_dir / "isolation_forest.joblib")
    joblib.dump(preprocessor, artifact_dir / "preprocessor.joblib")
    feature_schema = {
        "ordered_features": FEATURES,
        "identifier_columns": [
            "transaction_id",
            "user_id",
            "transaction_timestamp",
            "category",
        ],
        "preprocessing": "RobustScaler fitted on the training partition only",
        "category_mapping": category_mapping,
        "unknown_category_code": -1,
        "score_direction": "Higher anomaly_score means more unusual",
        "decision_threshold": threshold,
    }
    (artifact_dir / "feature_schema.json").write_text(
        json.dumps(feature_schema, indent=2), encoding="utf-8"
    )
    metadata = {
        "model_version": version,
        "training_date_utc": datetime.now(timezone.utc).isoformat(),
        "project_title": data_config["project_title"],
        "model_type": "scikit-learn IsolationForest",
        "purpose": "Unusual spending behaviour detection, not fraud detection",
        "dataset_sources": ["synthetic_kenyan_young_adult_finance"],
        "synthetic_records_used": True,
        "training_rows": int(len(train_frame)),
        "validation_rows": int(len(validation_frame)),
        "evaluation_rows": int(len(evaluation_frame)),
        "training_date_range": [
            pd.Timestamp(train_frame["transaction_timestamp"].min()).isoformat(),
            pd.Timestamp(train_frame["transaction_timestamp"].max()).isoformat(),
        ],
        "validation_date_range": [
            pd.Timestamp(
                validation_frame["transaction_timestamp"].min()
            ).isoformat(),
            pd.Timestamp(
                validation_frame["transaction_timestamp"].max()
            ).isoformat(),
        ],
        "evaluation_date_range": [
            pd.Timestamp(
                evaluation_frame["transaction_timestamp"].min()
            ).isoformat(),
            pd.Timestamp(
                evaluation_frame["transaction_timestamp"].max()
            ).isoformat(),
        ],
        "features": FEATURES,
        "category_mapping": category_mapping,
        "selected_contamination": selected_contamination,
        "decision_threshold": threshold,
        "threshold_selection": "Maximum validation F1 subject to configured minimum recall",
        "validation_threshold_metrics": validation_threshold_metrics,
        "evaluation_metrics": overall,
        "inference_seconds": inference_seconds,
        "known_limitations": [
            "Labels and financial records are controlled synthetic data.",
            "Heuristic feature explanations are not causal model attributions.",
            "Valid rare spending may be flagged and requires user review.",
        ],
    }
    (artifact_dir / "model_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    (report_dir / "isolation_forest_evaluation.md").write_text(
        markdown_report(metadata, tuning, overall, by_type),
        encoding="utf-8",
    )
    LOGGER.info(
        "Isolation Forest complete. Evaluation F1=%s.",
        "unavailable" if overall is None else f"{overall['f1']:.4f}",
    )
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--data-config", type=Path, default=None)
    parser.add_argument("--model-config", type=Path, default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    root = args.root.resolve() if args.root else repository_root(__file__)
    data_config_path = (
        args.data_config.resolve()
        if args.data_config
        else root / "config" / "data_config.yaml"
    )
    model_config_path = (
        args.model_config.resolve()
        if args.model_config
        else root / "config" / "model_config.yaml"
    )
    train(
        root,
        load_yaml(data_config_path),
        load_yaml(model_config_path),
    )


if __name__ == "__main__":
    main()
