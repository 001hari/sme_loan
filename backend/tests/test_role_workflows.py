"""Isolated unit coverage for authentication, workflows, DAO SQL, and dummy risk."""

from contextlib import contextmanager

import pytest

from backend.app.entities import Business, LoanApplication
from backend.app.repositories.workflow_repository import WorkflowRepository
from backend.app.services.auth_service import (
    AuthenticationError,
    AuthorizationError,
    DuplicateEmailError,
    hash_password,
    verify_password,
)
from backend.app.services.risk_prediction_service import (
    calculate_prediction,
    classify_risk_score,
    sigmoid,
)
from backend.app.services.sme_hybrid_prediction_service import RiskPrediction as HybridRiskPrediction
from backend.app.services.workflow_service import Principal, WorkflowService


def valid_business(**overrides):
    values = dict(business_id=1001, business_name="Northwind Foods", city="Pune",
                  state="Maharashtra", sector="Food Processing", legal_status="Partnership",
                  business_age_years=5, employee_count=12)
    values.update(overrides)
    return Business(**values)


def valid_application(**overrides):
    values = dict(business_age_years=5, employee_count=12, annual_revenue=5_000_000,
                  previous_year_revenue=4_500_000, annual_profit=500_000,
                  monthly_expenses=150_000, total_liabilities=800_000,
                  business_credit_score=720, prior_loan_count=1, late_payment_history=0,
                  missed_payments_12m=0, loan_purpose="Working Capital", loan_amount=800_000,
                  loan_tenure_months=24, cash_flow_stability="Stable", revenue_growth_rate=.1,
                  debt_to_revenue_ratio=.16, loan_to_revenue_ratio=.16, profit_margin=.1, dscr=1.5)
    values.update(overrides)
    return LoanApplication(**values)


class FakeResult:
    def __init__(self, row=None, rows=None):
        self.row, self.rows = row, rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, generated_business_id=2345):
        self.calls = []
        self.fail_application_insert = False
        self.generated_business_id = generated_business_id

    def execute(self, statement, params=()):
        self.calls.append((statement, params))
        if "SELECT EXISTS (SELECT 1 FROM businesses" in statement:
            return FakeResult({"already_exists": False})
        if "INSERT INTO businesses" in statement:
            return FakeResult({"business_id": self.generated_business_id})
        if "INSERT INTO loan_applications" in statement:
            if self.fail_application_insert:
                raise RuntimeError("simulated insert error")
            return FakeResult({"loan_application_id": 81, "application_status": "SUBMITTED", "submitted_at": "now"})
        if "UPDATE application_info_requests" in statement:
            return FakeResult({"loan_application_id": 81})
        if "UPDATE loan_applications" in statement and "RETURNING" in statement:
            return FakeResult({"loan_application_id": 81})
        if "INSERT INTO application_info_requests" in statement or "INSERT INTO predictions" in statement:
            return FakeResult({"request_id": 19} if "application_info_requests" in statement else {"prediction_id": 29})
        return FakeResult()


class FakeDatabase:
    def __init__(self, conn=None):
        self.conn = conn or FakeConnection()
        self.commits = 0
        self.rollbacks = 0

    @contextmanager
    def connection(self):
        try:
            yield self.conn
            self.commits += 1
        except Exception:
            self.rollbacks += 1
            raise


class FakeAuthRepository:
    def __init__(self):
        self.users = {}
        self.applicant_accounts = {}
        self.next_id = 1

    def create_user(self, *, full_name, email, phone, password_hash, role):
        if email in self.users:
            raise DuplicateEmailError("duplicate")
        user_id = self.next_id
        self.next_id += 1
        self.users[email] = dict(user_id=user_id, full_name=full_name, email=email,
                                 phone_number=phone, password_hash=password_hash,
                                 role=role, is_active=True)
        return user_id

    def get_user_by_email(self, email):
        return self.users.get(email)

    def business_id_exists(self, business_id):
        return business_id == 999

    def applicant_company_exists(self, company_name):
        return company_name.strip().casefold() in self.applicant_accounts

    def create_applicant_account(self, company_name, password_hash):
        key = company_name.strip().casefold()
        if key in self.applicant_accounts:
            from backend.app.services.auth_service import DuplicateCompanyNameError
            raise DuplicateCompanyNameError("duplicate")
        user = dict(user_id=self.next_id, company_name=company_name, full_name=company_name,
                    email=None, phone_number=None, password_hash=password_hash,
                    role="SME_APPLICANT", is_active=True)
        self.next_id += 1
        self.applicant_accounts[key] = user
        return user["user_id"]

    def get_applicant_by_company_name(self, company_name):
        return self.applicant_accounts.get(company_name.strip().casefold())


