"""
Tests verifying WebSocket JWT authentication and object-level ownership checks (BACKEND-02).
"""
import pytest
from app.routes.websockets import verify_ws_token_and_ownership
from app.auth import create_access_token
from app.models import User, Download
from app.database import SessionLocal, Base, engine


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        # Create test users if not existing
        u1 = db.query(User).filter(User.username == "ws_user1").first()
        if not u1:
            u1 = User(id=101, username="ws_user1", email="ws1@example.com", hashed_password="pw", role="user")
            db.add(u1)
        u2 = db.query(User).filter(User.username == "ws_user2").first()
        if not u2:
            u2 = User(id=102, username="ws_user2", email="ws2@example.com", hashed_password="pw", role="user")
            db.add(u2)
        admin = db.query(User).filter(User.username == "ws_admin").first()
        if not admin:
            admin = User(id=103, username="ws_admin", email="admin@example.com", hashed_password="pw", role="admin")
            db.add(admin)

        # Create download belonging to user 1
        d1 = db.query(Download).filter(Download.id == 901).first()
        if not d1:
            d1 = Download(id=901, url="https://example.com/video1", user_id=101, status="PENDING")
            db.add(d1)
        db.commit()


def test_ws_missing_token_rejected():
    assert verify_ws_token_and_ownership(token=None, download_id=901) is False
    assert verify_ws_token_and_ownership(token="", download_id=901) is False


def test_ws_invalid_token_rejected():
    assert verify_ws_token_and_ownership(token="not.a.valid.jwt.token", download_id=901) is False


def test_ws_valid_token_owner_allowed():
    token = create_access_token(data={"sub": "ws_user1"})
    assert verify_ws_token_and_ownership(token=token, download_id=901) is True


def test_ws_valid_token_non_owner_forbidden():
    token = create_access_token(data={"sub": "ws_user2"})
    assert verify_ws_token_and_ownership(token=token, download_id=901) is False


def test_ws_admin_token_allowed_for_any_download():
    token = create_access_token(data={"sub": "ws_admin"})
    assert verify_ws_token_and_ownership(token=token, download_id=901) is True
