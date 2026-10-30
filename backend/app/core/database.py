"""
SQLAlchemy database engine and session management.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine():
    settings = get_settings()
    url = settings.database_url
    kwargs: dict = {}
    if url.startswith("sqlite"):
        # SQLite requires check_same_thread=False for use with FastAPI
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)

    # Enable WAL mode for SQLite to improve concurrent read performance.
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, _connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _build_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def init_db() -> None:
    """Create all tables. Call once at startup."""
    # Import models so Base has them registered before create_all.
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Safely migrate existing tables if columns were added
    with engine.begin() as conn:
        for col, col_type in [
            ("nemotron_critique", "TEXT"),
            ("nebius_telemetry", "TEXT"),
            ("reasoning_log", "TEXT"),
            ("patch_approval", "VARCHAR(16)"),
            ("patch_feedback", "TEXT"),
            ("repair_report", "TEXT"),
            ("error_message", "TEXT"),
            ("repair_iterations", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.exec_driver_sql(f"ALTER TABLE jobs ADD COLUMN {col} {col_type};")
            except Exception:
                pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]
