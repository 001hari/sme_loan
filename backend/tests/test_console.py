import pytest
from contextlib import contextmanager

from backend.app.console import provision_staff
from backend.app.console.main import CREDIT_RADAR_BANNER
from backend.app.console.role_app import RoleBasedConsoleApplication, _log_unexpected_failure
from backend.app.services.sme_hybrid_prediction_service import RiskPrediction
from backend.app.services.auth_service import AuthenticationError
from backend.app.services.workflow_service import Principal, WorkflowService
from backend.app.repositories.workflow_repository import WorkflowRepository


class FakeService:
    def __init__(self):
        self.authenticated_roles = []
        self.registrations = []
        self.registered_companies = set()
        self.applicant_logins = []
        self.fail_applicant_login = False
        self.registration_error = None
        self.existing_business_ids = set()
        self.checked_business_ids = []
        self.rm_application_calls = []
        self.rm_applications_calls = []
        self.validated_application_ids = []
        self.information_requests = []

    def authenticate(self, email, _password, role):
        self.authenticated_roles.append((email, role))
        return Principal(3, "Test Officer", email, role)

    def register_applicant(self, *values):
        if self.registration_error is not None:
            raise self.registration_error
        self.registrations.append(values)
        self.registered_companies.add(values[0].casefold())

    def submit_application(self, _principal, business, application):
        return {"loan_application_id": 44, "business_id": 27, "application_status": "SUBMITTED"}

    def applicant_company_exists(self, company_name):
        return company_name.casefold() in self.registered_companies

    def authenticate_applicant(self, company_name, password):
        self.applicant_logins.append((company_name, password))
        if self.fail_applicant_login:
            raise AuthenticationError("Invalid company name or password for an SME applicant.")
        return Principal(7, company_name, None, "SME_APPLICANT")

    def business_id_exists(self, _principal, business_id):
        self.checked_business_ids.append(business_id)
        return business_id in self.existing_business_ids

    def rm_applications(self, _principal, *, assigned=False):
        self.rm_applications_calls.append(assigned)
        return [{"loan_application_id": 4, "business_id": "SME000004", "business_name": "Northwind Foods",
                 "applicant_name": "Asha Rao", "loan_amount": 1000, "submitted_at": "today",
                 "application_status": "SUBMITTED"}]

    def rm_application(self, _principal, application_id):
        self.rm_application_calls.append(application_id)
        return {"loan_application_id": application_id, "business_id": 123,
                "business_name": "Northwind Foods", "application_status": "RM_VALIDATED",
                "info_requests": []}

    def validate_application(self, _principal, application_id):
        self.validated_application_ids.append(application_id)
        return True

    def request_information(self, _principal, application_id, request_text):
        self.information_requests.append((application_id, request_text))
        return 37

    def officer_applications(self, _principal):
        return [{"loan_application_id": 4, "business_name": "Northwind Foods", "loan_amount": 1000,
                 "application_status": "RM_VALIDATED"}]

    def officer_application(self, _principal, _application_id):
        return {"loan_application_id": 4, "business_name": "Northwind Foods"}

    def assess_risk(self, _principal, _application_id):
        return RiskPrediction(0, "Non-default", 0.25, 0.75)


def test_main_menu_has_only_three_requested_roles_and_exit():
    answers = iter(["bad", "4"])
    output = []
    app = RoleBasedConsoleApplication(FakeService(), input_fn=lambda _p: next(answers),
                                      password_fn=lambda _p: "unused", output_fn=output.append)
    app.run()
    assert any("SME Applicant" in line and "Relationship Manager" in line and "Loan Officer" in line for line in output)
    assert not any("Approval Authority" in line for line in output)
    assert "Goodbye." in output


def test_staff_login_uses_visible_input_and_logout_returns_to_main_menu():
    answers = iter(["3", "officer@example.com", "visible-password", "0", "4"])
    prompts = []
    output = []
    service = FakeService()
    app = RoleBasedConsoleApplication(
        service,
        input_fn=lambda prompt: (prompts.append(prompt), next(answers))[1],
        output_fn=output.append,
    )
    app.run()
    assert service.authenticated_roles == [("officer@example.com", "LOAN_OFFICER")]
    assert "Password: " in prompts
    assert "Logged out." in output


