"""Password hashing and role-aware authentication services."""

import base64
import hashlib
import hmac
import re
import secrets

from backend.app.services.validation_service import validate_company_name, validate_password, validate_personal_name


ITERATIONS = 600_000
PASSWORD_PATTERN = re.compile(r"^.{8,256}$", re.DOTALL)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 .()\-]{6,30}$")
ROLES = {"SME_APPLICANT", "RELATIONSHIP_MANAGER", "LOAN_OFFICER"}


class AuthenticationError(ValueError):
    """Authentication failed without disclosing account details."""


class AuthorizationError(PermissionError):
    """The current user is not allowed to perform an operation."""


class DuplicateEmailError(ValueError):
    """An account already uses the submitted email address."""


class DuplicateCompanyNameError(ValueError):
    """An SME applicant account already uses the submitted company name."""


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if not isinstance(password, str) or not PASSWORD_PATTERN.fullmatch(password):
        raise ValueError("Password must contain between 8 and 256 characters.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return "$".join(("pbkdf2_sha256", str(ITERATIONS), base64.b64encode(salt).decode(), base64.b64encode(digest).decode()))


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt_b64, digest_b64 = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64, validate=True)
        expected = base64.b64decode(digest_b64, validate=True)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def validate_registration(full_name: str, email: str, phone: str, password: str, confirmation: str) -> tuple[str, str, str]:
    name = validate_personal_name(full_name)
    email, phone = email.strip().lower(), phone.strip()
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Enter a valid email address.")
    digits = sum(char.isdigit() for char in phone)
    if not PHONE_PATTERN.fullmatch(phone) or not 8 <= digits <= 15:
        raise ValueError("Enter a valid phone number with 8 to 15 digits.")
    validate_password(password)
    if password != confirmation:
        raise ValueError("Passwords do not match. Please enter the confirmation password again.")
    hash_password(password)
    return name, email, phone


def validate_company_registration(company_name: str, password: str, confirmation: str) -> str:
    name = validate_company_name(company_name)
    validate_password(password)
    if password != confirmation:
        raise ValueError("Passwords do not match. Please enter the confirmation password again.")
    return name


def require_role(principal: dict, expected: str) -> None:
    if principal.get("role") != expected:
        raise AuthorizationError(f"This action requires the {expected} role.")
