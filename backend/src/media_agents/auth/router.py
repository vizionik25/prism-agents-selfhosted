import re
from fastapi import APIRouter, Depends, HTTPException, status, Query

from media_agents.auth.github import (
    get_github_auth_url,
    generate_state,
    exchange_code_for_token,
    get_github_user,
    get_primary_email,
)
from media_agents.auth.jwt import create_access_token
from media_agents.auth.dependencies import get_current_user
from media_agents.services import user as user_service
from media_agents.analytics import analytics
from media_agents.analytics.events import USER_SIGNED_IN, USER_SIGNED_UP
from media_agents.analytics.traits import full_identify_payload, signin_traits
from pydantic import BaseModel
from media_agents import env
from media_agents.auth.pwd_utils import get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    avatar_url: str | None
    role: str = "USER"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserRegister(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    email_or_username: str
    password: str


@router.get("/github")
async def github_login():
    if not env.ENABLE_GITHUB_AUTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub authentication is disabled.",
        )
    state = generate_state()
    url = get_github_auth_url(state)
    return {"url": url, "state": state}


@router.get("/callback", response_model=TokenResponse)
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    if not env.ENABLE_GITHUB_AUTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub authentication is disabled.",
        )
    access_token = await exchange_code_for_token(code)
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authenticate with GitHub",
        )

    github_user = await get_github_user(access_token)
    if github_user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from GitHub",
        )

    github_id = str(github_user["id"])
    username = github_user["login"]
    avatar_url = github_user.get("avatar_url")
    email = await get_primary_email(access_token)

    if email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not get email from GitHub",
        )

    user = await user_service.get_user_by_github_id(github_id)
    is_new_user = user is None

    if is_new_user:
        user = await user_service.create_user(
            github_id=github_id,
            username=username,
            email=email,
            avatar_url=avatar_url,
            access_token=access_token,
        )
    else:
        user = await user_service.update_user(
            user_id=user["id"],
            username=username,
            avatar_url=avatar_url,
            access_token=access_token,
        )

    user_email = user.get("email")
    if is_new_user:
        analytics.identify(
            user_id=user["id"],
            traits=full_identify_payload(user),
            email=user_email,
        )
        analytics.capture(
            user_id=user["id"],
            event=USER_SIGNED_UP,
            email=user_email,
            properties={"signup_source": "github"},
        )
    else:
        analytics.identify(
            user_id=user["id"],
            traits=signin_traits(user),
            email=user_email,
        )
        analytics.capture(
            user_id=user["id"],
            event=USER_SIGNED_IN,
            email=user_email,
            properties={"signup_source": "github"},
        )

    token = create_access_token(user["id"])

    role_val = user.get("role", "USER")
    if hasattr(role_val, "value"):
        role_val = role_val.value

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            avatar_url=user.get("avatarUrl"),
            role=str(role_val),
        ),
    )


@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister):
    if not env.ENABLE_LOCAL_AUTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local authentication is disabled.",
        )

    username = data.username.strip()
    email = data.email.strip().lower()

    if len(username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 3 characters.",
        )
    password = data.password
    # Enforce strong password policy: minimum length and complexity requirements
    if (
        len(password) < 8
        or not re.search(r"[A-Z]", password)
        or not re.search(r"[a-z]", password)
        or not re.search(r"\d", password)
        or not re.search(r"[^A-Za-z0-9]", password)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.",
        )

    # Check uniqueness
    existing_email = await user_service.get_user_by_email(email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    existing_username = await user_service.get_user_by_username(username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken.",
        )

    # Create user
    password_hash = get_password_hash(data.password)
    user = await user_service.create_local_user(
        username=username,
        email=email,
        password_hash=password_hash,
    )

    # Analytics identify/capture
    analytics.identify(
        user_id=user["id"],
        traits=full_identify_payload(user),
        email=user["email"],
    )
    analytics.capture(
        user_id=user["id"],
        event=USER_SIGNED_UP,
        email=user["email"],
        properties={"signup_source": "local"},
    )

    token = create_access_token(user["id"])
    role_val = user.get("role", "USER")
    if hasattr(role_val, "value"):
        role_val = role_val.value

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            avatar_url=user.get("avatarUrl"),
            role=str(role_val),
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    if not env.ENABLE_LOCAL_AUTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local authentication is disabled.",
        )

    login_str = data.email_or_username.strip()
    if "@" in login_str:
        user = await user_service.get_user_by_email(login_str.lower())
    else:
        user = await user_service.get_user_by_username(login_str)

    if user is None or not user.get("passwordHash"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password.",
        )

    if not verify_password(data.password, user["passwordHash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password.",
        )

    analytics.identify(
        user_id=user["id"],
        traits=signin_traits(user),
        email=user["email"],
    )
    analytics.capture(
        user_id=user["id"],
        event=USER_SIGNED_IN,
        email=user["email"],
        properties={"signup_source": "local"},
    )

    token = create_access_token(user["id"])
    role_val = user.get("role", "USER")
    if hasattr(role_val, "value"):
        role_val = role_val.value

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            avatar_url=user.get("avatarUrl"),
            role=str(role_val),
        ),
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role", "USER")
    if hasattr(role, "value"):
        role = role.value
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        avatar_url=current_user.get("avatarUrl"),
        role=str(role),
    )