def test_banner_matches_centered_credit_radar_box_exactly():
    expected = (
        "╔══════════════════════════════════════════════════════════════╗\n"
        "║                                                              ║\n"
        "║                         CREDIT RADAR                         ║\n"
        "║                                                              ║\n"
        "║                SME LOAN RISK PREDICTION SYSTEM               ║\n"
        "║                                                              ║\n"
        "╚══════════════════════════════════════════════════════════════╝"
    )
    assert CREDIT_RADAR_BANNER == expected
    lines = CREDIT_RADAR_BANNER.splitlines()
    assert len({len(line) for line in lines}) == 1


def test_main_menu_retains_requested_role_numbers():
    output = []
    app = RoleBasedConsoleApplication(FakeService(), input_fn=lambda _prompt: "4",
                                      password_fn=lambda _prompt: "unused", output_fn=output.append)
    app.run()
    assert "1. SME Applicant\n2. Relationship Manager\n3. Loan Officer\n4. Exit" in output


def test_registration_diagnostics_log_exception_type_without_sensitive_message(caplog):
    _log_unexpected_failure("Applicant account registration", RuntimeError("password=do-not-log"))
    assert "RuntimeError" in caplog.text
    assert "Applicant account registration" in caplog.text
    assert "do-not-log" not in caplog.text


def test_applicant_registration_uses_company_name_and_omits_personal_prompts():
    answers = iter(["1", "Northwind Foods", "Test@123", "Test@123", "0"])
    prompts, output = [], []
    service = FakeService()
    app = RoleBasedConsoleApplication(service, input_fn=lambda prompt: (prompts.append(prompt), next(answers))[1],
                                      password_fn=lambda _prompt: pytest.fail("applicant registration must use visible input"),
                                      output_fn=output.append)
    app._applicant_entry()
    assert prompts == ["Select an option: ", "Company / Organization Name: ", "Create Password: ",
                       "Confirm Password: ", "Select an option: "]
    assert service.registrations == [("Northwind Foods", "Test@123", "Test@123")]
    assert "Successfully Registered! Your SME Applicant account has been created." in output
    assert not any(term in "\n".join(prompts).lower()
                   for term in ("applicant full name", "email", "phone"))
    assert "strong-password-1" not in "\n".join(output)


def test_registration_console_to_real_service_reaches_password_prompts():
    class ApplicantRepository:
        def __init__(self):
            self.account = None

        def applicant_company_exists(self, company_name):
            return False

        def create_applicant_account(self, company_name, password_hash):
            self.account = (company_name, password_hash)
            return 9

    repository = ApplicantRepository()
    answers = iter(["1", "Tcs", "Test@123", "Test@123", "0"])
    prompts = []
    app = RoleBasedConsoleApplication(
        WorkflowService(repository), input_fn=lambda prompt: (prompts.append(prompt), next(answers))[1],
        password_fn=lambda _prompt: pytest.fail("applicant registration must use visible input"),
        output_fn=lambda _line: None,
    )
    app._applicant_entry()
    assert "Create Password: " in prompts and "Confirm Password: " in prompts
    assert repository.account is not None
    assert repository.account[0] == "Tcs"
    assert repository.account[1] != "strong-password-1"


def test_short_password_displays_exact_validation_error():
    class Repository:
        def __init__(self):
            self.saved = []

        def applicant_company_exists(self, _company_name):
            return False

        def create_applicant_account(self, *args):
            self.saved.append(args)
            return 9

    answers = iter(["1", "Northwind Foods", "short7!", "Test@123", "Test@123", "0"])
    output = []
    repository = Repository()
    app = RoleBasedConsoleApplication(
        WorkflowService(repository), input_fn=lambda _prompt: next(answers),
        password_fn=lambda _prompt: pytest.fail("applicant registration must use visible input"),
        output_fn=output.append,
    )
    app._applicant_entry()
    assert "Password must be at least 8 characters long." in output
    assert len(repository.saved) == 1


