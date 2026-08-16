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

    async def increment(self, user_id: UUID, target_step: int) -> str | None:
        """target_step 이하면 no-op(None 반환). 변경 시 해당 user 의 auth_user_id 반환.

        Sprint 29 R1 (auth-cache): `RETURNING auth_user_id` 로 변경 여부 + User cache key 를
        한 쿼리로 얻어, caller(service)가 실제 변경 시에만 cache 를 무효화하도록 한다.
        target=4 면 onboarded_at = now().
        """
        result = await self._session.execute(
            text(
                "UPDATE users "
                "SET onboarding_step = :target, "
                "    onboarded_at = CASE WHEN :target = 4 THEN now() ELSE onboarded_at END "
                "WHERE id = :user_id AND onboarding_step < :target "
                "RETURNING auth_user_id"
            ),
            {"user_id": user_id, "target": target_step},
        )
        row = result.first()
        return row[0] if row else None
