import pytest
from fastapi.testclient import TestClient
import os

os.environ["ENABLE_LOCAL_AUTH"] = "true"

from media_agents.main import app
from media_agents.services import user as user_service
import media_agents.env as env

env.ENABLE_LOCAL_AUTH = True

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_prisma(monkeypatch):
    async def mock_get_user_by_email(email):
        return None
    async def mock_get_user_by_username(username):
        return None
    async def mock_create_local_user(username, email, password_hash):
        return {"id": "1", "username": username, "email": email, "role": "USER", "avatarUrl": None}

    monkeypatch.setattr(user_service, "get_user_by_email", mock_get_user_by_email)
    monkeypatch.setattr(user_service, "get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr(user_service, "create_local_user", mock_create_local_user)

    # Mock analytics to avoid sending events during tests
    from media_agents.analytics import analytics
    monkeypatch.setattr(analytics, "identify", lambda *args, **kwargs: None)
    monkeypatch.setattr(analytics, "capture", lambda *args, **kwargs: None)

def test_register_weak_password():
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "weak"
    })
    assert response.status_code == 400
    assert "Password must be at least 8 characters long" in response.json()["detail"]

def test_register_weak_password_no_special():
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "strongpassword"
    })
    assert response.status_code == 400
    assert "Password must be at least 8 characters long" in response.json()["detail"]

def test_register_strong_password():
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "StrongPassword1!"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