def test_password_mismatch_displays_exact_validation_error():
    class Repository:
        def __init__(self):
            self.saved = []

        def applicant_company_exists(self, _company_name):
            return False

        def create_applicant_account(self, *args):
            self.saved.append(args)
            return 9

    answers = iter(["1", "Northwind Foods", "Swaroop@7", "swaroop@6", "Swaroop@7", "0"])
    output, prompts = [], []
    repository = Repository()
    app = RoleBasedConsoleApplication(
        WorkflowService(repository), input_fn=lambda prompt: (prompts.append(prompt), next(answers))[1],
        password_fn=lambda _prompt: pytest.fail("applicant registration must use visible input"),
        output_fn=output.append,
    )
    app._applicant_entry()
    mismatch_message = "[!] ERROR: Passwords do not match.\nPlease enter the confirmation password again."
    assert mismatch_message in output
    assert len(repository.saved) == 1
    assert prompts.count("Create Password: ") == 1
    assert prompts.count("Confirm Password: ") == 2
    assert "Password must contain at least one uppercase letter." not in output


def test_database_commit_failure_displays_error_without_success(caplog):
    class Result:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def execute(self, statement, params=()):
            if "SELECT EXISTS" in statement:
                return Result({"already_exists": False})
            if "INSERT INTO businesses" in statement:
                return Result({"business_id": 101})
            if "INSERT INTO loan_applications" in statement:
                return Result({"loan_application_id": 88, "application_status": "SUBMITTED",
                               "submitted_at": "now"})
            if "INSERT INTO users" in statement:
                return Result({"user_id": 45})
            return Result()

    class CommitFailureDatabase:
        def __init__(self):
            self.open_count = 0

        @contextmanager
        def connection(self):
            self.open_count += 1
            yield Connection()
            if self.open_count == 2:
                failure = RuntimeError("commit failed; password=must-not-be-logged")
                failure.sqlstate = "08006"
                raise failure

    answers = iter(["1", "Northwind Foods", "Test@123", "Test@123", "0"])
    output = []
    service = WorkflowService(WorkflowRepository(CommitFailureDatabase()))
    app = RoleBasedConsoleApplication(
        service, input_fn=lambda _prompt: next(answers),
        password_fn=lambda _prompt: pytest.fail("applicant registration must use visible input"),
        output_fn=output.append,
    )
    app._applicant_entry()
    assert any("database is unavailable" in line for line in output)
    assert "Successfully Registered! Your SME Applicant account has been created." not in output
    assert "RuntimeError" in caplog.text and "08006" in caplog.text
    assert "must-not-be-logged" not in caplog.text


def test_duplicate_company_registration_directs_applicant_to_login():
    answers = iter(["1", "Northwind Foods", "0"])
    password_prompts, output = [], []
    service = FakeService()
    service.registered_companies.add("northwind foods")
    app = RoleBasedConsoleApplication(
        service, input_fn=lambda _prompt: next(answers),
        password_fn=lambda prompt: (password_prompts.append(prompt), "unused-password")[1],
        output_fn=output.append,
    )
    app._applicant_entry()
    assert password_prompts == []
    assert any("already registered" in line and "Login" in line for line in output)
    assert service.registrations == []


def test_applicant_login_uses_company_name_and_visible_input():
    answers = iter(["2", "Northwind Foods", "strong-password-1", "0", "0"])
    prompts, output = [], []
    service = FakeService()
    app = RoleBasedConsoleApplication(
        service,
        input_fn=lambda prompt: (prompts.append(prompt), next(answers))[1],
        output_fn=output.append,
    )
    app._applicant_entry()
    assert service.applicant_logins == [("Northwind Foods", "strong-password-1")]
    assert "Password: " in prompts
    assert "Welcome, Northwind Foods." in output


def test_staff_provisioning_password_and_confirmation_use_visible_input(monkeypatch):
    prompts = []
    output = []
    answers = iter([
        "1", "Taylor Smith", "taylor@example.com", "+14155550123",
        "Swaroop@7", "swaroop@6", "Swaroop@7",
    ])

    class Database:
        def has_migration(self, _version):
            return True

    class Service:
        def provision_staff(self, *values):
            assert values[3:5] == ("Swaroop@7", "Swaroop@7")
            return 17

    monkeypatch.setattr(provision_staff, "DatabaseConnection", Database)
    monkeypatch.setattr(provision_staff, "WorkflowRepository", lambda _database: object())
    monkeypatch.setattr(provision_staff, "WorkflowService", lambda _repository: Service())
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: (prompts.append(prompt), next(answers))[1],
    )
    monkeypatch.setattr("builtins.print", output.append)

    assert provision_staff.main() == 0
    assert prompts.count("Create Password: ") == 1
    assert prompts.count("Confirm Password: ") == 2
    assert "[!] ERROR: Passwords do not match.\nPlease enter the confirmation password again." in output


