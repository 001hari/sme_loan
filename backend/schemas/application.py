from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApplicationCreate(BaseModel):
    applicant_name: str = Field(min_length=2, max_length=120)
    business_name: str = Field(min_length=2, max_length=160)
    annual_revenue: Decimal = Field(gt=0)
    requested_loan_amount: Decimal = Field(gt=0)
    existing_loan_amount: Decimal = Field(ge=0)
    years_in_business: int = Field(ge=0, le=150)
    credit_score: int = Field(ge=300, le=900)


class ApplicationRead(BaseModel):
    id: UUID
    applicant_name: str
    business_name: str
    annual_revenue: Decimal
    requested_loan_amount: Decimal
    existing_loan_amount: Decimal
    years_in_business: int
    credit_score: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictionRead(BaseModel):
    id: UUID
    application_id: UUID
    default_probability: float
    risk_category: str
    model_version: str
    is_mock: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
