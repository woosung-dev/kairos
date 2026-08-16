# apps/api/src/auth/repository.py
"""User Repository — AsyncSession 유일 보유자."""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_auth_user_id(self, auth_user_id: str) -> User | None:
        """외부 인증 ID(JWT sub)로 사용자 조회."""
        return (await self.session.exec(
            select(User).where(User.auth_user_id == auth_user_id)
        )).one_or_none()

    # find_by_email 은 ADR-031 에서 삭제했다. 호출자가 0건인 dead code 였고,
    # `users.email` 에 UNIQUE 가 없는데 `.one_or_none()` 이라 컷오버 후
    # (레거시 행 + 재가입 행이 같은 이메일을 갖는 순간) MultipleResultsFound 500 이 된다.
    # 이메일로 사용자를 찾을 일이 생기면 정렬 기준을 명시한 `.first()` 로 새로 만든다.

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        """ID로 사용자 조회."""
        return (await self.session.exec(
            select(User).where(User.id == user_id)
        )).one_or_none()

    async def save(self, user: User) -> User:
        """사용자 저장 (insert or update)."""
        self.session.add(user)
        await self.session.flush()
        return user

    async def commit(self) -> None:
        await self.session.commit()
