"""Role-based interactive console UI; all authorization lives in services."""

import logging
from decimal import Decimal, InvalidOperation
from typing import Callable

from backend.app.entities import Business, LoanApplication
from backend.app.services.auth_service import AuthenticationError, DuplicateCompanyNameError
from backend.app.services.workflow_service import WorkflowService
from backend.app.services.validation_service import (
    parse_number, required_text, validate_alpha_text, validate_company_name, validate_numeric_value,
    validate_password, validate_range,
)


logger = logging.getLogger(__name__)


def _format_inr(value) -> str:
    """Format a numeric amount with Indian digit grouping and two decimals."""
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
        if not amount.is_finite():
            return str(value)
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    negative = amount < 0
    whole, fraction = f"{abs(amount):.2f}".split(".")
    if len(whole) > 3:
        groups = [whole[-3:]]
        whole = whole[:-3]
        while whole:
            groups.insert(0, whole[-2:])
            whole = whole[:-2]
        whole = ",".join(groups)
    return f"Rs. {'-' if negative else ''}{whole}.{fraction}"


def _format_console_table(headers: tuple[str, ...], rows: list[tuple], *, max_widths: tuple[int, ...] | None = None,
                          title: str | None = None) -> list[str]:
    """Build a dependency-free, fixed-width table; long cell text is shortened safely."""
    values = [["Not Assigned" if value is None else str(value) for value in row] for row in rows]
    widths = []
    for index, header in enumerate(headers):
        content_width = max((len(row[index]) for row in values), default=0)
        width = max(len(header), content_width)
        if max_widths:
            width = min(width, max_widths[index])
        widths.append(width)

    def fit(value: str, width: int) -> str:
        return value if len(value) <= width else value[:max(1, width - 1)] + "…"

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def render(row) -> str:
        return "| " + " | ".join(fit(str(value), width).ljust(width) for value, width in zip(row, widths)) + " |"

    lines = [border, render(headers), border]
    lines.extend(render(row) for row in values)
    lines.append(border)
    if title:
        lines.insert(0, title.center(len(border)))
    return lines


def _format_application_list(rows: list[dict], *, include_applicant: bool, title: str = "LOAN APPLICATIONS") -> list[str]:
    headers = (("Application ID", "Business ID", "Company Name", "Applicant Name", "Loan Amount",
                "Submission Date", "Application Status") if include_applicant else
               ("Application ID", "Business ID", "Company Name", "Loan Amount", "Submission Date",
                "Application Status"))
    table_rows = []
    for row in rows:
        amount = _format_inr(row.get("loan_amount")) if row.get("loan_amount") is not None else None
        submitted = row.get("submitted_at")
        submitted = str(submitted)[:10] if submitted is not None else None
        values = (row.get("loan_application_id"), row.get("business_id"), row.get("business_name"))
        if include_applicant:
            values += (row.get("applicant_name"),)
        table_rows.append(values + (amount, submitted, row.get("application_status")))
    widths = (15, 13, 22, 22, 21, 19, 18) if include_applicant else (15, 13, 22, 21, 19, 18)
    return _format_console_table(headers, table_rows, max_widths=widths, title=title)


def _log_unexpected_failure(operation: str, exc: Exception) -> None:
    """Log safe error metadata without exception text, SQL parameters, or secrets."""
    diagnostic = getattr(exc, "diag", None)
    logger.error(
        "%s failed: exception_type=%s sqlstate=%s constraint=%s table=%s column=%s",
        operation,
        type(exc).__name__,
        getattr(exc, "sqlstate", None),
        getattr(diagnostic, "constraint_name", None),
        getattr(diagnostic, "table_name", None),
        getattr(diagnostic, "column_name", None),
    )


def _registration_failure_message(exc: Exception) -> str:
    """Return a useful public message without revealing database diagnostics."""
    sqlstate = getattr(exc, "sqlstate", None)
    if sqlstate and sqlstate.startswith("08"):
        return "Error: The database is unavailable, so registration could not be saved. Please try again later."
    if sqlstate == "23503":
        return "Error: The applicant account could not be linked to its role profile. Please contact support."
    if sqlstate == "23514":
        return "Error: The account details did not meet a database rule. Check the company name and try again."
    if sqlstate:
        return "Error: The database could not save the applicant account. Please try again or contact support."
    return "Error: Registration failed unexpectedly. Please try again or contact support."


