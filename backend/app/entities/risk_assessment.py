"""Human-readable risk summary associated with a prediction record."""

from dataclasses import dataclass
from datetime import datetime, timezone

from ._validation import require_non_blank, require_probability


@dataclass
class RiskAssessment:
    loan_id: int
    default_probability: float
    risk_category: str
    assessed_by_user_id: int | None = None
    assessment_id: int | None = None
    prediction_id: int | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def validate(self) -> None:
        if isinstance(self.loan_id, bool) or not isinstance(self.loan_id, int) or self.loan_id <= 0:
            raise ValueError("loan_id must be a positive integer.")
        require_probability(self.default_probability, "default_probability")
        require_non_blank(self.risk_category, "risk_category")
