"""Applicant related FastAPI routes.

Endpoints:
- POST /submit – create a new loan application
- GET /applications – list my applications
- GET /applications/{app_id} – get details
- GET /applications/{app_id}/requests – list info requests
- POST /applications/{app_id}/respond – respond to a request
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from backend.app.api.schemas import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationDetailResponse,
    InfoRequestResponse,
    RespondInfoRequest,
)
from backend.app.api.dependencies import WorkflowServiceDep, CurrentPrincipal

router = APIRouter()


@router.post("/submit", response_model=ApplicationResponse)
def submit_application(
    request: ApplicationCreateRequest,
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    # Convert request to Business and LoanApplication entities (simplified)
    # Assuming Business and LoanApplication constructors accept dicts matching fields.
    from backend.app.entities import Business, LoanApplication

    business = Business(**request.business.dict())
    loan_app = LoanApplication(
        loan_amount=request.loan_amount,
        loan_term_months=request.loan_term_months,
        purpose=request.purpose,
    )
    try:
        result = service.submit_application(principal, business, loan_app)
        return ApplicationResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/applications", response_model=List[ApplicationResponse])
def list_my_applications(
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    try:
        apps = service.applicant_applications(principal)
        return [ApplicationResponse(**app) for app in apps]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/applications/{app_id}", response_model=ApplicationDetailResponse)
def get_application_detail(
    app_id: int,
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    apps = service.applicant_applications(principal)
    for app in apps:
        if app["application_id"] == app_id:
            return ApplicationDetailResponse(**app)
    raise HTTPException(status_code=404, detail="Application not found")


@router.get("/applications/{app_id}/requests", response_model=List[InfoRequestResponse])
def list_info_requests(
    app_id: int,
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    # Filter requests belonging to this application
    all_requests = service.applicant_requests(principal, open_only=False)
    filtered = [r for r in all_requests if r["application_id"] == app_id]
    return [InfoRequestResponse(**r) for r in filtered]


@router.post("/applications/{app_id}/respond", response_model=dict)
def respond_to_request(
    app_id: int,
    request_id: int,
    payload: RespondInfoRequest,
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    # Ensure the request belongs to the given application (simple check)
    requests = service.applicant_requests(principal, open_only=False)
    if not any(r["request_id"] == request_id and r["application_id"] == app_id for r in requests):
        raise HTTPException(status_code=404, detail="Request not found for this application")
    success = service.respond_to_request(principal, request_id, payload.response)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to submit response")
    return {"status": "response recorded"}
