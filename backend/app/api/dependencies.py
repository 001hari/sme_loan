"""FastAPI dependencies for authentication and service injection.

- JWT token creation & verification using ``python-jose``.
- ``get_current_user`` returns a ``Principal`` dict compatible with existing services.
- ``get_workflow_service`` builds a ``WorkflowService`` instance for each request.
"""

import os
from pathlib import Path

# Load .env if present without external dependencies
env_path = Path(__file__).resolve().parents[3] / '.env'
if env_path.is_file():
    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key, val)

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt

from backend.app.services.auth_service import AuthenticationError, AuthorizationError, verify_password, hash_password, ROLES
from backend.app.services.workflow_service import WorkflowService, Principal
from backend.app.repositories.workflow_repository import WorkflowRepository
from backend.app.database.connection import DatabaseConnection

# ---------------------------------------------------------------------
# JWT configuration (read from .env, fallback to a static secret for dev)
# ---------------------------------------------------------------------
# Ensure a JWT secret is provided; fail fast if missing or insecure
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY or JWT_SECRET_KEY == "dev-secret-key":
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable must be set to a secure, non‑default value."
    )
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT token.

    ``data`` should contain at least ``sub`` (user id) and ``role``.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> dict:
    """Decode and verify a JWT token, returning the payload.
    Raises ``HTTPException`` with 401 on failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception

# ---------------------------------------------------------------------
# Dependency that provides the authenticated principal as a dict
# ---------------------------------------------------------------------
from fastapi.security import OAuth2PasswordBearer

oauth_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/staff")

def get_current_principal(token: str = Depends(oauth_scheme)) -> dict:
    """FastAPI dependency extracting the ``Principal`` dict from the JWT.

    The ``token`` is taken from the ``Authorization: Bearer <token>`` header.
    If no token is supplied, a 401 error is raised.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_access_token(token)
    # Payload must contain ``sub`` (user_id) and ``role``.
    user_id = payload.get("sub")
    role = payload.get("role")
    if user_id is None or role is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    # ``full_name`` and ``email`` are optional but helpful for downstream services.
    return {
        "user_id": int(user_id),
        "full_name": payload.get("full_name", ""),
        "email": payload.get("email"),
        "role": role,
    }

# ---------------------------------------------------------------------
# Dependency that constructs a WorkflowService for each request.
# ---------------------------------------------------------------------
def get_workflow_service() -> WorkflowService:
    """Create a fresh ``WorkflowService`` with a new DB connection.

    The service is lightweight; creating it per request is fine for this
    prototype. In production you may want a connection pool.
    """
    db = DatabaseConnection()
    repo = WorkflowRepository(db)
    return WorkflowService(repo)

# Export type alias for FastAPI injection
CurrentPrincipal = Annotated[dict, Depends(get_current_principal)]
WorkflowServiceDep = Annotated[WorkflowService, Depends(get_workflow_service)]
