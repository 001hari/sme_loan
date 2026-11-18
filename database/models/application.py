import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Float, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    applicant_name: Mapped[str] = mapped_column(String(120), nullable=False)
    business_name: Mapped[str] = mapped_column(String(160), nullable=False)
    annual_revenue: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    requested_loan_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    existing_loan_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    years_in_business: Mapped[int] = mapped_column(Integer, nullable=False)
    credit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="SUBMITTED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    predictions: Mapped[list["LoanPrediction"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class LoanPrediction(Base):
    __tablename__ = "loan_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False
    )
    default_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_category: Mapped[str] = mapped_column(String(30), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped[LoanApplication] = relationship(back_populates="predictions")
