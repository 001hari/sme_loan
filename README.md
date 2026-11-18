SME Loan Default Risk Prediction System

An end-to-end application for managing SME loan applications and predicting potential loan default risk using machine learning.

Overview

The system allows users to submit SME loan applications, store applicant and financial information, and generate risk predictions.

Project Status: Development / Prototype

Technology Stack

Component| Technology
Frontend| Streamlit
Backend| FastAPI
Database| PostgreSQL
ORM| SQLAlchemy
Machine Learning| Python
API Communication| REST API

Architecture

flowchart TD
    A[Streamlit Frontend] <-->|HTTP / JSON| B[FastAPI Backend]
    B <-->|SQLAlchemy| C[(PostgreSQL)]
    B -->|Python Function Call| D[ML Module]
    D --> E[Risk Prediction]
    E --> B
    B --> A

Project Structure

sme-loan-system/
├── frontend/       # Streamlit application
├── backend/        # FastAPI and business logic
├── database/       # SQLAlchemy models and connection
├── ml/             # ML training and inference
├── docs/           # Project documentation
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md

Prerequisites

- Python 3.11+
- PostgreSQL
- Git

Setup and Installation

1. Clone the repository

git clone YOUR_REPOSITORY_URL
cd sme-loan-system

2. Create and activate a virtual environment

Windows:

python -m venv .venv
.venv\Scripts\Activate.ps1

macOS/Linux:

python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Create a PostgreSQL database

Create a database named "sme_loan".

5. Configure environment variables

Copy ".env.example" to ".env" and update the database connection:

DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/sme_loan

Never commit ".env" or database credentials.

Running the Application

Run the backend and frontend in separate terminals from the project root.

Terminal 1 — Backend

python -m uvicorn backend.main:app --reload

API: http://127.0.0.1:8000

API Documentation: http://127.0.0.1:8000/docs

Terminal 2 — Frontend

python -m streamlit run frontend/app.py

Application: http://localhost:8501

Application Flow

1. User submits a loan application through Streamlit.
2. FastAPI validates and processes the request.
3. SQLAlchemy stores application data in PostgreSQL.
4. FastAPI calls the ML inference module.
5. The prediction is stored in PostgreSQL.
6. The result is displayed in Streamlit.

Development Status

Implemented

- Streamlit frontend
- FastAPI backend
- PostgreSQL integration
- Application submission and retrieval
- Mock ML inference and prediction storage

Upcoming

- Trained ML model integration
- Complete loan review and decision workflow
- Authentication and role-based access
- Additional testing and validation

Important Notes

- Current predictions are generated using a mock implementation, not a trained model.
- Do not use mock predictions for real lending decisions.
- Document uploads are outside the current prototype scope.
- Office database access requires approved network connectivity and credentials.

Disclaimer

This project is a development prototype and is not intended for production lending decisions.

==

plese refer to docs section for more detail