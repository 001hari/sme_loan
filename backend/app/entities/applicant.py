"""Applicant identity and contact details."""

from dataclasses import dataclass

from ._validation import require_non_blank


@dataclass
class Applicant:
    applicant_id: int | None
    full_name: str
    email: str
    phone: str | None = None
    user_id: int | None = None

    def validate(self) -> None:
        require_non_blank(self.full_name, "full_name")
        require_non_blank(self.email, "email")
        if "@" not in self.email:
            raise ValueError("email must be a valid email address.")
