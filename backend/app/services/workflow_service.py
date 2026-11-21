"""Role-enforced business workflows above the PostgreSQL DAO layer."""

from dataclasses import dataclass

from backend.app.entities import Business, LoanApplication
from backend.app.repositories.workflow_repository import DuplicateBusinessIDError, WorkflowRepository
from backend.app.services.auth_service import (
    AuthenticationError,
    DuplicateCompanyNameError,
    DuplicateEmailError,
    ROLES,
    hash_password,
    require_role,
    validate_registration,
    validate_company_registration,
    verify_password,
)
from backend.app.services.sme_hybrid_prediction_service import predict_sme_hybrid
from backend.app.services.validation_service import validate_company_name


@dataclass(frozen=True)
class Principal:
    user_id: int
    full_name: str
    email: str | None
    role: str


class WorkflowService:
    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    def register_applicant(self, company_name: str, password: str, confirmation: str) -> int:
        name = validate_company_registration(company_name, password, confirmation)
        if self.repository.applicant_company_exists(name):
            raise DuplicateCompanyNameError("This company is already registered. Please choose Login.")
        return self.repository.create_applicant_account(name, hash_password(password))

    def applicant_company_exists(self, company_name: str) -> bool:
        name = validate_company_name(company_name)
        return self.repository.applicant_company_exists(name)

    def provision_staff(self, full_name: str, email: str, phone: str, password: str, confirmation: str, role: str) -> int:
        if role not in {"RELATIONSHIP_MANAGER", "LOAN_OFFICER"}:
            raise ValueError("Staff role must be RELATIONSHIP_MANAGER or LOAN_OFFICER.")
        name, normalized_email, normalized_phone = validate_registration(full_name, email, phone, password, confirmation)
        return self.repository.create_user(
            full_name=name, email=normalized_email, phone=normalized_phone,
            password_hash=hash_password(password), role=role,
        )

    def authenticate(self, email: str, password: str, expected_role: str) -> Principal:
        if expected_role not in ROLES:
            raise ValueError("Unsupported role.")
        user = self.repository.get_user_by_email(email.strip().lower())
        if not user or not user["is_active"] or user["role"] != expected_role or not verify_password(password, user["password_hash"]):
            raise AuthenticationError("Invalid email or password for this role.")
        return Principal(user["user_id"], user["full_name"], user["email"], user["role"])

    def authenticate_applicant(self, company_name: str, password: str) -> Principal:
        name = company_name.strip()
        user = self.repository.get_applicant_by_company_name(name)
        if (not name or not user or not user["is_active"]
                or user["role"] != "SME_APPLICANT"
                or not verify_password(password, user["password_hash"])):
            raise AuthenticationError("Invalid company name or password for an SME applicant.")
        return Principal(user["user_id"], user["company_name"], None, user["role"])

    @staticmethod
    def _user_id(principal: Principal | dict) -> int:
        return principal.user_id if isinstance(principal, Principal) else principal["user_id"]

    def submit_application(self, principal, business: Business, application: LoanApplication) -> dict:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "SME_APPLICANT")
        business.business_age_years = application.business_age_years
        business.employee_count = application.employee_count
        business.validate()
        application.validate()
        return self.repository.create_applicant_application(self._user_id(principal), business, application)

    def business_id_exists(self, principal, business_id: int) -> bool:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "SME_APPLICANT")
        if isinstance(business_id, bool) or not isinstance(business_id, int) or business_id <= 0:
            raise ValueError("Business ID must be a positive integer.")
        return self.repository.business_id_exists(business_id)

    def applicant_applications(self, principal) -> list[dict]:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "SME_APPLICANT")
        return self.repository.get_applicant_applications(self._user_id(principal))

    def applicant_requests(self, principal, *, open_only: bool = False) -> list[dict]:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "SME_APPLICANT")
        return self.repository.get_applicant_requests(self._user_id(principal), open_only=open_only)

    def respond_to_request(self, principal, request_id: int, response: str) -> bool:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "SME_APPLICANT")
        return self.repository.respond_to_request(self._user_id(principal), request_id, response.strip())

    def rm_applications(self, principal, *, assigned: bool = False) -> list[dict]:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "RELATIONSHIP_MANAGER")
        return self.repository.list_rm_applications(self._user_id(principal), assigned=assigned)

    def rm_application(self, principal, application_id: int) -> dict | None:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "RELATIONSHIP_MANAGER")
        return self.repository.get_rm_application(self._user_id(principal), application_id)

    def validate_application(self, principal, application_id: int) -> bool:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "RELATIONSHIP_MANAGER")
        return self.repository.validate_application(self._user_id(principal), application_id)

    def request_information(self, principal, application_id: int, request_text: str) -> int | None:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "RELATIONSHIP_MANAGER")
        if not request_text.strip():
            raise ValueError("Additional information request is required.")
        return self.repository.request_information(self._user_id(principal), application_id, request_text.strip())

    def officer_applications(self, principal) -> list[dict]:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "LOAN_OFFICER")
        return self.repository.list_officer_applications()

    def officer_application(self, principal, application_id: int) -> dict | None:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "LOAN_OFFICER")
        return self.repository.get_officer_application(application_id)

    def assess_risk(self, principal, application_id: int):
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "LOAN_OFFICER")
        application = self.repository.get_officer_application(application_id)
        if not application:
            raise ValueError("Application is unavailable or has not completed RM validation.")
        prediction = predict_sme_hybrid(application)
        prediction_id = self.repository.save_prediction(self._user_id(principal), application_id, prediction)
        if prediction_id is None:
            raise ValueError("Application is no longer eligible for assessment.")
        return prediction

    def latest_prediction(self, principal, application_id: int) -> dict | None:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "LOAN_OFFICER")
        return self.repository.latest_prediction(application_id)

    def decide_application(self, principal, application_id: int, decision: str, remarks: str) -> bool:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "LOAN_OFFICER")
        if not remarks.strip():
            raise ValueError("Decision remarks are required.")
        return self.repository.decide_application(self._user_id(principal), application_id, decision, remarks.strip())

    def processed_applications(self, principal) -> list[dict]:
        require_role(principal.__dict__ if isinstance(principal, Principal) else principal, "LOAN_OFFICER")
        return self.repository.list_processed_applications(self._user_id(principal))
