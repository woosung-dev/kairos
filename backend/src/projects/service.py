# backend/src/projects/service.py
"""Project 서비스 — AsyncSession import 금지. 단일 도메인 CRUD + cross-workspace 가드.

Sprint 19 PR #1 C9 (Codex F-1/F-2/F-3/F-4/F-6):
- 모든 mutation/find 메서드가 workspace_id 명시 수령
- secondary FK (meeting_id) cross-workspace 거부 → fail-closed RuntimeError
- cross-tenant resource → 404 lock-in (silent return 금지)
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from src.projects.exceptions import (
    CrossWorkspaceMemberError,
    ProjectNotFoundError,
    WorkspaceMismatchError,
)
from src.projects.models import Project
from src.projects.repository import ProjectRepository
from src.workspaces.exceptions import PersonalWorkspaceProtected
from src.workspaces.repository import WorkspaceRepository

if TYPE_CHECKING:
    from src.meetings.repository import MeetingRepository


class ProjectService:
    def __init__(
        self,
        repo: ProjectRepository,
        ws_repo: WorkspaceRepository,
        meeting_repo: "MeetingRepository | None" = None,
    ) -> None:
        self.repo = repo
        self.ws_repo = ws_repo
        self.meeting_repo = meeting_repo

    async def _verify_secondary_fks(
        self,
        workspace_id: uuid.UUID,
        meeting_id: uuid.UUID | None = None,
    ) -> None:
        """Codex F-2/F-6: secondary FK cross-workspace 거부.

        fail-closed (Codex 2차 Minor 1): repo 미주입 시 RuntimeError (silent skip 금지).
        """
        if meeting_id is not None:
            if self.meeting_repo is None:
                raise RuntimeError("meeting_repo 필수 (F-2 검증)")
            meeting = await self.meeting_repo.find_by_id(meeting_id, workspace_id)
            if meeting is None:
                # cross-tenant meeting → 404 (F-4 lock-in)
                from src.meetings.exceptions import MeetingNotFoundError

                raise MeetingNotFoundError()

    async def create_project(
        self,
        workspace_id: uuid.UUID,
        title: str,
        created_by_id: uuid.UUID,
        description: str | None = None,
        visibility: str = "public",
        tags: list[str] | None = None,
    ) -> dict:
        """프로젝트 생성."""
        project = Project(
            workspace_id=workspace_id,
            title=title,
            created_by_id=created_by_id,
            description=description,
            visibility=visibility,
            tags=tags or [],
        )
        project = await self.repo.save(project)

        # Sprint 22 OBN-02: 첫 프로젝트 생성 시 onboarding step=2 (same transaction).
        # commit 이전 위치 — UPDATE rollback 방지.
        # graceful: hook 실패 시도 project 생성 흐름 보존 (CI E2E fail 학습).
        try:
            from src.onboarding.service import OnboardingService
            onboarding = OnboardingService(self.repo.session)
            await onboarding.increment_step(created_by_id, 2)
        except Exception as ob_err:
            import logging
            logging.getLogger(__name__).warning(
                "onboarding step=2 advance 실패 (비치명적): %s", ob_err
            )

        await self.repo.commit()
        return self._to_dict(project)

    async def list_projects(
        self,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """워크스페이스 프로젝트 목록 (페이지네이션 + visibility 권한 분기)."""
        offset = (page - 1) * page_size
        projects = await self.repo.find_by_workspace(
            workspace_id,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
            status=status,
            tag=tag,
            offset=offset,
            limit=page_size,
        )
        total = await self.repo.count_by_workspace(
            workspace_id,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
            status=status,
        )

        return {
            "items": [self._to_dict(p) for p in projects],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasNext": page * page_size < total,
        }

    async def get_project(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> dict:
        """프로젝트 상세 (Codex F-1/F-4: tenant 검증 1차 + visibility 검증 2차)."""
        # Codex F-1: tenant 검증 (find_by_id가 workspace_id WHERE)
        project = await self.repo.find_by_id(project_id, workspace_id)
        if project is None:
            # Codex F-4: cross-tenant resource → 404 (정보 누설 방지)
            raise ProjectNotFoundError()
        # visibility 권한 검증 (admin 이상 우회, 그 외 visibility별 분기)
        if requester_role not in ("admin", "owner"):
            if project.visibility == "draft":
                if project.created_by_id != requester_user_id:
                    raise ProjectNotFoundError()
            elif project.visibility == "private":
                if requester_user_id is None or not await self.repo.is_member(
                    project_id, requester_user_id, workspace_id
                ):
                    raise ProjectNotFoundError()
        return self._to_dict(project)

    # --- ProjectMember (Sprint 6 L-6, Sprint 19 PR #1 C9 workspace_id 강제) ---

    async def list_members(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[dict]:
        """프로젝트 멤버 목록 (Codex F-1: tenant 사전 검증)."""
        project = await self.repo.find_by_id(project_id, workspace_id)
        if project is None:
            raise ProjectNotFoundError()
        members = await self.repo.find_members(project_id, workspace_id)
        return [
            {
                "id": str(m.id),
                "projectId": str(m.project_id),
                "userId": str(m.user_id),
                "role": m.role,
                "createdAt": m.created_at.isoformat(),
            }
            for m in members
        ]

    async def add_member(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
    ) -> dict:
        """프로젝트 멤버 추가. cross-workspace 검증 포함.

        검증 순서 (변경 금지):
          1. project 없음 또는 cross-tenant → ProjectNotFoundError(404, Codex F-4)
          2. personal workspace → PersonalWorkspaceProtected
          3. WorkspaceMember(workspace_id, user_id) 없음 → CrossWorkspaceMemberError(403)
          4. 중복 → repo.add_member (UniqueConstraint 위반 시 DB 레벨 처리)
        """
        project = await self.repo.find_by_id(project_id, workspace_id)
        if project is None:
            raise ProjectNotFoundError()
        # Sprint 15 ADR-016 AD-43: personal workspace는 ProjectMember 추가 불가
        ws = await self.ws_repo.find_by_id(workspace_id)
        if ws is not None and getattr(ws, "type", "team") == "personal":
            raise PersonalWorkspaceProtected("프로젝트 멤버 추가")
        ws_member = await self.ws_repo.find_member(workspace_id, user_id)
        if ws_member is None:
            raise CrossWorkspaceMemberError()
        member = await self.repo.add_member(project_id, project.workspace_id, user_id, role)
        await self.repo.commit()
        return {
            "id": str(member.id),
            "projectId": str(member.project_id),
            "userId": str(member.user_id),
            "role": member.role,
            "createdAt": member.created_at.isoformat(),
        }

    async def remove_member(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """프로젝트 멤버 제거 (Codex F-1: tenant 사전 검증)."""
        project = await self.repo.find_by_id(project_id, workspace_id)
        if project is None:
            raise ProjectNotFoundError()
        await self.repo.remove_member(project_id, user_id, workspace_id)
        await self.repo.commit()

    async def update_project(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        visibility: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """프로젝트 수정 (Codex F-1)."""
        project = await self.repo.find_by_id(project_id, workspace_id)
        if project is None:
            raise ProjectNotFoundError()

        if title is not None:
            project.title = title
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status
        if visibility is not None:
            project.visibility = visibility
        if tags is not None:
            project.tags = tags

        project.updated_at = datetime.utcnow()
        project = await self.repo.save(project)
        await self.repo.commit()
        return self._to_dict(project)

    async def delete_project(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> None:
        """프로젝트 삭제 (Codex F-1/F-4)."""
        project = await self.repo.find_by_id(project_id, workspace_id)
        if project is None:
            raise ProjectNotFoundError()
        await self.repo.delete(project)
        await self.repo.commit()

    async def archive_project(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> dict:
        """프로젝트 아카이브 (status → archived)."""
        return await self.update_project(workspace_id, project_id, status="archived")

    async def add_meeting_project(
        self,
        workspace_id: uuid.UUID,
        meeting_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> dict:
        """회의-프로젝트 연결 (Codex F-1/F-2/F-3: meeting + project 둘 다 tenant 검증)."""
        # F-2 secondary FK: meeting tenant 검증 (fail-closed)
        await self._verify_secondary_fks(workspace_id, meeting_id=meeting_id)
        # F-1/F-3: project tenant 검증 (repo.add_meeting_link 안에서도 한 번 더)
        link = await self.repo.add_meeting_link(meeting_id, project_id, workspace_id)
        await self.repo.commit()
        return {
            "id": str(link.id),
            "meetingId": str(link.meeting_id),
            "projectId": str(link.project_id),
        }

    async def remove_meeting_project(
        self,
        workspace_id: uuid.UUID,
        meeting_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        """회의-프로젝트 연결 해제 (Codex F-1/F-2/F-3)."""
        await self._verify_secondary_fks(workspace_id, meeting_id=meeting_id)
        await self.repo.remove_meeting_link(meeting_id, project_id, workspace_id)
        await self.repo.commit()

    async def get_meeting_projects(
        self, workspace_id: uuid.UUID, meeting_id: uuid.UUID
    ) -> list[dict]:
        """회의에 연결된 프로젝트 목록 (Codex F-1/F-2)."""
        await self._verify_secondary_fks(workspace_id, meeting_id=meeting_id)
        projects = await self.repo.find_projects_by_meeting(meeting_id, workspace_id)
        return [self._to_dict(p) for p in projects]

    @staticmethod
    def _to_dict(project: Project) -> dict:
        """Project → camelCase dict 변환."""
        return {
            "id": str(project.id),
            "workspaceId": str(project.workspace_id),
            "title": project.title,
            "description": project.description,
            "status": project.status,
            "visibility": project.visibility,
            "tags": project.tags,
            "sortOrder": project.sort_order,
            "createdById": str(project.created_by_id),
            "createdAt": project.created_at.isoformat(),
            "updatedAt": project.updated_at.isoformat(),
        }
