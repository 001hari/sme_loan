from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    PredictionRead,
)
from backend.services.application_service import (
    create_application,
    get_application,
    list_applications,
    predict_application,
)

router = APIRouter(tags=["Applications"])


@router.post(
    "/applications",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    return create_application(db, payload)


@router.get("/applications", response_model=list[ApplicationRead])
def get_applications(db: Session = Depends(get_db)):
    return list_applications(db)


@router.get("/applications/{application_id}", response_model=ApplicationRead)
def get_application_by_id(application_id: UUID, db: Session = Depends(get_db)):
    application = get_application(db, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post(
    "/applications/{application_id}/predict",
    response_model=PredictionRead,
)
def run_prediction(application_id: UUID, db: Session = Depends(get_db)):
    application = get_application(db, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return predict_application(db, application)