def test_applicant_login_reports_incorrect_password_without_echoing_it():
    answers = iter(["2", "Northwind Foods", "0"])
    output = []
    service = FakeService()
    service.fail_applicant_login = True
    app = RoleBasedConsoleApplication(service, input_fn=lambda _prompt: next(answers),
                                      password_fn=lambda _prompt: "wrong-secret", output_fn=output.append)
    app._applicant_entry()
    assert any("Invalid company name or password" in line for line in output)
    assert "wrong-secret" not in "\n".join(output)


def test_business_form_and_application_summary_distinguish_company_name():
    answers = iter([
        "Northwind Foods Ltd", "1", "1", "Pune", "Maharashtra",
        "12", "1000000", "50000", "100000", "1", "0", "0", "1", "200000", "3",
        "4", "900000", "100000", "700", "1", ".1", "1.5",
    ])
    prompts, events = [], []
    service = FakeService()
    def read(prompt):
        prompts.append(prompt)
        events.append(prompt)
        return next(answers)
    app = RoleBasedConsoleApplication(service, input_fn=read,
                                      password_fn=lambda _prompt: "unused", output_fn=events.append)
    business, application = app._collect_application(Principal(1, "Asha Rao", "asha@example.com", "SME_APPLICANT"))
    app._show_application({"loan_application_id": 81, "business_id": 101,
                           "business_name": business.business_name, "applicant_name": "Asha Rao"})
    assert business.business_name == "Northwind Foods Ltd"
    assert prompts[0].startswith("Company / Organization Name (")
    assert "Business ID: " not in prompts
    assert any("Business Sector / Industry (select a number from 1-10)" in p for p in events)
    assert any("Business Legal Structure (select a number from 1-4)" in p for p in events)
    assert any("Business Location - City" in p and "Thiruvananthapuram" in p for p in prompts)
    assert any("Business Location - State" in p and "Kerala" in p for p in prompts)
    assert any("Company / Organization Name" in p and "ABC Technologies" in p for p in prompts)
    assert business.business_id is None  # Assigned only after PostgreSQL inserts the business.
    assert any("0 = No, 1 = Yes" in p for p in prompts)
    assert any("0.2 for 20% growth" in p and "-0.1 for 10% decline" in p for p in prompts)
    assert not any("Debt-to-revenue ratio (" in p or "Loan-to-revenue ratio (" in p or "Profit margin (" in p
                   for p in prompts)
    assert "Debt-to-revenue ratio, loan-to-revenue ratio, and profit margin are calculated automatically." in events
    assert application.debt_to_revenue_ratio == 0.1
    assert application.loan_to_revenue_ratio == 0.2
    assert application.profit_margin == 0.1
    assert any("1.5" in p for p in prompts if "DSCR" in p)
    required_order = ["Company / Organization Name", "Business Sector / Industry",
                      "Business Legal Structure", "Business Location - City", "Business Location - State",
                      "Employee count", "Annual revenue", "Monthly expenses", "Existing Loan Details",
                      "Previous loan count", "Late payment history", "Missed payments in the last 12 months",
                      "Loan purpose", "Loan amount", "Loan tenure in months"]
    prompt_text = "\n".join(events)
    positions = [prompt_text.index(item) for item in required_order]
    assert positions == sorted(positions)
    input_text = "\n".join(prompts).lower()
    assert not any(term in input_text for term in ("applicant full name", "email", "phone"))
    assert any("Company / Organization" in event and "Northwind Foods Ltd" in event for event in events)
    assert any("Applicant Full Name" in event and "Asha Rao" in event for event in events)
    assert any("Business ID" in event and "101" in event for event in events)
    assert any("Application ID" in event and "81" in event for event in events)


def test_business_id_is_not_manually_prompted_during_application_entry():
    answers = iter(["Cobalt Foods", "1", "1", "Pune", "Maharashtra",
                    "5", "1000000", "50000", "100000", "1", "0", "0", "1", "200000", "3",
                    "4", "900000", "100000", "700", "1", ".1", "1.5"])
    prompts = []
    service = FakeService()
    app = RoleBasedConsoleApplication(service, input_fn=lambda prompt: (prompts.append(prompt), next(answers))[1],
                                      password_fn=lambda _prompt: "unused", output_fn=lambda _line: None)
    business, _ = app._collect_application(Principal(1, "Asha Rao", "asha@example.com", "SME_APPLICANT"))
    assert service.checked_business_ids == []
    assert business.business_id is None
    assert "Business ID: " not in prompts


