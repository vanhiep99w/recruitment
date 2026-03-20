"""JWT-backed request auth context helpers."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import settings


@dataclass(slots=True)
class AuthContext:
    """Authenticated request context extracted from a JWT."""

    user_id: uuid.UUID
    org_id: uuid.UUID
    role: str = "recruiter"


def _decode_token(token: str) -> AuthContext:
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    raw_user_id = payload.get("user_id") or payload.get("sub")
    raw_org_id = payload.get("org_id")
    role = payload.get("role", "recruiter")

    if not raw_user_id or not raw_org_id:
        raise ValueError("Token must include user_id/sub and org_id claims")

    return AuthContext(
        user_id=uuid.UUID(str(raw_user_id)),
        org_id=uuid.UUID(str(raw_org_id)),
        role=str(role),
    )


def create_access_token(
    *,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    role: str = "recruiter",
    expires_delta: timedelta | None = None,
) -> str:
    """Create an HS256 access token for local development and tests."""

    expiry = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "user_id": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "exp": int(expiry.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Attach decoded JWT claims to request.state when Authorization is present."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request.state.auth = None
        request.state.user_id = None
        request.state.org_id = None
        request.state.role = None

        header = request.headers.get("authorization", "")
        if header.startswith("Bearer "):
            token = header.removeprefix("Bearer ").strip()
            try:
                auth = _decode_token(token)
            except (JWTError, ValueError):
                request.state.auth = None
            else:
                request.state.auth = auth
                request.state.user_id = auth.user_id
                request.state.org_id = auth.org_id
                request.state.role = auth.role

        return await call_next(request)


async def require_auth_context(request: Request) -> AuthContext:
    """Require an authenticated request and return its auth context."""

    auth = getattr(request.state, "auth", None)
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return auth
