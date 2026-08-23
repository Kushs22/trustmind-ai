from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    authenticate_user,
    build_token_response,
    create_anonymous_user,
    register_user,
    user_to_response,
)
from app.services.rate_limit import RateLimitExceeded, enforce_rate_limit

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _rate_limit_http(exc: RateLimitExceeded) -> HTTPException:
    headers = {}
    if exc.retry_after_seconds is not None:
        headers["Retry-After"] = str(exc.retry_after_seconds)
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=str(exc),
        headers=headers or None,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        enforce_rate_limit(request, action="auth_register")
    except RateLimitExceeded as exc:
        raise _rate_limit_http(exc) from exc
    try:
        user = register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return build_token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        enforce_rate_limit(request, action="auth_login")
    except RateLimitExceeded as exc:
        raise _rate_limit_http(exc) from exc
    user = authenticate_user(db, payload)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return build_token_response(user)


@router.post("/anonymous", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def anonymous_session(request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        enforce_rate_limit(request, action="auth_anonymous")
    except RateLimitExceeded as exc:
        raise _rate_limit_http(exc) from exc
    user = create_anonymous_user(db)
    return build_token_response(user)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return user_to_response(user)
