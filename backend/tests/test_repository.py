from contextlib import contextmanager

import pytest

from backend.app.entities import Business, LoanApplication
from backend.app.repositories.loan_application_repository import (
    DuplicateBusinessIDError,
    LoanApplicationRepository,
)


def business(**overrides) -> Business:
    values = dict(
        business_id=123,
        business_name="Rao Foods",
        city="Vadodara",
        state="Gujarat",
        sector="Food Processing",
        legal_status="Partnership",
    )
    values.update(overrides)
    return Business(**values)


def application() -> LoanApplication:
    return LoanApplication(
        business_age_years=4,
        employee_count=12,
        annual_revenue=1_000_000,
        previous_year_revenue=900_000,
        annual_profit=100_000,
        monthly_expenses=50_000,
        total_liabilities=200_000,
        business_credit_score=700,
        prior_loan_count=1,
        late_payment_history=0,
        missed_payments_12m=0,
        loan_purpose="Working Capital",
        loan_amount=300_000,
        loan_tenure_months=24,
        cash_flow_stability="Stable",
        revenue_growth_rate=0.1,
        debt_to_revenue_ratio=0.2,
        loan_to_revenue_ratio=0.3,
        profit_margin=0.1,
        dscr=1.2,
    )


class Cursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, *, existing=None, final_row=None):
        self.existing = existing
        self.final_row = final_row or {
            "loan_application_id": 7,
            "business_id": 123,
            "business_name": "Rao Foods",
            "risk_predicted_score": None,
            "approval_result": None,
        }
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        if "FROM businesses WHERE business_id" in sql:
            return Cursor(row=self.existing)
        if "INSERT INTO loan_applications" in sql:
            return Cursor(row={"loan_application_id": 7})
        if "SELECT loan_applications.*" in sql and "WHERE application_id" in sql:
            return Cursor(row=self.final_row)
        if "SELECT loan_applications.*" in sql:
            return Cursor(rows=[])
        return Cursor()


class FakeDatabase:
    def __init__(self, conn):
        self.conn = conn

    @contextmanager
    def connection(self):
        yield self.conn


def test_insert_uses_parameters_and_leaves_prediction_fields_null() -> None:
    conn = FakeConnection()
    repo = LoanApplicationRepository(FakeDatabase(conn))

    saved = repo.create_application(business(), application())

    assert saved["risk_predicted_score"] is None
    assert saved["approval_result"] is None
    insert_sql, insert_params = next(call for call in conn.calls if "INSERT INTO loan_applications" in call[0])
    assert "risk_predicted_score" not in insert_sql
    assert "approval_result" not in insert_sql
    assert "123" not in insert_sql
    assert insert_params[0] == 123


def test_conflicting_business_id_is_rejected() -> None:
    existing = {
        "business_name": "Different Company",
        "city": "Vadodara",
        "state": "Gujarat",
        "sector": "Food Processing",
        "legal_status": "Partnership",
    }
    repo = LoanApplicationRepository(FakeDatabase(FakeConnection(existing=existing)))

    with pytest.raises(DuplicateBusinessIDError, match="different business details"):
        repo.create_application(business(), application())


def test_existing_business_can_create_another_application() -> None:
    existing = {
        "business_name": "Rao Foods",
        "city": "Vadodara",
        "state": "Gujarat",
        "sector": "Food Processing",
        "legal_status": "Partnership",
    }
    conn = FakeConnection(existing=existing)
    repo = LoanApplicationRepository(FakeDatabase(conn))

    saved = repo.create_application(business(), application())

    assert saved["loan_application_id"] == 7
    assert any("INSERT INTO loan_applications" in sql for sql, _ in conn.calls)


def test_search_and_list_use_parameterized_business_id_and_limit() -> None:
    conn = FakeConnection()
    repo = LoanApplicationRepository(FakeDatabase(conn))

    assert repo.get_applications_by_business_id(123) == []
    assert repo.get_all_applications(limit=20) == []

    search_sql, search_params = next((sql, params) for sql, params in conn.calls if "WHERE business_id = %s" in sql)
    list_sql, list_params = next((sql, params) for sql, params in conn.calls if "LIMIT %s" in sql)
    assert "123" not in search_sql
    assert search_params == (123,)
    assert list_params == (20,)


def test_get_application_by_id_uses_a_bound_parameter() -> None:
    conn = FakeConnection()
    repo = LoanApplicationRepository(FakeDatabase(conn))

    row = repo.get_application_by_id(7)

    assert row["loan_application_id"] == 7
    sql, params = next((sql, params) for sql, params in conn.calls if "WHERE application_id = %s" in sql)
    assert "7" not in sql
    assert params == (7,)
