import pytest

from backend.app.services.validation_service import (
    parse_number, required_text, validate_choice, validate_company_name, validate_password,
    validate_personal_name, validate_strong_password, validate_alpha_text, validate_numeric_value,
)


def test_required_text_strips_and_rejects_blank_values() -> None:
    assert required_text("  SME  ", "business_id") == "SME"
    with pytest.raises(ValueError, match="required"):
        required_text("  ", "business_id")


def test_number_parser_rejects_invalid_and_non_finite_values() -> None:
    with pytest.raises(ValueError, match="whole number"):
        parse_number("1.5", "employee_count", integer=True)
    with pytest.raises(ValueError, match="finite"):
        parse_number("nan", "annual_revenue")


def test_business_text_and_numeric_validators_normalize_and_enforce_bounds():
    assert validate_alpha_text("  New Delhi  ", "City") == "New Delhi"
    assert validate_numeric_value(100, "Business Age Years", minimum=0, maximum=100,
                                  minimum_exclusive=True) == 100
    assert validate_numeric_value(0, "Previous Year Revenue", minimum=0) == 0
    with pytest.raises(ValueError, match="letters and spaces"):
        validate_alpha_text("New-Delhi", "City")
    with pytest.raises(ValueError, match="greater than zero"):
        validate_numeric_value(0, "Annual Revenue", minimum=0, minimum_exclusive=True)
    with pytest.raises(ValueError, match="at most 100"):
        validate_numeric_value(101, "Business Age Years", maximum=100)
    with pytest.raises(ValueError, match="finite"):
        validate_numeric_value(float("inf"), "Annual Revenue")


def test_choice_validation_uses_observed_dataset_categories() -> None:
    choices = ("Stable", "Moderate", "Unstable")
    assert validate_choice("Stable", "cash_flow_stability", choices) == "Stable"
    with pytest.raises(ValueError, match="must be one of"):
        validate_choice("Unknown", "cash_flow_stability", choices)


@pytest.mark.parametrize("name", ["Rahul Kumar", "Bhabani Biswal", "Amit", "  Amit  "])
def test_personal_name_validation_accepts_and_normalizes_names(name: str) -> None:
    assert validate_personal_name(name) == name.strip()


@pytest.mark.parametrize("name", ["", "   ", "R", "Rahul123", "Rahul@Kumar", "@Rahul", "A" * 51])
def test_personal_name_validation_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValueError):
        validate_personal_name(name)


@pytest.mark.parametrize("name", ["Infosys", "Wipro Technologies", "Tata Consultancy Services", "  Wipro  "])
def test_company_name_validation_accepts_and_normalizes_names(name: str) -> None:
    assert validate_company_name(name) == name.strip()


@pytest.mark.parametrize("name", ["", "   ", "A", "Wipro123", "Wipro@", "ABC Ltd123", "12345", "@Company", "A" * 51])
def test_company_name_validation_rejects_invalid_values(name: str) -> None:
    with pytest.raises(ValueError):
        validate_company_name(name)


@pytest.mark.parametrize("password", ["Test@123", "Rahul@123", "Loan#2026"])
def test_password_validation_accepts_policy_compliant_values(password: str) -> None:
    assert validate_password(password) == password


@pytest.mark.parametrize("password,reason", [
    ("", "empty"), ("rahul@123", "uppercase"), ("RAHUL@123", "lowercase"),
    ("Rahulabcd", "number"), ("Rahul1234", "special"), ("Rah@123", "8 characters"),
    ("RahulPassword@123", "12 characters"), ("Rahul Ku@1", "spaces"),
])
def test_password_validation_reports_specific_failures(password: str, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        validate_password(password)


@pytest.mark.parametrize("password,message", [
    ("", "Password cannot be empty."),
    ("888", "Password must be at least 8 characters long."),
    ("LongPassword123!", "Password must not exceed 12 characters."),
    ("Test pass1!", "Password must not contain spaces."),
    ("test1234", "Password must contain at least one uppercase letter."),
    ("TEST@123", "Password must contain at least one lowercase letter."),
    ("Test@abc", "Password must contain at least one number."),
    ("Test1234", "Password must contain at least one special character."),
])
def test_strong_password_reports_first_failed_rule(password: str, message: str) -> None:
    with pytest.raises(ValueError) as error:
        validate_strong_password(password)
    assert str(error.value) == message
