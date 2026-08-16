# apps/api/src/workspaces/service.py
"""Workspace 서비스 — AsyncSession import 금지."""
import uuid

from src.projects.models import Project
from src.projects.repository import ProjectRepository
from src.workspaces.exceptions import WorkspaceNotFoundError
from src.workspaces.models import Workspace, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository
from src.workspaces.templates import DEFAULT_TEMPLATE_PROJECTS


class WorkspaceService:
    def __init__(
        self,
        repo: WorkspaceRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self.repo = repo
        self.project_repo = project_repo

    async def create_workspace(
        self, name: str, owner_id: uuid.UUID
    ) -> dict:
        """워크스페이스 생성. owner 멤버 + 기본 템플릿 프로젝트를 자동 시딩."""
        workspace = Workspace(name=name, owner_id=owner_id)
        workspace = await self.repo.save(workspace)

        # owner를 멤버로 자동 추가
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner_id,
            role="owner",
        )
        await self.repo.add_member(member)

        # 빈 화면 마찰 제거 — 기본 템플릿 프로젝트 시딩
        for template in DEFAULT_TEMPLATE_PROJECTS:
            project = Project(
                workspace_id=workspace.id,
                title=template.title,
                description=template.description,
                tags=list(template.tags),
                sort_order=template.sort_order,
                created_by_id=owner_id,
            )
            await self.project_repo.save(project)

        # Sprint 22 OBN-02: team workspace 생성 시 onboarding step=1 (same transaction).
        # repo.session 으로 호출자의 AsyncSession 재사용 — commit 이전 위치 (UPDATE rollback 방지).
        # graceful: hook 실패 시도 workspace 생성 흐름 보존 (CI E2E fail 학습).
        try:
            from src.onboarding.service import OnboardingService
            onboarding = OnboardingService(self.repo.session)
            await onboarding.increment_step(workspace.owner_id, 1)
        except Exception as ob_err:
            import logging
            logging.getLogger(__name__).warning(
                "onboarding step=1 advance 실패 (비치명적, team workspace): %s", ob_err
            )

        # 동일 session을 공유하므로 repo 한 곳에서만 commit
        await self.repo.commit()

        return {
            "id": str(workspace.id),
            "name": workspace.name,
            "ownerId": str(workspace.owner_id),
            "type": getattr(workspace, "type", "team"),
            "createdAt": workspace.created_at.isoformat(),
            "updatedAt": workspace.updated_at.isoformat(),
        }

    async def list_workspaces(self, user_id: uuid.UUID) -> list[dict]:
        """사용자가 속한 워크스페이스 목록 (Sprint 15: type 필드 포함 — Promote modal에서 team 필터)."""
        workspaces = await self.repo.find_by_user(user_id)
        return [
            {
                "id": str(ws.id),
                "name": ws.name,
                "ownerId": str(ws.owner_id),
                "type": getattr(ws, "type", "team"),
                "createdAt": ws.created_at.isoformat(),
                "updatedAt": ws.updated_at.isoformat(),
            }
            for ws in workspaces
        ]

    async def get_workspace(self, workspace_id: uuid.UUID) -> dict:
        """워크스페이스 상세 (memberCount 포함)."""
        workspace = await self.repo.find_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError()
        member_count = await self.repo.get_member_count(workspace_id)
        return {
            "id": str(workspace.id),
            "name": workspace.name,
            "ownerId": str(workspace.owner_id),
            "type": getattr(workspace, "type", "team"),
            "memberCount": member_count,
            "inboxThreshold": workspace.inbox_threshold,
            "createdAt": workspace.created_at.isoformat(),
            "updatedAt": workspace.updated_at.isoformat(),
        }

    async def update_settings(
        self, workspace_id: uuid.UUID, inbox_threshold: float
    ) -> dict:
        """워크스페이스 설정 업데이트 (임계값 등)."""
        workspace = await self.repo.find_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError()
        await self.repo.update_threshold(workspace_id, inbox_threshold)
        await self.repo.commit()
        return {"inboxThreshold": inbox_threshold}

    async def delete_workspace(self, workspace_id: uuid.UUID) -> None:
        """워크스페이스 삭제 (owner 전용은 라우터 require_owner 가 강제).

        I-19: personal 은 lazy seed 무결성 보호를 위해 삭제 금지.
        cascade 는 단일 트랜잭션 — 실패 시 전체 롤백.
        """
        workspace = await self.repo.find_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError()
        if getattr(workspace, "type", "team") == "personal":
            from src.workspaces.exceptions import PersonalWorkspaceProtected
            raise PersonalWorkspaceProtected("워크스페이스 삭제")

        member_user_ids = await self.repo.delete_workspace_cascade(workspace_id)
        await self.repo.commit()

        # 삭제된 워크스페이스의 RBAC 캐시 즉시 무효화 (60s TTL 지연 회피)
        from src.auth.rbac import invalidate_member_cache
        for user_id in member_user_ids:
            invalidate_member_cache(workspace_id, user_id)