def test_invalid_annual_revenue_retries_until_valid_number():
    answers = iter(["-50000", "abc", "1000000"])
    output = []
    app = RoleBasedConsoleApplication(FakeService(), input_fn=lambda _prompt: next(answers),
                                      output_fn=output.append)
    value = app._number("Annual Revenue: ", minimum=0, minimum_exclusive=True,
                        field_name="Annual Revenue")
    assert value == 1000000
    assert "Annual Revenue must be greater than zero." in output
    assert any("valid number" in message for message in output)


@pytest.mark.parametrize("value", ["0.2", "1.5", "-0.1"])
def test_decimal_ratio_inputs_accept_valid_signed_decimal_values(value):
    answers = iter([value])
    app = RoleBasedConsoleApplication(FakeService(), input_fn=lambda _prompt: next(answers),
                                      output_fn=lambda _line: None)
    parsed = app._number("Revenue growth rate (decimal): ", field_name="Revenue Growth Rate")
    assert parsed == float(value)


def test_invalid_decimal_inputs_retry_until_a_valid_decimal_is_entered():
    answers = iter(["abc", "1..5", "", "0.2"])
    prompts, output = [], []
    app = RoleBasedConsoleApplication(FakeService(),
                                      input_fn=lambda prompt: (prompts.append(prompt), next(answers))[1],
                                      output_fn=output.append)
    parsed = app._number("Debt-to-revenue ratio (decimal): ", minimum=0,
                         field_name="Debt To Revenue Ratio")
    assert parsed == 0.2
    assert len(prompts) == 4
    assert sum("valid number" in message for message in output) == 2
    assert any("required" in message for message in output)


def test_submission_success_panel_uses_returned_ids_and_actual_application_values():
    class BusinessInput:
        business_name = "ABC Technologies"

    class ApplicationInput:
        loan_amount = 500000

    output = []
    answers = iter(["1", "Y", "0"])
    app = RoleBasedConsoleApplication(FakeService(), input_fn=lambda _p: next(answers),
                                      output_fn=output.append)
    app._collect_application = lambda _principal: (BusinessInput(), ApplicationInput())
    app._applicant_dashboard(Principal(7, "Applicant", None, "SME_APPLICANT"))
    rendered = "\n".join(output)
    assert "LOAN APPLICATION SUBMITTED" in rendered
    assert "[SUCCESS] Your loan application has been submitted!" in rendered
    assert "Application ID" in rendered and "44" in rendered
    assert "Business ID" in rendered and "27" in rendered
    assert "ABC Technologies" in rendered
    assert "Rs. 5,00,000.00" in rendered
    assert "Your application is now available for review." in rendered


def test_relationship_manager_validation_panel_uses_actual_details_and_only_follows_success():
    output = []
    answers = iter(["3", "4", "5"])
    service = FakeService()
    RoleBasedConsoleApplication(service, input_fn=lambda _p: next(answers),
                               output_fn=output.append)._rm_dashboard(
                                   Principal(2, "Ravi Sharma", "ravi@example.com", "RELATIONSHIP_MANAGER"))
    rendered = "\n".join(output)
    assert "APPLICATION VALIDATION COMPLETED" in rendered
    assert "[SUCCESS] Application successfully validated!" in rendered
    assert "Northwind Foods" in rendered and "123" in rendered and "Ravi Sharma" in rendered
    assert "RM_VALIDATED" in rendered

    class FailedValidationService(FakeService):
        def validate_application(self, _principal, _application_id):
            return False

    failed_output = []
    answers = iter(["3", "4", "5"])
    RoleBasedConsoleApplication(FailedValidationService(), input_fn=lambda _p: next(answers),
                               output_fn=failed_output.append)._rm_dashboard(
                                   Principal(2, "Ravi Sharma", "ravi@example.com", "RELATIONSHIP_MANAGER"))
    assert "[WARNING] Application is unavailable or not awaiting verification." in failed_output
    assert "APPLICATION VALIDATION COMPLETED" not in "\n".join(failed_output)


