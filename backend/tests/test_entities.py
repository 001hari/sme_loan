"""Validation checks for the dataset-aligned domain entities."""

import pytest

from backend.app.entities import Business, LoanApplication


def make_business(**overrides) -> Business:
    values = {
        "business_id": 123,
        "business_name": "Rao Foods",
        "city": "Vadodara",
        "state": "Gujarat",
        "sector": "Food Processing",
        "legal_status": "Partnership",
    }
    values.update(overrides)
    return Business(**values)


def make_application(**overrides) -> LoanApplication:
    values = {
        "business_age_years": 4.2,
        "employee_count": 12,
        "annual_revenue": 1_000_000.0,
        "previous_year_revenue": 900_000.0,
        "annual_profit": -10_000.0,
        "monthly_expenses": 50_000.0,
        "total_liabilities": 200_000.0,
        "business_credit_score": 700,
        "prior_loan_count": 1,
        "late_payment_history": 0,
        "missed_payments_12m": 0,
        "loan_purpose": "Working Capital",
        "loan_amount": 300_000.0,
        "loan_tenure_months": 24,
        "cash_flow_stability": "Stable",
        "revenue_growth_rate": -0.08,
        "debt_to_revenue_ratio": 0.2,
        "loan_to_revenue_ratio": 0.3,
        "profit_margin": -0.01,
        "dscr": -0.2,
    }
    values.update(overrides)
    return LoanApplication(**values)


def test_business_requires_dataset_identity_fields() -> None:
    make_business().validate()
    with pytest.raises(ValueError, match="business_id"):
        make_business(business_id=0).validate()
    with pytest.raises(ValueError, match="sector"):
        make_business(sector="Other").validate()


def test_business_can_wait_for_database_generated_id_and_validates_identity_text():
    make_business(business_id=None).validate()
    with pytest.raises(ValueError, match="letters and spaces"):
        make_business(city="New-York").validate()
    with pytest.raises(ValueError, match="Company / Organization Name"):
        make_business(business_name="Northwind 24").validate()


def test_loan_application_preserves_signed_financial_features() -> None:
    app = make_application()
    app.validate()
    assert app.risk_predicted_score is None
    assert app.approval_result is None


@pytest.mark.parametrize("score", [299, 901])
def test_credit_score_must_match_dataset_definition(score: int) -> None:
    with pytest.raises(ValueError, match="300 and 900"):
        make_application(business_credit_score=score).validate()


def test_loan_tenure_must_be_a_value_used_by_dataset() -> None:
    with pytest.raises(ValueError, match="one of"):
        make_application(loan_tenure_months=30).validate()


@pytest.mark.parametrize("age", [0, 101])
def test_business_age_must_be_positive_and_at_most_100(age):
    with pytest.raises(ValueError, match="Business Age Years"):
        make_application(business_age_years=age).validate()


def test_previous_year_revenue_allows_zero_but_annual_revenue_does_not():
    make_application(previous_year_revenue=0).validate()
    with pytest.raises(ValueError, match="Annual Revenue must be greater than zero"):
        make_application(annual_revenue=0).validate()


def test_outcome_fields_cannot_be_given_invalid_numeric_values() -> None:
    with pytest.raises(ValueError, match="risk_predicted_score"):
        make_application(risk_predicted_score=float("nan")).validate()
