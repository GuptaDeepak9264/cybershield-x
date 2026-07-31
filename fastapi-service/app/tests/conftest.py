import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import ThreatIntelEntry, User

TEST_JWT_SECRET = "test-jwt-secret-different-from-secret-key-abcdef123456"

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _override_settings(monkeypatch):
    # Keep the app's JWT_SECRET in sync with what test tokens are signed
    # with, without touching a real .env file.
    get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    yield
    get_settings.cache_clear()


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def student_user(db_session):
    user = User(id=1, username="student1", email="s1@example.com", role="STUDENT", is_active=True)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def admin_user(db_session):
    user = User(id=2, username="admin1", email="a1@example.com", role="ADMIN", is_active=True)
    db_session.add(user)
    db_session.commit()
    return user


def make_token(user) -> str:
    """Stand-in for django-service's /accounts/api/token/ - same claim shape."""
    payload = {"user_id": user.id, "username": user.username, "role": user.role}
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture()
def auth_headers():
    def _headers(user) -> dict:
        return {"Authorization": f"Bearer {make_token(user)}"}

    return _headers
