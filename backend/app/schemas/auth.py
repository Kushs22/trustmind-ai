from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.passwords import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, validate_password_strength


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        error = validate_password_strength(value)
        if error:
            raise ValueError(error)
        return value


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
