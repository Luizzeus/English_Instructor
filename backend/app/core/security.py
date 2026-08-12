"""Self-hosted email/password auth: bcrypt for hashing, our own signed JWTs for
sessions. No external auth provider — see docs/architecture.md section 1.1 for
why this replaced Clerk (and why it's hand-rolled instead of fastapi-users:
that library's SQLAlchemy adapter requires async, and psycopg3's async mode
needs a Windows event-loop-policy workaround that's already deprecated)."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)

_JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(student_id: int) -> str:
    settings = get_settings()
    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is not configured")
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(student_id), "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=_JWT_ALGORITHM)


def _decode_access_token(token: str) -> int:
    """Returns the student_id encoded in the token, or raises HTTPException(401)."""
    settings = get_settings()
    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is not configured")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc


def get_current_student_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    return _decode_access_token(credentials.credentials)
