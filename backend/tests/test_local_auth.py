import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from media_agents.main import app
import media_agents.env as env
from media_agents.services import user as user_service

# The test client
client = TestClient(app)


@pytest.fixture(scope="module")
def enable_auth():
    old_val = env.ENABLE_LOCAL_AUTH
    env.ENABLE_LOCAL_AUTH = True
    yield
    env.ENABLE_LOCAL_AUTH = old_val


def test_register_weak_password(enable_auth, monkeypatch):
    monkeypatch.setattr(user_service, "get_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(
        user_service, "get_user_by_username", AsyncMock(return_value=None)
    )

    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "weak",
        },
    )
    assert response.status_code == 400
    assert "Password must be at least 8 characters long" in response.json()["detail"]


def test_register_weak_password_no_special(enable_auth, monkeypatch):
    monkeypatch.setattr(user_service, "get_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(
        user_service, "get_user_by_username", AsyncMock(return_value=None)
    )

    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "Password1",
        },
    )
    assert response.status_code == 400
    assert (
        "Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character."
        in response.json()["detail"]
    )


def test_register_strong_password(enable_auth, monkeypatch):
    monkeypatch.setattr(user_service, "get_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(
        user_service, "get_user_by_username", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        user_service,
        "create_local_user",
        AsyncMock(
            return_value={
                "id": "mock_id",
                "email": "test@example.com",
                "username": "testuser",
                "role": "USER",
                "avatarUrl": "",
            }
        ),
    )

    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongPassword1!",
        },
    )
    assert response.status_code == 200


def test_register_strong_password_other_special(enable_auth, monkeypatch):
    monkeypatch.setattr(user_service, "get_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(
        user_service, "get_user_by_username", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        user_service,
        "create_local_user",
        AsyncMock(
            return_value={
                "id": "mock_id",
                "email": "test@example.com",
                "username": "testuser",
                "role": "USER",
                "avatarUrl": "",
            }
        ),
    )

    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongPassword1-",
        },
    )
    assert response.status_code == 200
