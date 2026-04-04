# backend/src/workspaces/repository.py
"""Workspace Repository — AsyncSession 유일 보유자."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.workspaces.models import Workspace, WorkspaceMember


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, workspace: Workspace) -> Workspace:
        self.session.add(workspace)
        await self.session.flush()
        return workspace

    async def find_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        result = await self.session.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def find_by_user(self, user_id: uuid.UUID) -> list[Workspace]:
        """사용자가 속한 워크스페이스 목록."""
        result = await self.session.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_member_count(self, workspace_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        return result.scalar_one()

    async def find_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        result = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_workspace_and_user(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        """워크스페이스-유저 조합으로 멤버 조회. RBAC 검증용."""
        return await self.find_member(workspace_id, user_id)

    async def add_member(self, member: WorkspaceMember) -> WorkspaceMember:
        self.session.add(member)
        await self.session.flush()
        return member

    async def commit(self) -> None:
        await self.session.commit()
