from sqlalchemy.orm import Session

from backend.config import settings
from backend.schemas.user import StaffUserCreate, UserRegister
from backend.security import hash_password, verify_password
from database.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def register_user(db: Session, payload: UserRegister) -> User:
    """Public self-registration strictly for loan applicants."""
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        phone_number=payload.phone_number,
        role="applicant",
        company_name=payload.company_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_staff_user(db: Session, payload: StaffUserCreate) -> User:
    """Internal user creation by admin (e.g., manager, officer, authority)."""
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        phone_number=payload.phone_number,
        role=payload.role,
        company_name=None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def seed_admin_user(db: Session) -> User | None:
    """Seeds the initial admin user if an admin does not already exist."""
    admin_exists = db.query(User).filter(User.role == "admin").first()
    if not admin_exists:
        admin_user = User(
            full_name=settings.seed_admin_name,
            email=settings.seed_admin_email,
            password_hash=hash_password(settings.seed_admin_password),
            phone_number=settings.seed_admin_phone,
            role="admin",
            company_name=None,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        return admin_user
    return None