def test_risk_assessment_panel_displays_model_return_values_and_application_details():
    class OfficerService(FakeService):
        def officer_application(self, _principal, application_id):
            return {"loan_application_id": application_id, "business_id": 27,
                    "business_name": "ABC Technologies", "loan_amount": 500000,
                    "application_status": "RM_VALIDATED"}

        def assess_risk(self, _principal, _application_id):
            return RiskPrediction(1, "Default / High Risk", 0.361, 0.639, "test-version", "SME Hybrid Model")

    output = []
    answers = iter(["3", "44", "0"])
    RoleBasedConsoleApplication(OfficerService(), input_fn=lambda _p: next(answers),
                               output_fn=output.append)._officer_dashboard(
                                   Principal(3, "Officer", "officer@example.com", "LOAN_OFFICER"))
    rendered = "\n".join(output)
    assert "SME HYBRID MODEL RISK ASSESSMENT" in rendered
    assert "[SUCCESS] Risk assessment completed successfully!" in rendered
    assert "ABC Technologies" in rendered and "27" in rendered
    assert "Default / High Risk" in rendered and "36.10%" in rendered
    assert "SME Hybrid Model" in rendered and "COMPLETED" in rendered
    assert "synthetic-data-trained model" in rendered


def test_relationship_manager_and_loan_officer_views_use_company_name():
    output = []
    service = FakeService()
    manager_app = RoleBasedConsoleApplication(service, input_fn=lambda _p: next(manager_answers),
                                               password_fn=lambda _prompt: "unused", output_fn=output.append)
    manager_answers = iter(["1", "5"])
    manager_app._rm_dashboard(Principal(2, "Ravi", "ravi@example.com", "RELATIONSHIP_MANAGER"))
    assert any("Company Name" in line for line in output)
    assert any("Northwind Foods" in line for line in output)
    output.clear()
    officer_answers = iter(["1", "0"])
    officer_app = RoleBasedConsoleApplication(service, input_fn=lambda _p: next(officer_answers),
                                               password_fn=lambda _prompt: "unused", output_fn=output.append)
    officer_app._officer_dashboard(Principal(3, "Officer", "officer@example.com", "LOAN_OFFICER"))
    assert any("Northwind Foods" in line for line in output)


def test_rm_application_table_renders_multiple_rows_and_handles_empty_results():
    class MultiApplicationService(FakeService):
        def rm_applications(self, _principal, *, assigned=False):
            return [
                {"loan_application_id": 2, "business_id": 102, "business_name": "Wipro",
                 "applicant_name": "Wipro", "loan_amount": 1000000, "submitted_at": "2026-11-16T12:00:00",
                 "application_status": "SUBMITTED"},
                {"loan_application_id": 3, "business_id": 101, "business_name": "Cognizant",
                 "applicant_name": "Cognizant", "loan_amount": 1000, "submitted_at": "2026-11-17",
                 "application_status": "SUBMITTED"},
            ]

    output = []
    answers = iter(["1", "5"])
    RoleBasedConsoleApplication(MultiApplicationService(), input_fn=lambda _p: next(answers),
                               output_fn=output.append)._rm_dashboard(
                                   Principal(2, "Ravi", "ravi@example.com", "RELATIONSHIP_MANAGER"))
    assert "NEW LOAN APPLICATIONS" in "\n".join(output)
    assert any("Wipro" in line and "Rs. 10,00,000.00" in line for line in output)
    assert any("Cognizant" in line and "Rs. 1,000.00" in line for line in output)

    class EmptyService(FakeService):
        def rm_applications(self, _principal, *, assigned=False):
            return []

    empty_output = []
    answers = iter(["1", "5"])
    RoleBasedConsoleApplication(EmptyService(), input_fn=lambda _p: next(answers),
                               output_fn=empty_output.append)._rm_dashboard(
                                   Principal(2, "Ravi", "ravi@example.com", "RELATIONSHIP_MANAGER"))
    assert "No matching applications." in empty_output


