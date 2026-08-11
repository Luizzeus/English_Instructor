from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class ClerkUser:
    clerk_user_id: str
    session_id: str | None


@lru_cache
def _get_jwk_client() -> PyJWKClient:
    settings = get_settings()
    if not settings.clerk_jwks_url:
        raise RuntimeError("CLERK_JWKS_URL is not configured")
    return PyJWKClient(settings.clerk_jwks_url)


def get_current_clerk_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> ClerkUser:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    settings = get_settings()
    token = credentials.credentials

    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    # Clerk session tokens carry the requesting origin in `azp` instead of a
    # standard `aud` — reject tokens issued for an origin we don't recognize.
    azp = claims.get("azp")
    if azp is not None and azp not in settings.clerk_authorized_parties:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token issued for an untrusted origin")

    return ClerkUser(clerk_user_id=claims["sub"], session_id=claims.get("sid"))
