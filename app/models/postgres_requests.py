from pydantic import BaseModel, EmailStr, Field


class AdminCreateRequest(BaseModel):
    email: EmailStr = Field(..., description="Admin email address")
    username: str = Field(..., description="Admin username")
    hashed_password: str = Field(
        ..., description="Pre‑hashed password for the admin user"
    )


class UserPasswordUpdateRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    new_hashed_password: str = Field(..., description="New pre‑hashed password")
