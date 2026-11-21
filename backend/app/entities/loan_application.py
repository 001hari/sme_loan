"""An application-time snapshot of the dataset's 18 loan features."""

from dataclasses import dataclass
from math import isfinite
from typing import ClassVar

from ._validation import require_non_blank
from backend.app.services.validation_service import validate_integer_value, validate_numeric_value


@dataclass
class LoanApplication:
    business_age_years: float
    employee_count: int
    annual_revenue: float
    previous_year_revenue: float
    annual_profit: float
    monthly_expenses: float
    total_liabilities: float
    business_credit_score: int
    prior_loan_count: int
    late_payment_history: int | bool
    missed_payments_12m: int
    loan_purpose: str
    loan_amount: float
    loan_tenure_months: int
    cash_flow_stability: str
    revenue_growth_rate: float
    debt_to_revenue_ratio: float
    loan_to_revenue_ratio: float
    profit_margin: float
    dscr: float
    loan_application_id: int | None = None
    risk_predicted_score: float | None = None
    approval_result: str | None = None

    VALID_TENURES: ClassVar[tuple[int, ...]] = (12, 18, 24, 36, 48, 60, 72)
    VALID_LOAN_PURPOSES: ClassVar[tuple[str, ...]] = (
        "Working Capital",
        "Business Expansion",
        "Equipment Purchase",
        "Inventory Purchase",
        "Infrastructure",
        "Debt Refinancing",
    )
    VALID_CASH_FLOW_STABILITY: ClassVar[tuple[str, ...]] = ("Stable", "Moderate", "Unstable")

    def validate(self) -> None:
        validate_numeric_value(self.business_age_years, "Business Age Years", minimum=0,
                               maximum=100, minimum_exclusive=True)
        if isinstance(self.employee_count, bool) or not isinstance(self.employee_count, int):
            raise ValueError("employee_count must be an integer.")
        if self.employee_count < 1:
            raise ValueError("employee_count must be at least 1.")
        validate_numeric_value(self.annual_revenue, "Annual Revenue", minimum=0, minimum_exclusive=True)
        validate_numeric_value(self.previous_year_revenue, "Previous Year Revenue", minimum=0)
        validate_numeric_value(self.loan_amount, "Loan Amount", minimum=0, minimum_exclusive=True)
        for field_name in ("monthly_expenses", "total_liabilities"):
            validate_numeric_value(getattr(self, field_name), field_name.replace("_", " ").title(), minimum=0)
        validate_integer_value(self.prior_loan_count, "Prior Loan Count", minimum=0)
        if isinstance(self.business_credit_score, bool) or not isinstance(self.business_credit_score, int):
            raise ValueError("business_credit_score must be an integer.")
        if not 300 <= self.business_credit_score <= 900:
            raise ValueError("business_credit_score must be between 300 and 900.")
        if (
            not isinstance(self.late_payment_history, (int, bool))
            or self.late_payment_history not in (0, 1, False, True)
        ):
            raise ValueError("late_payment_history must be 0 or 1.")
        try:
            validate_integer_value(self.missed_payments_12m, "Missed Payments in Last 12 Months",
                                   minimum=0, maximum=6)
        except ValueError as exc:
            if "whole number" in str(exc):
                raise ValueError("missed_payments_12m must be an integer.") from exc
            raise ValueError("missed_payments_12m must be between 0 and 6, as defined by the dataset.") from exc
        if isinstance(self.loan_tenure_months, bool) or not isinstance(self.loan_tenure_months, int):
            raise ValueError("loan_tenure_months must be an integer.")
        if self.loan_tenure_months not in self.VALID_TENURES:
            raise ValueError(f"loan_tenure_months must be one of {self.VALID_TENURES}.")
        if self.loan_purpose not in self.VALID_LOAN_PURPOSES:
            raise ValueError("loan_purpose must match a category in the dataset.")
        if self.cash_flow_stability not in self.VALID_CASH_FLOW_STABILITY:
            raise ValueError("cash_flow_stability must match a category in the dataset.")
        for field_name in (
            "annual_profit",
            "revenue_growth_rate",
            "debt_to_revenue_ratio",
            "loan_to_revenue_ratio",
            "profit_margin",
            "dscr",
        ):
            validate_numeric_value(getattr(self, field_name), field_name)
        if self.risk_predicted_score is not None:
            value = self.risk_predicted_score
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError("risk_predicted_score must be a finite number or None.")
        if self.approval_result is not None:
            require_non_blank(self.approval_result, "approval_result")
