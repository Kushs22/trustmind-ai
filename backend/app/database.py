from collections.abc import Generator
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import database_url_safe_summary, settings

logger = logging.getLogger(__name__)


def _engine_kwargs() -> dict:
    """Dialect-specific engine options. Postgres gets a short connect timeout so a
    bad/unreachable DATABASE_URL fails fast (with logs) instead of blocking the
    Render port scan until timeout."""
    if settings.is_sqlite:
        return {"connect_args": {"check_same_thread": False}}
    # psycopg2 connect_timeout is seconds; keeps lifespan from hanging indefinitely.
    return {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "connect_args": {"connect_timeout": 15},
    }


engine = create_engine(settings.database_url, **_engine_kwargs())
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
    if not settings.requires_persistent_database:
        return
    if settings.is_sqlite:
        raise RuntimeError(
            "DATABASE_URL must point to PostgreSQL on Render (or set "
            "TRUSTMIND_REQUIRE_POSTGRES only when Postgres is configured). "
            f"Current URL summary: {database_url_safe_summary(settings.database_url)}. "
            "sqlite:///./trustmind.db lives on ephemeral disk and loses users "
            "and check-ins on every redeploy. Create a Render Postgres database "
            "and set DATABASE_URL to its Internal connection string "
            "(postgres:// or postgresql:// — both are normalised automatically)."
        )
    if not settings.is_postgres:
        raise RuntimeError(
            "DATABASE_URL on Render must be a PostgreSQL URL "
            f"(got {database_url_safe_summary(settings.database_url)}). "
            "Paste the Render Postgres Internal URL from the database Info page."
        )


def _ensure_check_in_support_urgency_columns() -> None:
    """
    create_all does not ALTER existing tables. Add support-urgency columns when missing
    so Render Postgres / long-lived SQLite stay compatible after deploy.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "check_ins" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("check_ins")}
    additions = [
        ("support_urgency", "INTEGER"),
        ("support_urgency_band", "VARCHAR(20)"),
        ("support_urgency_rationale", "TEXT"),
        ("support_urgency_uncertain", "BOOLEAN DEFAULT FALSE"),
    ]
    missing = [(name, ddl) for name, ddl in additions if name not in existing]
    if not missing:
        return
    with engine.begin() as conn:
        for name, ddl in missing:
            conn.execute(text(f"ALTER TABLE check_ins ADD COLUMN {name} {ddl}"))
            logger.info("Added check_ins.%s column", name)


def init_db() -> None:
    from app.models import CheckIn, User  # noqa: F401

    summary = database_url_safe_summary(settings.database_url)
    logger.info(
        "Initialising database (%s; sqlite=%s postgres=%s render=%s)",
        summary,
        settings.is_sqlite,
        settings.is_postgres,
        settings.requires_persistent_database,
    )
    try:
        assert_production_database()
        Base.metadata.create_all(bind=engine)
        _ensure_check_in_support_urgency_columns()
    except Exception:
        logger.exception(
            "Database initialisation failed for %s. "
            "On Render: use the Postgres Internal URL on the web service "
            "(same region), keep the default start command with $PORT, and "
            "confirm psycopg2-binary is installed. Do not wrap the URL in quotes.",
            summary,
        )
        raise
    logger.info("Database initialisation complete (%s)", summary)
    if settings.is_sqlite:
        logger.warning(
            "Using SQLite (%s). Fine for local dev; production on Render must use "
            "PostgreSQL via DATABASE_URL.",
            summary,
        )
