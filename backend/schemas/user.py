from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Public Applicant Registration ──────────────────────────────────
class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone_number: str | None = Field(default=None, max_length=25)
    company_name: str | None = Field(default=None, max_length=160)


# ── Admin-only Staff Creation (RM, Loan Officer, Approval Authority) ──
class StaffUserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone_number: str | None = Field(default=None, max_length=25)
    role: str = Field(pattern="^(manager|officer|authority)$")


# ── Authentication ────────────────────────────────────────────────
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ── Responses ─────────────────────────────────────────────────────
class UserRead(BaseModel):
    uid: int
    full_name: str
    email: str
    phone_number: str | None
    role: str
    is_active: bool
    company_name: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
