"""Temporary development predictor.

Replace this implementation only after the ML team supplies:
- the trained model/pipeline artifact,
- the exact ordered feature schema,
- preprocessing code used during training,
- class/probability mapping,
- a model version and evaluation report.

This deterministic mock is for testing the application wiring only. It is NOT a
credit-risk model and must never be used for real lending decisions.
"""

from typing import Any


def predict_default(features: dict[str, Any]) -> dict[str, Any]:
    # Deliberately simple deterministic placeholder so the full flow can be tested.
    # The arbitrary score is not statistically meaningful.
    credit_score = int(features["credit_score"])
    loan_to_revenue = float(features["requested_loan_amount"]) / max(
        float(features["annual_revenue"]), 1.0
    )

    probability = 0.50
    probability += max(0, 650 - credit_score) / 1000
    probability += min(loan_to_revenue, 2.0) * 0.10
    probability -= min(int(features["years_in_business"]), 10) * 0.015
    probability = max(0.01, min(probability, 0.99))

    if probability < 0.30:
        category = "LOW"
    elif probability < 0.60:
        category = "MEDIUM"
    else:
        category = "HIGH"

    return {
        "default_probability": round(probability, 4),
        "risk_category": category,
        "model_version": "mock-v0",
        "is_mock": True,
    }
