"""Pydantic models for API request and response payloads.

Separate modules are kept for clarity; they are imported by the route
implementations.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, PositiveInt, conint, validator

# ------------------------------ Auth -----------------------------------
class RegisterApplicantRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=8)
    confirmation: str = Field(..., min_length=8)

class RegisterStaffRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    email: str
    phone: str = Field(..., min_length=8, max_length=30)
    password: str = Field(..., min_length=8)
    confirmation: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(RELATIONSHIP_MANAGER|LOAN_OFFICER)$")

class LoginRequest(BaseModel):
    email: str
    password: str
    role: str = Field(..., pattern="^(SME_APPLICANT|RELATIONSHIP_MANAGER|LOAN_OFFICER)$")

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# -------------------------- Applicant ---------------------------------
class BusinessInfo(BaseModel):
    sector: str
    annual_revenue: conint(gt=0)
    employee_count: conint(gt=0)
    business_age_years: conint(gt=0)
    # add any other required fields – keep generic for now

class ApplicationCreateRequest(BaseModel):
    business: BusinessInfo
    loan_amount: conint(gt=0)
    loan_term_months: conint(gt=0)
    purpose: str = Field(..., min_length=1, max_length=500)

class ApplicationResponse(BaseModel):
    application_id: int
    status: str
    created_at: str
    business_id: int
    loan_amount: int
    loan_term_months: int
    purpose: str

class ApplicationDetailResponse(ApplicationResponse):
    business: dict
    # additional fields if needed

class InfoRequestResponse(BaseModel):
    request_id: int
    application_id: int
    text: str
    status: str
    created_at: str

class RespondInfoRequest(BaseModel):
    response: str = Field(..., min_length=1, max_length=1000)

# ------------------------- Relationship Manager ------------------------
class ValidateApplicationResponse(BaseModel):
    success: bool
    message: Optional[str] = None

class RequestAdditionalInfo(BaseModel):
    request_text: str = Field(..., min_length=1, max_length=1000)

# ---------------------------- Officer --------------------------------
class RiskPredictionResult(BaseModel):
    predicted_class: int
    probability_default: float
    probability_non_default: float
    risk_score: float = Field(..., ge=0.0, le=1.0)
    # risk_score can be a derived metric (e.g., probability_default)

class AssessmentResponse(BaseModel):
    prediction: RiskPredictionResult
    message: Optional[str] = None

# ---------------------------- Enums -----------------------------------
class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
