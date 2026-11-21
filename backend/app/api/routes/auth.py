# -*- coding: utf-8 -*-
"""Authentication routes for FastAPI.

Provides:
- Register SME applicant
- Register staff (Relationship Manager or Loan Officer)
- Staff login (email/password)
- Applicant login (company_name/password)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.schemas import (
    RegisterApplicantRequest,
    RegisterStaffRequest,
    LoginRequest,
    LoginResponse,
)
from backend.app.api.dependencies import create_access_token, get_workflow_service, WorkflowServiceDep

router = APIRouter()

@router.post("/register/applicant", response_model=dict)
def register_applicant(
    request: RegisterApplicantRequest,
    service: WorkflowServiceDep,

):
    try:
        user_id = service.register_applicant(
            request.company_name, request.password, request.confirmation
        )
        return {"user_id": user_id, "message": "Applicant registered successfully"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/register/staff", response_model=dict)
def register_staff(
    request: RegisterStaffRequest,
    service: WorkflowServiceDep,

):
    try:
        user_id = service.provision_staff(
            request.full_name,
            request.email,
            request.phone,
            request.password,
            request.confirmation,
            request.role,
        )
        return {"user_id": user_id, "message": f"{request.role} registered successfully"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/login/staff", response_model=LoginResponse)
def login_staff(
    form: LoginRequest,
    service: WorkflowServiceDep,

):
    if form.role not in {"RELATIONSHIP_MANAGER", "LOAN_OFFICER"}:
        raise HTTPException(status_code=400, detail="Invalid role for staff login")
    try:
        principal = service.authenticate(form.email, form.password, form.role)
        token = create_access_token(
            {
                "sub": str(principal.user_id),
                "role": principal.role,
                "full_name": principal.full_name,
                "email": principal.email,
            }
        )
        return LoginResponse(access_token=token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))

class ApplicantLoginRequest(BaseModel):
    company_name: str
    password: str

@router.post("/login/applicant", response_model=LoginResponse)
def login_applicant(
    request: ApplicantLoginRequest,
    service: WorkflowServiceDep,

):
    try:
        principal = service.authenticate_applicant(request.company_name, request.password)
        token = create_access_token(
            {"sub": str(principal.user_id), "role": principal.role, "full_name": principal.full_name}
        )
        return LoginResponse(access_token=token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))
