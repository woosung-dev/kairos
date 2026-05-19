# Onboarding 도메인 — idempotent UPDATE repository
from uuid import UUID

from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession


class OnboardingRepository:
    """User.onboarding_step idempotent updater.

    호출자의 transaction 에 합류 — commit/flush 없음 (단일 세션 안전).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def increment(self, user_id: UUID, target_step: int) -> None:
        """target_step 이하면 no-op. target=4 면 onboarded_at = now()."""
        await self._session.execute(
            text(
                "UPDATE users "
                "SET onboarding_step = :target, "
                "    onboarded_at = CASE WHEN :target = 4 THEN now() ELSE onboarded_at END "
                "WHERE id = :user_id AND onboarding_step < :target"
            ),
            {"user_id": user_id, "target": target_step},
        )