class RoleBasedConsoleApplication:
    def __init__(self, service: WorkflowService, input_fn: Callable[[str], str] = input,
                 password_fn: Callable[[str], str] | None = None, output_fn: Callable[[str], None] = print) -> None:
        self.service = service
        self.input = input_fn
        # Use the same visible console input by default for password prompts.
        self.password = password_fn or input_fn
        self.output = output_fn

    def _text(self, prompt: str) -> str:
        while True:
            try:
                return required_text(self.input(prompt), prompt.rstrip(": "))
            except ValueError as exc:
                self.output(str(exc))

    def _success_panel(self, title: str, message: str,
                       sections: list[tuple[str, tuple[str, ...], list[tuple]]],
                       footer: str | None = None) -> None:
        border = "=" * 60
        self.output(border)
        self.output(title.center(60))
        self.output(border)
        self.output(f"[SUCCESS] {message}")
        for heading, headers, rows in sections:
            if heading:
                self.output("")
                self.output(heading)
            for line in _format_console_table(headers, rows, max_widths=(24, 56)):
                self.output(f"  {line}")
        if footer:
            self.output("")
            self.output(footer)
        self.output("")
        self.output(border)

    def _number(self, prompt: str, *, integer: bool = False, minimum=None, maximum=None,
                minimum_exclusive: bool = False, field_name: str | None = None) -> int | float:
        label = field_name or prompt.rstrip(": ")
        while True:
            try:
                value = parse_number(self.input(prompt), label, integer=integer)
                if integer:
                    validate_range(value, label, minimum=minimum, maximum=maximum)
                else:
                    value = validate_numeric_value(value, label, minimum=minimum, maximum=maximum,
                                                   minimum_exclusive=minimum_exclusive)
                return value
            except ValueError as exc:
                self.output(str(exc))

    def _alpha_text(self, prompt: str, field_name: str | None = None) -> str:
        label = field_name or prompt.rstrip(": ")
        while True:
            try:
                return validate_alpha_text(self.input(prompt), label)
            except ValueError as exc:
                self.output(str(exc))

    def _company_name(self, prompt: str = "Company / Organization Name: ") -> str:
        while True:
            try:
                return validate_company_name(self.input(prompt))
            except ValueError as exc:
                self.output(str(exc))

    def _select(self, title: str, values: tuple) -> str:
        self.output(title)
        for i, value in enumerate(values, start=1):
            self.output(f"  {i}. {value}")
        while True:
            raw = self.input("Select a number: ").strip()
            try:
                index = int(raw)
                if 1 <= index <= len(values):
                    return values[index - 1]
            except ValueError:
                pass
            self.output("Choose one of the listed numbers.")

    def _confirm(self, prompt: str) -> bool:
        while True:
            answer = self.input(prompt).strip().lower()
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            self.output("Enter Y or N.")

    def _login(self, role: str):
        self.output(f"\n{role.replace('_', ' ').title()} Login")
        email = self._text("Registered email: ")
        password = self.password("Password: ")
        try:
            principal = self.service.authenticate(email, password, role)
            self.output(f"Welcome, {principal.full_name}.")
            return principal
        except AuthenticationError as exc:
            self.output(str(exc))
            return None
        except Exception:
            self.output("Login could not be completed. Check the database and try again.")
            return None

    def _applicant_entry(self) -> None:
        while True:
            self.output("\nSME Applicant\n1. Register\n2. Login\n0. Back")
            choice = self.input("Select an option: ").strip()
            if choice == "0":
                return
            if choice == "1":
                company_name = self._company_name()
                try:
                    if self.service.applicant_company_exists(company_name):
                        self.output("This company is already registered. Please choose Login.")
                        continue
                except ValueError as exc:
                    self.output(f"Error: {exc}")
                    continue
                except Exception as exc:
                    _log_unexpected_failure("Applicant company duplicate check", exc)
                    self.output("Error: Company registration could not be checked. Please try again or contact support.")
                    continue
                self.output(
                    "Password Requirements:\n"
                    "- 8 to 12 characters.\n"
                    "- At least one uppercase letter (A-Z).\n"
                    "- At least one lowercase letter (a-z).\n"
                    "- At least one number (0-9).\n"
                    "- At least one special character (@, #, $, %, !, etc.).\n"
                    "- No spaces allowed."
                )
                while True:
                    password = self.input("Create Password: ")
                    try:
                        validate_password(password)
                    except ValueError as exc:
                        self.output(str(exc))
                        continue
                    while True:
                        confirmation = self.input("Confirm Password: ")
                        if password != confirmation:
                            self.output("[!] ERROR: Passwords do not match.\nPlease enter the confirmation password again.")
                            continue
                        break
                    break
                try:
                    self.service.register_applicant(company_name, password, confirmation)
                    self.output("Successfully Registered! Your SME Applicant account has been created.")
                except DuplicateCompanyNameError as exc:
                    self.output(str(exc))
                except ValueError as exc:
                    self.output(f"Error: {exc}")
                except Exception as exc:
                    _log_unexpected_failure("Applicant account registration", exc)
                    self.output(_registration_failure_message(exc))
                continue
            if choice == "2":
                principal = self._applicant_login()
                if principal:
                    self._applicant_dashboard(principal)
                continue
            self.output("Choose 1, 2, or 0.")

    def _applicant_login(self):
        self.output("\nSME Applicant Login")
        company_name = self._text("Company / Organization Name: ")
        password = self.password("Password: ")
        try:
            principal = self.service.authenticate_applicant(company_name, password)
            self.output(f"Welcome, {principal.full_name}.")
            return principal
        except AuthenticationError as exc:
            self.output(str(exc))
            return None
        except Exception as exc:
            _log_unexpected_failure("Applicant company login", exc)
            self.output("Login could not be completed. Check the database and try again.")
            return None

    def _collect_application(self, principal) -> tuple[Business, LoanApplication]:
        self.output("\nBusiness information")
        #self.output("Business ID (auto-generated after submission; no input required).")
        business = Business(
            business_id=None,
            business_name=self._company_name(
                "Company / Organization Name (English letters and spaces only, e.g., ABC Technologies): "
            ),
            sector=self._select("Business Sector / Industry (select a number from 1-10):", Business.VALID_SECTORS),
            legal_status=self._select("Business Legal Structure (select a number from 1-4):", Business.VALID_LEGAL_STATUSES),
            city=self._alpha_text("Business Location - City (letters and spaces, e.g., Thiruvananthapuram): ", "City"),
            state=self._alpha_text("Business Location - State (state name, e.g., Kerala): ", "State"),
        )
        self.output("\nBusiness and loan information")
        employee_count = self._number("Employee count (positive whole number, e.g., 100): ", integer=True,
                                       minimum=1, field_name="Employee Count")
        annual_revenue = self._number("Annual revenue (positive amount in Rs., e.g., 1000000): ", minimum=0,
                                      minimum_exclusive=True, field_name="Annual Revenue")
        monthly_expenses = self._number("Monthly expenses (zero or positive Rs. amount, e.g., 50000): ", minimum=0)
        total_liabilities = self._number(
            "Existing Loan Details - total outstanding liabilities (zero or positive Rs. amount, e.g., 200000): ",
            minimum=0)
        prior_loan_count = self._number("Previous loan count (zero or positive whole number, e.g., 3): ",
                                        integer=True, minimum=0)
        late_payment_history = bool(self._number("Late payment history (0 = No, 1 = Yes): ", integer=True,
                                                  minimum=0, maximum=1))
        missed_payments_12m = self._number(
            "Missed payments in the last 12 months (whole number from 0 to 6, e.g., 1): ", integer=True,
            minimum=0, maximum=6)
        loan_purpose = self._select("Loan purpose (select a number from 1-6):", LoanApplication.VALID_LOAN_PURPOSES)
        loan_amount = self._number("Loan amount (positive amount in Rs., e.g., 500000): ", minimum=0,
                                   minimum_exclusive=True, field_name="Loan Amount")
        loan_tenure_months = int(self._select(
            "Loan tenure in months (select a number from 1-7): ", tuple(str(x) for x in LoanApplication.VALID_TENURES)))
        business_age_years = self._number(
            "Business age in years (positive number up to 100; decimals accepted, e.g., 10): ", minimum=0,
            maximum=100, minimum_exclusive=True, field_name="Business Age Years")
        previous_year_revenue = self._number(
            "Previous year revenue (zero or positive Rs. amount, e.g., 900000): ", minimum=0,
            field_name="Previous Year Revenue")
        annual_profit = self._number(
            "Annual profit (Rs. amount; negative allowed, e.g., 100000 or -50000): ", field_name="Annual Profit")
        business_credit_score = self._number("Business credit score (whole number from 300 to 900, e.g., 700): ",
                                             integer=True, minimum=300, maximum=900,
                                             field_name="Business Credit Score")
        cash_flow_stability = self._select("Cash-flow stability (select a number from 1-3):",
                                           LoanApplication.VALID_CASH_FLOW_STABILITY)
        self.output("Debt-to-revenue ratio, loan-to-revenue ratio, and profit margin are calculated automatically.")
        revenue_growth_rate = self._number(
            "Revenue growth rate (decimal, e.g., 0.2 for 20% growth or -0.1 for 10% decline): ",
            field_name="Revenue Growth Rate")
        dscr = self._number("Debt service coverage ratio - DSCR (zero or positive decimal, e.g., 1.5): ",
                            minimum=0, field_name="DSCR")

        application = LoanApplication(
            employee_count=employee_count,
            annual_revenue=annual_revenue,
            monthly_expenses=monthly_expenses,
            total_liabilities=total_liabilities,
            prior_loan_count=prior_loan_count,
            late_payment_history=late_payment_history,
            missed_payments_12m=missed_payments_12m,
            loan_purpose=loan_purpose,
            loan_amount=loan_amount,
            loan_tenure_months=loan_tenure_months,
            business_age_years=business_age_years,
            previous_year_revenue=previous_year_revenue,
            annual_profit=annual_profit,
            business_credit_score=business_credit_score,
            cash_flow_stability=cash_flow_stability,
            revenue_growth_rate=revenue_growth_rate,
            debt_to_revenue_ratio=total_liabilities / annual_revenue,
            loan_to_revenue_ratio=loan_amount / annual_revenue,
            profit_margin=annual_profit / annual_revenue,
            dscr=dscr,
        )
        business.business_age_years = application.business_age_years
        business.employee_count = application.employee_count
        business.validate()
        application.validate()
        return business, application

    def _show_application(self, row: dict, *, title: str = "LOAN APPLICATION DETAILS") -> None:
        labels = {
            "loan_application_id": "Application ID", "application_id": "Application ID",
            "business_id": "Business ID", "business_name": "Company / Organization",
            "applicant_name": "Applicant Full Name", "sector": "Sector", "legal_status": "Legal Status",
            "city": "City", "state": "State", "business_age_years": "Business Age Years",
            "company_age_years": "Business Age Years", "employee_count": "Employee Count",
            "company_employee_count": "Employee Count", "annual_revenue": "Annual Revenue",
            "previous_year_revenue": "Previous Year Revenue", "annual_profit": "Annual Profit",
            "monthly_expenses": "Monthly Expenses", "total_liabilities": "Total Liabilities",
            "business_credit_score": "Business Credit Score", "prior_loan_count": "Prior Loan Count",
            "late_payment_history": "Late Payment History", "missed_payments_12m": "Missed Payments 12M",
            "loan_amount": "Loan Amount", "loan_tenure_months": "Loan Tenure Months",
            "loan_purpose": "Loan Purpose", "cash_flow_stability": "Cash Flow Stability",
            "revenue_growth_rate": "Revenue Growth Rate", "debt_to_revenue_ratio": "Debt To Revenue Ratio",
            "loan_to_revenue_ratio": "Loan To Revenue Ratio", "profit_margin": "Profit Margin",
            "dscr": "DSCR", "application_status": "Application Status",
            "decision_remarks": "Decision Remarks", "submitted_at": "Submission Date",
            "updated_at": "Last Updated", "applicant_email": "Applicant Email",
            "applicant_id": "Applicant ID", "relationship_manager_id": "Relationship Manager ID",
            "loan_officer_id": "Loan Officer ID",
        }
        preferred = (
            "loan_application_id", "business_id", "business_name", "applicant_name", "sector", "legal_status",
            "city", "state", "business_age_years", "company_age_years", "employee_count",
            "company_employee_count", "annual_revenue", "previous_year_revenue", "annual_profit",
            "monthly_expenses", "total_liabilities", "business_credit_score", "prior_loan_count",
            "late_payment_history", "missed_payments_12m", "loan_amount", "loan_tenure_months",
            "loan_purpose", "cash_flow_stability", "revenue_growth_rate", "debt_to_revenue_ratio",
            "loan_to_revenue_ratio", "profit_margin", "dscr", "application_status", "decision_remarks",
            "submitted_at", "updated_at", "applicant_email", "applicant_id", "relationship_manager_id",
            "loan_officer_id",
        )
        keys = [key for key in preferred if key in row]
        if "loan_application_id" in row:
            keys = [key for key in keys if key != "application_id"]
        if "business_age_years" in row:
            keys = [key for key in keys if key != "company_age_years"]
        if "employee_count" in row:
            keys = [key for key in keys if key != "company_employee_count"]
        keys.extend(key for key in row if key not in keys and key not in {"info_requests", "rm_id"})
        decimal_places = {
            "business_age_years": 2, "company_age_years": 2, "annual_revenue": 2,
            "previous_year_revenue": 2, "annual_profit": 2, "monthly_expenses": 2,
            "total_liabilities": 2, "loan_amount": 2, "revenue_growth_rate": 2,
            "debt_to_revenue_ratio": 4, "loan_to_revenue_ratio": 4, "profit_margin": 4, "dscr": 4,
        }
        table_rows = []
        for key in keys:
            value = row[key]
            if value is not None and key == "loan_amount":
                value = _format_inr(value)
            elif value is not None and key in decimal_places:
                try:
                    value = f"{float(value):.{decimal_places[key]}f}"
                except (TypeError, ValueError):
                    pass
            table_rows.append((labels.get(key, key.replace("_", " ").title()), value))
        for line in _format_console_table(("FIELD", "VALUE"), table_rows, max_widths=(28, 64), title=title):
            self.output(line)

    def _show_applicant_application_details(self, principal) -> None:
        # This scoped service method only returns applications owned by the current applicant.
        applications = self.service.applicant_applications(principal)
        if not applications:
            self.output("No applications are available to view.")
            return
        for line in _format_application_list(applications, include_applicant=False, title="MY LOAN APPLICATIONS"):
            self.output(line)
        if len(applications) == 1:
            selected = applications[0]
        else:
            application_id = self._number("Application ID to view: ", integer=True, minimum=1)
            selected = next((row for row in applications
                             if str(row.get("loan_application_id", row.get("application_id"))) == str(application_id)), None)
            if selected is None:
                self.output("That Application ID is not among your applications.")
                return
        self._show_application(selected, title="MY LOAN APPLICATION DETAILS")

    def _applicant_dashboard(self, principal) -> None:
        while True:
            self.output("\nApplicant Dashboard\n1. Submit New Loan Application\n2. View My Applications\n3. View My Application Details\n4. View Additional Information Requests\n5. Respond to Additional Information Request\n0. Logout")
            choice = self.input("Select an option: ").strip()
            try:
                if choice == "0":
                    self.output("Logged out.")
                    return
                if choice == "1":
                    while True:
                        business, application = self._collect_application(principal)
                        self.output("\nReview application")
                        for key, value in vars(business).items():
                            if key == "business_id":
                                continue
                            label = "Company / Organization Name" if key == "business_name" else key.replace("_", " ").title()
                            self.output(f"{label}: {value}")
                        for key, value in vars(application).items():
                            if key not in {"loan_application_id", "risk_predicted_score", "approval_result"}:
                                self.output(f"{key.replace('_', ' ').title()}: {value}")
                        if self._confirm("Do you want to submit this loan application? (Y/N): "):
                            saved = self.service.submit_application(principal, business, application)
                            self._success_panel(
                                "LOAN APPLICATION SUBMITTED",
                                "Your loan application has been submitted!",
                                [("", ("Field", "Details"), [
                                    ("Application ID", saved.get("loan_application_id")),
                                    ("Business ID", saved.get("business_id")),
                                    ("Company Name", business.business_name),
                                    ("Loan Amount", _format_inr(application.loan_amount)),
                                    ("Application Status", saved.get("application_status")),
                                ])],
                                footer="Your application is now available for review.",
                            )
                            break
                        if not self._confirm("Return to editing this application? (Y/N): "):
                            self.output("Submission cancelled; no application was saved.")
                            break
                    continue
                if choice == "2":
                    rows = self.service.applicant_applications(principal)
                    if not rows:
                        self.output("No applications found.")
                    else:
                        for line in _format_application_list(rows, include_applicant=False,
                                                             title="MY LOAN APPLICATIONS"):
                            self.output(line)
                    continue
                if choice == "3":
                    self._show_applicant_application_details(principal)
                    continue
                if choice == "4":
                    rows = self.service.applicant_requests(principal)
                    if not rows:
                        self.output("No information requests found.")
                    for row in rows:
                        self.output(f"Request {row['request_id']} | Application {row['loan_application_id']} | {row['request_status']}\nRequest: {row['request_text']}\nResponse: {row['applicant_response'] or 'Not yet provided'}")
                    continue
                if choice == "5":
                    rows = self.service.applicant_requests(principal, open_only=True)
                    for row in rows:
                        self.output(f"Request {row['request_id']} | Application {row['loan_application_id']} | {row['request_text']}")
                    if rows:
                        request_id = self._number("Request ID to respond to: ", integer=True, minimum=1)
                        response = self._text("Your response: ")
                        self.output("[SUCCESS] Response saved." if self.service.respond_to_request(principal, request_id, response)
                                    else "[WARNING] Request not found or already answered.")
                    else:
                        self.output("No open requests.")
                    continue
                self.output("Choose 1, 2, 3, 4, 5, or 0.")
            except (ValueError, PermissionError) as exc:
                self.output(f"[ERROR] {exc}")
            except Exception:
                self.output("[ERROR] Action could not be completed. Check the database and try again.")

    def _rm_dashboard(self, principal) -> None:
        while True:
            self.output("\nRelationship Manager Dashboard\n1. View New Applications\n2. View Application Details\n3. Validate Application\n4. Request Additional Information\n5. Logout")
            choice = self.input("Select an option: ").strip()
            try:
                if choice == "5":
                    self.output("Logged out.")
                    return
                if choice == "1":
                    rows = self.service.rm_applications(principal)
                    if not rows:
                        self.output("No matching applications.")
                    else:
                        for line in _format_application_list(rows, include_applicant=True,
                                                             title="NEW LOAN APPLICATIONS"):
                            self.output(line)
                    continue
                if choice in {"2", "3", "4"}:
                    app_id = self._number("Application ID: ", integer=True, minimum=1)
                    if choice == "2":
                        row = self.service.rm_application(principal, app_id)
                        if not row:
                            self.output("Application not found or assigned to another manager.")
                        else:
                            self._show_application(row)
                            for request in row.get("info_requests", []):
                                self.output(f"Request {request['request_id']} [{request['request_status']}]: {request['request_text']} | Response: {request['applicant_response'] or 'Pending'}")
                    elif choice == "3":
                        details = self.service.rm_application(principal, app_id)
                        if self.service.validate_application(principal, app_id):
                            manager_name = (principal.get("full_name") if isinstance(principal, dict)
                                            else principal.full_name)
                            self._success_panel(
                                "APPLICATION VALIDATION COMPLETED",
                                "Application successfully validated!",
                                [("", ("Field", "Details"), [
                                    ("Application ID", app_id),
                                    ("Business ID", details.get("business_id") if details else None),
                                    ("Company Name", details.get("business_name") if details else None),
                                    ("Relationship Manager", manager_name),
                                    ("Validation Status", "RM_VALIDATED"),
                                ])],
                                footer="The application is ready for the next processing stage.",
                            )
                        else:
                            self.output("[WARNING] Application is unavailable or not awaiting verification.")
                    else:
                        request_text = self._text("Additional information required and remarks: ")
                        request_id = self.service.request_information(principal, app_id, request_text)
                        self.output(f"[SUCCESS] Information request {request_id} sent." if request_id
                                    else "[WARNING] Application is unavailable or not eligible.")
                    continue
                self.output("Choose 1, 2, 3, 4, or 5.")
            except (ValueError, PermissionError) as exc:
                self.output(f"[ERROR] {exc}")
            except Exception:
                self.output("[ERROR] Action could not be completed. Check the database and try again.")

    def _officer_dashboard(self, principal) -> None:
        while True:
            self.output("\nLoan Officer Dashboard\n1. View RM-Validated Applications\n2. View Application Details\n3. Run Risk Assessment\n4. View Prediction Results\n5. Approve or Reject Loan Application\n6. View Previously Processed Applications\n0. Logout")
            choice = self.input("Select an option: ").strip()
            try:
                if choice == "0":
                    self.output("Logged out.")
                    return
                if choice == "1":
                    rows = self.service.officer_applications(principal)
                    if not rows:
                        self.output("No RM-validated applications are available.")
                    else:
                        for line in _format_application_list(rows, include_applicant=True,
                                                             title="RM-VALIDATED LOAN APPLICATIONS"):
                            self.output(line)
                    continue
                if choice == "6":
                    rows = self.service.processed_applications(principal)
                    if not rows:
                        self.output("No processed applications.")
                    for row in rows:
                        self.output(f"Application {row['loan_application_id']} | Company / Organization: {row['business_name']} | {row['application_status']} | {row['decision_remarks']}")
                    continue
                if choice in {"2", "3", "4", "5"}:
                    app_id = self._number("Application ID: ", integer=True, minimum=1)
                    if choice == "2":
                        row = self.service.officer_application(principal, app_id)
                        self._show_application(row) if row else self.output("Application not found or not RM-validated.")
                    elif choice == "3":
                        row = self.service.officer_application(principal, app_id)
                        if not row:
                            self.output("Application not found or not RM-validated.")
                            continue
                        prediction = self.service.assess_risk(principal, app_id)
                        self._success_panel(
                            "SME HYBRID MODEL RISK ASSESSMENT",
                            "Risk assessment completed successfully!",
                            [
                                ("ASSESSMENT INFORMATION", ("Assessment Information", "Result"), [
                                    ("Application ID", row.get("loan_application_id", app_id)),
                                    ("Business ID", row.get("business_id")),
                                    ("Company Name", row.get("business_name")),
                                    ("Model Name", prediction.prediction_method),
                                    ("Predicted Risk Class", prediction.predicted_class_label),
                                    ("Default Risk Score", f"{prediction.risk_score:.2f}%"),
                                    ("Assessment Status", "COMPLETED"),
                                ]),
                            ],
                            footer=("NOTE: This result is based on a synthetic-data-trained model. It is a model-generated "
                                    "decision-support indicator, not a real-world validated banking decision or loan approval."),
                        )
                    elif choice == "4":
                        row = self.service.latest_prediction(principal, app_id)
                        self.output(str(row) if row else "No prediction has been recorded.")
                    else:
                        decision = self._select("Final decision:", ("APPROVED", "REJECTED"))
                        remarks = self._text("Decision remarks: ")
                        self.output("[SUCCESS] Final decision saved." if self.service.decide_application(principal, app_id, decision, remarks)
                                    else "[WARNING] Run an assessment first; application is unavailable or already processed.")
                    continue
                self.output("Choose 1, 2, 3, 4, 5, 6, or 0.")
            except (ValueError, PermissionError) as exc:
                self.output(f"[ERROR] {exc}")
            except Exception:
                self.output("[ERROR] Action could not be completed. Check the database and try again.")

    def run(self) -> None:
        while True:
            self.output("\n" + "=" * 60)
            self.output("1. SME Applicant\n2. Relationship Manager\n3. Loan Officer\n4. Exit")
            choice = self.input("Select a role: ").strip()
            try:
                if choice == "4":
                    self.output("Goodbye.")
                    return
                if choice == "1":
                    self._applicant_entry()
                elif choice in {"2", "3"}:
                    role = "RELATIONSHIP_MANAGER" if choice == "2" else "LOAN_OFFICER"
                    principal = self._login(role)
                    if principal:
                        (self._rm_dashboard if choice == "2" else self._officer_dashboard)(principal)
                else:
                    self.output("Choose 1, 2, 3, or 4.")
            except (EOFError, KeyboardInterrupt):
                self.output("\nApplication closed safely.")
                return
