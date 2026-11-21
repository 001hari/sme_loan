"""Small validation helpers shared by domain entities."""

from math import isfinite


def require_non_blank(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank.")


def require_non_negative(value: int | float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric.")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{field_name} must be finite and non-negative.")


def require_probability(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric.")
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{field_name} must be between 0 and 1.")
