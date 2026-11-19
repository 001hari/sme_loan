from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.auth_routes import router as auth_router
from backend.api.routes import router
from backend.config import settings
from backend.services.auth_service import seed_admin_user
from database import models
from database.base import Base
from database.session import SessionLocal, engine

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Development API for the SME loan risk prediction prototype.",
)


@app.on_event("startup")
def startup_tasks():
    # 1. Create tables if they do not exist
    Base.metadata.create_all(bind=engine)

    # 2. Automatically seed admin user
    db = SessionLocal()
    try:
        admin = seed_admin_user(db)
        if admin:
            print(f"[SEEDER] Default admin created successfully: {admin.email}")
        else:
            print("[SEEDER] Admin user already exists. Skipping seed.")
    finally:
        db.close()


# Restrict origins before deployment. This permissive setting is for local development only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(router, prefix=settings.api_v1_prefix)


@app.get("/")
def root():
    return {"message": "SME Loan Risk API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
