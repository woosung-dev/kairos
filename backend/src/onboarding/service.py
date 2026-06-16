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
        """target_step 이상 advance. target ≤ current 면 no-op.

        Sprint 29 R1 (auth-cache): step 이 실제 변경되면 User cache(clerk_id 키, 60s TTL)
        를 무효화해 `/me` onboardingStep 의 ≤60s stale 을 제거한다. caller 트랜잭션 합류라
        invalidation 은 pre-commit 이지만 순차 흐름에선 다음 요청이 fresh 를 읽어 자가치유되고,
        no-op(이미 advance 됨)이면 clerk_id=None 이라 무효화도 skip 한다.
        """
        clerk_id = await self._repo.increment(user_id, target_step)
        if clerk_id is not None:
            # 지연 import: auth.dependencies ↔ onboarding 순환 import 회피.
            from src.auth.dependencies import invalidate_user_cache

            invalidate_user_cache(clerk_id)

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
            return OnboardingResponse.model_validate(
                {"step": 0, "totalSteps": 4, "onboardedAt": None, "isCompleted": False}
            )
        step = int(row[0])
        return OnboardingResponse.model_validate(
            {
                "step": step,
                "totalSteps": 4,
                "onboardedAt": row[1],
                "isCompleted": step >= 4,
            }
        )
