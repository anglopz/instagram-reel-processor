from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import DomainException, Unauthorized
from src.infrastructure.auth.jwt_handler import create_token
from src.infrastructure.auth.password import hash_password, verify_password
from src.infrastructure.database.models import UserModel
from src.presentation.api.dependencies import get_session
from src.presentation.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    existing = await session.execute(
        select(UserModel).where(UserModel.email == body.email)
    )
    if existing.scalar_one_or_none() is not None:
        raise DomainException(
            "Email already registered",
            status_code=409,
            error_code="EMAIL_EXISTS",
        )

    user = UserModel(
        id=uuid4(),
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    session.add(user)
    await session.commit()

    token = create_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    result = await session.execute(
        select(UserModel).where(UserModel.email == body.email)
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise Unauthorized("Invalid email or password")

    token = create_token(user.id, user.email)
    return TokenResponse(access_token=token)