def test_password_hash_uses_unique_salt_and_verifies_correctly():
    first, second = hash_password("secure-password-123"), hash_password("secure-password-123")
    assert first != second
    assert verify_password("secure-password-123", first)
    assert not verify_password("wrong-password", first)
    assert "secure-password-123" not in first


def test_eight_character_password_is_accepted_and_hashed():
    encoded = hash_password("passw0rd")
    assert encoded != "passw0rd"
    assert verify_password("passw0rd", encoded)


@pytest.mark.parametrize("password", ["1234567", "x" * 257])
def test_passwords_outside_eight_to_256_characters_are_rejected(password):
    with pytest.raises(ValueError, match="between 8 and 256"):
        hash_password(password)


@pytest.mark.parametrize("password,confirmation", [
    ("Test@123", "Short@1"),
    ("Test@123", "LongPass@12345"),
])
def test_applicant_confirmation_mismatch_is_reported_before_confirmation_format_checks(password, confirmation):
    with pytest.raises(ValueError, match="Passwords do not match. Please enter the confirmation password again."):
        WorkflowService(FakeAuthRepository()).register_applicant(
            "Rao Foods", password, confirmation
        )


def test_applicant_registration_and_login():
    repository = FakeAuthRepository()
    service = WorkflowService(repository)
    user_id = service.register_applicant("Rao Foods", "Test@123", "Test@123")
    principal = service.authenticate_applicant("rao foods", "Test@123")
    assert principal.user_id == user_id
    assert principal.role == "SME_APPLICANT"
    account = repository.applicant_accounts["rao foods"]
    assert account["company_name"] == "Rao Foods"
    assert account["email"] is None and account["phone_number"] is None
    assert account["full_name"] == "Rao Foods"  # compatibility display field; company_name is the login key
    assert account["password_hash"] != "Test@123"


def test_applicant_password_confirmation_mismatch_is_rejected():
    with pytest.raises(ValueError, match="Passwords do not match. Please enter the confirmation password again."):
        WorkflowService(FakeAuthRepository()).register_applicant(
            "Rao Foods", "Test@123", "Wrong@123"
        )


@pytest.mark.parametrize("role", ["RELATIONSHIP_MANAGER", "LOAN_OFFICER"])
def test_staff_password_confirmation_compares_before_format_validation(role):
    with pytest.raises(ValueError, match="Passwords do not match. Please enter the confirmation password again."):
        WorkflowService(FakeAuthRepository()).provision_staff(
            "Ravi Kumar", "ravi@example.com", "9876543210", "Swaroop@7", "swaroop@6", role
        )


def test_duplicate_applicant_company_registration_is_rejected_case_insensitively():
    service = WorkflowService(FakeAuthRepository())
    service.register_applicant("Rao Foods", "Test@123", "Test@123")
    with pytest.raises(ValueError, match="already registered"):
        service.register_applicant("  RAO FOODS  ", "Other@123", "Other@123")


def test_applicant_login_rejects_incorrect_password():
    service = WorkflowService(FakeAuthRepository())
    service.register_applicant("Rao Foods", "Test@123", "Test@123")
    with pytest.raises(AuthenticationError):
        service.authenticate_applicant("Rao Foods", "wrong-password-123")


def test_company_duplicate_check_is_available_through_workflow_service():
    service = WorkflowService(FakeAuthRepository())
    assert service.applicant_company_exists("Tcs") is False


