"""Inference adapter for the saved raw-input SME Hybrid Model."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = ROOT / "ml" / "artifacts" / "sme_hybrid_model.joblib"
METADATA_PATH = ROOT / "ml" / "artifacts" / "sme_hybrid_model_metadata.json"
MODEL_NAME = "SME Hybrid Model"
MODEL_VERSION = "1.0.0"


@dataclass(frozen=True)
class RiskPrediction:
    predicted_class: int
    predicted_class_label: str
    default_probability: float
    prediction_confidence: float
    model_version: str = MODEL_VERSION
    prediction_method: str = MODEL_NAME

    @property
    def risk_score(self) -> float:
        return round(self.default_probability * 100.0, 4)

    @property
    def risk_category(self) -> str:
        # The existing PostgreSQL check permits these coarse class-aligned values.
        return "HIGH" if self.predicted_class == 1 else "LOW"

    @property
    def suggested_decision(self) -> str:
        # The model is decision support only; retain the existing schema value
        # without turning a model class into a loan approval/rejection.
        return "MANUAL_REVIEW"


@lru_cache(maxsize=1)
def _load_model_and_metadata():
    if not MODEL_PATH.is_file() or not METADATA_PATH.is_file():
        raise RuntimeError(
            "SME Hybrid Model artifact is missing. Train it with "
            "python -m ml.training.train_sme_hybrid_model first."
        )
    model = joblib.load(MODEL_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    if metadata.get("model_name") != MODEL_NAME:
        raise RuntimeError("The saved model metadata does not identify the SME Hybrid Model.")
    return model, metadata


def clear_model_cache() -> None:
    """Clear the in-process artifact cache; useful for controlled model refresh/tests."""
    _load_model_and_metadata.cache_clear()


def application_features(application: dict, feature_names: list[str]) -> pd.DataFrame:
    missing = [name for name in feature_names if name not in application or application[name] is None]
    if missing:
        raise ValueError("Risk assessment is missing required application fields: " + ", ".join(missing))
    # Preserve raw values and canonical feature names; fitted transformers own
    # all imputation, scaling, and category encoding.
    return pd.DataFrame([{name: application[name] for name in feature_names}], columns=feature_names)


def predict_sme_hybrid(application: dict) -> RiskPrediction:
    model, metadata = _load_model_and_metadata()
    feature_names = metadata.get("feature_names")
    if not isinstance(feature_names, list) or not feature_names:
        raise RuntimeError("Saved model metadata has no feature mapping.")
    row = application_features(application, feature_names)
    class_values = list(model.classes_)
    default_class = metadata.get("default_class")
    if default_class not in class_values:
        raise RuntimeError("Saved model classes do not include the configured default class.")
    predicted = int(model.predict(row)[0])
    probabilities = model.predict_proba(row)[0]
    default_probability = float(probabilities[class_values.index(default_class)])
    labels = metadata.get("class_mapping", {})
    class_label = labels.get(str(predicted))
    if class_label is None:
        raise RuntimeError(f"Saved model has no display label for class {predicted}.")
    return RiskPrediction(
        predicted_class=predicted,
        predicted_class_label=class_label,
        default_probability=default_probability,
        prediction_confidence=float(max(probabilities)),
        model_version=metadata.get("model_version", MODEL_VERSION),
    )
