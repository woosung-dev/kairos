# backend/src/auth/repository.py
"""User Repository — AsyncSession 유일 보유자."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_clerk_id(self, clerk_id: str) -> User | None:
        """Clerk ID로 사용자 조회."""
        result = await self.session.execute(
            select(User).where(User.clerk_id == clerk_id)
        )
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> User | None:
        """이메일로 사용자 조회."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        """ID로 사용자 조회."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def save(self, user: User) -> User:
        """사용자 저장 (insert or update)."""
        self.session.add(user)
        await self.session.flush()
        return user

    async def commit(self) -> None:
        await self.session.commit()
