import pytest
from fastapi.testclient import TestClient
from media_agents.main import app


@pytest.fixture(scope="module")
def client():
    import media_agents.env as env

    old_val = env.ENABLE_LOCAL_AUTH
    env.ENABLE_LOCAL_AUTH = True

    c = TestClient(app)
    yield c
    env.ENABLE_LOCAL_AUTH = old_val


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

    from media_agents.services import user as user_service

    monkeypatch.setattr(user_service, "get_user_by_email", mock_get_user_by_email)
    monkeypatch.setattr(user_service, "get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr(user_service, "create_local_user", mock_create_local_user)

    # Mock analytics to avoid sending events during tests
    from media_agents.analytics import analytics  # noqa: E402

    monkeypatch.setattr(analytics, "identify", lambda *args, **kwargs: None)
    monkeypatch.setattr(analytics, "capture", lambda *args, **kwargs: None)


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
