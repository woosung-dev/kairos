# backend/src/auth/repository.py
"""User Repository — AsyncSession 유일 보유자."""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_clerk_id(self, clerk_id: str) -> User | None:
        """Clerk ID로 사용자 조회."""
        return (await self.session.exec(
            select(User).where(User.clerk_id == clerk_id)
        )).one_or_none()

    async def find_by_email(self, email: str) -> User | None:
        """이메일로 사용자 조회."""
        return (await self.session.exec(
            select(User).where(User.email == email)
        )).one_or_none()

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

    async def upsert_by_clerk_id(
        self,
        *,
        clerk_id: str,
        email: str,
        display_name: str,
        avatar_url: str | None,
    ) -> User:
        """Race-safe upsert (Codex P2-2 fix, Sprint 27b Wave 1 게이트).

        Clerk webhook + lazy seed (`get_current_user`) 가 동시 발생 시 find-then-insert
        패턴은 unique constraint `clerk_id` 에서 IntegrityError → 500 → Clerk 재시도 무한
        루프 위험. PostgreSQL `INSERT ... ON CONFLICT (clerk_id) DO UPDATE` 로 단일
        statement 원자성 보장. onboarding_step / onboarded_at 은 webhook 으로 덮어쓰지
        않음 (lazy seed 가 관리, I-단조증가 불변식 보존).
        """
        from sqlmodel import text as _text

        await self.session.execute(
            _text(
                """
                INSERT INTO users (
                    id, clerk_id, email, display_name, avatar_url,
                    created_at, updated_at, onboarding_step
                )
                VALUES (
                    gen_random_uuid(), :clerk_id, :email, :display_name, :avatar_url,
                    now(), now(), 0
                )
                ON CONFLICT (clerk_id) DO UPDATE
                SET email = EXCLUDED.email,
                    display_name = EXCLUDED.display_name,
                    avatar_url = EXCLUDED.avatar_url,
                    updated_at = now()
                """
            ),
            {
                "clerk_id": clerk_id,
                "email": email,
                "display_name": display_name,
                "avatar_url": avatar_url,
            },
        )
        await self.session.flush()
        refreshed = await self.find_by_clerk_id(clerk_id)
        assert refreshed is not None, "upsert 후 row 부재 — DB 제약 위반 가능성"
        return refreshed

    async def commit(self) -> None:
        await self.session.commit()
