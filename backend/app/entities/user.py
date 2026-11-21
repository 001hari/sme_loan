"""Persisted identity for one of the three supported application roles."""

from dataclasses import dataclass

from ._validation import require_non_blank


@dataclass
class User:
    full_name: str
    email: str
    password_hash: str
    phone_number: str
    role: str
    user_id: int | None = None
    is_active: bool = True

    def validate(self) -> None:
        require_non_blank(self.full_name, "full_name")
        require_non_blank(self.email, "email")
        require_non_blank(self.password_hash, "password_hash")
        require_non_blank(self.phone_number, "phone_number")
        if "@" not in self.email or self.email.startswith("@") or self.email.endswith("@"):
            raise ValueError("email must be a valid email address.")
        if self.role not in {"SME_APPLICANT", "RELATIONSHIP_MANAGER", "LOAN_OFFICER"}:
            raise ValueError("role must be one of the supported application roles.")
        if self.user_id is not None and (
            isinstance(self.user_id, bool) or not isinstance(self.user_id, int) or self.user_id < 1
        ):
            raise ValueError("user_id must be a positive integer or None.")
        if not isinstance(self.is_active, bool):
            raise ValueError("is_active must be a boolean.")
