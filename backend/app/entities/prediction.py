"""Predictions produced by the available model families."""

from dataclasses import dataclass
from datetime import datetime, timezone

from ._validation import require_probability


@dataclass
class PredictionResult:
    loan_id: int
    logistic_regression_prediction: int | None = None
    logistic_regression_probability: float | None = None
    random_forest_prediction: int | None = None
    random_forest_probability: float | None = None
    soft_voting_prediction: int | None = None
    soft_voting_probability: float | None = None
    risk_category: str | None = None
    model_version: str | None = None
    prediction_id: int | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def validate(self) -> None:
        if isinstance(self.loan_id, bool) or not isinstance(self.loan_id, int) or self.loan_id <= 0:
            raise ValueError("loan_id must be a positive integer.")
        for field_name in (
            "logistic_regression_probability",
            "random_forest_probability",
            "soft_voting_probability",
        ):
            value = getattr(self, field_name)
            if value is not None:
                require_probability(value, field_name)
        for field_name in (
            "logistic_regression_prediction",
            "random_forest_prediction",
            "soft_voting_prediction",
        ):
            value = getattr(self, field_name)
            if value is not None and value not in (0, 1):
                raise ValueError(f"{field_name} must be 0, 1, or None.")
