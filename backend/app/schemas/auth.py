import json

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    is_anonymous: bool


class UserResponse(BaseModel):
    id: str
    email: str | None
    is_anonymous: bool

    model_config = {"from_attributes": True}
