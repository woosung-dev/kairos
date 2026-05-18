# backend/src/workspaces/repository.py
"""Workspace Repository — AsyncSession 유일 보유자.

Sprint 19 PR #1 C12 (Codex F-1/F-5): 헌법 I-9 강제.
find_member_by_id / find_invite_by_id / update_member_role / remove_member /
deactivate_invite / increment_invite_use_count 모두 workspace_id 명시 + WHERE 절.
"""
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, func, select, update

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

    # --- 멤버 관리 (Sprint 19 PR #1 C12: workspace_id 강제) ---

    async def find_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        """워크스페이스-유저 조합으로 멤버 조회. RBAC 검증 + I-17 cross-workspace 차단에서 사용."""
        result = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_member_by_id(
        self, member_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> WorkspaceMember | None:
        """헌법 I-9 (Codex F-1): member_id + workspace_id 동시 필터."""
        result = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.id == member_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
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
        self, member_id: uuid.UUID, workspace_id: uuid.UUID, role: str
    ) -> None:
        """헌법 I-9 (Codex F-5): mutation 도 workspace_id WHERE 강제."""
        await self.session.execute(
            update(WorkspaceMember)
            .where(
                WorkspaceMember.id == member_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
            .values(role=role)
        )

    async def remove_member(
        self, member_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """헌법 I-9 (Codex F-5): mutation 도 workspace_id WHERE 강제."""
        await self.session.execute(
            delete(WorkspaceMember).where(
                WorkspaceMember.id == member_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
        )

    # --- 초대 링크 (Sprint 19 PR #1 C12: workspace_id 강제) ---

    async def save_invite(self, invite: WorkspaceInvite) -> WorkspaceInvite:
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def find_invite_by_code(self, code: str) -> WorkspaceInvite | None:
        """공개 endpoint 진입점 — code 가 unique 라 workspace_id 불필요."""
        result = await self.session.execute(
            select(WorkspaceInvite).where(WorkspaceInvite.code == code)
        )
        return result.scalar_one_or_none()

    async def find_invite_by_id(
        self, invite_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> WorkspaceInvite | None:
        """헌법 I-9 (Codex F-1): invite_id + workspace_id 동시 필터."""
        result = await self.session.execute(
            select(WorkspaceInvite).where(
                WorkspaceInvite.id == invite_id,
                WorkspaceInvite.workspace_id == workspace_id,
            )
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

    async def increment_invite_use_count(
        self, invite_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """헌법 I-9 (Codex F-5): mutation 도 workspace_id WHERE 강제."""
        await self.session.execute(
            update(WorkspaceInvite)
            .where(
                WorkspaceInvite.id == invite_id,
                WorkspaceInvite.workspace_id == workspace_id,
            )
            .values(use_count=WorkspaceInvite.use_count + 1)
        )

    async def deactivate_invite(
        self, invite_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """헌법 I-9 (Codex F-5): mutation 도 workspace_id WHERE 강제."""
        await self.session.execute(
            update(WorkspaceInvite)
            .where(
                WorkspaceInvite.id == invite_id,
                WorkspaceInvite.workspace_id == workspace_id,
            )
            .values(is_active=False)
        )

    async def commit(self) -> None:
        await self.session.commit()
