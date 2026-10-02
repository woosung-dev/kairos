# push_subscriptions 데이터 접근 — 사용자 단위 리소스라 모든 조회·삭제에 user_id WHERE 강제 (B-2 대체)
import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.push.models import PushSubscription
from src.push.schemas import PushTarget


class PushRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        endpoint: str,
        p256dh: str,
        auth: str,
    ) -> uuid.UUID:
        """endpoint 단위 upsert — 같은 endpoint 면 id 를 유지하고 현재 사용자로 rebind 한다.

        B-10 G3-keep-dialect (`pg_insert` → `session.execute`, C-19). flush 후 IntegrityError 를
        잡는 방식은 asyncpg MissingGreenlet 함정이라 쓰지 않는다.
        created_at/updated_at 은 모델 기본값(`datetime.utcnow`, naive UTC)과 같은 기준으로 넣는다.
        """
        now = datetime.utcnow()
        insert_stmt = pg_insert(PushSubscription.__table__).values(
            id=uuid.uuid4(),
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            created_at=now,
            updated_at=now,
        )
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["endpoint"],
            set_={
                "user_id": insert_stmt.excluded.user_id,
                "p256dh": insert_stmt.excluded.p256dh,
                "auth": insert_stmt.excluded.auth,
                "updated_at": insert_stmt.excluded.updated_at,
            },
        ).returning(PushSubscription.id)
        return (await self.session.execute(stmt)).scalar_one()

    async def list_by_user(self, user_id: uuid.UUID) -> list[PushTarget]:
        """사용자의 구독을 원시 값으로 복사해 돌려준다 (발송 단계는 세션을 닫은 뒤에 돈다)."""
        rows = (
            await self.session.exec(
                select(PushSubscription)
                .where(PushSubscription.user_id == user_id)
                .order_by(PushSubscription.created_at)
            )
        ).all()
        return [
            PushTarget(id=row.id, endpoint=row.endpoint, p256dh=row.p256dh, auth=row.auth)
            for row in rows
        ]

    async def delete_by_id(self, subscription_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """본인 구독 1건 삭제. 없거나 남의 것이면 아무것도 지우지 않는다 (B-10 G3-convert)."""
        await self.session.exec(
            delete(PushSubscription).where(
                PushSubscription.id == subscription_id,
                PushSubscription.user_id == user_id,
            )
        )

    async def delete_by_ids(
        self, subscription_ids: Sequence[uuid.UUID], user_id: uuid.UUID
    ) -> int:
        """404/410 정리 — `id AND user_id` 로만 지운다. 지운 행 수 반환 (B-10 G3-keep rowcount)."""
        result = await self.session.execute(
            delete(PushSubscription).where(
                PushSubscription.id.in_(subscription_ids),
                PushSubscription.user_id == user_id,
            )
        )
        return result.rowcount  # type: ignore[return-value]

    async def commit(self) -> None:
        await self.session.commit()
