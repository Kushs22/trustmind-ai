import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    check_ins: Mapped[list["CheckIn"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class CheckIn(Base):
    __tablename__ = "check_ins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    concern_level: Mapped[str] = mapped_column(String(50))
    ai_confidence: Mapped[str] = mapped_column(String(20))
    uncertainty_level: Mapped[str] = mapped_column(String(50))
    grounding_status: Mapped[str] = mapped_column(String(255))
    abstention_status: Mapped[str] = mapped_column(String(100))
    explanation: Mapped[str] = mapped_column(Text)
    safe_next_steps: Mapped[str] = mapped_column(Text)  # JSON array stored as text
    safety_note: Mapped[str] = mapped_column(Text)
    text_preview: Mapped[str | None] = mapped_column(String(280), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True)
    abstained: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship(back_populates="check_ins")
