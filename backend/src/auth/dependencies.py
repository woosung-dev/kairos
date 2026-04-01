# backend/src/auth/dependencies.py
"""Auth 의존성 — Depends() 조립의 유일한 위치."""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.repository import UserRepository
from src.auth.service import AuthService
from src.common.database import get_async_session
from src.core.config import get_settings


async def verify_clerk_token(authorization: str = Header(...)) -> dict:
    """Clerk JWT 검증. Bearer 토큰에서 클레임 추출."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다")

    token = authorization.removeprefix("Bearer ")

    try:
        from clerk_backend_api import Clerk

        settings = get_settings()
        clerk = Clerk(bearer_auth=settings.clerk_secret_key.get_secret_value())
        # Clerk SDK로 JWT 검증
        claims = clerk.sessions.verify_token(token)
        return {"sub": claims.sub}
    except Exception:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")


async def get_user_by_clerk_id(
    clerk_id: str,
    session: AsyncSession,
) -> User:
    """Clerk ID로 DB 사용자 조회."""
    repo = UserRepository(session)
    user = await repo.find_by_clerk_id(clerk_id)
    if user is None:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    return user


async def get_current_user(
    claims: dict = Depends(verify_clerk_token),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """현재 인증된 사용자를 반환. 다른 라우터에서 Depends로 사용."""
    return await get_user_by_clerk_id(claims["sub"], session)


async def get_auth_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    return UserRepository(session)


async def get_auth_service(
    repo: UserRepository = Depends(get_auth_repository),
) -> AuthService:
    return AuthService(repo)
