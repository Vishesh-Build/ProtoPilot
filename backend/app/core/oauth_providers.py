"""
Minimal OAuth2 clients for Google and GitHub — plain httpx calls against
each provider's real endpoints (no authlib dependency needed, httpx is
already in the project).
"""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import settings


class OAuthError(Exception):
    pass


@dataclass
class OAuthProfile:
    provider_user_id: str
    email: str
    name: str


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def build_google_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def fetch_google_profile(code: str) -> OAuthProfile:
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code >= 400:
            raise OAuthError(f"Google token exchange failed: {token_resp.text[:200]}")
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise OAuthError("Google token response had no access_token")

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_resp.status_code >= 400:
            raise OAuthError(f"Google userinfo request failed: {userinfo_resp.text[:200]}")
        info = userinfo_resp.json()

    if not info.get("email"):
        raise OAuthError("Google account has no email on file")

    return OAuthProfile(
        provider_user_id=info["sub"],
        email=info["email"],
        name=info.get("name") or info["email"].split("@")[0],
    )


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def build_github_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "read:user user:email",
        "state": state,
    }
    return f"{GITHUB_AUTH_URL}?{urlencode(params)}"


async def fetch_github_profile(code: str) -> OAuthProfile:
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "code": code,
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "redirect_uri": settings.github_redirect_uri,
            },
        )
        if token_resp.status_code >= 400:
            raise OAuthError(f"GitHub token exchange failed: {token_resp.text[:200]}")
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise OAuthError(f"GitHub token response had no access_token: {token_data}")

        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"}

        user_resp = await client.get(GITHUB_USER_URL, headers=headers)
        if user_resp.status_code >= 400:
            raise OAuthError(f"GitHub user request failed: {user_resp.text[:200]}")
        user_data = user_resp.json()

        email = user_data.get("email")
        if not email:
            # Private email — GitHub only gives it via the dedicated emails
            # endpoint, and only if the `user:email` scope was granted.
            emails_resp = await client.get(GITHUB_EMAILS_URL, headers=headers)
            if emails_resp.status_code < 400:
                emails = emails_resp.json()
                primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
                if primary:
                    email = primary["email"]

    if not email:
        raise OAuthError(
            "Couldn't get an email from GitHub — make sure your GitHub account "
            "has a public or verified primary email."
        )

    return OAuthProfile(
        provider_user_id=str(user_data["id"]),
        email=email,
        name=user_data.get("name") or user_data.get("login"),
    )
