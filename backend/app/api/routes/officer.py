# -*- coding: utf-8 -*-
"""Loan Officer API routes.

Provides endpoints for Loan Officers to view eligible applications, retrieve
application details, perform risk assessment using the existing SME Hybrid
model, and view saved predictions.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from backend.app.api.schemas import (
    ApplicationDetailResponse,
    RiskPredictionResult,
    AssessmentResponse,
)
from backend.app.api.dependencies import CurrentPrincipal, WorkflowServiceDep

router = APIRouter()

# ---------------------------------------------------------------------
# Helper to enforce that the principal is a Loan Officer. Service methods
# already perform role checks, but we raise a clear HTTP 403 if the role is
# not LOAN_OFFICER for extra safety.
# ---------------------------------------------------------------------
def _ensure_officer(principal: dict) -> None:
    if principal.get("role") != "LOAN_OFFICER":
        raise HTTPException(status_code=403, detail="Loan Officer role required")

# ---------------------------------------------------------------------
# 1. List eligible applications for the officer.
# ---------------------------------------------------------------------
@router.get("/applications", response_model=List[ApplicationDetailResponse])
def list_officer_applications(
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    _ensure_officer(principal)
    apps = service.officer_applications(principal)
    return [ApplicationDetailResponse(**app) for app in apps]

# ---------------------------------------------------------------------
# 2. Retrieve a single application with full details.
# ---------------------------------------------------------------------
@router.get("/applications/{app_id}", response_model=ApplicationDetailResponse)
def get_officer_application(
    app_id: int,
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    _ensure_officer(principal)
    app = service.officer_application(principal, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationDetailResponse(**app)

# ---------------------------------------------------------------------
# 3. Perform risk assessment for a given application.
# ---------------------------------------------------------------------
@router.post(
    "/applications/{app_id}/assess-risk",
    response_model=AssessmentResponse,
)
def assess_risk(
    app_id: int,
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    _ensure_officer(principal)
    try:
        prediction = service.assess_risk(principal, app_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    # prediction is a dict returned by predict_sme_hybrid; we map it to the
    # RiskPredictionResult schema.
    risk = RiskPredictionResult(**prediction)
    return AssessmentResponse(prediction=risk)

# ---------------------------------------------------------------------
# 4. Retrieve the latest saved prediction for an application.
# ---------------------------------------------------------------------
@router.get(
    "/assessments/{app_id}", response_model=RiskPredictionResult
)
def get_latest_assessment(
    app_id: int,
    principal: CurrentPrincipal,
    service: WorkflowServiceDep,
):
    _ensure_officer(principal)
    pred = service.latest_prediction(principal, app_id)
    if not pred:
        raise HTTPException(status_code=404, detail="No assessment found for this application")
    return RiskPredictionResult(**pred)

