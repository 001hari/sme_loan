# -*- coding: utf-8 -*-
"""FastAPI application entry point.

Provides:
- CORS configuration (allowed origins read from environment).
- Inclusion of versioned routers.
- Centralized exception handling for AuthenticationError, AuthorizationError and generic errors.
"""

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes import auth, applicant, rm, officer
from backend.app.services.auth_service import AuthenticationError, AuthorizationError

app = FastAPI(
    title="SME Loan Risk Prediction API",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS – allowed origins can be configured via .env (FRONTEND_ORIGIN) or default to localhost for dev
allowed_origins = os.getenv("FRONTEND_ORIGIN", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers under /api/v1
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(applicant.router, prefix="/api/v1/applicant", tags=["applicant"])
app.include_router(rm.router, prefix="/api/v1/rm", tags=["relationship_manager"])
app.include_router(officer.router, prefix="/api/v1/officer", tags=["loan_officer"])

# Global exception handlers
@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})

@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    # Log the exception details (FastAPI will also log)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Root and health endpoints (no authentication required)
@app.get("/", tags=["root"])
def root() -> dict:
    """Root endpoint returning basic API info."""
    return {
        "message": "SME Loan Risk Prediction API is running successfully",
        "status": "healthy",
        "documentation": "/docs",
        "openapi": "/openapi.json",
        "version": "1.0.0",
    }

@app.get("/health", tags=["health"])
def health() -> dict:
    """Simple health check endpoint."""
    return {"status": "healthy"}

