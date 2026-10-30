"""
Pytest fixtures for the backend test suite.

Strategy for Python 3.14 + SQLite:
- Use a file-based SQLite test database (not in-memory) so all connections
  share the same tables regardless of connection pooling.
- Wipe tables before and after the session.
- Use NullPool so no background threads remain after the session ends.
"""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

TEST_DB_PATH = Path(__file__).parent / "test_patchpilot.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(scope="session")
def test_engine():
    import app.models  # noqa: F401
    from app.core.database import Base

    # Clean up any leftover from a previous run
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    e = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(bind=e)
    yield e
    Base.metadata.drop_all(bind=e)
    e.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture
def db_session(test_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session, test_engine):
    """
    Starlette TestClient with the DB dependency overridden to use the
    test database, and init_db redirected to the test engine.
    """
    from fastapi.testclient import TestClient
    from app.core.database import get_db
    from app.main import app
    import app.core.database as db_module

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Make init_db() a no-op for tests (tables already created above)
    original_engine = db_module.engine
    db_module.engine = test_engine

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
    db_module.engine = original_engine


# ── Helper fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("myapp/main.py", "def add(a, b):\n    return a + b\n")
        zf.writestr(
            "myapp/tests/test_main.py",
            "from myapp.main import add\ndef test_add():\n    assert add(1,2)==3\n",
        )
    return buf.getvalue()


@pytest.fixture
def traversal_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../../etc/passwd", "root:x:0:0:root:/root:/bin/bash")
    return buf.getvalue()
