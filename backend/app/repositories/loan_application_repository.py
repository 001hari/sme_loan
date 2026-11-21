"""Parameterized PostgreSQL access for businesses and loan applications."""

from dataclasses import fields

from backend.app.database.connection import DatabaseConnection
from backend.app.entities import Business, LoanApplication


class DuplicateBusinessIDError(ValueError):
    """Raised when an existing business ID is submitted with conflicting details."""


APPLICATION_FIELDS = tuple(
    field.name
    for field in fields(LoanApplication)
    if field.name not in {"loan_application_id", "risk_predicted_score", "approval_result"}
)
APPLICATION_INSERT_SQL = (
    "INSERT INTO loan_applications (business_id, "
    + ", ".join(APPLICATION_FIELDS)
    + ") VALUES ("
    + ", ".join(["%s"] * (len(APPLICATION_FIELDS) + 1))
    + ") RETURNING application_id AS loan_application_id"
)
APPLICATION_UPDATE_SQL = (
    "UPDATE loan_applications SET "
    + ", ".join(f"{field} = %s" for field in APPLICATION_FIELDS)
    + " WHERE application_id = %s RETURNING application_id AS loan_application_id"
)
APPLICATION_SELECT = """
    SELECT loan_applications.*, loan_applications.application_id AS loan_application_id,
           businesses.business_name, businesses.city,
           businesses.state, businesses.sector, businesses.legal_status
    FROM loan_applications
    JOIN businesses USING (business_id)
"""


class LoanApplicationRepository:
    def __init__(self, database: DatabaseConnection) -> None:
        self.database = database

    @staticmethod
    def _business_values(business: Business) -> tuple[str, ...]:
        return (
            business.business_name.strip(),
            business.city.strip(),
            business.state.strip(),
            business.sector.strip(),
            business.legal_status.strip(),
        )

    @staticmethod
    def _application_values(application: LoanApplication) -> tuple[object, ...]:
        values = tuple(getattr(application, name) for name in APPLICATION_FIELDS)
        late_payment_index = APPLICATION_FIELDS.index("late_payment_history")
        values = list(values)
        values[late_payment_index] = bool(values[late_payment_index])
        return tuple(values)

    def create_application(self, business: Business, application: LoanApplication) -> dict:
        business.validate()
        application.validate()
        with self.database.connection() as conn:
            existing = conn.execute(
                """SELECT business_name, city, state, sector, legal_status
                   FROM businesses WHERE business_id = %s""",
                (business.business_id,),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """INSERT INTO businesses
                       (business_id, business_name, city, state, sector, legal_status)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (business.business_id, *self._business_values(business)),
                )
            elif tuple(existing[key] for key in ("business_name", "city", "state", "sector", "legal_status")) != self._business_values(business):
                raise DuplicateBusinessIDError(
                    "This Business ID already exists with different business details. "
                    "Use the existing details or correct the Business ID."
                )

            inserted = conn.execute(
                APPLICATION_INSERT_SQL,
                (business.business_id, *self._application_values(application)),
            ).fetchone()
            application_id = inserted["loan_application_id"]
            saved = conn.execute(
                APPLICATION_SELECT + " WHERE application_id = %s",
                (application_id,),
            ).fetchone()
            return dict(saved)

    def get_all_applications(self, limit: int = 100) -> list[dict]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer.")
        with self.database.connection() as conn:
            rows = conn.execute(
                APPLICATION_SELECT + " ORDER BY created_at DESC, application_id DESC LIMIT %s",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_application_by_id(self, application_id: int) -> dict | None:
        if isinstance(application_id, bool) or not isinstance(application_id, int) or application_id < 1:
            raise ValueError("application_id must be a positive integer.")
        with self.database.connection() as conn:
            row = conn.execute(
                APPLICATION_SELECT + " WHERE application_id = %s",
                (application_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def get_applications_by_business_id(self, business_id: int) -> list[dict]:
        if isinstance(business_id, bool) or not isinstance(business_id, int) or business_id < 1:
            raise ValueError("business_id is required.")
        with self.database.connection() as conn:
            rows = conn.execute(
                APPLICATION_SELECT
                + " WHERE business_id = %s ORDER BY created_at DESC, application_id DESC",
                (business_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def update_application(self, application_id: int, application: LoanApplication) -> dict | None:
        application.validate()
        with self.database.connection() as conn:
            updated = conn.execute(
                APPLICATION_UPDATE_SQL,
                (*self._application_values(application), application_id),
            ).fetchone()
            if updated is None:
                return None
            row = conn.execute(
                APPLICATION_SELECT + " WHERE application_id = %s",
                (application_id,),
            ).fetchone()
            return dict(row)

    def delete_application(self, application_id: int) -> bool:
        with self.database.connection() as conn:
            deleted = conn.execute(
                "DELETE FROM loan_applications WHERE application_id = %s RETURNING application_id",
                (application_id,),
            ).fetchone()
            return deleted is not None
