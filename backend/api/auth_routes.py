from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies import get_current_user, get_db, require_admin
from backend.schemas.user import (
    StaffUserCreate,
    TokenResponse,
    UserLogin,
    UserRead,
    UserRegister,
)
from backend.security import create_access_token
from backend.services.auth_service import (
    authenticate_user,
    create_staff_user,
    get_user_by_email,
    register_user,
)
from database.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Public: Only Applicants Can Self-Register ────────────────────────
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    return register_user(db, payload)


# ── Admin-Only: Create Staff Users (RM, Loan Officer, Authority) ────
@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Admin creates staff user (RM, Loan Officer, Approval Authority)",
)
def create_internal_user(
    payload: StaffUserCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    return create_staff_user(db, payload)


# ── Admin-Only: List All Users ──────────────────────────────────────
@router.get(
    "/users",
    response_model=list[UserRead],
    summary="Admin lists all users",
)
def list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    return db.query(User).order_by(User.uid.asc()).all()


# ── Public: Login ───────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )
    token = create_access_token(
        data={"sub": str(user.uid), "role": user.role, "email": user.email}
    )
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


# ── Authenticated: Current User Profile ──────────────────────────────
@router.get("/me", response_model=UserRead)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
