import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.session import Base, get_db
from app.db import base  # noqa: F401 — registers all ORM models (Dataset, etc.) with Base.metadata

# Use in-memory SQLite with StaticPool so all threads/connections share the same DB.
# This is required because FastAPI runs sync endpoints in a thread pool — without
# StaticPool, each thread would get a fresh, empty in-memory database.
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


@pytest.fixture(scope="function")
def db_session():
    """
    Creates an isolated database schema in memory for each test function,
    yielding a clean session and dropping all tables after test completion.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Provides a FastAPI TestClient with the dependency 'get_db' overridden
    to use the clean database session created by the db_session fixture.
    """
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up overrides after test run
    app.dependency_overrides.clear()