def test_rm_application_details_table_handles_none_long_values_and_missing_application():
    output = []
    app = RoleBasedConsoleApplication(FakeService(), output_fn=output.append)
    app._show_application({"loan_application_id": 4, "business_id": 123,
                           "business_name": "A Very Long Company Name " * 5,
                           "sector": None, "application_status": "SUBMITTED"})
    rendered = "\n".join(output)
    assert "LOAN APPLICATION DETAILS" in rendered
    assert "FIELD" in rendered and "VALUE" in rendered
    assert "Not Assigned" in rendered
    assert "…" in rendered

    missing_output = []
    answers = iter(["2", "999", "5"])
    class MissingService(FakeService):
        def rm_application(self, _principal, application_id):
            self.rm_application_calls.append(application_id)
            return None
    service = MissingService()
    RoleBasedConsoleApplication(service, input_fn=lambda _p: next(answers),
                               output_fn=missing_output.append)._rm_dashboard(
                                   Principal(2, "Ravi", "ravi@example.com", "RELATIONSHIP_MANAGER"))
    assert service.rm_application_calls == [999]
    assert "Application not found or assigned to another manager." in missing_output


def test_applicant_dashboard_adds_details_option_and_formats_own_applications():
    application = {
        "loan_application_id": 3, "business_id": 101, "business_name": "Cognizant",
        "applicant_name": "Cognizant", "sector": "Information Technology", "legal_status": "Private Limited",
        "city": "TVM", "state": "KL", "business_age_years": 10, "employee_count": 1000,
        "annual_revenue": 1000000, "previous_year_revenue": 1000000, "annual_profit": 100000,
        "monthly_expenses": 100000, "total_liabilities": 10000, "business_credit_score": 700,
        "prior_loan_count": 3, "late_payment_history": True, "missed_payments_12m": 1,
        "loan_amount": 1000, "loan_tenure_months": 12, "loan_purpose": "Working Capital",
        "cash_flow_stability": "Moderate", "revenue_growth_rate": 1000, "debt_to_revenue_ratio": 1000,
        "loan_to_revenue_ratio": 1900, "profit_margin": 1000, "dscr": 10010,
        "application_status": "SUBMITTED", "decision_remarks": None, "submitted_at": "2026-11-17",
    }
    class ApplicantService(FakeService):
        def applicant_applications(self, _principal):
            return [application]

    output = []
    answers = iter(["2", "3", "0"])
    RoleBasedConsoleApplication(ApplicantService(), input_fn=lambda _p: next(answers),
                               output_fn=output.append)._applicant_dashboard(
                                   Principal(7, "Cognizant", None, "SME_APPLICANT"))
    rendered = "\n".join(output)
    assert "3. View My Application Details" in rendered
    assert "MY LOAN APPLICATIONS" in rendered
    assert "MY LOAN APPLICATION DETAILS" in rendered
    assert "1000.0000" in rendered
    assert "Not Assigned" in rendered


def test_applicant_details_require_application_to_be_in_scoped_own_application_list():
    own_rows = [
        {"loan_application_id": 3, "business_id": 101, "business_name": "Own Company",
         "loan_amount": 1000, "application_status": "SUBMITTED"},
        {"loan_application_id": 4, "business_id": 102, "business_name": "Second Company",
         "loan_amount": 2000, "application_status": "SUBMITTED"},
    ]
    class ApplicantService(FakeService):
        def applicant_applications(self, _principal):
            return own_rows

    output = []
    answers = iter(["3", "999", "0"])
    RoleBasedConsoleApplication(ApplicantService(), input_fn=lambda _p: next(answers),
                               output_fn=output.append)._applicant_dashboard(
                                   Principal(7, "Applicant", None, "SME_APPLICANT"))
    assert "That Application ID is not among your applications." in output
    assert "MY LOAN APPLICATION DETAILS" not in "\n".join(output)


def test_applicant_with_no_applications_gets_message_and_officer_views_use_tables():
    class EmptyApplicantService(FakeService):
        def applicant_applications(self, _principal):
            return []

    output = []
    answers = iter(["3", "0"])
    RoleBasedConsoleApplication(EmptyApplicantService(), input_fn=lambda _p: next(answers),
                               output_fn=output.append)._applicant_dashboard(
                                   Principal(7, "Applicant", None, "SME_APPLICANT"))
    assert "No applications are available to view." in output

    officer_output = []
    answers = iter(["1", "2", "4", "0"])
    RoleBasedConsoleApplication(FakeService(), input_fn=lambda _p: next(answers),
                               output_fn=officer_output.append)._officer_dashboard(
                                   Principal(3, "Officer", "officer@example.com", "LOAN_OFFICER"))
    rendered = "\n".join(officer_output)
    assert "RM-VALIDATED LOAN APPLICATIONS" in rendered
    assert "FIELD" in rendered and "VALUE" in rendered


