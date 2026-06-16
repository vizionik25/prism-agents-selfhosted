import base64
import secrets
from typing import Optional
import httpx
import os

from media_agents.env import get_github_redirect_url


GITHUB_API_URL = "https://api.github.com"
GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


def get_github_auth_url(state: str) -> str:
    params = {
        "client_id": os.environ.get("GITHUB_CLIENT_ID", ""),
        "redirect_uri": get_github_redirect_url(),
        "scope": "read:user user:email",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GITHUB_AUTH_URL}?{query}"


def generate_state() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


async def exchange_code_for_token(code: str) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": os.environ.get("GITHUB_CLIENT_ID", ""),
                "client_secret": os.environ.get("GITHUB_CLIENT_SECRET", ""),
                "code": code,
                "redirect_uri": get_github_redirect_url(),
            },
            headers={"Accept": "application/json"},
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return data.get("access_token")


async def get_github_user(access_token: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        if response.status_code != 200:
            return None
        return response.json()


async def get_github_emails(access_token: str) -> list:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        if response.status_code != 200:
            return []
        emails = response.json()
        return [e for e in emails if e.get("primary") and e.get("verified")]


async def get_primary_email(access_token: str) -> Optional[str]:
    user_data = await get_github_user(access_token)
    if user_data and user_data.get("email"):
        return user_data["email"]

    emails = await get_github_emails(access_token)
    if emails:
        return emails[0]["email"]
    return None