def test_applicant_account_repository_uses_company_identity_and_null_contact_fields():
    class AccountConnection:
        def __init__(self):
            self.calls = []
            self.account = None

        def execute(self, statement, params=()):
            self.calls.append((statement, params))
            if "SELECT EXISTS" in statement:
                return FakeResult({"already_exists": False})
            if "INSERT INTO users" in statement:
                self.account = dict(user_id=12, company_name=params[0], full_name=params[1],
                                    email=None, password_hash=params[2], phone_number=None,
                                    role="SME_APPLICANT", is_active=True)
                return FakeResult({"user_id": 12})
            if "SELECT user_id,company_name,password_hash,role,is_active" in statement:
                return FakeResult(self.account)
            return FakeResult()

    connection = AccountConnection()
    database = FakeDatabase(connection)
    repository = WorkflowRepository(database)
    assert not repository.applicant_company_exists("Northwind Foods")
    assert repository.create_applicant_account("Northwind Foods", "secure-hash") == 12
    exists_sql, exists_params = connection.calls[0]
    insert_sql, insert_params = connection.calls[1]
    assert "company_name" in exists_sql and "full_name" not in exists_sql
    assert "lower(btrim(company_name))" in exists_sql
    assert exists_params == ("Northwind Foods",)
    assert "company_name,full_name,email,password_hash,phone_number,role" in insert_sql
    assert "NULL" in insert_sql and "SME_APPLICANT" in insert_sql
    assert insert_params == ("Northwind Foods", "Northwind Foods", "secure-hash")
    assert connection.calls[2][0] == "INSERT INTO sme_applicants(user_id) VALUES (%s)"
    saved = repository.get_applicant_by_company_name("northwind foods")
    assert saved["user_id"] == 12 and saved["password_hash"] == "secure-hash"
    assert database.commits == 3


def test_incorrect_password_is_rejected():
    repo = FakeAuthRepository()
    repo.create_user(full_name="Asha", email="asha@example.com", phone="12345678",
                     password_hash=hash_password("secure-password-123"), role="SME_APPLICANT")
    with pytest.raises(AuthenticationError):
        WorkflowService(repo).authenticate("asha@example.com", "incorrect-password", "SME_APPLICANT")


def test_login_rejects_wrong_role_even_with_valid_credentials():
    repo = FakeAuthRepository()
    repo.create_user(full_name="Asha", email="asha@example.com", phone="12345678",
                     password_hash=hash_password("secure-password-123"), role="SME_APPLICANT")
    with pytest.raises(AuthenticationError):
        WorkflowService(repo).authenticate("asha@example.com", "secure-password-123", "RELATIONSHIP_MANAGER")


def test_duplicate_email_is_rejected():
    repo = FakeAuthRepository()
    service = WorkflowService(repo)
    service.provision_staff("Asha", "asha@example.com", "12345678", "Test@123", "Test@123", "LOAN_OFFICER")
    with pytest.raises(DuplicateEmailError):
        service.provision_staff("Asha Rao", "ASHA@example.com", "12345678", "Other@123", "Other@123", "LOAN_OFFICER")


@pytest.mark.parametrize("args", [
    ("Asha", "bad-email", "12345678", "Test@123", "Test@123"),
    ("Asha", "asha@example.com", "123", "Test@123", "Test@123"),
    ("Asha", "asha@example.com", "12345678", "Test@123", "Wrong@123"),
])
def test_staff_registration_rejects_invalid_email_phone_or_confirmation(args):
    with pytest.raises(ValueError):
        WorkflowService(FakeAuthRepository()).provision_staff(*args, "RELATIONSHIP_MANAGER")


def test_staff_provisioning_supports_only_staff_roles():
    repo = FakeAuthRepository()
    service = WorkflowService(repo)
    user_id = service.provision_staff("Ravi", "ravi@example.com", "12345678",
                                      "Test@123", "Test@123", "RELATIONSHIP_MANAGER")
    assert repo.users["ravi@example.com"]["role"] == "RELATIONSHIP_MANAGER"
    assert user_id == 1
    with pytest.raises(ValueError):
        service.provision_staff("Bad", "bad@example.com", "12345678", "Test@123",
                                "Test@123", "APPROVAL_AUTHORITY")


