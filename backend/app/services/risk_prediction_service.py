"""Transparent, deterministic Sprint 1 sigmoid demonstration (not a trained model)."""

from dataclasses import dataclass
from math import exp, isfinite, log1p


METHOD = "Dummy Logistic Regression (Sigmoid)"
LOW_RISK_THRESHOLD = 30.0
HIGH_RISK_THRESHOLD = 60.0


@dataclass(frozen=True)
class RiskPrediction:
    risk_score: float
    risk_category: str
    suggested_decision: str
    prediction_method: str = METHOD


def sigmoid(value: float) -> float:
    """Numerically stable sigmoid with finite input validation."""
    if not isfinite(value):
        raise ValueError("The risk score input must be finite.")
    if value >= 0:
        z = exp(-min(value, 709.0))
        return 1.0 / (1.0 + z)
    z = exp(max(value, -709.0))
    return z / (1.0 + z)


def classify_risk_score(
    score: float,
    *,
    low_threshold: float = LOW_RISK_THRESHOLD,
    high_threshold: float = HIGH_RISK_THRESHOLD,
) -> tuple[str, str]:
    if not isfinite(score) or not 0 <= score <= 100:
        raise ValueError("Risk score must be a finite percentage between 0 and 100.")
    if not 0 <= low_threshold < high_threshold <= 100:
        raise ValueError("Risk thresholds must satisfy 0 <= low < high <= 100.")
    category = "LOW" if score < low_threshold else "MEDIUM" if score < high_threshold else "HIGH"
    decision = {
        "LOW": "SUGGESTED_APPROVE",
        "MEDIUM": "MANUAL_REVIEW",
        "HIGH": "SUGGESTED_REJECT",
    }[category]
    return category, decision


def calculate_prediction(application: dict) -> RiskPrediction:
    """Calculate a deterministic scaled-logit risk demonstration.

    z = -1.20 + .60*age_risk - .25*revenue_scale - .60*profit_margin
        + .40*expense_ratio + .50*liability_ratio + .75*credit_risk
        + .15*prior_loans + .90*missed_payments + .65*loan_ratio
        + .20*tenure_scale
    Ratios are bounded before applying these fixed demonstration weights.
    """
    required = (
        "business_age_years", "annual_revenue", "annual_profit", "monthly_expenses",
        "total_liabilities", "business_credit_score", "prior_loan_count",
        "missed_payments_12m", "loan_amount", "loan_tenure_months",
    )
    values = {}
    for key in required:
        if isinstance(application.get(key), bool):
            raise ValueError(f"Prediction feature {key} must be numeric, not boolean.")
        try:
            value = float(application[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Missing or invalid prediction feature: {key}.") from exc
        if not isfinite(value):
            raise ValueError(f"Prediction feature {key} must be finite.")
        values[key] = value
    revenue = values["annual_revenue"]
    if revenue <= 0:
        raise ValueError("annual_revenue must be greater than zero.")
    if values["business_age_years"] < 0:
        raise ValueError("business_age_years must be non-negative.")
    if values["monthly_expenses"] < 0 or values["total_liabilities"] < 0:
        raise ValueError("Expenses and liabilities must be non-negative.")
    if not 300 <= values["business_credit_score"] <= 900:
        raise ValueError("business_credit_score must be between 300 and 900.")
    if values["prior_loan_count"] < 0:
        raise ValueError("prior_loan_count must be non-negative.")
    if not 0 <= values["missed_payments_12m"] <= 6:
        raise ValueError("missed_payments_12m must be between 0 and 6.")
    if values["loan_amount"] <= 0:
        raise ValueError("loan_amount must be greater than zero.")
    if values["loan_tenure_months"] not in {12, 18, 24, 36, 48, 60, 72}:
        raise ValueError("loan_tenure_months is not supported.")

    clamp = lambda value, low, high: max(low, min(high, value))
    age_risk = clamp((10.0 - values["business_age_years"]) / 10.0, 0.0, 1.0)
    revenue_scale = clamp(log1p(revenue) / log1p(10_000_000), 0.0, 2.0)
    profit_margin = clamp(values["annual_profit"] / revenue, -2.0, 2.0)
    expense_ratio = clamp(values["monthly_expenses"] * 12.0 / revenue, 0.0, 2.0)
    liability_ratio = clamp(values["total_liabilities"] / revenue, 0.0, 5.0)
    credit_risk = clamp((700.0 - values["business_credit_score"]) / 300.0, -1.0, 2.0)
    prior_loans = clamp(values["prior_loan_count"] / 10.0, 0.0, 2.0)
    missed_payments = clamp(values["missed_payments_12m"] / 6.0, 0.0, 1.0)
    loan_ratio = clamp(values["loan_amount"] / revenue, 0.0, 3.0)
    tenure_scale = clamp(values["loan_tenure_months"] / 72.0, 0.0, 1.5)

    z = (
        -1.20 + 0.60 * age_risk - 0.25 * revenue_scale - 0.60 * profit_margin
        + 0.40 * expense_ratio + 0.50 * liability_ratio + 0.75 * credit_risk
        + 0.15 * prior_loans + 0.90 * missed_payments + 0.65 * loan_ratio
        + 0.20 * tenure_scale
    )
    score = sigmoid(z) * 100.0
    category, decision = classify_risk_score(score)
    return RiskPrediction(round(score, 4), category, decision)
