import uuid

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


def register_user(db: Session, payload: RegisterRequest) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ValueError("An account with this email already exists")

    user = User(
        id=str(uuid.uuid4()),
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        is_anonymous=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: LoginRequest) -> User | None:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or user.hashed_password is None:
        return None
    if not verify_password(payload.password, user.hashed_password):
        return None
    return user


def create_anonymous_user(db: Session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=None,
        hashed_password=None,
        is_anonymous=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def build_token_response(user: User) -> TokenResponse:
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        is_anonymous=user.is_anonymous,
    )


def user_to_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, is_anonymous=user.is_anonymous)


def delete_user_data(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