def test_applicant_service_denies_staff_actions():
    service = WorkflowService(FakeAuthRepository())
    applicant = Principal(1, "Asha", "asha@example.com", "SME_APPLICANT")
    manager = Principal(2, "Ravi", "ravi@example.com", "RELATIONSHIP_MANAGER")
    with pytest.raises(AuthorizationError):
        service.rm_applications(applicant)
    with pytest.raises(AuthorizationError):
        service.applicant_applications(manager)


def test_sigmoid_is_stable_for_extreme_inputs():
    assert sigmoid(1000) == pytest.approx(1.0)
    assert sigmoid(-1000) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        sigmoid(float("inf"))


@pytest.mark.parametrize("score,expected", [(0, "LOW"), (29.999, "LOW"), (30, "MEDIUM"),
                                             (59.999, "MEDIUM"), (60, "HIGH"), (100, "HIGH")])
def test_risk_score_boundaries_and_decision(score, expected):
    category, decision = classify_risk_score(score)
    assert category == expected
    assert decision == {"LOW": "SUGGESTED_APPROVE", "MEDIUM": "MANUAL_REVIEW", "HIGH": "SUGGESTED_REJECT"}[expected]


def test_dummy_prediction_is_deterministic_bounded_and_marked_as_demo():
    row = {**vars(valid_application()), "business_name": "Northwind Foods"}
    prediction = calculate_prediction(row)
    assert prediction == calculate_prediction(row)
    assert 0 <= prediction.risk_score <= 100
    assert "Dummy Logistic Regression" in prediction.prediction_method


def test_prediction_rejects_missing_or_invalid_features():
    invalid = {"business_age_years": 4, "annual_revenue": 0, "annual_profit": 1,
               "monthly_expenses": 1, "total_liabilities": 1, "business_credit_score": 700,
               "prior_loan_count": 0, "missed_payments_12m": 0, "loan_amount": 100,
               "loan_tenure_months": 12}
    with pytest.raises(ValueError, match="annual_revenue"):
        calculate_prediction(invalid)


def test_applicant_application_insert_is_parameterized_and_transactional():
    connection = FakeConnection()
    database = FakeDatabase(connection)
    repository = WorkflowRepository(database)
    applicant_business = valid_business(business_id=None)
    saved = repository.create_applicant_application(7, applicant_business, valid_application())
    assert saved["loan_application_id"] == 81
    assert saved["business_id"] == 2345
    assert database.commits == 1
    business_sql, business_params = next(call for call in connection.calls if "INSERT INTO businesses" in call[0])
    app_sql, app_params = next(call for call in connection.calls if "INSERT INTO loan_applications" in call[0])
    assert "Northwind Foods" not in business_sql and "Northwind Foods" not in app_sql
    assert "RETURNING business_id" in business_sql
    assert "INSERT INTO businesses(business_id" not in business_sql
    assert "business_id," not in business_sql.split("VALUES", 1)[0].split("businesses(", 1)[1]
    assert business_params[0:2] == (7, 7)
    assert business_params[2] == "Northwind Foods"
    assert app_params[0] == 2345
    assert applicant_business.business_id == 2345
    assert "application_status" in app_sql


@pytest.mark.parametrize("highest_existing,expected_next", [(100, 101), (101, 102)])
def test_generated_business_id_is_returned_and_linked_to_loan_application(highest_existing, expected_next):
    connection = FakeConnection(generated_business_id=highest_existing + 1)
    assert connection.generated_business_id == expected_next
    business_to_submit = valid_business(business_id=None)
    saved = WorkflowRepository(FakeDatabase(connection)).create_applicant_application(
        7, business_to_submit, valid_application()
    )
    business_sql, _ = next(call for call in connection.calls if "INSERT INTO businesses" in call[0])
    loan_sql, loan_params = next(call for call in connection.calls if "INSERT INTO loan_applications" in call[0])
    assert "RETURNING business_id" in business_sql
    assert "business_id," not in business_sql.split("VALUES", 1)[0].split("businesses(", 1)[1]
    assert loan_params[0] == expected_next
    assert saved["business_id"] == business_to_submit.business_id == expected_next
    assert "INSERT INTO loan_applications(business_id," in loan_sql


def test_application_insert_rolls_back_if_loan_insert_fails():
    conn = FakeConnection()
    conn.fail_application_insert = True
    db = FakeDatabase(conn)
    with pytest.raises(RuntimeError):
        WorkflowRepository(db).create_applicant_application(7, valid_business(), valid_application())
    assert db.rollbacks == 1
    assert db.commits == 0


