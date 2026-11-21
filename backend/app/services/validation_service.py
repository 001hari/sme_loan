"""Small reusable validators for console input and business entities."""

from math import isfinite
import re


_PERSONAL_NAME_PATTERN = re.compile(r"^[A-Za-z ]+$")
_COMPANY_NAME_PATTERN = re.compile(r"^[A-Za-z ]+$")


def validate_company_name(value: str) -> str:
    """Validate the applicant's company label using the requested name policy."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Company / Organization Name is required.")
    name = value.strip()
    if not 2 <= len(name) <= 50:
        raise ValueError("Company / Organization Name must be between 2 and 50 characters.")
    if not _COMPANY_NAME_PATTERN.fullmatch(name):
        raise ValueError("Company / Organization Name may contain only English letters and spaces.")
    return name


def validate_alpha_text(value: str, field_name: str, *, maximum_length: int = 100) -> str:
    """Require non-empty English letters and spaces and return trimmed text."""
    cleaned = required_text(value, field_name)
    if len(cleaned) > maximum_length:
        raise ValueError(f"{field_name} must be {maximum_length} characters or fewer.")
    if not re.fullmatch(r"[A-Za-z ]+", cleaned):
        raise ValueError(f"{field_name} may contain only English letters and spaces.")
    return cleaned


def validate_numeric_value(value, field_name: str, *, minimum: float | None = None,
                           maximum: float | None = None, minimum_exclusive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric.")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number.") from exc
    if not isfinite(number):
        raise ValueError(f"{field_name} must be a finite number.")
    if minimum is not None and (number <= minimum if minimum_exclusive else number < minimum):
        if minimum_exclusive:
            if minimum == 0:
                raise ValueError(f"{field_name} must be greater than zero.")
            raise ValueError(f"{field_name} must be greater than {minimum:g}.")
        raise ValueError(f"{field_name} must be at least {minimum:g}.")
    if maximum is not None and number > maximum:
        raise ValueError(f"{field_name} must be at most {maximum:g}.")
    return number


def validate_integer_value(value, field_name: str, *, minimum: int | None = None,
                           maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be a whole number.")
    if minimum is not None and value < minimum:
        raise ValueError(f"{field_name} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field_name} must be at most {maximum}.")
    return value


def validate_personal_name(value: str) -> str:
    """Validate and normalize a person's name (not a company name)."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Full name is required.")
    name = value.strip()
    if not 2 <= len(name) <= 50:
        raise ValueError("Full name must be between 2 and 50 characters.")
    if not _PERSONAL_NAME_PATTERN.fullmatch(name):
        raise ValueError("Full name may contain only letters and spaces.")
    return name


def validate_strong_password(value: str) -> str:
    """Validate a registration password and report the first unmet rule."""
    if not isinstance(value, str) or not value:
        raise ValueError("Password cannot be empty.")
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if len(value) > 12:
        raise ValueError("Password must not exceed 12 characters.")
    if any(char.isspace() for char in value):
        raise ValueError("Password must not contain spaces.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"[0-9]", value):
        raise ValueError("Password must contain at least one number.")
    if not re.search(r"[^A-Za-z0-9\s]", value):
        raise ValueError("Password must contain at least one special character.")
    return value


def validate_password(value: str) -> str:
    """Backward-compatible name for the shared strong password validator."""
    return validate_strong_password(value)


def required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    return cleaned


def parse_number(value: str, field_name: str, *, integer: bool = False) -> int | float:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be entered as text containing a number.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    try:
        number = int(cleaned) if integer else float(cleaned)
    except ValueError as exc:
        raise ValueError(f"Enter a valid {'whole number' if integer else 'number'} for {field_name}.") from exc
    if isinstance(number, float) and not isfinite(number):
        raise ValueError(f"{field_name} must be finite.")
    return number


def validate_range(value: int | float, field_name: str, *, minimum: float | None = None, maximum: float | None = None) -> None:
    if minimum is not None and value < minimum:
        raise ValueError(f"{field_name} must be at least {minimum:g}.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field_name} must be at most {maximum:g}.")


def validate_choice(value: str, field_name: str, choices: tuple[str, ...]) -> str:
    cleaned = required_text(value, field_name)
    if cleaned not in choices:
        raise ValueError(f"{field_name} must be one of: {', '.join(choices)}.")
    return cleaned
