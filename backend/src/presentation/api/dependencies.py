from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import Unauthorized
from src.infrastructure.auth.jwt_handler import verify_token
from src.infrastructure.database.session import create_session_factory

_session_factory = create_session_factory()
_bearer_scheme = HTTPBearer()


async def get_session() -> AsyncSession:  # type: ignore[misc]
    async with _session_factory() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> UUID:
    payload = verify_token(credentials.credentials)
    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise Unauthorized("Invalid token payload") from exc
