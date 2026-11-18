from uuid import UUID

from sqlalchemy.orm import Session

from backend.schemas.application import ApplicationCreate
from database.models import LoanApplication, LoanPrediction
from ml.inference import predict_default


def create_application(db: Session, payload: ApplicationCreate) -> LoanApplication:
    application = LoanApplication(**payload.model_dump(), status="SUBMITTED")
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def get_application(db: Session, application_id: UUID):
    return db.get(LoanApplication, application_id)


def list_applications(db: Session):
    return db.query(LoanApplication).order_by(LoanApplication.created_at.desc()).all()


def predict_application(db: Session, application: LoanApplication) -> LoanPrediction:
    features = {
        "annual_revenue": float(application.annual_revenue),
        "requested_loan_amount": float(application.requested_loan_amount),
        "existing_loan_amount": float(application.existing_loan_amount),
        "years_in_business": application.years_in_business,
        "credit_score": application.credit_score,
    }
    result = predict_default(features)

    prediction = LoanPrediction(
        application_id=application.id,
        default_probability=result["default_probability"],
        risk_category=result["risk_category"],
        model_version=result["model_version"],
        is_mock=result["is_mock"],
    )
    db.add(prediction)
    application.status = "RISK_ASSESSED"
    db.commit()
    db.refresh(prediction)
    return prediction
