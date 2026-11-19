# SME Loan Default Risk Prediction System

An end-to-end application for managing SME loan applications and predicting potential loan default risk using machine learning.

---

## Overview

The system allows users to submit SME loan applications, store applicant and financial information, authenticate with role-based access, and generate default risk predictions.

**Project Status:** Development / Prototype

---

## Technology Stack

| Component | Technology |
|---|---|
| **Backend** | FastAPI, Python 3.11 |
| **Frontend** | Streamlit |
| **Database** | PostgreSQL |
| **ORM** | SQLAlchemy 2.0 |
| **Security & Auth** | bcrypt (password hashing), Python-Jose (JWT tokens) |
| **Machine Learning** | Python |
| **API Architecture** | REST API (FastAPI) |

---

## Architecture

```mermaid
flowchart TD
    A[Streamlit Frontend] <-->|HTTP / JSON| B[FastAPI Backend]
    B <-->|SQLAlchemy| C[(PostgreSQL)]
    B -->|Python Function Call| D[ML Module]
    D --> E[Risk Prediction]
    E --> B
    B --> A
```

---

## Project Structure

```
sme-loan-system/
├── backend/
│   ├── api/
│   │   ├── auth_routes.py      # Register, Login, Me endpoints
│   │   └── routes.py           # Application submission and retrieval
│   ├── schemas/
│   │   ├── application.py      # Pydantic schemas for loan applications
│   │   └── user.py             # Pydantic schemas for auth and users
│   ├── services/
│   │   ├── application_service.py # Loan application business logic
│   │   └── auth_service.py     # Auth logic, hashing & admin seeder
│   ├── config.py               # App configuration & JWT settings
│   ├── dependencies.py         # DB session & get_current_user JWT guard
│   ├── main.py                 # FastAPI app entry point & startup seeder
│   └── security.py             # bcrypt hashing & JWT token encode/decode
├── database/
│   ├── models/
│   │   ├── application.py      # LoanApplication & LoanPrediction tables
│   │   └── user.py             # User table (uid, role, password_hash)
│   ├── base.py                 # SQLAlchemy DeclarativeBase
│   └── session.py              # Engine & SessionLocal setup
├── frontend/                   # Streamlit application
├── ml/                         # ML training and inference
├── docs/                       # Project documentation
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Phase 1: Backend Foundation & Authentication (Completed)

In **Phase 1**, the core backend foundation and authentication infrastructure were established:

### 1. Python 3.11 & Environment Setup
- Isolated Python 3.11 virtual environment configured (`venv`).
- Added robust dependencies for FastAPI, SQLAlchemy, PostgreSQL (`psycopg`), bcrypt, and `python-jose`.

### 2. Database Schema & Models
- **`users` Table:**
  - `uid` (`Integer`, Primary Key, autoincrementing)
  - `full_name` (`String(120)`, not null)
  - `email` (`String(255)`, unique, indexed)
  - `password_hash` (`String(255)`, bcrypt)
  - `phone_number` (`String(25)`, optional)
  - `role` (`String(30)`: `admin`, `applicant`, `manager`, `officer`, `authority`)
  - `is_active` (`Boolean`, default `True`)
  - `company_name` (`String(160)`, optional)
  - `created_at` (`DateTime`, server default `now()`)
- **`loan_applications` Table:** Stores SME loan applicant & financial details.
- **`loan_predictions` Table:** Stores default probability and risk categories.

### 3. JWT Authentication & Security
- **Password Security:** Direct `bcrypt` hashing with salt generation.
- **JWT Tokens:** HS256 algorithm encoding `uid`, `role`, and `email` with configurable expiration.
- **Protected Route Guard:** Reusable `get_current_user` FastAPI dependency for role-based authorization.

### 4. Automatic Admin Seeder
- Runs automatically during application startup (`@app.on_event("startup")`).
- Detects if an `admin` exists in PostgreSQL; if not, automatically seeds:
  - **Email:** `admin@smeloan.com`
  - **Password:** `Admin@12345`
  - **Role:** `admin`
  - *(Credentials customizable via `.env`)*

### 5. Authentication & User Management Endpoints
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Public (Applicants only) | Self-registration for loan applicants (role automatically set to `applicant`) |
| `POST` | `/api/v1/auth/login` | Public | Authenticate with email/password & receive JWT token |
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieve profile of the currently logged-in user |
| `POST` | `/api/v1/auth/users` | Admin only | Admin creates internal staff: Relationship Manager (`manager`), Loan Officer (`officer`), or Approval Authority (`authority`) |
| `GET` | `/api/v1/auth/users` | Admin only | Admin lists all registered and staff users in the system |

---

## Prerequisites

- **Python 3.11**
- **PostgreSQL 16+**
- **Git**

---

## Setup and Installation

### 1. Clone the repository
```bash
git clone YOUR_REPOSITORY_URL
cd sme_loan
```

### 2. Activate virtual environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the project root:
```env
APP_NAME="SME Loan Risk API"
APP_ENV=development
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/sme_loan
FRONTEND_API_BASE_URL=http://127.0.0.1:8000/api/v1

JWT_SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
SEED_ADMIN_EMAIL=admin@smeloan.com
SEED_ADMIN_PASSWORD=Admin@12345
SEED_ADMIN_NAME="System Administrator"
SEED_ADMIN_PHONE="+1234567890"
```

---

## Running the Application

### Terminal 1 — Backend (FastAPI)
```powershell
.\venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload
```
- **API Root:** http://127.0.0.1:8000
- **Swagger Documentation:** http://127.0.0.1:8000/docs
- **Health Check:** http://127.0.0.1:8000/health

### Terminal 2 — Frontend (Streamlit)
```powershell
.\venv\Scripts\Activate.ps1
streamlit run frontend/app.py
```
- **Web App:** http://localhost:8501

---

## Development Roadmap

### Completed (Phase 1)
- [x] Python 3.11 environment & PostgreSQL database integration
- [x] User model with `uid` (Integer primary key)
- [x] Bcrypt password hashing & JWT token issuance/verification
- [x] Auto-admin seeder on startup (`admin@smeloan.com`)
- [x] Public self-registration strictly restricted to `applicant` role
- [x] Admin-only staff creation endpoint for Relationship Manager (`manager`) and Loan Officer (`officer`)
- [x] User login, list users, and `/me` profile endpoints
- [x] Initial loan application submission and retrieval endpoints

### Upcoming (Phase 2 & beyond)
- [ ] Role-based access control guards on loan routes (Officer, Manager, Authority)
- [ ] Trained ML model integration (replacing mock scoring)
- [ ] Full loan lifecycle & approval workflow
- [ ] Supporting document upload handling
- [ ] Connect Streamlit UI with new JWT auth endpoints

---

## Important Notes

- Predictions in prototype mode currently use a mock logic module until the final trained model is plugged in.
- Never commit `.env` or database credentials to version control.

---

Please refer to the `docs/` folder for additional architectural diagrams and use case specifications.
