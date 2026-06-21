import pytest
from fastapi.testclient import TestClient
from media_agents.main import app

from media_agents.main import app


@pytest.fixture(scope="module")
def client():
    import media_agents.env as env

    old_val = env.ENABLE_LOCAL_AUTH
    env.ENABLE_LOCAL_AUTH = True

    from media_agents.main import app

    c = TestClient(app)
    yield c
    env.ENABLE_LOCAL_AUTH = old_val


import media_agents.env as env  # noqa: E402

env.ENABLE_LOCAL_AUTH = True
import media_agents.auth.router as auth_router  # noqa: E402

auth_router.ENABLE_LOCAL_AUTH = True

from media_agents.services import user as user_service  # noqa: E402

    c = TestClient(app)
    yield c
    env.ENABLE_LOCAL_AUTH = old_val


@pytest.fixture(autouse=True)
def mock_prisma(monkeypatch):
    from media_agents.services import user as user_service

    async def mock_get_user_by_email(email):
        return None

    async def mock_get_user_by_username(username):
        return None

    async def mock_create_local_user(username, email, password_hash):
        return {
            "id": "1",
            "username": username,
            "email": email,
            "role": "USER",
            "avatarUrl": None,
        }



    from media_agents.services import user as user_service

    monkeypatch.setattr(user_service, "get_user_by_email", mock_get_user_by_email)
    monkeypatch.setattr(user_service, "get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr(user_service, "create_local_user", mock_create_local_user)

    # Mock analytics to avoid sending events during tests
    from media_agents.analytics import analytics  # noqa: E402
    from media_agents.analytics import analytics

    monkeypatch.setattr(analytics, "identify", lambda *args, **kwargs: None)
    monkeypatch.setattr(analytics, "capture", lambda *args, **kwargs: None)



def test_register_weak_password(client):
def test_register_weak_password(client, monkeypatch):
    from media_agents.auth import router

    monkeypatch.setattr(router, "ENABLE_LOCAL_AUTH", True, raising=False)
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


    response = client.post(
        "/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "weak"},
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


def test_register_weak_password_no_special(client):
def test_register_weak_password_no_special(client, monkeypatch):
    from media_agents.auth import router

    monkeypatch.setattr(router, "ENABLE_LOCAL_AUTH", True, raising=False)
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
            "password": "strongpassword",
            "password": "Password1",
        },
    )
    assert response.status_code == 400
    assert (
        "Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character."
        in response.json()["detail"]
    )
        "Password must be at least 8 characters long and contain at least one uppercase letter"
        in response.json()["detail"]
    )


def test_register_strong_password(client, monkeypatch):
    from media_agents.auth import router

    monkeypatch.setattr(router, "ENABLE_LOCAL_AUTH", True, raising=False)

    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongPassword1!",
        },
    )
    assert response.status_code == 200


def test_rate_limiting(client, monkeypatch):
    from media_agents.auth import router
    from media_agents.auth.rate_limit import _rate_limit_store

    monkeypatch.setattr(router, "ENABLE_LOCAL_AUTH", True, raising=False)

    # Clear the rate limit store to avoid flaky tests
    _rate_limit_store.clear()

    import time

    for _ in range(5):
        client.post(
            "/auth/login",
            json={
                "email_or_username": "nonexistent@example.com",
                "password": "StrongPassword1!",
            },
        )
        time.sleep(0.01)

    response = client.post(
        "/auth/login",
        json={
            "email_or_username": "nonexistent@example.com",
            "password": "StrongPassword1!",
        },
    )

    assert response.status_code == 429
    assert response.json()["detail"] == "Too Many Requests"


def test_rate_limiting_headers(client, monkeypatch):
    from media_agents.auth import router
    from media_agents.auth.rate_limit import _rate_limit_store

    monkeypatch.setattr(router, "ENABLE_LOCAL_AUTH", True, raising=False)

    # Clear the rate limit store to avoid flaky tests
    _rate_limit_store.clear()

    import time

    for _ in range(5):
        client.post(
            "/auth/login",
            json={
                "email_or_username": "nonexistent@example.com",
                "password": "StrongPassword1!",
            },
            headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"},
        )
        time.sleep(0.01)
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

def test_register_strong_password(client):
    response = client.post(
        "/auth/login",
        json={
            "email_or_username": "nonexistent@example.com",
            "password": "StrongPassword1!",
        },
        headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"},
    )

    assert response.status_code == 429
    assert response.json()["detail"] == "Too Many Requests"

    # A different IP should be allowed
    response2 = client.post(
        "/auth/login",
        json={
            "email_or_username": "nonexistent@example.com",
            "password": "StrongPassword1!",
        },
        headers={"X-Forwarded-For": "4.3.2.1"},
    )
    assert response2.status_code != 429
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
