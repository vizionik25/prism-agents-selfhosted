import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError


def _get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET environment variable must be set to a value of at least "
            "32 characters. Generate one with `python -c 'import secrets; "
            "print(secrets.token_urlsafe(48))'`."
        )
    return secret


def _get_jwt_algorithm() -> str:
    return os.environ.get("JWT_ALGORITHM", "HS256")


def _get_jwt_expiration_hours() -> int:
    return int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        "sub": str(user_id),
        "exp": now + timedelta(hours=_get_jwt_expiration_hours()),
        "iat": now,
    }
    return jwt.encode(to_encode, _get_jwt_secret(), algorithm=_get_jwt_algorithm())


def decode_token(token: str) -> Optional[uuid.UUID]:
    try:
        payload = jwt.decode(
            token, _get_jwt_secret(), algorithms=[_get_jwt_algorithm()]
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return uuid.UUID(user_id)
    except JWTError:
        return None