def test_applicant_application_query_scopes_by_authenticated_applicant():
    conn = FakeConnection()
    WorkflowRepository(FakeDatabase(conn)).get_applicant_applications(42)
    statement, params = conn.calls[-1]
    assert "b.applicant_user_id=%s" in statement
    assert params == (42,)


def test_duplicate_business_id_lookup_uses_parameterized_query():
    conn = FakeConnection()
    repo = WorkflowRepository(FakeDatabase(conn))
    assert not repo.business_id_exists(1001)
    statement, params = conn.calls[0]
    assert "business_id=%s" in statement
    assert params == (1001,)


def test_business_id_check_is_restricted_to_applicant_role():
    service = WorkflowService(FakeAuthRepository())
    applicant = Principal(1, "Asha", "asha@example.com", "SME_APPLICANT")
    manager = Principal(2, "Ravi", "ravi@example.com", "RELATIONSHIP_MANAGER")
    assert service.business_id_exists(applicant, 999)
    with pytest.raises(AuthorizationError):
        service.business_id_exists(manager, 999)


def test_rm_validation_assigns_manager_and_only_changes_eligible_status():
    conn = FakeConnection()
    assert WorkflowRepository(FakeDatabase(conn)).validate_application(5, 81)
    statement, params = conn.calls[0]
    assert "application_status='RM_VALIDATED'" in statement
    assert "application_status='SUBMITTED'" in statement
    assert "role='RELATIONSHIP_MANAGER'" in statement
    assert params == (5, 5, 81, 5, 5)


def test_information_request_and_applicant_response_are_separate_from_predictions():
    conn = FakeConnection()
    repo = WorkflowRepository(FakeDatabase(conn))
    assert repo.request_information(5, 81, "Please provide bank statements") == 19
    assert all("predictions" not in sql.lower() for sql, _ in conn.calls)
    conn.calls.clear()
    assert repo.respond_to_request(7, 19, "Uploaded statements")
    assert any("UPDATE application_info_requests" in sql for sql, _ in conn.calls)
    assert not any("predictions" in sql.lower() for sql, _ in conn.calls)


def test_assessment_is_blocked_before_rm_validation():
    class OfficerRepo(FakeAuthRepository):
        def get_officer_application(self, _app_id):
            return None
    service = WorkflowService(OfficerRepo())
    officer = Principal(3, "Officer", "officer@example.com", "LOAN_OFFICER")
    with pytest.raises(ValueError, match="RM validation"):
        service.assess_risk(officer, 81)


def test_prediction_insert_uses_prediction_table_and_preserves_history():
    conn = FakeConnection()
    repo = WorkflowRepository(FakeDatabase(conn))
    prediction = HybridRiskPrediction(1, "Default / High Risk", .55, .55)
    prediction_id = repo.save_prediction(8, 81, prediction)
    assert prediction_id == 29
    sql, params = conn.calls[-1]
    assert "INSERT INTO predictions" in sql
    assert "decision_remarks" not in sql
    assert params[0:2] == (81, 8)
    assert params[2:8] == ("SME Hybrid Model", "1.0.0", 55.0, "HIGH", "MANUAL_REVIEW", .55)


def test_final_decision_requires_risk_assessment_and_records_loan_officer():
    conn = FakeConnection()
    repo = WorkflowRepository(FakeDatabase(conn))
    assert repo.decide_application(8, 81, "APPROVED", "Reviewed and approved")
    statement, params = conn.calls[0]
    assert "application_status='RISK_ASSESSED'" in statement
    assert "EXISTS (SELECT 1 FROM predictions" in statement
    assert "role='LOAN_OFFICER'" in statement
    assert params == ("APPROVED", "APPROVED", "Reviewed and approved", 8, 81, 8)


@pytest.mark.parametrize("decision", ["APPROVE", "PENDING", "REJECT"])
def test_final_decision_rejects_nonterminal_values(decision):
    with pytest.raises(ValueError):
        WorkflowRepository(FakeDatabase()).decide_application(8, 81, decision, "Remarks")
