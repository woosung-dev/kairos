# backend/src/actions/repository.py
"""ActionItem Repository — AsyncSession 유일 보유자."""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, select, update

from src.actions.models import ActionItem


class ActionItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(
        self, action_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> ActionItem | None:
        """헌법 I-9 (Codex F-1): action_id + workspace_id 동시 필터."""
        return (await self.session.exec(
            select(ActionItem).where(
                ActionItem.id == action_id,
                ActionItem.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
        priority: str | None = None,
        project_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ActionItem]:
        stmt = select(ActionItem).where(ActionItem.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(ActionItem.status == status)
        if priority:
            stmt = stmt.where(ActionItem.priority == priority)
        if project_id:
            stmt = stmt.where(ActionItem.project_id == project_id)
        stmt = stmt.order_by(ActionItem.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(ActionItem)
            .where(ActionItem.workspace_id == workspace_id)
        )
        if status:
            stmt = stmt.where(ActionItem.status == status)
        return (await self.session.exec(stmt)).one()

    async def find_by_meeting(self, meeting_id: uuid.UUID) -> list[ActionItem]:
        """회의에서 추출된 액션 아이템 조회."""
        stmt = (
            select(ActionItem)
            .where(ActionItem.meeting_id == meeting_id)
            .order_by(ActionItem.created_at.desc())
        )
        return list((await self.session.exec(stmt)).all())

    async def cancel_todo_by_project(self, project_id: uuid.UUID) -> int:
        """프로젝트 archive 시 todo 상태 액션을 cancelled로 변경.

        BL-054 manifest G3-keep: rowcount 반환을 위해 session.execute() 유지
        (SQLModel exec() 의 ScalarResult 에는 .rowcount 미존재).
        """
        result = await self.session.execute(
            update(ActionItem)
            .where(
                ActionItem.project_id == project_id,
                ActionItem.status == "todo",
            )
            .values(status="cancelled")
        )
        await self.session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def save(self, item: ActionItem) -> ActionItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def commit(self) -> None:
        await self.session.commit()
