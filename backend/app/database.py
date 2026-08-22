from collections.abc import Generator
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def assert_production_database() -> None:
    """Refuse ephemeral SQLite on Render so check-in history cannot silently vanish."""
    if settings.requires_persistent_database and settings.is_sqlite:
        raise RuntimeError(
            "DATABASE_URL must point to PostgreSQL on Render (or set "
            "TRUSTMIND_REQUIRE_POSTGRES only when Postgres is configured). "
            "sqlite:///./trustmind.db lives on ephemeral disk and loses users "
            "and check-ins on every redeploy. Create a Render Postgres database "
            "and set DATABASE_URL to its connection string."
        )


def init_db() -> None:
    from app.models import CheckIn, User  # noqa: F401

    assert_production_database()
    Base.metadata.create_all(bind=engine)
    if settings.is_sqlite:
        logger.warning(
            "Using SQLite (%s). Fine for local dev; production on Render must use "
            "PostgreSQL via DATABASE_URL.",
            settings.database_url,
        )
