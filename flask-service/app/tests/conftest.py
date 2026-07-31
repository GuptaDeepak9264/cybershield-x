import os
import shutil
import tempfile

import jwt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import create_app
from app.config import Settings
from app.models import Base, ThreatIntelEntry, User

TEST_JWT_SECRET = "test-jwt-secret-different-from-secret-key-abcdef123456"


@pytest.fixture()
def media_root():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def app(media_root):
    settings = Settings(env={
        "DB_ENGINE": "sqlite3",
        "JWT_SECRET": TEST_JWT_SECRET,
        "MEDIA_ROOT": media_root,
        "SMTP_HOST": "",  # force console fallback in tests - no real SMTP
        "EMAIL_OUTBOX_PATH": os.path.join(media_root, "email_outbox.log"),
    })

    flask_app = create_app(settings)

    # Point the app's engine at a shared in-memory SQLite DB instead of the
    # real SQLITE_PATH file, so tests never touch django-service's actual
    # db.sqlite3.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    flask_app.config["DB_SESSION_FACTORY"] = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    flask_app.config["TESTING"] = True

    yield flask_app

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    session = app.config["DB_SESSION_FACTORY"]()
    yield session
    session.close()


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
    payload = {"user_id": user.id, "username": user.username, "role": user.role}
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture()
def auth_headers():
    def _headers(user) -> dict:
        return {"Authorization": f"Bearer {make_token(user)}"}

    return _headers