def test_applicant_application_list_displays_every_owned_application_in_table():
    class ApplicantService(FakeService):
        def applicant_applications(self, _principal):
            return [
                {"loan_application_id": 3, "business_id": 101, "business_name": "Cognizant",
                 "loan_amount": 1000, "submitted_at": "2026-11-17", "application_status": "SUBMITTED"},
                {"loan_application_id": 4, "business_id": 102, "business_name": "Infosys",
                 "loan_amount": 2000, "submitted_at": "2026-11-18", "application_status": "RM_VALIDATED"},
            ]

    output = []
    answers = iter(["2", "0"])
    RoleBasedConsoleApplication(ApplicantService(), input_fn=lambda _p: next(answers),
                               output_fn=output.append)._applicant_dashboard(
                                   Principal(7, "Applicant", None, "SME_APPLICANT"))
    rendered = "\n".join(output)
    assert "MY LOAN APPLICATIONS" in rendered
    assert "Cognizant" in rendered and "Infosys" in rendered
    assert "SUBMITTED" in rendered and "RM_VALIDATED" in rendered


def test_details_hide_duplicate_rm_id_keep_officer_id_and_render_nulls_as_unassigned():
    output = []
    RoleBasedConsoleApplication(FakeService(), output_fn=output.append)._show_application({
        "loan_application_id": 8,
        "relationship_manager_id": None,
        "rm_id": None,
        "loan_officer_id": None,
    })
    rendered = "\n".join(output)
    assert rendered.count("Relationship Manager ID") == 1
    assert "RM ID" not in rendered
    assert "Loan Officer ID" in rendered
    assert rendered.count("Not Assigned") == 2


def test_details_display_manager_assignment_once_when_legacy_and_canonical_columns_match():
    output = []
    RoleBasedConsoleApplication(FakeService(), output_fn=output.append)._show_application({
        "relationship_manager_id": 42,
        "rm_id": 42,
        "loan_officer_id": 73,
    })
    rendered = "\n".join(output)
    assert rendered.count("Relationship Manager ID") == 1
    assert "| 42" in rendered
    assert "RM ID" not in rendered
    assert "Loan Officer ID" in rendered and "73" in rendered


def test_relationship_manager_dashboard_renumbers_actions_and_reopens_assigned_details():
    answers = iter(["1", "2", "4", "3", "4", "4", "4", "Please provide the latest bank statement.", "5"])
    output = []
    service = FakeService()
    app = RoleBasedConsoleApplication(service, input_fn=lambda _prompt: next(answers),
                                      password_fn=lambda _prompt: "unused", output_fn=output.append)
    app._rm_dashboard(Principal(2, "Ravi", "ravi@example.com", "RELATIONSHIP_MANAGER"))

    expected_menu = (
        "\nRelationship Manager Dashboard\n1. View New Applications\n"
        "2. View Application Details\n3. Validate Application\n"
        "4. Request Additional Information\n5. Logout"
    )
    assert expected_menu in output
    assert not any("View Assigned Applications" in line for line in output)
    assert service.rm_applications_calls == [False]
    assert service.rm_application_calls == [4, 4]
    assert service.validated_application_ids == [4]
    assert service.information_requests == [(4, "Please provide the latest bank statement.")]
    assert "[SUCCESS]" in "\n".join(output)
    assert "[SUCCESS] Information request 37 sent." in output
    assert "Logged out." in output


def test_risk_radar_display_uses_company_name():
    output = []
    answers = iter(["3", "4", "0"])
    officer_app = RoleBasedConsoleApplication(FakeService(), input_fn=lambda _p: next(answers),
                                               password_fn=lambda _prompt: "unused", output_fn=output.append)
    officer_app._officer_dashboard(Principal(3, "Officer", "officer@example.com", "LOAN_OFFICER"))
    rendered = "\n".join(output)
    assert "Company Name" in rendered and "Northwind Foods" in rendered
    assert "SME HYBRID MODEL RISK ASSESSMENT" in rendered
