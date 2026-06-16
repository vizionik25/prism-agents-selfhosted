"""Tests for media_agents.auth.jwt — the JWT_SECRET guard, encode/decode round-trip,
and the timezone-aware timestamp regression for the datetime.utcnow() removal.
"""

from __future__ import annotations

import time
import uuid

import pytest
from jose import jwt as jose_jwt

from media_agents.auth import jwt as jwt_module


# ---- _get_jwt_secret guard ------------------------------------------------


def test_jwt_secret_raises_when_missing(unset_jwt_secret: None) -> None:
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        jwt_module._get_jwt_secret()


def test_jwt_secret_raises_when_too_short(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "short")
    with pytest.raises(RuntimeError, match="32 characters"):
        jwt_module._get_jwt_secret()


def test_jwt_secret_returns_when_valid() -> None:
    # auto_jwt_secret fixture set a 44-char value
    secret = jwt_module._get_jwt_secret()
    assert len(secret) >= 32


# ---- create_access_token / decode_token round-trip -------------------------


def test_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    token = jwt_module.create_access_token(user_id)
    decoded = jwt_module.decode_token(token)
    assert decoded == user_id


def test_decode_returns_none_for_garbage() -> None:
    assert jwt_module.decode_token("not.a.jwt") is None


def test_decode_returns_none_for_tampered_token() -> None:
    user_id = uuid.uuid4()
    token = jwt_module.create_access_token(user_id)
    # Flip the last character of the signature
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert jwt_module.decode_token(tampered) is None


def test_decode_returns_none_when_sub_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = jwt_module._get_jwt_secret()
    token = jose_jwt.encode({"foo": "bar"}, secret, algorithm="HS256")
    assert jwt_module.decode_token(token) is None


# ---- Regression: timestamps must be timezone-aware UTC --------------------


def test_token_timestamps_are_tz_aware() -> None:
    """Regression for the deprecated datetime.utcnow() → datetime.now(timezone.utc) fix."""
    user_id = uuid.uuid4()
    token = jwt_module.create_access_token(user_id)
    secret = jwt_module._get_jwt_secret()

    # Decode without exp validation so we can inspect the raw claims
    payload = jose_jwt.decode(
        token, secret, algorithms=["HS256"], options={"verify_exp": False}
    )

    # python-jose serializes datetimes to integer Unix timestamps; verify they look sane
    now = int(time.time())
    iat = payload["iat"]
    exp = payload["exp"]
    assert isinstance(iat, int) and isinstance(exp, int)
    assert abs(iat - now) < 5  # within 5 s of now
    assert exp - iat == 24 * 3600  # 24h default TTL
