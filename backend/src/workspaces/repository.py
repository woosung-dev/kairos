# backend/src/workspaces/repository.py
"""Workspace Repository — AsyncSession 유일 보유자.

Sprint 19 PR #1 C12 (Codex F-1/F-5): 헌법 I-9 강제.
find_member_by_id / find_invite_by_id / update_member_role / remove_member /
deactivate_invite / increment_invite_use_count 모두 workspace_id 명시 + WHERE 절.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import delete, func, select, text, update

from src.workspaces.models import Workspace, WorkspaceInvite, WorkspaceMember

if TYPE_CHECKING:
    from src.auth.models import User


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

    # DB 에 ondelete CASCADE 가 없어 FK 자식 → 부모 순서로 앱 레벨 삭제.
    # feedback_entries 는 user-level 이라 삭제 대신 workspace_id NULL (컨텍스트만 해제).
    # transcript_segments / meeting_summaries 는 workspace_id 컬럼이 없어 meeting 경유.
    _CASCADE_DELETE_STATEMENTS = (
        "DELETE FROM memory_ai_calls WHERE workspace_id = :ws",
        "DELETE FROM promotion_audit"
        " WHERE source_workspace_id = :ws OR target_workspace_id = :ws",
        "DELETE FROM item_promotion_audit"
        " WHERE source_workspace_id = :ws OR target_workspace_id = :ws",
        "DELETE FROM memory_events WHERE workspace_id = :ws",
        "DELETE FROM memory_items WHERE workspace_id = :ws",
        "DELETE FROM memory_query_embedding_cache WHERE workspace_id = :ws",
        "DELETE FROM semantic_caches WHERE workspace_id = :ws",
        "DELETE FROM embedding_chunks WHERE workspace_id = :ws",
        "DELETE FROM external_documents WHERE workspace_id = :ws",
        "DELETE FROM integration_sync_runs WHERE workspace_id = :ws",
        "DELETE FROM integration_oauth_states WHERE workspace_id = :ws",
        "DELETE FROM integration_connections WHERE workspace_id = :ws",
        "DELETE FROM transcript_segments WHERE meeting_id IN"
        " (SELECT id FROM meetings WHERE workspace_id = :ws)",
        "DELETE FROM meeting_summaries WHERE meeting_id IN"
        " (SELECT id FROM meetings WHERE workspace_id = :ws)",
        "DELETE FROM action_items WHERE workspace_id = :ws",
        "DELETE FROM meeting_project_links WHERE workspace_id = :ws",
        "DELETE FROM inbox_items WHERE workspace_id = :ws",
        "DELETE FROM notes WHERE workspace_id = :ws",
        "DELETE FROM meetings WHERE workspace_id = :ws",
        "DELETE FROM project_members WHERE workspace_id = :ws",
        "DELETE FROM projects WHERE workspace_id = :ws",
        "UPDATE feedback_entries SET workspace_id = NULL WHERE workspace_id = :ws",
        "DELETE FROM workspace_invites WHERE workspace_id = :ws",
        "DELETE FROM workspace_members WHERE workspace_id = :ws",
        "DELETE FROM workspaces WHERE id = :ws",
    )

    async def delete_workspace_cascade(
        self, workspace_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """워크스페이스 + 산하 데이터 전체 삭제. commit 은 caller 책임 (단일 트랜잭션).

        R2 객체는 여기서 지우지 않는다 — 트랜잭션 내 외부 IO 금지, r2-cleanup cron 위임.
        반환: 삭제 전 멤버 user_id 목록 (RBAC 캐시 즉시 무효화용).
        """
        member_user_ids = [
            m.user_id for m in await self.list_members(workspace_id)
        ]
        for stmt in self._CASCADE_DELETE_STATEMENTS:
            await self.session.exec(text(stmt).bindparams(ws=workspace_id))
        return member_user_ids

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

    async def list_members_with_users(
        self, workspace_id: uuid.UUID
    ) -> list[tuple[WorkspaceMember, "User | None"]]:
        """멤버 + User 단일 JOIN — list_members 의 멤버당 find_by_id N+1 제거.

        이 쿼리는 header(전 페이지) + useSyncWorkspaceRole 이 호출하는 hot path.
        """
        from src.auth.models import User

        rows = (await self.session.exec(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id, isouter=True)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )).all()
        return list(rows)

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
                INSERT INTO workspace_members
                    (id, workspace_id, user_id, role, default_project_visibility)
                VALUES (:id, :workspace_id, :user_id, :role, :default_project_visibility)
                ON CONFLICT (workspace_id, user_id) DO NOTHING
                RETURNING id
                """
            ).bindparams(
                id=member.id,
                workspace_id=member.workspace_id,
                user_id=member.user_id,
                role=member.role,
                default_project_visibility=member.default_project_visibility,
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

    async def delete_project_members_for_user(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """CAND-B fix — 워크스페이스 제거 시 해당 유저의 ProjectMember 잔재 정리.

        project_members 테이블은 projects 도메인 소유이므로 모델 import 없이
        workspace_id + user_id 로 스코프된 raw DELETE 로 잔재를 제거한다.
        gate(visibility filter)에 workspace_members EXISTS 가드가 있어 보안은
        이미 닫혀 있지만, 잔재 행 자체를 남기지 않아 불변식(제거 시 ProjectMember 도
        revoke)을 충족한다.
        """
        await self.session.exec(
            text(
                """
                DELETE FROM project_members
                WHERE workspace_id = :workspace_id AND user_id = :user_id
                """
            ).bindparams(workspace_id=workspace_id, user_id=user_id)
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
