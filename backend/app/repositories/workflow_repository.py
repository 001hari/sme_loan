"""Parameterized DAO operations for the four-core-table role workflows."""

from dataclasses import fields

from backend.app.database.connection import DatabaseConnection
from backend.app.entities import Business, LoanApplication
from backend.app.services.auth_service import DuplicateCompanyNameError


class DuplicateEmailError(ValueError):
    pass


class DuplicateBusinessIDError(ValueError):
    pass


class WorkflowRepository:
    def __init__(self, database: DatabaseConnection) -> None:
        self.database = database

    def create_user(self, *, full_name: str, email: str, phone: str, password_hash: str, role: str) -> int:
        profile_table = {
            "SME_APPLICANT": "sme_applicants",
            "RELATIONSHIP_MANAGER": "relationship_managers",
            "LOAN_OFFICER": "loan_officers",
        }.get(role)
        if profile_table is None:
            raise ValueError("Unsupported role.")
        try:
            with self.database.connection() as conn:
                user_id = conn.execute(
                    """INSERT INTO users(full_name,email,password_hash,phone_number,role)
                       VALUES (%s,%s,%s,%s,%s) RETURNING user_id""",
                    (full_name, email, password_hash, phone, role),
                ).fetchone()["user_id"]
                # Retained profile tables remain populated for compatibility with prior FKs.
                conn.execute(f"INSERT INTO {profile_table}(user_id) VALUES (%s)", (user_id,))
                return user_id
        except Exception as exc:
            if getattr(exc, "sqlstate", None) == "23505":
                raise DuplicateEmailError("An account with this email already exists.") from exc
            raise

    def applicant_company_exists(self, company_name: str) -> bool:
        with self.database.connection() as conn:
            row = conn.execute(
                """SELECT EXISTS (SELECT 1 FROM users
                   WHERE role='SME_APPLICANT' AND company_name IS NOT NULL
                     AND lower(btrim(company_name))=lower(btrim(%s))) AS already_exists""",
                (company_name,),
            ).fetchone()
            return bool(row["already_exists"])

    def create_applicant_account(self, company_name: str, password_hash: str) -> int:
        try:
            with self.database.connection() as conn:
                user_id = conn.execute(
                    """INSERT INTO users(company_name,full_name,email,password_hash,phone_number,role)
                       VALUES (%s,%s,NULL,%s,NULL,'SME_APPLICANT') RETURNING user_id""",
                    (company_name, company_name, password_hash),
                ).fetchone()["user_id"]
                conn.execute("INSERT INTO sme_applicants(user_id) VALUES (%s)", (user_id,))
                return user_id
        except Exception as exc:
            if (getattr(exc, "sqlstate", None) == "23505"
                    and getattr(getattr(exc, "diag", None), "constraint_name", None) == "users_company_name_ci_key"):
                raise DuplicateCompanyNameError(
                    "This company is already registered. Please choose Login."
                ) from exc
            raise

    def get_applicant_by_company_name(self, company_name: str) -> dict | None:
        with self.database.connection() as conn:
            row = conn.execute(
                """SELECT user_id,company_name,password_hash,role,is_active
                   FROM users WHERE role='SME_APPLICANT'
                     AND lower(btrim(company_name))=lower(btrim(%s))""",
                (company_name,),
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> dict | None:
        with self.database.connection() as conn:
            row = conn.execute(
                """SELECT user_id, full_name, email, password_hash, phone_number, role, is_active
                   FROM users WHERE lower(email)=lower(%s)""",
                (email,),
            ).fetchone()
            return dict(row) if row else None

    def business_id_exists(self, business_id: int) -> bool:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT EXISTS (SELECT 1 FROM businesses WHERE business_id=%s) AS already_exists",
                (business_id,),
            ).fetchone()
            return bool(row["already_exists"])

    @staticmethod
    def _application_values(application: LoanApplication) -> tuple:
        excluded = {"loan_application_id", "risk_predicted_score", "approval_result"}
        values = []
        for field in fields(LoanApplication):
            if field.name in excluded:
                continue
            value = getattr(application, field.name)
            if field.name == "late_payment_history":
                value = bool(value)
            values.append(value)
        return tuple(values)

    def create_applicant_application(self, applicant_id: int, business: Business, application: LoanApplication) -> dict:
        business.validate()
        application.validate()
        try:
            with self.database.connection() as conn:
                business_row = conn.execute(
                    """INSERT INTO businesses(
                           applicant_id,applicant_user_id,business_name,city,state,sector,
                           legal_status,business_age_years,employee_count)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       RETURNING business_id""",
                    (applicant_id, applicant_id, business.business_name.strip(), business.city.strip(),
                     business.state.strip(), business.sector.strip(), business.legal_status.strip(),
                     business.business_age_years, business.employee_count),
                ).fetchone()
                if not business_row or business_row.get("business_id") is None:
                    raise RuntimeError("The database did not return the generated Business ID.")
                generated_business_id = int(business_row["business_id"])
                business.business_id = generated_business_id
                names = tuple(
                    field.name for field in fields(LoanApplication)
                    if field.name not in {"loan_application_id", "risk_predicted_score", "approval_result"}
                )
                columns = ", ".join(names)
                placeholders = ", ".join(["%s"] * len(names))
                row = conn.execute(
                    f"""INSERT INTO loan_applications(business_id,{columns},application_status)
                        VALUES (%s,{placeholders},'SUBMITTED')
                        RETURNING application_id AS loan_application_id,application_status,submitted_at""",
                    (generated_business_id, *self._application_values(application)),
                ).fetchone()
                result = dict(row)
                result["business_id"] = business.business_id
                return result
        except Exception as exc:
            if (getattr(exc, "sqlstate", None) == "23505"
                    and getattr(getattr(exc, "diag", None), "constraint_name", None) == "businesses_pkey"):
                raise DuplicateBusinessIDError("This Business ID already exists. Enter a different ID.") from exc
            raise

    @staticmethod
    def _application_select() -> str:
        return """SELECT la.*, la.application_id AS loan_application_id,
                         b.business_name,b.sector,b.legal_status,b.city,b.state,
                         b.business_age_years AS company_age_years,
                         b.employee_count AS company_employee_count,
                         b.applicant_user_id AS applicant_id,
                         COALESCE(u.company_name,u.full_name) AS applicant_name,u.email AS applicant_email
                  FROM loan_applications la JOIN businesses b USING (business_id)
                  LEFT JOIN users u ON u.user_id=b.applicant_user_id"""

    def get_applicant_applications(self, applicant_id: int) -> list[dict]:
        with self.database.connection() as conn:
            rows = conn.execute(
                self._application_select() + " WHERE b.applicant_user_id=%s ORDER BY la.submitted_at DESC,la.application_id DESC",
                (applicant_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_applicant_requests(self, applicant_id: int, *, open_only: bool = False) -> list[dict]:
        status_filter = " AND r.request_status='OPEN'" if open_only else ""
        with self.database.connection() as conn:
            rows = conn.execute(
                """SELECT r.*,la.application_status,b.business_name
                   FROM application_info_requests r
                   JOIN loan_applications la ON la.application_id=r.loan_application_id
                   JOIN businesses b USING (business_id)
                   WHERE b.applicant_user_id=%s""" + status_filter +
                " ORDER BY r.requested_at DESC,r.request_id DESC",
                (applicant_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def respond_to_request(self, applicant_id: int, request_id: int, response: str) -> bool:
        with self.database.connection() as conn:
            row = conn.execute(
                """UPDATE application_info_requests r
                   SET applicant_response=%s,request_status='RESPONDED',responded_at=CURRENT_TIMESTAMP
                   FROM loan_applications la,businesses b
                   WHERE r.request_id=%s AND r.request_status='OPEN'
                     AND la.application_id=r.loan_application_id AND b.business_id=la.business_id
                     AND b.applicant_user_id=%s RETURNING r.loan_application_id""",
                (response, request_id, applicant_id),
            ).fetchone()
            if not row:
                return False
            conn.execute(
                """UPDATE loan_applications SET application_status='SUBMITTED'
                   WHERE application_id=%s AND application_status='ADDITIONAL_INFO_REQUIRED'""",
                (row["loan_application_id"],),
            )
            return True

    def list_rm_applications(self, rm_id: int, *, assigned: bool = False) -> list[dict]:
        if assigned:
            condition = "la.relationship_manager_id=%s AND la.application_status IN ('SUBMITTED','ADDITIONAL_INFO_REQUIRED','RM_VALIDATED')"
            params = (rm_id,)
        else:
            condition = "la.application_status='SUBMITTED' AND (la.relationship_manager_id IS NULL OR la.relationship_manager_id=%s)"
            params = (rm_id,)
        with self.database.connection() as conn:
            rows = conn.execute(
                self._application_select() + " WHERE " + condition + " ORDER BY la.submitted_at,la.application_id",
                params,
            ).fetchall()
            return [dict(row) for row in rows]

    def get_rm_application(self, rm_id: int, application_id: int) -> dict | None:
        with self.database.connection() as conn:
            row = conn.execute(
                self._application_select() + " WHERE la.application_id=%s AND (la.relationship_manager_id IS NULL OR la.relationship_manager_id=%s)",
                (application_id, rm_id),
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            result["info_requests"] = [dict(item) for item in conn.execute(
                "SELECT * FROM application_info_requests WHERE loan_application_id=%s ORDER BY requested_at DESC,request_id DESC",
                (application_id,),
            ).fetchall()]
            return result

    def validate_application(self, rm_id: int, application_id: int) -> bool:
        with self.database.connection() as conn:
            row = conn.execute(
                """UPDATE loan_applications SET application_status='RM_VALIDATED',
                       rm_id=%s,relationship_manager_id=%s
                   WHERE application_id=%s AND application_status='SUBMITTED'
                     AND (relationship_manager_id IS NULL OR relationship_manager_id=%s)
                     AND EXISTS (SELECT 1 FROM users WHERE user_id=%s AND role='RELATIONSHIP_MANAGER')
                   RETURNING application_id""",
                (rm_id, rm_id, application_id, rm_id, rm_id),
            ).fetchone()
            return row is not None

    def request_information(self, rm_id: int, application_id: int, request_text: str) -> int | None:
        with self.database.connection() as conn:
            row = conn.execute(
                """UPDATE loan_applications SET application_status='ADDITIONAL_INFO_REQUIRED',
                       rm_id=%s,relationship_manager_id=%s
                   WHERE application_id=%s AND application_status IN ('SUBMITTED','RM_VALIDATED')
                     AND (relationship_manager_id IS NULL OR relationship_manager_id=%s)
                     AND EXISTS (SELECT 1 FROM users WHERE user_id=%s AND role='RELATIONSHIP_MANAGER')
                   RETURNING application_id""",
                (rm_id, rm_id, application_id, rm_id, rm_id),
            ).fetchone()
            if not row:
                return None
            request = conn.execute(
                """INSERT INTO application_info_requests(loan_application_id,requested_by,request_text)
                   VALUES (%s,%s,%s) RETURNING request_id""",
                (application_id, rm_id, request_text),
            ).fetchone()
            return request["request_id"]

    def list_officer_applications(self) -> list[dict]:
        with self.database.connection() as conn:
            rows = conn.execute(
                self._application_select() + " WHERE la.application_status IN ('RM_VALIDATED','RISK_ASSESSED') ORDER BY la.submitted_at,la.application_id"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_officer_application(self, application_id: int) -> dict | None:
        with self.database.connection() as conn:
            row = conn.execute(
                self._application_select() + " WHERE la.application_id=%s AND la.application_status IN ('RM_VALIDATED','RISK_ASSESSED')",
                (application_id,),
            ).fetchone()
            return dict(row) if row else None

    def save_prediction(self, officer_id: int, application_id: int, prediction) -> int | None:
        with self.database.connection() as conn:
            eligible = conn.execute(
                """UPDATE loan_applications SET application_status='RISK_ASSESSED',loan_officer_id=%s
                   WHERE application_id=%s AND application_status IN ('RM_VALIDATED','RISK_ASSESSED')
                     AND EXISTS (SELECT 1 FROM users WHERE user_id=%s AND role='LOAN_OFFICER')
                   RETURNING application_id""",
                (officer_id, application_id, officer_id),
            ).fetchone()
            if not eligible:
                return None
            row = conn.execute(
                """INSERT INTO predictions(application_id,loan_officer_id,model_name,model_version,
                       risk_score,risk_category,suggested_decision,prediction_confidence)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING prediction_id""",
                (application_id, officer_id, prediction.prediction_method,
                 getattr(prediction, "model_version", "sprint-1-demo"),
                 prediction.risk_score, prediction.risk_category, prediction.suggested_decision,
                 getattr(prediction, "prediction_confidence", None)),
            ).fetchone()
            return row["prediction_id"]

    def latest_prediction(self, application_id: int) -> dict | None:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM predictions WHERE application_id=%s ORDER BY predicted_at DESC,prediction_id DESC LIMIT 1",
                (application_id,),
            ).fetchone()
            return dict(row) if row else None

    def decide_application(self, officer_id: int, application_id: int, decision: str, remarks: str) -> bool:
        if decision not in {"APPROVED", "REJECTED"}:
            raise ValueError("Decision must be APPROVED or REJECTED.")
        with self.database.connection() as conn:
            row = conn.execute(
                """UPDATE loan_applications la SET application_status=%s,final_decision=%s,
                       decision_remarks=%s,loan_officer_id=%s,decided_at=CURRENT_TIMESTAMP
                   WHERE la.application_id=%s AND la.application_status='RISK_ASSESSED'
                     AND EXISTS (SELECT 1 FROM users WHERE user_id=%s AND role='LOAN_OFFICER')
                     AND EXISTS (SELECT 1 FROM predictions p WHERE p.application_id=la.application_id)
                   RETURNING la.application_id""",
                (decision, decision, remarks, officer_id, application_id, officer_id),
            ).fetchone()
            return row is not None

    def list_processed_applications(self, officer_id: int) -> list[dict]:
        with self.database.connection() as conn:
            rows = conn.execute(
                self._application_select() + " WHERE la.loan_officer_id=%s AND la.application_status IN ('APPROVED','REJECTED') ORDER BY la.decided_at DESC",
                (officer_id,),
            ).fetchall()
            return [dict(row) for row in rows]
