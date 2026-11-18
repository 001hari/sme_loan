from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.api.routes import router

from database.base import Base
from database.session import engine
from database import models


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Development API for the SME loan risk prediction prototype.",
)

@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)

# Restrict origins before deployment. This permissive setting is for local development only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_v1_prefix)


@app.get("/")
def root():
    return {"message": "SME Loan Risk API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
