# Risk Radar – SME Loan Risk Prediction System

Backend-focused SME Loan Risk Prediction System featuring REST APIs, Swagger UI demonstration, PostgreSQL data persistence, relationship manager validation, loan officer risk assessment, and an integrated SME Hybrid Model.

## Supported Python Runtimes

- **Python 3.11** (Target deployment environment: Office TCS Accops Windows VM)
- **Python 3.13** (Local development environment)

Package dependencies in `requirements.txt` provide pre-built Windows 64-bit wheels (`win_amd64`) compatible with both CPython 3.11 and CPython 3.13.

## Project Layout

```text
backend/                  FastAPI REST API, services, entities, PostgreSQL repositories, tests
database/schema.sql       PostgreSQL schema baseline
dataset/                  Preserved training, test, and synthetic CSVs
ml/artifacts/             Preserved .joblib and metadata artifacts (SME Hybrid Model)
ml/results/               Evaluation and comparison reports
ml/training/              Model training and evaluation scripts
tools/dataset/            Dataset generation and inspection utilities
requirements.txt          Cross-compatible dependencies for Python 3.11 and 3.13
```

## Environment Setup (Windows)

To set up a fresh virtual environment on either Python 3.11 or Python 3.13:

1. Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Upgrade `pip` and install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Configure environment variables:
   Copy `.env.example` to `.env` in the project root and provide connection details for PostgreSQL and JWT configuration (`JWT_SECRET_KEY`, `JWT_ALGORITHM`, etc.).

4. For a **fresh database only**, run `database/schema.sql` once via pgAdmin Query Tool or psql to establish the initial table baseline.

5. Apply versioned database migrations explicitly:

```powershell
python -m backend.app.database.migrate
```

6. Run the test suite:

```powershell
python -m pytest -q
```

## Running the Application

### 1. FastAPI REST API & Swagger UI (Primary Interface)

Start the FastAPI server:

```powershell
uvicorn backend.app.api.main:app --reload --host 127.0.0.1 --port 8000
```

Access the interactive API documentation and testing interface:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **API Health:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Console Application

Run the interactive terminal workflow:

```powershell
python -m backend.app.console.main
```

## Office Accops Deployment (CPython 3.11)

On the TCS Accops Windows virtual machine (which runs CPython 3.11):

1. Open PowerShell in the project directory inside the Accops environment.
2. Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Upgrade pip and install the cross-compatible requirements:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

4. Verify package installation:

```powershell
python -m pip check
```

5. Ensure `.env` is configured for the Accops database environment.
6. Run database migrations:

```powershell
python -m backend.app.database.migrate
```

7. Execute the backend test suite:

```powershell
python -m pytest -q
```

8. Launch the FastAPI server or console application as required:

```powershell
uvicorn backend.app.api.main:app --host 127.0.0.1 --port 8000
```
