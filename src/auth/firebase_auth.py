"""Firebase authentication helpers and FastAPI dependencies."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional

import httpx
import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth, credentials

from src.utils.config import settings
from src.protocols.schemas import FirebaseUser


security = HTTPBearer(auto_error=False)


@lru_cache()
def init_firebase_app() -> Optional[firebase_admin.App]:
    """Initialise the global Firebase Admin app if configured.

    Returns the app instance when configured, otherwise None.
    """
    if firebase_admin._apps:
        return firebase_admin.get_app()

    if not settings.firebase_service_account_path:
        # Backend auth is optional for some environments; if it's not configured
        # we simply don't initialise the app here.
        return None

    cred = credentials.Certificate(settings.firebase_service_account_path)
    return firebase_admin.initialize_app(cred)


async def verify_id_token(id_token: str) -> Dict[str, Any]:
    """Verify a Firebase ID token and return the decoded claims."""
    app = init_firebase_app()
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firebase authentication is not configured on the server.",
        )

    try:
        decoded = firebase_auth.verify_id_token(id_token, app=app)
        return decoded
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc


async def get_current_user(
    credentials_value: HTTPAuthorizationCredentials | None = Depends(security),
) -> FirebaseUser:
    """Extract and verify the current user from the Authorization header."""
    if credentials_value is None or credentials_value.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
        )

    decoded = await verify_id_token(credentials_value.credentials)

    return FirebaseUser(
        uid=decoded.get("uid") or decoded.get("sub"),
        email=decoded.get("email"),
        name=decoded.get("name"),
        picture=decoded.get("picture"),
        provider_id=str(decoded.get("firebase", {}).get("sign_in_provider", "")),
        claims=decoded,
    )


async def _firebase_rest_request(
    endpoint: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Make a request to Firebase Identity Toolkit REST API."""
    if not settings.firebase_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firebase API key is not configured on the server.",
        )

    url = (
        f"https://identitytoolkit.googleapis.com/v1/{endpoint}"
        f"?key={settings.firebase_api_key}"
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=payload)
        except httpx.RequestError as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Error communicating with Firebase authentication service.",
            ) from exc

    data = response.json()
    if response.status_code != 200:
        message = data.get("error", {}).get("message", "Authentication failed.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return data


async def signup_with_email_password(
    email: str,
    password: str,
) -> Dict[str, Any]:
    """Sign up a new user with email and password via Firebase REST API.

    Returns the raw Firebase REST response which includes idToken, refreshToken, etc.
    """
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    return await _firebase_rest_request("accounts:signUp", payload)


async def login_with_email_password(
    email: str,
    password: str,
) -> Dict[str, Any]:
    """Log in an existing user with email and password via Firebase REST API."""
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    return await _firebase_rest_request("accounts:signInWithPassword", payload)


async def verify_id_token_payload(id_token: str) -> FirebaseUser:
    """Verify an ID token and return a FirebaseUser instance."""
    decoded = await verify_id_token(id_token)
    return FirebaseUser(
        uid=decoded.get("uid") or decoded.get("sub"),
        email=decoded.get("email"),
        name=decoded.get("name"),
        picture=decoded.get("picture"),
        provider_id=str(decoded.get("firebase", {}).get("sign_in_provider", "")),
        claims=decoded,
    )

