# backend/src/workspaces/repository.py
"""Workspace Repository — AsyncSession 유일 보유자.

Sprint 19 PR #1 C12 (Codex F-1/F-5): 헌법 I-9 강제.
find_member_by_id / find_invite_by_id / update_member_role / remove_member /
deactivate_invite / increment_invite_use_count 모두 workspace_id 명시 + WHERE 절.
"""
import uuid
from datetime import datetime

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import delete, func, select, text, update

from src.workspaces.models import Workspace, WorkspaceInvite, WorkspaceMember


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, workspace: Workspace) -> Workspace:
        self.session.add(workspace)
        await self.session.flush()
        return workspace

    async def find_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        return (await self.session.exec(
            select(Workspace).where(Workspace.id == workspace_id)
        )).one_or_none()

    async def find_by_user(self, user_id: uuid.UUID) -> list[Workspace]:
        """사용자가 속한 워크스페이스 목록."""
        return list((await self.session.exec(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        )).all())

    async def get_member_count(self, workspace_id: uuid.UUID) -> int:
        return (await self.session.exec(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )).one()

    async def update_threshold(
        self, workspace_id: uuid.UUID, threshold: float
    ) -> None:
        await self.session.exec(
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(inbox_threshold=threshold, updated_at=datetime.utcnow())
        )

    # --- 멤버 관리 (Sprint 19 PR #1 C12: workspace_id 강제) ---

    async def find_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        """워크스페이스-유저 조합으로 멤버 조회. RBAC 검증 + I-17 cross-workspace 차단에서 사용."""
        return (await self.session.exec(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )).one_or_none()

    async def find_member_by_id(
        self, member_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> WorkspaceMember | None:
        """헌법 I-9 (Codex F-1): member_id + workspace_id 동시 필터."""
        return (await self.session.exec(
            select(WorkspaceMember).where(
                WorkspaceMember.id == member_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def list_members(
        self, workspace_id: uuid.UUID
    ) -> list[WorkspaceMember]:
        return list((await self.session.exec(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id
            )
        )).all())

    async def add_member(self, member: WorkspaceMember) -> WorkspaceMember | None:
        """멤버 추가 (race-safe). 이미 (workspace_id, user_id) 멤버면 None 반환.

        QA-0617-D fix: 기존 add+flush 는 동시 INSERT 시 uq_workspace_member UNIQUE
        위반 → 처리 안 된 IntegrityError → HTTP 500. asyncpg+greenlet 에서는
        flush 후 try/except IntegrityError 가 MissingGreenlet 으로 전파되므로
        (feedback_asyncpg_greenlet_precheck) ON CONFLICT DO NOTHING RETURNING 으로
        race backstop. RETURNING 이 row 를 내면 INSERT 성공, 없으면 이미 멤버(충돌)
        → caller 가 None 을 idempotent/409 로 처리.
        """
        row = (await self.session.exec(
            text(
                """
                INSERT INTO workspace_members (id, workspace_id, user_id, role)
                VALUES (:id, :workspace_id, :user_id, :role)
                ON CONFLICT (workspace_id, user_id) DO NOTHING
                RETURNING id
                """
            ).bindparams(
                id=member.id,
                workspace_id=member.workspace_id,
                user_id=member.user_id,
                role=member.role,
            )
        )).one_or_none()
        if row is None:
            return None
        return member

    async def update_member_role(
        self, member_id: uuid.UUID, workspace_id: uuid.UUID, role: str
    ) -> None:
        """헌법 I-9 (Codex F-5): mutation 도 workspace_id WHERE 강제."""
        await self.session.exec(
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
        await self.session.exec(
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
        return (await self.session.exec(
            select(WorkspaceInvite).where(WorkspaceInvite.code == code)
        )).one_or_none()

    async def find_invite_by_id(
        self, invite_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> WorkspaceInvite | None:
        """헌법 I-9 (Codex F-1): invite_id + workspace_id 동시 필터."""
        return (await self.session.exec(
            select(WorkspaceInvite).where(
                WorkspaceInvite.id == invite_id,
                WorkspaceInvite.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def list_invites(
        self, workspace_id: uuid.UUID
    ) -> list[WorkspaceInvite]:
        return list((await self.session.exec(
            select(WorkspaceInvite)
            .where(
                WorkspaceInvite.workspace_id == workspace_id,
                WorkspaceInvite.is_active.is_(True),
            )
            .order_by(WorkspaceInvite.created_at.desc())
        )).all())

    async def increment_invite_use_count(
        self, invite_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """헌법 I-9 (Codex F-5): mutation 도 workspace_id WHERE 강제."""
        await self.session.exec(
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
        await self.session.exec(
            update(WorkspaceInvite)
            .where(
                WorkspaceInvite.id == invite_id,
                WorkspaceInvite.workspace_id == workspace_id,
            )
            .values(is_active=False)
        )

    async def commit(self) -> None:
        await self.session.commit()
