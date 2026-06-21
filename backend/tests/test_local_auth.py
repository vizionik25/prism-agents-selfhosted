import pytest
from fastapi.testclient import TestClient


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

@pytest.fixture(autouse=True)
def mock_prisma(monkeypatch):
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


    monkeypatch.setattr(user_service, "get_user_by_email", mock_get_user_by_email)
    monkeypatch.setattr(user_service, "get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr(user_service, "create_local_user", mock_create_local_user)

    # Mock analytics to avoid sending events during tests
    from media_agents.analytics import analytics  # noqa: E402

    monkeypatch.setattr(analytics, "identify", lambda *args, **kwargs: None)


def test_register_weak_password(client, monkeypatch):
    from media_agents.auth import router

    monkeypatch.setattr(router, "ENABLE_LOCAL_AUTH", True, raising=False)

    response = client.post(
        "/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "weak"},
    )
    assert response.status_code == 400
    assert "Password must be at least 8 characters long" in response.json()["detail"]


def test_register_weak_password_no_special(client, monkeypatch):
    from media_agents.auth import router

    monkeypatch.setattr(router, "ENABLE_LOCAL_AUTH", True, raising=False)

    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "strongpassword",
        },
    )
    assert response.status_code == 400
    assert (
        "Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character."
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
