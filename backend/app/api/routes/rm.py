"""Relationship Manager (RM) FastAPI routes.

Endpoints:
- GET /assigned – list applications assigned to the RM
- GET /applications/{app_id} – get details of a specific application
- POST /applications/{app_id}/validate – validate the application (returns success flag)
- POST /applications/{app_id}/request-info – request additional information from the applicant
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from backend.app.api.schemas import (
    ApplicationDetailResponse,
    ValidateApplicationResponse,
    RequestAdditionalInfo,
)
from backend.app.api.dependencies import CurrentPrincipal, WorkflowServiceDep, get_workflow_service

router = APIRouter()


@router.get("/assigned", response_model=List[ApplicationDetailResponse])
def list_assigned_applications(
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    # RM sees only assigned applications; the repository handles assignment logic.
    apps = service.rm_applications(principal, assigned=True)
    return [ApplicationDetailResponse(**app) for app in apps]


@router.get("/applications/{app_id}", response_model=ApplicationDetailResponse)
def get_application_detail(
    app_id: int,
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    app = service.rm_application(principal, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationDetailResponse(**app)


@router.post("/applications/{app_id}/validate", response_model=ValidateApplicationResponse)
def validate_application(
    app_id: int,
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    success = service.validate_application(principal, app_id)
    return ValidateApplicationResponse(success=success, message="Validated" if success else "Validation failed")


@router.post("/applications/{app_id}/request-info", response_model=dict)
def request_additional_info(
    app_id: int,
    payload: RequestAdditionalInfo,
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    request_id = service.request_information(principal, app_id, payload.request_text)
    if request_id is None:
        raise HTTPException(status_code=400, detail="Unable to create request")
    return {"request_id": request_id, "message": "Information request created"}
