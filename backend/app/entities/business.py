"""A business identity from the SME dataset, without loan-specific values."""

from dataclasses import dataclass
from typing import ClassVar

from ._validation import require_non_blank
from backend.app.services.validation_service import validate_alpha_text, validate_company_name, validate_numeric_value


@dataclass
class Business:
    business_id: int | None
    business_name: str
    city: str
    state: str
    sector: str
    legal_status: str
    business_age_years: float | None = None
    employee_count: int | None = None

    VALID_SECTORS: ClassVar[tuple[str, ...]] = (
        "Manufacturing", "Retail", "Wholesale", "Information Technology",
        "Agriculture", "Food Processing", "Healthcare", "Construction",
        "Transportation", "Hospitality",
    )
    VALID_LEGAL_STATUSES: ClassVar[tuple[str, ...]] = (
        "Proprietorship", "Partnership", "LLP", "Private Limited",
    )

    def validate(self) -> None:
        if (self.business_id is not None and
                (isinstance(self.business_id, bool) or not isinstance(self.business_id, int) or self.business_id <= 0)):
            raise ValueError("business_id must be a positive integer.")
        validate_company_name(self.business_name)
        validate_alpha_text(self.city, "City")
        validate_alpha_text(self.state, "State")
        require_non_blank(self.sector, "sector")
        require_non_blank(self.legal_status, "legal_status")
        if self.sector not in self.VALID_SECTORS:
            raise ValueError("sector must match a category in the dataset.")
        if self.legal_status not in self.VALID_LEGAL_STATUSES:
            raise ValueError("legal_status must match a category in the dataset.")
        if self.business_age_years is not None:
            validate_numeric_value(self.business_age_years, "Business Age Years", minimum=0,
                                   maximum=100, minimum_exclusive=True)
        if self.employee_count is not None:
            if isinstance(self.employee_count, bool) or not isinstance(self.employee_count, int) or self.employee_count < 1:
                raise ValueError("employee_count must be a positive integer.")
