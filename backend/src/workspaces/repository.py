# backend/src/workspaces/repository.py
"""Workspace Repository — AsyncSession 유일 보유자."""
import uuid
from datetime import datetime

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.workspaces.models import Workspace, WorkspaceInvite, WorkspaceMember


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

    async def update_threshold(
        self, workspace_id: uuid.UUID, threshold: float
    ) -> None:
        await self.session.execute(
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(inbox_threshold=threshold, updated_at=datetime.utcnow())
        )

    # --- 멤버 관리 ---

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

    async def find_member_by_id(
        self, member_id: uuid.UUID
    ) -> WorkspaceMember | None:
        result = await self.session.execute(
            select(WorkspaceMember).where(WorkspaceMember.id == member_id)
        )
        return result.scalar_one_or_none()

    async def list_members(
        self, workspace_id: uuid.UUID
    ) -> list[WorkspaceMember]:
        result = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id
            )
        )
        return list(result.scalars().all())

    async def add_member(self, member: WorkspaceMember) -> WorkspaceMember:
        self.session.add(member)
        await self.session.flush()
        return member

    async def update_member_role(
        self, member_id: uuid.UUID, role: str
    ) -> None:
        await self.session.execute(
            update(WorkspaceMember)
            .where(WorkspaceMember.id == member_id)
            .values(role=role)
        )

    async def remove_member(self, member_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(WorkspaceMember).where(WorkspaceMember.id == member_id)
        )

    # --- 초대 링크 ---

    async def save_invite(self, invite: WorkspaceInvite) -> WorkspaceInvite:
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def find_invite_by_code(self, code: str) -> WorkspaceInvite | None:
        result = await self.session.execute(
            select(WorkspaceInvite).where(WorkspaceInvite.code == code)
        )
        return result.scalar_one_or_none()

    async def find_invite_by_id(
        self, invite_id: uuid.UUID
    ) -> WorkspaceInvite | None:
        result = await self.session.execute(
            select(WorkspaceInvite).where(WorkspaceInvite.id == invite_id)
        )
        return result.scalar_one_or_none()

    async def list_invites(
        self, workspace_id: uuid.UUID
    ) -> list[WorkspaceInvite]:
        result = await self.session.execute(
            select(WorkspaceInvite)
            .where(
                WorkspaceInvite.workspace_id == workspace_id,
                WorkspaceInvite.is_active.is_(True),
            )
            .order_by(WorkspaceInvite.created_at.desc())
        )
        return list(result.scalars().all())

    async def increment_invite_use_count(self, invite_id: uuid.UUID) -> None:
        await self.session.execute(
            update(WorkspaceInvite)
            .where(WorkspaceInvite.id == invite_id)
            .values(use_count=WorkspaceInvite.use_count + 1)
        )

    async def deactivate_invite(self, invite_id: uuid.UUID) -> None:
        await self.session.execute(
            update(WorkspaceInvite)
            .where(WorkspaceInvite.id == invite_id)
            .values(is_active=False)
        )

    async def commit(self) -> None:
        await self.session.commit()
