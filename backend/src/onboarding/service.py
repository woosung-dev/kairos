# Onboarding 도메인 — service 계층 (single-session safe, no commit/flush)
from uuid import UUID

from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from src.onboarding.repository import OnboardingRepository
from src.onboarding.schemas import OnboardingResponse


class OnboardingService:
    """다른 도메인이 호출하는 보조 service.

    Idempotency 규칙: increment_step(user_id, target) 은 현재 step >= target 이면 no-op.
    Transaction 합류: 호출 도메인의 session 을 그대로 사용, commit/flush 없음.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OnboardingRepository(session)

    async def increment_step(self, user_id: UUID, target_step: int) -> None:
        """target_step 이상 advance. target ≤ current 면 no-op."""
        await self._repo.increment(user_id, target_step)

    async def get_status(self, user_id: UUID) -> OnboardingResponse:
        """현재 step + onboarded_at 조회. user 없으면 step=0 default."""
        result = await self._session.execute(
            text(
                "SELECT onboarding_step, onboarded_at "
                "FROM users WHERE id = :user_id"
            ),
            {"user_id": user_id},
        )
        row = result.first()
        if row is None:
            return OnboardingResponse(step=0, onboarded_at=None, is_completed=False)
        step = int(row[0])
        return OnboardingResponse(
            step=step,
            onboarded_at=row[1],
            is_completed=(step >= 4),
        )
