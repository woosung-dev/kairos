# backend/src/workspaces/service.py
"""Workspace 서비스 — AsyncSession import 금지."""
import uuid

from src.auth.repository import UserRepository
from src.common.exceptions import NotFoundError
from src.projects.models import Project
from src.projects.repository import ProjectRepository
from src.workspaces.exceptions import MemberAlreadyExistsError, WorkspaceNotFoundError
from src.workspaces.models import Workspace, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository
from src.workspaces.templates import DEFAULT_TEMPLATE_PROJECTS


class WorkspaceService:
    def __init__(
        self,
        repo: WorkspaceRepository,
        user_repo: UserRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self.repo = repo
        self.user_repo = user_repo
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

        # 동일 session을 공유하므로 repo 한 곳에서만 commit
        await self.repo.commit()

        return {
            "id": str(workspace.id),
            "name": workspace.name,
            "ownerId": str(workspace.owner_id),
            "createdAt": workspace.created_at.isoformat(),
            "updatedAt": workspace.updated_at.isoformat(),
        }

    async def list_workspaces(self, user_id: uuid.UUID) -> list[dict]:
        """사용자가 속한 워크스페이스 목록."""
        workspaces = await self.repo.find_by_user(user_id)
        return [
            {
                "id": str(ws.id),
                "name": ws.name,
                "ownerId": str(ws.owner_id),
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

    async def add_member(
        self, workspace_id: uuid.UUID, email: str
    ) -> dict:
        """이메일로 사용자 찾아서 워크스페이스에 멤버로 추가."""
        # 워크스페이스 존재 확인
        workspace = await self.repo.find_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError()

        # 이메일로 사용자 조회
        user = await self.user_repo.find_by_email(email)
        if user is None:
            raise NotFoundError("해당 이메일의 사용자")

        # 이미 멤버인지 확인
        existing = await self.repo.find_member(workspace_id, user.id)
        if existing is not None:
            raise MemberAlreadyExistsError()

        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role="member",
        )
        member = await self.repo.add_member(member)
        await self.repo.commit()

        return {
            "id": str(member.id),
            "userId": str(member.user_id),
            "role": member.role,
        }
